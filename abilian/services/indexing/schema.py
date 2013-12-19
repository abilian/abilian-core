# coding=utf-8
"""
"""
from __future__ import absolute_import

from whoosh.analysis import (
    CharsetFilter, RegexTokenizer, LowercaseFilter,
    PathTokenizer,
    )

from whoosh.support.charset import accent_map
from whoosh.formats import Existence
from whoosh.fields import (
    SchemaClass, FieldType,
    ID, KEYWORD, DATETIME, TEXT, NUMERIC
    )

from abilian.services.security.models import Role, Anonymous
from abilian.core.util import noproxy
from abilian.core.subjects import User, Group

#: A Whoosh analyzer that folds accents and case.
accent_folder = RegexTokenizer() | LowercaseFilter() | CharsetFilter(accent_map)

class DefaultSearchSchema(SchemaClass):
  """
  General search schema
  """
  object_key = ID(stored=True, unique=True)
  id = NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=False)
  object_type = ID(stored=True, unique=False)
  created_at = DATETIME(stored=True, sortable=True)
  updated_at = DATETIME(stored=True, sortable=True)
  creator = ID(stored=True)
  owner = ID(stored=True)

  #: security index. This list roles and user/group ids allowed to *see* this
  #: content
  allowed_roles_and_users = KEYWORD(stored=True)

  # hierarchical index of ids path ('/' is the separator)
  parent_ids = FieldType(format=Existence(), analyzer=PathTokenizer(),
                         stored=True, unique=False)

  name = TEXT(stored=True, analyzer=accent_folder)
  description = TEXT(stored=True, analyzer=accent_folder)
  text = TEXT(stored=False, analyzer=accent_folder)

def indexable_role(principal):
  """
  Returns a string suitable for query against `allowed_roles_and_users`
  field.

  :param principal: It can be :data:`Anonymous`, :data:`Authenticated`,
      or an instance of :class:`User` or :class:`Group`.
  """
  principal = noproxy(principal)

  if (principal is Anonymous
      or (hasattr(principal, 'is_anonymous') and principal.is_anonymous())):
    return u'role:anonymous'
  elif isinstance(principal, Role):
    return u'role:{}'.format(unicode(principal))
  elif isinstance(principal, User):
    fmt = u'user:{:d}'
  elif isinstance(principal, Group):
    fmt = u'group:{:d}'
  else:
    raise ValueError(repr(principal))

  return fmt.format(principal.id)
