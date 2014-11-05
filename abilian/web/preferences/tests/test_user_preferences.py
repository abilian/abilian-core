# coding=utf-8
"""
"""
from __future__ import absolute_import

from pathlib import Path
import imghdr
from flask import url_for, request

from abilian.testing import BaseTestCase
from abilian.core.models.subjects import User
from abilian.web.preferences.user import UserPreferencesForm


AVATAR_COLORMAP = Path(__file__).parent / u'avatar-colormap.png'


class TestUserPreferences(BaseTestCase):

  def setUp(self):
    BaseTestCase.setUp(self)
    self.user = User(
      email=u'john@example.com',
      first_name=u'John', last_name=u'Doe', can_login=True)
    self.session.add(self.user)
    self.session.commit()

  def test_form_photo(self):
    url = url_for('preferences.user')
    photo = (AVATAR_COLORMAP.open('rb'), u'avatar.png', 'image/png')
    kwargs = dict(
        method='POST',
        data={'photo': photo,},
      )
    with self.app.test_request_context(url, **kwargs) as req:
      form = UserPreferencesForm(request.form)
      form.validate()
      assert form.photo.data is not None
      img_type = imghdr.what('ignored', form.photo.data)
      assert img_type == 'jpeg'
