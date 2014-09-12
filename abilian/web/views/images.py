# coding=utf-8
"""
Blueprint for views of dynamic images
"""
from __future__ import absolute_import

from flask import Blueprint, request, abort, make_response
from abilian.core.models.subjects import User, Group
from abilian.services.image import crop_and_resize

blueprint = Blueprint('images', __name__, url_prefix='/images')
route = blueprint.route

import pkg_resources

DEFAULT_AVATAR = pkg_resources.resource_filename('abilian.web', 'resources/img/avatar-default.png')

def get_default_picture(type):
  path = join(dirname(__file__), "..", "..", "static", "images", "user-%s.png" % type)
  photo = open(path).read()
  return photo


@route("/users/<int:user_id>/mugshot")
def user_avatar(user_id):
  try:
    size = int(request.args.get('s', 0))
  except:
    abort(400)

  if size > 500:
    raise Exception("Error, size = %d" % size)

  subject = User.query.get(user_id)
  if subject is None:
    abort(404)

  photo = subject.photo
  if not photo:
    photo = open(DEFAULT_AVATAR, 'rb').read()

  if size:
    photo = crop_and_resize(photo, size)

  response = make_response(photo)
  response.headers['content-type'] = 'image/jpeg'
  return response
