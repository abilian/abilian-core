""""""
from typing import TYPE_CHECKING, Set

from flask_login import AnonymousUserMixin, LoginManager

if TYPE_CHECKING:
    from abilian.core.models.subjects import Group


class AnonymousUser(AnonymousUserMixin):
    def has_role(self, role):
        from abilian.services import get_service

        security = get_service("security")
        return security.has_role(self, role)

    @property
    def groups(self) -> Set["Group"]:
        return set()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser
