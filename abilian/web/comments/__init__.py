# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from .extension import CommentExtension


def register_plugin(app):
    CommentExtension(app=app)
