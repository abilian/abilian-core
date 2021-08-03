""""""
from __future__ import annotations

from flask import Flask

from .criterion import TagCriterion
from .extension import TagsExtension

__all__ = ["TagsExtension", "TagCriterion"]


def register_plugin(app: Flask):
    TagsExtension(app)
