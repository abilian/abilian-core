# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import imghdr

from flask import request, url_for
from pathlib import Path

from abilian.core.models.subjects import User
from abilian.testing import BaseTestCase
from abilian.web.preferences.user import UserPreferencesForm

AVATAR_COLORMAP = Path(__file__).parent / u'avatar-colormap.png'


class TestUserPreferences(BaseTestCase):
    SERVICES = ('security',)

    def setUp(self):
        BaseTestCase.setUp(self)
        self.user = User(email=u'john@example.com',
                         first_name=u'John',
                         last_name=u'Doe',
                         can_login=True)
        self.session.add(self.user)
        self.session.commit()

    def test_form_photo(self):
        url = url_for('preferences.user')
        uploads = self.app.extensions['uploads']
        with AVATAR_COLORMAP.open('rb') as f:
            handle = uploads.add_file(self.user,
                                      f,
                                      filename=u'avatar.png',
                                      mimetype='image/png')

        kwargs = dict(method='POST', data={'photo': handle,},)

        with self.app.test_request_context(url, **kwargs):
            self.login(self.user)
            form = UserPreferencesForm(request.form)
            form.validate()
            assert form.photo.data is not None
            img_type = imghdr.what('ignored', form.photo.data)
            assert img_type == 'jpeg'
