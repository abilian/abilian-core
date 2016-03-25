# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from abilian.core.signals import register_js_api
from abilian.web import url_for

from .criterion import BaseCriterion, TextSearchCriterion

__all__ = ['BaseCriterion', 'TextSearchCriterion']


def _do_register_js_api(sender):
    app = sender
    js_api = app.js_api.setdefault('search', {})
    # hack to avoid url_for escape '%'
    js_api['live'] = url_for('search.live', q='') + u'%QUERY'


def register_plugin(app):
    from .views import search
    app.register_blueprint(search)
    register_js_api.connect(_do_register_js_api)
