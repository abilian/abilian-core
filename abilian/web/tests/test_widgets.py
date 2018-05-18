# coding=utf-8

from __future__ import absolute_import, division, print_function, \
    unicode_literals

import sqlalchemy as sa
from flask.signals import request_started
from pytest import mark
from wtforms import Form, IntegerField, StringField

# Import for side-effects (monkey-patch)
# noinspection PyUnresolvedReferences
import abilian.web.forms  # noqa
from abilian.core.entities import Entity
from abilian.web.views import default_view

from ..forms.widgets import EmailWidget, MainTableView, Panel, Row, \
    SingleView, linkify_url, text2html


class WidgetTestModel(Entity):
    """Mock model."""
    __tablename__ = "widget_test_model"
    id = sa.Column(sa.Integer, primary_key=True)
    price = sa.Column(sa.Integer)
    email = sa.Column(sa.Text)

    def __init__(self, *args, **kw):
        Entity.__init__(self, *args, **kw)
        self._display_value_called = False

    def display_value(self, attr):
        self._display_value_called = True
        return getattr(self, attr)


class DummyForm(Form):
    name = StringField("Nom du véhicule")
    price = IntegerField("Prix du véhicule")
    email = StringField("email", view_widget=EmailWidget())


def test_table_view(app, test_request_context):

    @default_view(app, WidgetTestModel)
    @app.route("/dummy_view/<object_id>")
    def dummy_view(object_id):
        pass

    request_started.send(app)  # needed for deferJS tag
    columns = ["name", "price"]
    view = MainTableView(columns)

    model1 = WidgetTestModel(id=1, name="Renault Megane", price=10000)
    model2 = WidgetTestModel(id=2, name="Peugeot 308", price=12000)
    models = [model1, model2]
    res = view.render(models)

    assert model1._display_value_called
    assert model2._display_value_called
    assert "Renault Megane" in res
    assert "10000" in res


def test_single_view(test_request_context):
    panels = [Panel("main", Row("name"), Row("price"), Row("email"))]
    view = SingleView(DummyForm, *panels, view=dict(can_edit=False, can_delete=False))
    model = WidgetTestModel(name="Renault Megane", price=10000, email="joe@example.com")
    form = DummyForm(obj=model)
    res = view.render(model, form)

    assert "Renault Megane" in res
    assert "10000" in res
    # 'mailto:' is created by EmailWidget
    assert "mailto:joe@example.com" in res


@mark.skip
def test_edit_view(app):
    with app.test_request_context():
        panels = [Panel("main", Row("name"), Row("price"))]
        view = SingleView(DummyForm, *panels)
        model = WidgetTestModel(name="Renault Megane", price=10000)
        form = DummyForm(obj=model)
        res = view.render_form(form)

        assert model._display_value_called
        assert "Renault Megane" in res
        assert "10000" in res


EXPECTED = (
    '<a href="http://example.com">example.com</a>'
    '&nbsp;<i class="fa fa-external-link"></i>'
)


def test_http():
    value = "http://example.com"
    result = linkify_url(value)
    assert result == EXPECTED


def test_no_http():
    value = "example.com"
    result = linkify_url(value)
    assert result == EXPECTED


def test1():
    result = text2html("a")
    assert result == "a"


def test2():
    result = text2html("a\nb")
    assert str(result) == "<p>a</p>\n<p>b</p>"


def test3():
    result = text2html("a\n\nb")
    assert str(result) == "<p>a</p>\n<p>b</p>"


def test4():
    result = text2html("a\n<a>toto</a>")
    assert str(result) == "<p>a</p>\n<p>&lt;a&gt;toto&lt;/a&gt;</p>"
