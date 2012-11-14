# coding=utf-8

from unittest import TestCase
from flask import Flask
from yaka.web.widgets import TableView


class Model(object):
  def __init__(self, **kw):
    for k, v in kw.items():
      setattr(self, k, v)


class TableViewTestCase(TestCase):

  def test(self):
    app = Flask(__name__)
    with app.test_request_context():
      columns = ['name', 'price']
      tv = TableView(columns)

      model1 = Model(name="Renault Megane", price=10000)
      model2 = Model(name="Peugeot 308", price=12000)

      models = [model1, model2]

      res = tv.render(models)

      assert "Renault Megane" in res
      assert "10000" in res
