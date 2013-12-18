# coding=utf-8
"""
"""
from __future__ import absolute_import

from .criterion import BaseCriterion, TextSearchCriterion

__all__ = ['BaseCriterion', 'TextSearchCriterion']

def register_plugin(app):
  from .views import search
  app.register_blueprint(search)
