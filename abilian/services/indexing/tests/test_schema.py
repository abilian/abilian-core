# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from flask_login import AnonymousUserMixin
from abilian.services.security.models import Anonymous, Reader
from abilian.services.indexing.schema import indexable_role

def test_indexable_role():

  assert indexable_role(Anonymous) == u'role:anonymous'
  assert indexable_role(AnonymousUserMixin()) == u'role:anonymous'
  assert indexable_role(Reader) == u'role:reader'
