""""""
import sqlalchemy as sa
from flask import Blueprint
from flask.ctx import RequestContext
from pytest import fixture, raises

from abilian.app import Application
from abilian.core.entities import Entity
# needed if running only this test, else SA won't have registered this mapping
# required by Entity.owner_id, etc
# noinspection PyUnresolvedReferences
from abilian.core.models.subjects import User  # noqa
from abilian.web.views import default_view
from abilian.web.views.registry import Registry


class RegEntity(Entity):
    name = sa.Column(sa.Unicode, default="")


class NonEntity:
    pass


@fixture
def registry(app: Application) -> Registry:
    app.default_view = Registry()
    return app.default_view


def test_register_class(app: Application, registry: Registry) -> None:
    registry.register(RegEntity, lambda ignored: "")
    assert RegEntity.entity_type in registry._map


def test_register_instance(app: Application, registry: Registry) -> None:
    obj = RegEntity()
    registry.register(obj, lambda ignored: "")
    assert RegEntity.entity_type in registry._map


def test_custom_url_func(app: Application, registry: Registry) -> None:
    name = "obj"
    obj = RegEntity(id=1, name=name)

    def custom_url(obj: RegEntity, obj_type: str, obj_id: int) -> str:
        return obj.name

    registry.register(obj, custom_url)
    assert registry.url_for(obj) == name

    def url_from_type_and_id(obj: RegEntity, obj_type: str, obj_id: int) -> str:
        return f"{obj_type}:{obj_id}"

    registry.register(obj, url_from_type_and_id)
    assert registry.url_for(obj) == "test_registry.RegEntity:1"


def test_default_url_func(
    app: Application, registry: Registry, test_request_context: RequestContext
) -> None:
    obj = RegEntity(id=1)

    @app.route("/regentities_path/<int:object_id>/view", endpoint="regentity.view")
    def dummy_default_view(object_id):
        pass

    assert registry.url_for(obj) == "/regentities_path/1/view"
    assert (
        registry.url_for(obj, _external=True)
        == "http://localhost.localdomain/regentities_path/1/view"
    )


def test_default_view_decorator(
    app: Application, registry: Registry, test_request_context: RequestContext
) -> None:
    bp = Blueprint("registry", __name__, url_prefix="/blueprint")

    @default_view(bp, RegEntity)
    @bp.route("/<int:object_id>")
    def view(object_id):
        pass

    obj = RegEntity(id=1)
    # blueprint not registered: no rule set
    with raises(KeyError):
        registry.url_for(obj)

    # blueprint registered: default view is set
    app.register_blueprint(bp)

    assert registry.url_for(obj) == "/blueprint/1"
    assert (
        registry.url_for(obj, _external=True)
        == "http://localhost.localdomain/blueprint/1"
    )
