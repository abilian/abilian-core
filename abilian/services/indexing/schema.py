""""""
from whoosh.analysis import CharsetFilter, LowercaseFilter, NgramFilter, \
    PathTokenizer, RegexTokenizer
#: A Whoosh analyzer that splits on word boundaries and folds accents and case.
from whoosh.fields import DATETIME, ID, KEYWORD, NUMERIC, TEXT, FieldType, \
    Schema, SchemaClass
from whoosh.formats import Existence
from whoosh.support.charset import accent_map

from abilian.core.models.subjects import Group, User
from abilian.core.util import unwrap
from abilian.services.security.models import Anonymous, Role

accent_folder = (
    RegexTokenizer(r"\w+")
    | LowercaseFilter()  # defaults doesn't split on '.'
    | CharsetFilter(accent_map)
)

#: Analyzer for edge-ngrams, from 2 to 6 characters long
edge_ngram = accent_folder | NgramFilter(minsize=2, maxsize=6, at="start")


def EdgeNgramField() -> TEXT:
    return TEXT(analyzer=edge_ngram)


class _DefaultSearchSchema(SchemaClass):
    """General search schema."""

    object_key = ID(stored=True, unique=True)
    id = NUMERIC(bits=64, signed=False, stored=True)
    object_type = ID(stored=True)
    creator = ID(stored=True)
    owner = ID(stored=True)

    #: security index. This list roles and user/group ids allowed to *see* this
    #: content
    allowed_roles_and_users = KEYWORD(stored=True)

    #: tags indexing
    tag_ids = KEYWORD(stored=True)
    tag_text = TEXT(analyzer=accent_folder)

    # hierarchical index of ids path ('/' is the separator)
    parent_ids = FieldType(format=Existence(), analyzer=PathTokenizer(), stored=True)

    name = TEXT(stored=True, analyzer=accent_folder)
    slug = ID(stored=True)
    description = TEXT(stored=True, analyzer=accent_folder)
    text = TEXT(analyzer=accent_folder)


_default_dyn_fields = {
    "*_prefix": EdgeNgramField(),
    "*_at": DATETIME(stored=True, sortable=True),
}


def DefaultSearchSchema(*args, **kwargs) -> Schema:
    schema = _DefaultSearchSchema()
    for name, field in _default_dyn_fields.items():
        schema.add(name, field, glob=True)
    return schema


def indexable_role(principal: Role) -> str:
    """Return a string suitable for query against `allowed_roles_and_users`
    field.

    :param principal: It can be :data:`Anonymous`, :data:`Authenticated`,
      or an instance of :class:`User` or :class:`Group`.
    """
    principal = unwrap(principal)

    if hasattr(principal, "is_anonymous") and principal.is_anonymous:
        # transform anonymous user to anonymous role
        principal = Anonymous

    if isinstance(principal, Role):
        return f"role:{principal.name}"
    elif isinstance(principal, User):
        fmt = "user:{:d}"
    elif isinstance(principal, Group):
        fmt = "group:{:d}"
    else:
        raise ValueError(repr(principal))

    return fmt.format(principal.id)
