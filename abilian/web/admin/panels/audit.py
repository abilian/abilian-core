# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import datetime
from itertools import chain

import pytz
import sqlalchemy as sa
from flask import (get_template_attribute, render_template,
                   render_template_string, request)
from flask_babel import format_date, get_locale
from markupsafe import Markup
from sqlalchemy.orm.attributes import NO_VALUE
from werkzeug.exceptions import InternalServerError
from werkzeug.routing import BuildError

from abilian.core.entities import Entity, all_entity_classes
from abilian.core.extensions import db
from abilian.core.models.subjects import User
from abilian.core.util import local_dt
from abilian.i18n import _
from abilian.services.audit import AuditEntry
from abilian.services.security import SecurityAudit
from abilian.web.util import url_for
from abilian.web.views.base import JSONView

from ..panel import AdminPanel


def format_date_for_input(date):
    date_fmt = get_locale().date_formats['short'].pattern
    date_fmt = date_fmt \
        .replace('MMMM', 'MM') \
        .replace('MMM', 'MM')  # force numerical months
    return format_date(date, date_fmt)


class JSONUserSearch(JSONView):
    """
    Search users by fullname
    """

    def data(self, q, *args, **kwargs):
        q = q.replace(u'%', u' ').strip().lower()

        if not q or len(q) < 2:
            raise InternalServerError()

        query = User.query
        lower = sa.sql.func.lower
        filters = []
        for part in q.split(u' '):
            filters.append(sa.sql.or_(
                lower(User.first_name).like(part + "%"), lower(
                    User.last_name).like(part + "%")))

        filters = sa.sql.and_(*filters) if len(filters) > 1 else filters[0]

        if u'@' in q:
            # FIXME: where does this 'part' variable come from ?
            filters = sa.sql.or_(
                lower(User.email).like('%' + part + '%'), filters)

        query = query \
            .filter(filters) \
            .order_by(User.last_name, User.first_name)

        result = {'results': [
            {'id': obj.id,
             'text':
             u'{} {} ({})'.format(obj.first_name, obj.last_name, obj.email)}
            for obj in query.values(User.id, User.first_name, User.last_name,
                                    User.email)
        ]}
        return result


class AuditPanel(AdminPanel):
    """Global audit log.

    Can receive one out of two possible GET parameter, datetime type:

    * before: events that happened immediately before 't' (less recent than 't')
    * after: events that happened immediately after 't' (more recent than 't')
    """
    id = 'audit'
    label = 'Audit trail'
    icon = 'list-alt'

    def install_additional_rules(self, add_url_rule):
        add_url_rule('/search_users',
                     view_func=JSONUserSearch.as_view(b'search_users'))

    # noinspection PyComparisonWithNone
    def get(self):
        LIMIT = 30

        base_audit_q = AuditEntry.query
        base_security_q = SecurityAudit.query

        before = request.args.get('before')
        after = request.args.get('after')

        # filter on user
        filter_user = None
        user_id = request.args.get('user')
        if user_id:
            user_id = int(user_id)
            filter_user = User.query.get(user_id)
            base_audit_q = base_audit_q \
                .filter(AuditEntry.user == filter_user)
            base_security_q = base_security_q \
                .filter(SecurityAudit.manager == filter_user)

        # filter by types
        all_classes = sorted(all_entity_classes(), key=lambda c: c.__name__)
        all_types = set(e.entity_type for e in all_classes)
        filter_types = set(request.args.getlist('types')) & all_types
        if filter_types:
            if len(filter_types) == 1:
                t = list(filter_types)[0]
                audit_expr = AuditEntry.entity_type == t
                sec_expr = sa.sql.or_(SecurityAudit.object == None,
                                      Entity._entity_type == t)
            else:
                audit_expr = AuditEntry.entity_type.in_(filter_types)
                sec_expr = sa.sql.or_(SecurityAudit.object == None,
                                      Entity._entity_type.in_(filter_types))

            base_audit_q = base_audit_q.filter(audit_expr)
            base_security_q = base_security_q \
                .join(SecurityAudit.object) \
                .filter(sec_expr) \
                .reset_joinpoint()

        def after_query(q, model, date):
            return q \
                .filter(model.happened_at > date) \
                .order_by(model.happened_at.asc())

        def before_query(q, model, date):
            return q \
                .filter(model.happened_at < date) \
                .order_by(model.happened_at.desc())

        if after:
            after = datetime.strptime(after, u'%Y-%m-%dT%H:%M:%S.%f')
            audit_q = after_query(base_audit_q, AuditEntry, after)
            security_q = after_query(base_security_q, SecurityAudit, after)
        else:
            before = (datetime.strptime(before, u'%Y-%m-%dT%H:%M:%S.%f') if
                      before else datetime.utcnow())
            audit_q = before_query(base_audit_q, AuditEntry, before)
            security_q = before_query(base_security_q, SecurityAudit, before)

        audit_entries = audit_q \
            .options(sa.orm.joinedload(AuditEntry.entity)) \
            .limit(LIMIT) \
            .all()
        security_entries = security_q \
            .options(sa.orm.joinedload(SecurityAudit.object)) \
            .limit(LIMIT) \
            .all()
        # audit_entries = []
        all_entries = list(chain(
            (AuditEntryPresenter(e) for e in audit_entries), (
                SecurityEntryPresenter(e) for e in security_entries)))
        all_entries.sort()

        if after:
            all_entries = all_entries[:LIMIT]
        else:
            all_entries = all_entries[-LIMIT:]

        all_entries.reverse()  # event are presented from most to least recent

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
            top_date = entries[0][1][0].date.astimezone(pytz.utc).replace(
                tzinfo=None)
            lowest_date = entries[-1][1][-1].date \
                .astimezone(pytz.utc) \
                .replace(tzinfo=None)

            after_queries = (
                after_query(base_audit_q, AuditEntry, top_date),
                after_query(base_security_q, SecurityAudit, top_date),)

            before_queries = (
                before_query(base_audit_q, AuditEntry, lowest_date),
                before_query(base_security_q, SecurityAudit,
                             lowest_date).limit(1),)

            if not any(q.limit(1).first() is not None for q in after_queries):
                top_date = u''
            else:
                top_date = top_date.isoformat()

            if not any(q.first() is not None for q in before_queries):
                lowest_date = u''
            else:
                lowest_date = lowest_date.isoformat()

        current_date = None
        if entries:
            current_date = format_date_for_input(entries[0][0])

        # build prev/next urls
        url_params = {}
        if filter_user:
            url_params['user'] = filter_user.id
        if filter_types:
            url_params['types'] = list(filter_types)[0]

        return render_template("admin/audit.html",
                               entries=entries,
                               filter_user=filter_user,
                               all_classes=[(c.__name__, c.entity_type)
                                            for c in all_classes],
                               filter_types=filter_types,
                               url_params=url_params,
                               current_date=current_date,
                               top_date=top_date,
                               lowest_date=lowest_date)


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


class AuditEntryPresenter(BaseEntryPresenter):

    def __init__(self, entry):
        assert isinstance(entry, AuditEntry)
        super(AuditEntryPresenter, self).__init__(entry.user, entry.happened_at)
        self.entry = entry

    def render(self):
        render = render_template_string
        e = self.entry
        user = render(self._USER_FMT, user=e.user)
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
        elif e.op == 2:
            msg = _(u'{user} has deleted {entity_type}: {entity_id} "{entity}"')
        else:
            raise Exception("Bad entry type: {}".format(e.type))

        self.msg = Markup(msg.format(user=user,
                                     entity=entity_html,
                                     entity_type=e.entity_type.rsplit('.', 1)[
                                         -1],
                                     entity_id=e.entity_id,))
        tmpl = get_template_attribute('admin/_macros.html', 'm_audit_entry')
        return tmpl(self)


class SecurityEntryPresenter(BaseEntryPresenter):

    def __init__(self, entry):
        assert isinstance(entry, SecurityAudit)
        super(SecurityEntryPresenter, self).__init__(entry.manager,
                                                     entry.happened_at)
        self.entry = entry

    def render(self):
        render = render_template_string
        e = self.entry

        manager = render(
            u'<img class="avatar" '
            u'src="{{ user_photo_url(user=e.manager, size=16) }}" alt="" />'
            u'<a href="'
            '{{ url_for("social.user", user_id=e.manager.id) }}">'
            u'{{ e.manager.name }}</a>',
            e=e)

        if self.entry.user:
            principal = render(self._USER_FMT, user=self.entry.user)
        elif self.entry.group:
            principal = render(self._GROUP_FMT, group=self.entry.group)
        else:
            principal = u''

        entity = u''
        if e.object_id:
            entity_url = None
            entity_name = e.object_name
            if e.object:
                entity_name = getattr(e.object, 'path', e.object.name)
                entity_url = url_for(e.object)

            entity = render(u'{%- if url %}<a href="{{ url }}">{%- endif %}'
                            u'{{ name }}{%- if url %}</a>{%- endif %}',
                            url=entity_url,
                            name=entity_name)

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
