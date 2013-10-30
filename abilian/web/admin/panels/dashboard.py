# coding=utf-8
"""
"""
from __future__ import absolute_import

from datetime import datetime, timedelta
from flask import render_template
from flask.ext.babel import lazy_gettext as _l
from abilian.core.subjects import User
from abilian.services.audit import AuditEntry, CREATION

from ..panel import AdminPanel


class DashboardPanel(AdminPanel):
  id = 'dashboard'
  path = ''
  label = _l('Dashboard')
  icon = 'eye-open'

  def get(self):
    stats = {
      'today': stats_since(timedelta(days=1)),
      'this_week': stats_since(timedelta(days=7)),
      'this_month': stats_since(timedelta(days=30)),
    }
    return render_template("admin/dashboard.html", stats=stats)


def stats_since(dt):
  new_members = new_documents = new_messages = 0

  now = datetime.utcnow()
  entries = AuditEntry.query \
    .filter(AuditEntry.happened_at > now - dt) \
    .filter(AuditEntry.type == CREATION).all()
  for e in entries:
    entity_class = e.entity_type.split('.')[-1]
    if entity_class == 'User':
      new_members += 1
    elif entity_class == 'Document':
      new_documents += 1
    elif entity_class == 'Message':
      new_messages += 1

  active_users = User.query.filter(User.last_active > now - dt).count()

  return {
    'new_members': new_members,
    'active_users': active_users,
    'new_documents': new_documents,
    'new_messages': new_messages,
  }
