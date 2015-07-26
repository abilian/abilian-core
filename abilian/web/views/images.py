# coding=utf-8
"""
Blueprint for views of dynamic images
"""
from __future__ import absolute_import, print_function, division

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import colorsys

import sqlalchemy as sa
import pkg_resources

from flask import Blueprint, request, make_response, render_template
from werkzeug.exceptions import BadRequest, NotFound
from abilian.core.util import utc_dt
from abilian.core.models.blob import Blob
from abilian.core.models.subjects import User
from abilian.web.util import url_for

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
                            request.args.get(self.expire_vary_arg))
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
    from abilian.services.image import crop_and_resize, get_format

    try:
      fmt = get_format(image)
    except IOError:
      #  not a known image file
      raise NotFound()

    content_type = u'image/png' if fmt == 'PNG' else u'image/jpeg'

    if size:
      image = crop_and_resize(image, size)
    else:
      image = image.read()

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

  def __init__(self, image, *args, **kwargs):
    """
    :param image: path to image file
    """
    BaseImageView.__init__(self, *args, **kwargs)
    self.image_path = Path(image)
    if not self.image_path.exists():
      p = unicode(self.image_path)
      raise ValueError('Invalid image path: {}'.format(repr(p)))

  def prepare_args(self, args, kwargs):
    kwargs['image'] = self.image_path.open('rb')
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
    if not blob:
      raise NotFound()

    kwargs['image'] = blob.file.open('rb')
    return args, kwargs


blob_image = BlobView.as_view('blob_image')
route("/files/<int:object_id>")(blob_image)


class UserMugshot(BaseImageView):
  expire_vary_arg = 'md5'

  def prepare_args(self, args, kwargs):
    args, kwargs = BaseImageView.prepare_args(self, args, kwargs)

    user_id = kwargs['user_id']
    user = User.query\
        .options(sa.orm.undefer(User.photo))\
        .get(user_id)

    if user is None:
      raise NotFound()

    kwargs['user'] = user
    kwargs['image'] = user.photo
    return args, kwargs

  def get(self, user, image, size, *args, **kwargs):
    if image:
      #  user has set a photo
      return super(UserMugshot, self).get(image, size, *args, **kwargs)

    # render svg avatar
    if user.last_name:
      letter = user.last_name[0]
    elif user.first_name:
      letter = user.first_name[0]
    else:
      letter = u"?"
    letter = letter.upper()
    # generate bg color, pastel: sat=65% in hsl color space
    id_hash = hash((user.name + user.email).encode('utf-8'))
    hue = id_hash % 10
    hue = (hue * 36) / 360.0  # 10 colors: 360 / 10
    color = colorsys.hsv_to_rgb(hue, 0.65, 1.0)
    color = [int(x * 255) for x in color]
    color = u'rgb({0[0]}, {0[1]}, {0[2]})'.format(color)
    svg = render_template('default/avatar.svg',
                          color=color, letter=letter, size=size)
    response = make_response(svg)
    response.headers['content-type'] = u'image/svg+xml'
    self.set_cache_headers(response)
    return response


user_photo = UserMugshot.as_view('user_photo', set_expire=True, max_size=500)
route("/users/<int:user_id>")(user_photo)
route('/users/default')(StaticImageView.as_view('user_default',
                                                set_expire=True,
                                                image=DEFAULT_AVATAR,))


def user_url_args(user, size):
  endpoint = 'images.user_default'
  kwargs = {'s': size,
            'md5': DEFAULT_AVATAR_MD5,}

  if not user.is_anonymous():
    endpoint = 'images.user_photo'
    kwargs['user_id'] = user.id
    content = (user.photo if user.photo
               else (user.name + user.email).encode('utf-8'))
    kwargs['md5'] = hashlib.md5(content).hexdigest()

  return endpoint, kwargs


def user_photo_url(user, size):
  """
  Return url to use for this user
  """
  endpoint, kwargs = user_url_args(user, size)
  return url_for(endpoint, **kwargs)
