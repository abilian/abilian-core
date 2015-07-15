# coding=utf-8
"""
"""
from __future__ import absolute_import

from .extension import TagsExtension

def register_plugin(app):
  TagsExtension(app=app)
