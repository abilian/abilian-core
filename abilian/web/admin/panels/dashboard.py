# coding=utf-8
"""
"""
from __future__ import absolute_import

from datetime import datetime, timedelta
import sqlalchemy as sa

from flask import render_template, current_app

from abilian.i18n import _l
from abilian.core.models.subjects import User
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
  after_date = datetime.utcnow() - dt
  session = current_app.db.session()
  counts_per_type = session\
    .query(AuditEntry.entity_type.label('type'),
           sa.func.count(AuditEntry.entity_type).label('count'))\
    .group_by(AuditEntry.entity_type)\
    .filter(AuditEntry.happened_at > after_date) \
    .filter(AuditEntry.type == CREATION)\
    .all()

  for entity_type, count in counts_per_type:
    entity_class = entity_type.split('.')[-1]
    if entity_class == 'User':
      new_members = count
    elif entity_class == 'Document':
      new_documents = count
    elif entity_class == 'Message':
      new_messages = count

  active_users = session.query(sa.func.count(User.id))\
                        .filter(User.last_active > after_date).scalar()

  return {
    'new_members': new_members,
    'active_users': active_users,
    'new_documents': new_documents,
    'new_messages': new_messages,
  }
