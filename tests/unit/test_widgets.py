# coding=utf-8
import os

from unittest import TestCase
from flask import Flask
from yaka.web.widgets import TableView, SingleView, Panel, Row


class Model(object):
  def __init__(self, **kw):
    for k, v in kw.items():
      setattr(self, k, v)


class TableViewTestCase(TestCase):

  def setUp(self):
    # Hack to set up the template folder properly.
    template_dir = os.path.dirname(__file__) + "/../../yaka/templates"
    template_dir = os.path.normpath(template_dir)
    self.app = Flask(__name__, template_folder=template_dir)

  def test_table_view(self):
    with self.app.test_request_context():
      columns = ['name', 'price']
      view = TableView(columns)

      model1 = Model(name="Renault Megane", price=10000)
      model2 = Model(name="Peugeot 308", price=12000)

      models = [model1, model2]

      res = view.render(models)

      assert "Renault Megane" in res
      assert "10000" in res

  def test_single_view(self):
    with self.app.test_request_context():
      panels = [Panel('main', Row('name', 'price'))]
      view = SingleView(*panels)

      model = Model(name="Renault Megane", price=10000)
      res = view.render(model)

      assert "Renault Megane" in res
      assert "10000" in res
