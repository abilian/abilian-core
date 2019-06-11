""""""
from typing import Set

from flask_login import AnonymousUserMixin, LoginManager


class AnonymousUser(AnonymousUserMixin):
    def has_role(self, role):
        from abilian.services import get_service

        security = get_service("security")
        return security.has_role(self, role)

    @property
    # pyre-fixme[31]: Expression `Set` is not a valid type.
    def groups(self) -> Set:
        return set()


login_manager = LoginManager()
login_manager.anonymous_user = AnonymousUser
