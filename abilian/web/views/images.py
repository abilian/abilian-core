# coding=utf-8
"""
Blueprint for views of dynamic images
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import colorsys
import hashlib

import pkg_resources
import sqlalchemy as sa
from flask import Blueprint, make_response, render_template, request
from pathlib import Path
from werkzeug.exceptions import BadRequest, NotFound

from abilian.core.models.blob import Blob
from abilian.core.models.subjects import User
from abilian.services.image import CROP, RESIZE_MODES, get_size
from abilian.web.util import url_for

from .files import BaseFileDownload

blueprint = Blueprint('images', __name__, url_prefix='/images')
route = blueprint.route

DEFAULT_AVATAR = Path(pkg_resources.resource_filename(
    'abilian.web', 'resources/img/avatar-default.png'))
DEFAULT_AVATAR_MD5 = hashlib.md5(DEFAULT_AVATAR.open('rb').read()).hexdigest()


class BaseImageView(BaseFileDownload):
    max_size = None

    def __init__(self, max_size=None, *args, **kwargs):
        super(BaseImageView, self).__init__(*args, **kwargs)
        # override class default value only if arg is specified in constructor. This
        # allows subclasses to easily override theses defaults.
        if max_size is not None:
            self.max_size = max_size

    def prepare_args(self, args, kwargs):
        args, kwargs = super(BaseImageView, self).prepare_args(args, kwargs)
        size = request.args.get('s', 0)
        try:
            size = int(size)
        except ValueError:
            raise BadRequest(
                'Invalid value for "s": {}. Not an integer.'.format(repr(size)))

        if self.max_size is not None:
            if size > self.max_size:
                raise BadRequest('Size too large: {:d} (max: {:d})'.format(
                    size, self.max_size))

        kwargs['size'] = size

        resize_mode = request.args.get('m', CROP)
        if resize_mode not in RESIZE_MODES:
            resize_mode = CROP

        kwargs['mode'] = resize_mode
        return args, kwargs

    def make_response(self, image, size, mode, *args, **kwargs):
        """
        :param image: image as bytes
        :param s: requested maximum width/height size
        """
        from abilian.services.image import resize, get_format

        try:
            fmt = get_format(image)
        except IOError:
            #  not a known image file
            raise NotFound()

        self.content_type = u'image/png' if fmt == 'PNG' else u'image/jpeg'
        ext = u'.' + unicode(fmt.lower())

        filename = kwargs.get('filename')
        if not filename:
            filename = u'image'
        if not filename.lower().endswith(ext):
            filename += ext
        self.filename = filename

        if size:
            image = resize(image, size, size, mode=mode)
            if mode == CROP:
                assert get_size(image) == (size, size)
        else:
            image = image.read()

        return make_response(image)

    def get_filename(self, *args, **kwargs):
        return self.filename

    def get_content_type(self, *args, **kwargs):
        return self.content_type


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
        kwargs['filename'] = self.image_path.name
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

        meta = blob.meta
        filename = meta.get('filename', meta.get('md5', unicode(blob.uuid)))
        kwargs['filename'] = filename
        kwargs['image'] = blob.file.open('rb')
        return args, kwargs


blob_image = BlobView.as_view(b'blob_image')
route("/files/<int:object_id>")(blob_image)


class UserMugshot(BaseImageView):
    expire_vary_arg = 'md5'

    def prepare_args(self, args, kwargs):
        args, kwargs = super(UserMugshot, self).prepare_args(args, kwargs)

        user_id = kwargs['user_id']
        user = User.query \
          .options(sa.orm.undefer(User.photo)) \
          .get(user_id)

        if user is None:
            raise NotFound()

        kwargs['user'] = user
        kwargs['image'] = user.photo
        return args, kwargs

    def make_response(self, user, image, size, *args, **kwargs):
        if image:
            #  user has set a photo
            return super(UserMugshot, self).make_response(image, size, *args,
                                                          **kwargs)

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
                              color=color,
                              letter=letter,
                              size=size)
        response = make_response(svg)
        self.content_type = u'image/svg+xml'
        self.filename = u'avatar-{}.svg'.format(id_hash)
        return response


user_photo = UserMugshot.as_view(b'user_photo', set_expire=True, max_size=500)
route("/users/<int:user_id>")(user_photo)
route('/users/default')(StaticImageView.as_view(b'user_default',
                                                set_expire=True,
                                                image=DEFAULT_AVATAR))


def user_url_args(user, size):
    endpoint = 'images.user_default'
    kwargs = {'s': size, 'md5': DEFAULT_AVATAR_MD5,}

    if not user.is_anonymous():
        endpoint = 'images.user_photo'
        kwargs['user_id'] = user.id
        content = (user.photo if user.photo else
                   (user.name + user.email).encode('utf-8'))
        kwargs['md5'] = hashlib.md5(content).hexdigest()

    return endpoint, kwargs


def user_photo_url(user, size):
    """Return url to use for this user.
    """
    endpoint, kwargs = user_url_args(user, size)
    return url_for(endpoint, **kwargs)
