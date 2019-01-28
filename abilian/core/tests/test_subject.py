# -*- coding: utf-8 -*-

from six import text_type

from abilian.core.models.subjects import User


def test_non_ascii_password():
    """Ensure we can store and test non-ascii password without any
    UnicodeEncodeError."""
    user = User()

    user.set_password("Hé")

    if not isinstance(user.password, str):
        # when actually retrieved from database, it should be Unicode
        user.password = str(user.password)

    assert user.authenticate("Hé")
