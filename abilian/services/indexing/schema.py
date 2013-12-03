# coding=utf-8
"""
"""
from __future__ import absolute_import

from whoosh.analysis import CharsetFilter, RegexTokenizer, LowercaseFilter
from whoosh.support.charset import accent_map
from whoosh.fields import (
    SchemaClass,
    ID, DATETIME, TEXT, NUMERIC
    )

#: A Whoosh analyzer that folds accents and case.
accent_folder = RegexTokenizer() | LowercaseFilter() | CharsetFilter(accent_map)

class DefaultSearchSchema(SchemaClass):
  """
  General search schema
  """
  id = NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True)
  object_type = ID(stored=True, unique=False)
  created_at = DATETIME(stored=True, sortable=True)
  updated_at = DATETIME(stored=True, sortable=True)
  creator = ID(stored=True)
  owner = ID(stored=True)

  name = TEXT(stored=True, analyzer=accent_folder)
  description = TEXT(stored=True, analyzer=accent_folder)
  text = TEXT(stored=False, analyzer=accent_folder)
