# coding=utf-8
"""
"""
from __future__ import absolute_import


from .extension import AttachmentExtension

def register_plugin(app):
  AttachmentExtension(app=app)