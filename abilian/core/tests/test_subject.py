# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from abilian.core.models.subjects import User


def test_non_ascii_password():
    """Ensure we can store and test non-ascii password without
    any UnicodeEncodeError.
    """
    user = User()

    user.set_password(u'Hé')

    if not isinstance(user.password, unicode):
        # when actually retrieved from database, it should be unicode
        user.password = unicode(user.password)

    assert user.authenticate(u'Hé')
