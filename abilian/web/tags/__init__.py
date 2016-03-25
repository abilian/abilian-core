# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from .extension import TagsExtension
from .criterion import TagCriterion

__all__ = ['TagsExtension', 'TagCriterion']


def register_plugin(app):
    TagsExtension(app=app)
