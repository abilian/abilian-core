# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function

from .criterion import TagCriterion
from .extension import TagsExtension

__all__ = ["TagsExtension", "TagCriterion"]


def register_plugin(app):
    TagsExtension(app=app)
