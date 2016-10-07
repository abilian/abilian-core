# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import hashlib

from flask import Blueprint, Response, g, make_response, request
from sqlalchemy.sql.expression import func, or_
from werkzeug.exceptions import NotFound

from abilian.core.models.subjects import User
from abilian.web import url_for
from abilian.web.views import JSONModelSearch

bp = Blueprint('users', __name__, url_prefix='/users')


@bp.url_value_preprocessor
def get_user(endpoint, values):
    try:
        user_id = values.pop('user_id')
        user = User.query.get(user_id)
        if user:
            values['user'] = user
        else:
            raise NotFound()
    except KeyError:
        # this endpoint is not looking for a specific user
        pass


@bp.route('/<int:user_id>/photo')
def photo(user):
    if not user.photo:
        raise NotFound()

    data = user.photo
    self_photo = (user.id == g.user.id)

    if self_photo:
        # special case: for its own photo user has an etag, so that on change photo
        # is immediatly reloaded from server.
        #
        # FIXME: there should be a photo_digest field on user object
        acc = hashlib.md5(data)
        etag = acc.hexdigest()

        if request.if_none_match and etag in request.if_none_match:
            return Response(status=304)

    r = make_response(data)
    r.headers['content-type'] = 'image/jpeg'

    if not self_photo:
        r.headers.add('Cache-Control', 'public, max-age=600')
    else:
        # user always checks its own mugshot is up-to-date, in order to avoid seeing
        # old one immediatly after having uploaded of a new picture.
        r.headers.add('Cache-Control', 'private, must-revalidate')
        r.set_etag(etag)

    return r


# JSON search
class UserJsonListing(JSONModelSearch):

    Model = User
    minimum_input_length = 0

    def filter(self, query, q, **kwargs):
        if q:
            query = query.filter(
                or_(
                    func.lower(User.first_name).like(q + "%"),
                    func.lower(User.last_name).like(q + "%")))
        return query

    def order_by(self, query):
        return query.order_by(
            func.lower(User.last_name), func.lower(User.first_name))

    def get_item(self, obj):
        d = super(UserJsonListing, self).get_item(obj)
        d['email'] = obj.email
        d['can_login'] = obj.can_login
        d['photo'] = url_for('users.photo', user_id=obj.id)
        return d


bp.route('/json/')(UserJsonListing.as_view('json_list'))
