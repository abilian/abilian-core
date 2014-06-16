# coding=utf-8
"""
"""
from __future__ import absolute_import
from datetime import datetime
from itertools import chain
from markupsafe import Markup
import pytz

import sqlalchemy as sa
from sqlalchemy.orm.attributes import NO_VALUE

from werkzeug.routing import BuildError
from flask import request, render_template, render_template_string, \
  get_template_attribute
from flask.ext.babel import gettext as _

from abilian.core.extensions import db
from abilian.core.entities import Entity
from abilian.core.util import local_dt
from abilian.services.audit import AuditEntry
from abilian.services.security import SecurityAudit
from abilian.web.util import url_for

from ..panel import AdminPanel


class AuditPanel(AdminPanel):
  """Global audit log.

  Can receive one out of two possible GET parameter, datetime type:

  * before: events that happened immediately before 't' (less recent than 't')
  * after: events that happened immediately after 't' (more recent than 't')
  """
  id = 'audit'
  label = 'Audit trail'
  icon = 'list-alt'

  def get(self):
    LIMIT = 30

    before = request.args.get('before')
    after = request.args.get('after')

    def after_query(model, date):
      return model.query.filter(model.happened_at > date)\
                        .order_by(model.happened_at.asc())

    def before_query(model, date):
      return model.query.filter(model.happened_at < date)\
                        .order_by(model.happened_at.desc())
    if after:
      after = datetime.strptime(after, u'%Y-%m-%dT%H:%M:%S.%f')
      audit_q = after_query(AuditEntry, after)
      security_q = after_query(SecurityAudit, after)
    else:
      before = (datetime.strptime(before, u'%Y-%m-%dT%H:%M:%S.%f')
                if before else datetime.utcnow())
      audit_q = before_query(AuditEntry, before)
      security_q = before_query(SecurityAudit, before)

    audit_q.options(sa.orm.contains_eager('entity'))\
      .outerjoin(sa.orm.with_polymorphic(Entity, [], aliased=True),
                 AuditEntry._fk_entity_id == Entity.id)

    audit_entries = audit_q.limit(LIMIT).all()
    security_entries = security_q.limit(LIMIT).all()

    all_entries = list(chain((AuditEntryPresenter(e) for e in audit_entries),
                             (SecurityEntryPresenter(e) for e in security_entries)))
    all_entries.sort()

    if after:
      all_entries = all_entries[:LIMIT]
    else:
      all_entries = all_entries[-LIMIT:]

    all_entries.reverse()  # event are presented from most to least recent

    AuditEntryPresenter.prefetch([e for e in all_entries
                                  if isinstance(e, AuditEntryPresenter)])
    SecurityEntryPresenter.prefetch([e for e in all_entries
                                     if isinstance(e, SecurityEntryPresenter)])

    # group entries by day
    entries = []
    day_entries = None
    current_day = None

    for e in all_entries:
      e_date = e.date

      if e_date.date() != current_day:
        current_day = e_date.date()
        day_entries = []
        entries.append((e_date.date(), day_entries))
      day_entries.append(e)

    top_date = u''
    lowest_date = u''

    if entries:
      # top_date and lowest_date are converted to naive datetime (from UTC), so
      # that isoformat does not include TZ shift (else we should fix strptime
      # above)
      top_date = entries[0][1][0].date.astimezone(pytz.utc).replace(tzinfo=None)
      lowest_date = entries[-1][1][-1].date.astimezone(pytz.utc)\
                                            .replace(tzinfo=None)

      if not (after_query(AuditEntry, top_date).limit(1).first() is not None
              or after_query(SecurityAudit, top_date).limit(1).first() is not None):
        top_date = u''
      else:
        top_date = top_date.isoformat()

      if not (before_query(AuditEntry, lowest_date).limit(1).first() is not None
              or before_query(SecurityAudit, lowest_date).limit(1).first() is not None):
        lowest_date = u''
      else:
        lowest_date = lowest_date.isoformat()

    return render_template("admin/audit.html", entries=entries,
                           top_date=top_date, lowest_date=lowest_date)


#
#  Presenters for audit entries listing
#
class BaseEntryPresenter(object):

  _USER_FMT = (u'<a href="{{ url_for("social.user", user_id=user.id) }}">'
               '{{ user.name }}</a>')
  _GROUP_FMT = (u'<a href="{{ url_for("social.group_home", group_id=group.id)'
                ' }}">{{ group.name }}</a>')

  def __init__(self, user, date):
    self.user = user
    self.date = local_dt(date)

  def __cmp__(self, other):
    return cmp(self.date, other.date)

  def __repr__(self):
    return '{}({}, {} @ {})'.format(
      self.__class__.__name__, repr(self.user), repr(self.date), id(self))

  @staticmethod
  def model(model_name):
    return db.Model._decl_class_registry.get(model_name)

  def render(self):
    raise NotImplementedError

  @staticmethod
  def prefetch(entries):
    pass


class AuditEntryPresenter(BaseEntryPresenter):

  def __init__(self, entry):
    assert isinstance(entry, AuditEntry)
    super(AuditEntryPresenter, self).__init__(entry.user, entry.happened_at)
    self.entry = entry

  def render(self):
    render = render_template_string
    e = self.entry
    user = render(self._USER_FMT, user=e.user)
    self.changes = []
    # entity = e.entity_name or u''
    self.entity_deleted = e.entity is None
    entity_html = e.entity_name

    if not self.entity_deleted:
      try:
        entity_url = url_for(e.entity)
      except (BuildError, ValueError):
        pass
      else:
        entity_html = Markup(render(
          u'<a href="{{ url }}">{{ entity.path or entity.name }}</a>',
          url=entity_url,
          entity=e.entity))

    if e.type == 0:
      msg = _(u'{user} created {entity_type} {entity_id} "{entity}"')
    elif e.related or e.op == 1:
      msg = _(u'{user} made changes on {entity_type} {entity_id} "{entity}"')
      self.changes.extend(self.format_model_changes(e.changes))
    elif e.op == 2:
      msg = _(u'{user} has deleted {entity_type}: {entity_id} "{entity}"')
    else:
      raise Exception("Bad entry type: {}".format(e.type))

    self.msg = Markup(msg.format(user=user, entity=entity_html,
                                 entity_type=e.entity_type.rsplit('.', 1)[-1],
                                 entity_id=e.entity_id,))
    tmpl = get_template_attribute('admin/_macros.html', 'm_audit_entry')
    return tmpl(self)

  def format_model_changes(self, changes):
    formatted_items = []
    render = render_template_string
    for key, value in changes.items():
      key = render(u'<strong>{{ key }}</strong>', key=key)
      value_fmt = u'<em>{{ value }}</em>'

      if isinstance(value, dict):
        submodel_changes = u'\n'.join(
          u'<li>{}</li>'.format(msg) for msg in self.format_model_changes(value))
        submodel_changes = u'<ul>{}</ul>'.format(submodel_changes)
        change_msg = _(u'{key} changed:').format(key=key) + submodel_changes
      else:
        old_value, new_value = value
        if old_value and old_value is not NO_VALUE:
          old_value = render(value_fmt, value=old_value)
          change_msg = _(u'{key} changed from {old_value} to {new_value}')
        else:
          change_msg = _(u'{key} set to {new_value}')

        change_msg = change_msg.format(key=key, old_value=old_value,
                                       new_value=new_value)

      formatted_items.append(Markup(change_msg))
    return formatted_items


class SecurityEntryPresenter(BaseEntryPresenter):

  def __init__(self, entry):
    assert isinstance(entry, SecurityAudit)
    super(SecurityEntryPresenter, self).__init__(entry.manager, entry.happened_at)
    self.entry = entry

  @staticmethod
  def prefetch(entries):
    pass
    _cls_ids = {}
    _oids = {}
    for e in entries:
      if e.entry.object:
        model_name, oid = e.entry.object.split(':', 1)
        oid = int(oid)
        _oids[e.entry.object] = (model_name, oid,)
        _cls_ids.setdefault(model_name, []).append(oid)

    for cls_name, ids in _cls_ids.items():
      if not (cls_name and ids):
        pass
      model = SecurityEntryPresenter.model(cls_name)
      _cls_ids[cls_name] = model.query.filter(model.id.in_(ids)).all()

    for e in entries:
      oid = _oids.get(e.entry.object)
      if oid is not None:
        model_name, oid = oid
        e.object = e.model(model_name).query.get(oid)

  def render(self):
    render = render_template_string
    e = self.entry

    manager = render(
      u'<img src="{{ url_for("social.user_mugshot", user_id=e.manager_id, '
      's=16) }}" alt="" />'
      '<a href="''{{ url_for("social.user", user_id=e.manager_id) }}">'
      '{{ e.manager.name }}</a>', e=e)

    if self.entry.user:
      principal = render(self._USER_FMT, user=self.entry.user)
    elif self.entry.group:
      principal = render(self._GROUP_FMT, group=self.entry.group)
    else:
      principal = u''

    entity = u''
    if e.object:
      entity = render(
        u'<a href="{{ url_for(entity) }}">{{ entity.path or entity.name }}</a>',
        entity=self.object)

      if e.op == e.SET_INHERIT:
        msg = _(u'{manager} has activated inheritance on {entity}')
      elif e.op == e.UNSET_INHERIT:
        msg = _(u'{manager} has deactivated inheritance on {entity}')
      elif e.op == e.GRANT:
        msg = _(u'{manager} has given role "{role}" to {principal} '
                'on {entity}')
      elif e.op == e.REVOKE:
        msg = _(u'{manager} has revoked role "{role}" from '
                '{principal} on {entity}')
      else:
        raise Exception("Invalid entity op: {}".format(e.op))
    else:
      if e.op == e.GRANT:
        msg = _(u'{manager} has given role "{role}" to {principal}')
      elif e.op == e.REVOKE:
        msg = _(u'{manager} has revoked role "{role}" from {principal}')
      else:
        raise Exception("Invalid entity op: {}".format(e.op))

    self.msg = Markup(msg.format(manager=manager,
                                 principal=principal,
                                 role=e.role,
                                 entity=entity))
    tmpl = get_template_attribute('admin/_macros.html', 'm_security_entry')
    return tmpl(self)
