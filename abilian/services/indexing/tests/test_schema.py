# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask_login import AnonymousUserMixin

from abilian.services.indexing.schema import indexable_role
from abilian.services.security.models import Anonymous, Reader


def test_indexable_role():
    assert indexable_role(Anonymous) == "role:anonymous"
    assert indexable_role(AnonymousUserMixin()) == "role:anonymous"
    assert indexable_role(Reader) == "role:reader"
