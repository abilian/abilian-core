""""""
from flask_login import AnonymousUserMixin

from abilian.services.indexing.schema import indexable_role
from abilian.services.security.models import Anonymous, Reader


def test_indexable_role() -> None:
    assert indexable_role(Anonymous) == "role:anonymous"
    # pyre-fixme[6]: Expected `Role` for 1st param but got `AnonymousUserMixin`.
    assert indexable_role(AnonymousUserMixin()) == "role:anonymous"
    assert indexable_role(Reader) == "role:reader"
