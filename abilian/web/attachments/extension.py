# coding=utf-8
"""
"""
from __future__ import absolute_import

from abilian.core.models import attachment as attachments
from abilian.web import url_for

from .forms import AttachmentForm
from .views import bp as blueprint, UPLOAD_BUTTON

class AttachmentExtension(object):
  """
  API for comments, installed as an application extension.

  It is also available in templates as `attachments`.  
  """
  def __init__(self, app):
    app.extensions['attachments'] = self
    app.add_template_global(self, 'attachements')

  def is_support_attachements(self, obj):
    return attachments.is_support_attachements(obj)

  def for_entity(self, obj, check_support_attachments=False):
    return attachments.for_entity(obj, check_support_attachments=check_support_attachments)

  def has_attachments(self, obj):
    return bool(attachments.for_entity(obj, check_support_attachments=True))

  def count(self, obj):
    return len(attachments.for_entity(obj, check_support_attachments=True))

  def get_form_context(self, obj):
    """
    Return a dict: form instance, action button, submit url...
    Used by macro m_attachment_form(entity)
    """
    ctx = {}
    ctx['url'] = url_for('attachements.create', entity_id=obj.id)
    ctx['form'] = AttachmentForm()
    ctx['buttons'] = [UPLOAD_BUTTON]
    return ctx
    
