# coding=utf-8
"""
Blueprint for views of dynamic images
"""
from __future__ import absolute_import

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

import sqlalchemy as sa
import pkg_resources
from flask import Blueprint, request, make_response, g, Response
from werkzeug.exceptions import BadRequest, NotFound
from abilian.core.util import utc_dt
from abilian.core.models.blob import Blob
from abilian.core.models.subjects import User
from abilian.services.image import crop_and_resize, get_format

from .base import View

blueprint = Blueprint('images', __name__, url_prefix='/images')
route = blueprint.route

DEFAULT_AVATAR = Path(
    pkg_resources.resource_filename(
        'abilian.web',
        'resources/img/avatar-default.png')
)

DEFAULT_AVATAR_MD5 = hashlib.md5(DEFAULT_AVATAR.open('rb').read()).hexdigest()


class BaseImageView(View):
  """
  """
  max_size = None
  set_expire = False
  expire_offset = timedelta(days=365)

  #: argument name that must be found in view kwargs. This is a safety measure
  #: to prevent setting far expire date on resources without a varying argument
  #: in url (path or query string), such as a timestamp, a serial, a hash...
  expire_vary_arg = None

  def __init__(self, max_size=None, set_expire=None, expire_offset=None,
               expire_vary_arg=None):
    # override class default value only if arg is specified in constructor. This
    # allows subclasses to easily override theses defaults.
    if max_size is not None:
      self.max_size = max_size
    if set_expire is not None:
      self.set_expire = set_expire
    if expire_offset is not None:
      self.expire_offset = expire_offset
    if expire_vary_arg is not None:
      self.expire_vary_arg = expire_vary_arg

    if self.set_expire:
      if not self.expire_offset:
        raise ValueError('expire_offset is not set')
      if not self.expire_vary_arg:
        raise ValueError('expire_vary_arg is not set')

  def prepare_args(self, args, kwargs):
    if self.set_expire:
      vary_arg = kwargs.get(self.expire_vary_arg,
                            request.args.get(self.expire_vary_arg, None))
      if vary_arg is None:
        # argument for timestamp, serial etc is missing. We must refuse to serve
        # an image with expiry date set up to maybe 1 year from now.
        # Check the code that has generated this url!
        raise BadRequest(
          'Image version marker is missing ({}=?)'.format(
            repr(self.expire_vary_arg))
        )

    args, kwargs = View.prepare_args(self, args, kwargs)
    size = request.args.get('s', 0)
    try:
      size = int(size)
    except ValueError:
      raise BadRequest(
        'Invalid value for "s": {}. Not an integer.'.format(repr(size))
      )

    if self.max_size is not None:
      if size > self.max_size:
        raise BadRequest(
          'Size too large: {:d} (max: {:d})'.format(size, self.max_size)
        )

    kwargs['size'] = size
    return args, kwargs

  def get(self, image, size, *args, **kwargs):
    """
    :param image: image as bytes
    :param s: requested maximum width/height size
    """
    fmt = get_format(image)
    content_type = u'image/png' if fmt == 'PNG' else u'image/jpeg'

    if size:
      image = crop_and_resize(image, size)

    response = make_response(image)
    response.headers['content-type'] = content_type
    self.set_cache_headers(response)
    return response

  def set_cache_headers(self, response):
    """
    """
    if self.set_expire:
      response.cache_control.private = True
      response.cache_control.max_age = int(self.expire_offset.total_seconds())
      response.expires = utc_dt(datetime.utcnow() + self.expire_offset)


class StaticImageView(BaseImageView):
  """
  View for static assets not served by static directory.

  Useful for default avatars for example.
  """
  expire_vary_arg = 'md5'

  def __init__(self, image, md5, *args, **kwargs):
    """
    :param image: path to image file
    :param md5: md5 hexdigest of image file
    """
    BaseImageView.__init__(self, *args, **kwargs)
    self.image_path = Path(image)
    if not self.image_path.exists():
      p = unicode(self.image_path)
      raise ValueError('Invalid image path: {}'.format(repr(p)))

    self.md5 = md5

  def prepare_args(self, args, kwargs):
    kwargs['image'] = self.image_path.open('rb')
    kwargs[self.expire_vary_arg] = self.md5
    return BaseImageView.prepare_args(self, args, kwargs)


class BlobView(BaseImageView):
  """
  Default :attr:`expire_vary_arg` to `"md5"`.
  :attr:`set_expire` is set to `False` by default.
  """
  expire_vary_arg = 'md5'
  id_arg = 'object_id'

  def __init__(self, id_arg=None, *args, **kwargs):
    BaseImageView.__init__(self, *args, **kwargs)
    if id_arg is not None:
      self.id_arg = id_arg

  def prepare_args(self, args, kwargs):
    args, kwargs = BaseImageView.prepare_args(self, args, kwargs)
    b_id = kwargs.get(self.id_arg)
    try:
      b_id = int(b_id)
    except ValueError:
      raise BadRequest('Invalid image id: {}'.format(repr(b_id)))

    blob = Blob.query.get(b_id)
    if blob is None:
      raise NotFound()

    try:
      with blob.file.open('rb') as f:
        get_format(f)
    except IOError:
      # this blob is not a known image file
      raise NotFound()

    kwargs['image'] = blob.file.open('rb')
    return args, kwargs


blob_image = BlobView.as_view('blob_image')
route("/files/<int:object_id>")(blob_image)


class UserMugshot(BaseImageView):

  def prepare_args(self, args, kwargs):
    args, kwargs = BaseImageView.prepare_args(self, args, kwargs)

    user_id = kwargs['user_id']
    user = User.query\
      .options(sa.orm.undefer(User.photo))\
      .get(user_id)

    if user is None:
      raise NotFound()

    image = user.photo
    if not image:
      # FIXME: redirect to a unique url for default avatar
      image = DEFAULT_AVATAR.open('rb').read()

    kwargs['image'] = image
    self.is_self = user.id == g.user.id

    if self.is_self:
      self.etag = hashlib.md5(image).hexdigest()

    return args, kwargs

  def get(self, *args, **kwargs):
    if (self.is_self
        and request.if_none_match and
        self.etag in request.if_none_match):
      return Response(status=304)

    return BaseImageView.get(self, *args, **kwargs)

  def set_cache_headers(self, response):
    if not self.is_self:
      response.cache_control.max_age = 600
      response.cache_control.public = True
    else:
      # current user's photo. It *must* be revalidated, so that it changes
      # immediately after upload of a new one.
      response.cache_control.private = True
      response.cache_control.must_revalidate = True
      response.set_etag(self.etag)


user_avatar = UserMugshot.as_view('user_avatar', max_size=500)
route("/users/<int:user_id>/mugshot")(user_avatar)

route('/users/default')(StaticImageView.as_view('user_default',
                                                image=DEFAULT_AVATAR,
                                                md5=DEFAULT_AVATAR_MD5))
