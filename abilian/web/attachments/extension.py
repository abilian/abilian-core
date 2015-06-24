# coding=utf-8
"""
"""
from __future__ import absolute_import


class AttachmentExtension(object):
  """
  API for comments, installed as an application extension.

  It is also available in templates as `attachments`.  
  """
  def __init__(self, app):
    app.extension['attachments'] = self
    app.add_template_global(self, 'attachements')
