""""""
from __future__ import annotations

from abilian.app import Application
from abilian.core.signals import register_js_api
from abilian.web import url_for

from .criterion import BaseCriterion, TextSearchCriterion

__all__ = ["BaseCriterion", "TextSearchCriterion"]


def _do_register_js_api(sender: Application):
    app = sender
    js_api = app.js_api.setdefault("search", {})
    # hack to avoid url_for escape '%'
    js_api["live"] = f"{url_for('search.live', q='')}%QUERY"


def register_plugin(app: Application):
    from .views import search

    app.register_blueprint(search)
    register_js_api.connect(_do_register_js_api)
