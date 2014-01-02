# coding=utf-8
import os

from unittest import TestCase, skip
import sqlalchemy as sa
from flask import Flask
from wtforms import Form, TextField, IntegerField

# Import for side-effects (monkey-patch)
import abilian.web.forms

from abilian.i18n import babel
from abilian.core.extensions import db

from ..forms.widgets import MainTableView, SingleView, Panel, Row, \
  linkify_url, text2html, EmailWidget


class WidgetTestModel(db.Model):
  """
  Mock model.
  """
  __tablename__ = 'widget_test_model'
  id = sa.Column(sa.Integer, primary_key=True)

  def __init__(self, **kw):
    for k, v in kw.items():
      setattr(self, k, v)

    self._display_value_called = False

  def display_value(self, attr):
    self._display_value_called = True
    return getattr(self, attr)


class DummyForm(Form):
  name = TextField(u'Nom du véhicule')
  price = IntegerField(u"Prix du véhicule")
  email = TextField(u'email', view_widget=EmailWidget())


class BaseTestCase(TestCase):
  # TODO: use abilian.testing.BaseTestCase instead

  def setUp(self):
    # Hack to set up the template folder properly.
    template_dir = os.path.dirname(__file__) + "/../../web/templates"
    template_dir = os.path.normpath(template_dir)
    self.app = Flask(__name__, template_folder=template_dir)
    self.app.config.update({
      'TESTING': True,
      'CSRF_ENABLED': False,
      'WTF_CSRF_ENABLED': False,
      })

    # install 'deferJS' extension
    jinja_opts = {}
    jinja_opts.update(self.app.jinja_options)
    jinja_exts = []
    jinja_exts.extend(jinja_opts.setdefault('extensions', []))
    jinja_exts.append('abilian.core.jinjaext.DeferredJSExtension')
    jinja_opts['extensions'] = jinja_exts
    self.app.jinja_options = jinja_opts

    from abilian.core.jinjaext import DeferredJS
    DeferredJS(self.app)
    babel.init_app(self.app)


class TableViewTestCase(BaseTestCase):

  def test_table_view(self):
    with self.app.test_request_context():
      self.app.preprocess_request() # run before_request handlers: needed for deferJS
      columns = ['name', 'price']
      view = MainTableView(columns)

      model1 = WidgetTestModel(name="Renault Megane", _name="toto", price=10000)
      model2 = WidgetTestModel(name="Peugeot 308", _name="titi", price=12000)

      models = [model1, model2]

      res = view.render(models)

      assert model1._display_value_called
      assert model2._display_value_called
      assert "Renault Megane" in res
      assert "10000" in res


class ModelViewTestCase(BaseTestCase):
  # Hack to silence test harness bug
  __name__ = "ModelView test case"

  def test_single_view(self):
    with self.app.test_request_context():
      panels = [Panel('main', Row('name'), Row('price'), Row('email'))]
      view = SingleView(DummyForm, *panels)
      model = WidgetTestModel(name="Renault Megane",
                              price=10000, email="joe@example.com")
      form = DummyForm(obj=model)
      res = view.render(model, form)

      assert "Renault Megane" in res
      assert "10000" in res
      # 'mailto:' is created by EmailWidget
      assert "mailto:joe@example.com" in res

  @skip
  def test_edit_view(self):
    with self.app.test_request_context():
      panels = [Panel('main', Row('name'), Row('price'))]
      view = SingleView(DummyForm, *panels)
      model = WidgetTestModel(name="Renault Megane", price=10000)
      form = DummyForm(obj=model)
      res = view.render_form(form)

      assert model._display_value_called
      assert "Renault Megane" in res
      assert "10000" in res


class TestLinkify(TestCase):

  EXPECTED = '<a href="http://example.com">example.com</a><i class="icon-share-alt"></i>'

  def test_http(self):
    value = "http://example.com"
    result = linkify_url(value)
    self.assertEquals(result, self.EXPECTED)

  def test_no_http(self):
    value = "example.com"
    result = linkify_url(value)
    self.assertEquals(result, self.EXPECTED)


class TestText2Html(TestCase):

  def test1(self):
    result = text2html("a")
    self.assertEquals(result, "a")

  def test2(self):
    result = text2html("a\nb")
    self.assertEquals(str(result), "<p>a</p>\n<p>b</p>")

  def test3(self):
    result = text2html("a\n\nb")
    self.assertEquals(str(result), "<p>a</p>\n<p>b</p>")

  def test4(self):
    result = text2html("a\n<a>toto</a>")
    self.assertEquals(str(result), "<p>a</p>\n<p>&lt;a&gt;toto&lt;/a&gt;</p>")
