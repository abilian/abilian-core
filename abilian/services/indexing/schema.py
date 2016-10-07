# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from whoosh.analysis import CharsetFilter, LowercaseFilter, NgramFilter, \
    PathTokenizer, RegexTokenizer
from whoosh.fields import DATETIME, ID, KEYWORD, NUMERIC, TEXT, FieldType, \
    SchemaClass
from whoosh.formats import Existence
from whoosh.support.charset import accent_map

from abilian.core.models.subjects import Group, User
from abilian.core.util import noproxy
from abilian.services.security.models import Anonymous, Role

#: A Whoosh analyzer that splits on word boundaries and folds accents and case.
accent_folder = (
    RegexTokenizer(r'\w+')  # defaults doesn't split on '.'
    | LowercaseFilter() | CharsetFilter(accent_map))

#: Analyzer for edge-ngrams, from 2 to 6 characters long
edge_ngram = accent_folder | NgramFilter(minsize=2, maxsize=6, at='start')


def EdgeNgramField():
    return TEXT(stored=False, analyzer=edge_ngram)


class _DefaultSearchSchema(SchemaClass):
    """General search schema.
    """
    object_key = ID(stored=True, unique=True)
    id = NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=False)
    object_type = ID(stored=True, unique=False)
    creator = ID(stored=True)
    owner = ID(stored=True)

    #: security index. This list roles and user/group ids allowed to *see* this
    #: content
    allowed_roles_and_users = KEYWORD(stored=True)

    #: tags indexing
    tag_ids = KEYWORD(stored=True)
    tag_text = TEXT(stored=False, analyzer=accent_folder)

    # hierarchical index of ids path ('/' is the separator)
    parent_ids = FieldType(
        format=Existence(), analyzer=PathTokenizer(), stored=True, unique=False)

    name = TEXT(stored=True, analyzer=accent_folder)
    slug = ID(stored=True)
    description = TEXT(stored=True, analyzer=accent_folder)
    text = TEXT(stored=False, analyzer=accent_folder)


_default_dyn_fields = {
    '*_prefix': EdgeNgramField(),
    '*_at': DATETIME(
        stored=True, sortable=True),
}


def DefaultSearchSchema(*args, **kwargs):
    schema = _DefaultSearchSchema()
    for name, field in _default_dyn_fields.items():
        schema.add(name, field, glob=True)
    return schema


def indexable_role(principal):
    """Return a string suitable for query against `allowed_roles_and_users`
    field.

    :param principal: It can be :data:`Anonymous`, :data:`Authenticated`,
      or an instance of :class:`User` or :class:`Group`.
    """
    principal = noproxy(principal)

    if (hasattr(principal, 'is_anonymous') and principal.is_anonymous):
        # transform anonymous user to anonymous role
        principal = Anonymous

    if isinstance(principal, Role):
        return u'role:{}'.format(principal.name)
    elif isinstance(principal, User):
        fmt = u'user:{:d}'
    elif isinstance(principal, Group):
        fmt = u'group:{:d}'
    else:
        raise ValueError(repr(principal))

    return fmt.format(principal.id)
