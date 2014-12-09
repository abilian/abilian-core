# coding=utf-8
"""
Blueprint for views of dynamic images
"""
from __future__ import absolute_import

import hashlib

import sqlalchemy as sa
import pkg_resources
from flask import Blueprint, request, make_response, g, Response
from werkzeug.exceptions import BadRequest, NotFound
from abilian.core.models.subjects import User
from abilian.services.image import crop_and_resize


blueprint = Blueprint('images', __name__, url_prefix='/images')
route = blueprint.route

DEFAULT_AVATAR = pkg_resources.resource_filename('abilian.web',
                                                 'resources/img/avatar-default.png')


@route("/users/<int:user_id>/mugshot")
def user_avatar(user_id):
  try:
    size = int(request.args.get('s', 0))
  except:
    raise BadRequest()

  if size > 500:
    raise Exception("Error, size = %d" % size)

  user = User.query\
    .options(sa.orm.undefer(User.photo))\
    .get(user_id)

  if user is None:
    raise NotFound()

  is_self = user.id == g.user.id

  photo = user.photo
  if not photo:
    photo = open(DEFAULT_AVATAR, 'rb').read()

  etag = None

  if is_self:
    # FIXME: there should be a photo_digest field on user object
    acc = hashlib.md5(photo)
    etag = acc.hexdigest()

    if request.if_none_match and etag in request.if_none_match:
      return Response(status=304)

  if size:
    photo = crop_and_resize(photo, size)

  response = make_response(photo)
  response.headers['content-type'] = 'image/jpeg'
  if not is_self:
    response.headers.add('Cache-Control', 'public, max-age=600')
  else:
    # current user's photo. It *must* be revalidated, so that it changes
    # immediately after upload of a new one.
    response.headers.add('Cache-Control', 'private, must-revalidate')
    response.set_etag(etag)

  return response
