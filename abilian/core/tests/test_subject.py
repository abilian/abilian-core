# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from six import text_type

from abilian.core.models.subjects import User


def test_non_ascii_password():
    """Ensure we can store and test non-ascii password without
    any UnicodeEncodeError.
    """
    user = User()

    user.set_password(u'Hé')

    if not isinstance(user.password, text_type):
        # when actually retrieved from database, it should be unicode
        user.password = text_type(user.password)

    assert user.authenticate(u'Hé')
