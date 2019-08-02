from typing import Union

import sqlalchemy as sa
from flask import Flask
from flask.ctx import RequestContext
from flask.signals import request_started
from pytest import mark
from wtforms import Form, IntegerField, StringField

# Import for side-effects (monkey-patch)
# noinspection PyUnresolvedReferences
import abilian.web.forms  # noqa
from abilian.core.entities import Entity
from abilian.web.forms.widgets import EmailWidget, MainTableView, Panel, Row, \
    SingleView, linkify_url, text2html
from abilian.web.views import default_view


class WidgetTestModel(Entity):
    """Mock model."""

    __tablename__ = "widget_test_model"
    id = sa.Column(sa.Integer, primary_key=True)
    price = sa.Column(sa.Integer)
    email = sa.Column(sa.Text)

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._display_value_called = False

    def display_value(self, attr: str) -> Union[int, str]:
        self._display_value_called = True
        return getattr(self, attr)


class DummyForm(Form):
    name = StringField("Nom du véhicule")
    price = IntegerField("Prix du véhicule")
    email = StringField("email", view_widget=EmailWidget())


def test_table_view(app: Flask, test_request_context: RequestContext) -> None:
    @default_view(app, WidgetTestModel)
    @app.route("/dummy_view/<object_id>")
    def dummy_view(object_id):
        pass

    request_started.send(app)  # needed for deferJS tag
    columns = [{"name": "name"}, {"name": "price"}]
    view = MainTableView(columns)

    model1 = WidgetTestModel(id=1, name="Renault Megane", price=10000)
    model2 = WidgetTestModel(id=2, name="Peugeot 308", price=12000)
    models = [model1, model2]
    res = view.render(models)

    assert model1._display_value_called
    assert model2._display_value_called
    assert "Renault Megane" in res
    assert "10000" in res


def test_single_view(test_request_context: RequestContext) -> None:
    model = WidgetTestModel(name="Renault Megane", price=10000, email="joe@example.com")
    panels = [Panel("main", Row("name"), Row("price"), Row("email"))]
    form = DummyForm(obj=model)
    view = SingleView(form, *panels, view={"can_edit": False, "can_delete": False})
    res = view.render(model)

    assert "Renault Megane" in res
    assert "10000" in res
    # 'mailto:' is created by EmailWidget
    assert "mailto:joe@example.com" in res


@mark.skip
def test_edit_view(app):
    with app.test_request_context():
        model = WidgetTestModel(name="Renault Megane", price=10000)
        panels = [Panel("main", Row("name"), Row("price"))]
        form = DummyForm(obj=model)
        view = SingleView(form, *panels)
        res = view.render_form()

        assert model._display_value_called
        assert "Renault Megane" in res
        assert "10000" in res


EXPECTED = (
    '<a href="http://example.com">example.com</a>'
    '&nbsp;<i class="fa fa-external-link"></i>'
)


def test_http() -> None:
    value = "http://example.com"
    result = linkify_url(value)
    assert result == EXPECTED


def test_no_http() -> None:
    value = "example.com"
    result = linkify_url(value)
    assert result == EXPECTED


def test1() -> None:
    result = text2html("a")
    assert result == "a"


def test2() -> None:
    result = text2html("a\nb")
    assert str(result) == "<p>a</p>\n<p>b</p>"


def test3() -> None:
    result = text2html("a\n\nb")
    assert str(result) == "<p>a</p>\n<p>b</p>"


def test4() -> None:
    result = text2html("a\n<a>toto</a>")
    assert str(result) == "<p>a</p>\n<p>&lt;a&gt;toto&lt;/a&gt;</p>"
