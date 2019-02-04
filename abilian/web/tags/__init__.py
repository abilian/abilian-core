# coding=utf-8
""""""
from .criterion import TagCriterion
from .extension import TagsExtension

__all__ = ["TagsExtension", "TagCriterion"]


def register_plugin(app):
    TagsExtension(app=app)
