# -*- coding: utf-8 -*-
from unittest import TestCase
from abilian.core.models.subjects import User


class SubjectTestCase(TestCase):

  def test_non_ascii_password(self):
    """Ensure we can store and test non ascii password without
    any UnicodeEncodeError
    """
    user = User()

    try:
      user.set_password(u'Hé')
    except UnicodeEncodeError, e:
      self.fail(e)

    if not isinstance(user.password, unicode):
      # when actually retrivied from database, it should be unicode
      user.password = unicode(user.password)

    self.assertTrue(user.authenticate(u'Hé'))
