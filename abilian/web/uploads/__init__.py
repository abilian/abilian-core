# coding=utf-8
"""
"""
from __future__ import absolute_import

from .extension import FileUploadsExtension

def register_plugin(app):
  FileUploadsExtension(app)

