""""""
from flask_login import current_user, login_user
from pytest import fixture
from sqlalchemy.orm import Session

from abilian.app import Application as BaseApplication
from abilian.core.models.subjects import User
from abilian.core.sqlalchemy import SQLAlchemy
from abilian.services import get_service

from .models import UserPreference
from .panel import PreferencePanel
from .service import PreferenceService


class VisiblePanel(PreferencePanel):
    id = label = "visible"

    def is_accessible(self) -> bool:
        return True

    def get(self):
        return "Visible"


class AdminPanel(PreferencePanel):
    id = label = "admin"

    def is_accessible(self) -> bool:
        security = get_service("security")
        # pyre-fixme[16]: `Service` has no attribute `has_role`.
        return security.has_role(current_user, "admin")

    def get(self):
        return "Admin"


class Application(BaseApplication):
    def init_extensions(self) -> None:
        super().init_extensions()
        prefs = self.services["preferences"]
        prefs.app_state.panels = []
        # pyre-fixme[16]: `Service` has no attribute `register_panel`.
        prefs.register_panel(VisiblePanel(), self)
        # pyre-fixme[16]: `Service` has no attribute `register_panel`.
        prefs.register_panel(AdminPanel(), self)


@fixture
def app(config: type) -> Application:
    app = Application()
    app.setup(config)
    return app


def test_preferences(app: Application, session: Session) -> None:
    user = User(email="test@example.com")
    assert UserPreference.query.all() == []

    preference_service = PreferenceService()

    preferences = preference_service.get_preferences(user)
    assert preferences == {}

    preference_service.set_preferences(user, digest="daily")
    session.flush()

    preferences = preference_service.get_preferences(user)
    assert preferences == {"digest": "daily"}

    preference_service.clear_preferences(user)
    session.flush()

    preferences = preference_service.get_preferences(user)
    assert preferences == {}
    assert UserPreference.query.all() == []


def test_preferences_with_various_types(app: Application, session: Session) -> None:
    user = User(email="test@example.com")
    preference_service = PreferenceService()

    preference_service.set_preferences(user, some_int=1)
    session.flush()
    preferences = preference_service.get_preferences(user)
    assert preferences == {"some_int": 1}

    preference_service.set_preferences(user, some_bool=True)
    session.flush()
    preferences = preference_service.get_preferences(user)
    assert preferences == {"some_int": 1, "some_bool": True}


def test_visible_panels(app: Application, db: SQLAlchemy) -> None:
    user = User(email="test@example.com")
    security = app.services["security"]

    with app.test_request_context():
        security.start()
        login_user(user)

        for cp in app.template_context_processors["preferences"]:
            ctx = cp()
            if "menu" in ctx:
                break

        expected = ["preferences.visible"]
        # pyre-fixme[18]: Global name `ctx` is undefined.
        assert [p["endpoint"] for p in ctx["menu"]] == expected

        # pyre-fixme[16]: `Service` has no attribute `grant_role`.
        security.grant_role(user, "admin")
        # pyre-fixme[18]: Global name `cp` is undefined.
        ctx = cp()
        expected = ["preferences.visible", "preferences.admin"]
        assert [p["endpoint"] for p in ctx["menu"]] == expected
