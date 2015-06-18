# coding=utf-8
"""
"""
from __future__ import absolute_import

from .extension import CommentExtension

def register_plugin(app):
  CommentExtension(app=app)
  
