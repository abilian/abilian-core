# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from cgi import escape

import sqlalchemy as sa
from flask import current_app, render_template_string, request
from flask_babel import format_datetime
from flask_login import current_user
from sqlalchemy.sql.expression import asc, desc, func, nullslast, or_
from werkzeug.datastructures import MultiDict

from abilian.core.models.subjects import User, gen_random_password
from abilian.i18n import _
from abilian.services.security.models import Admin, Role
from abilian.web.nav import BreadcrumbItem
from abilian.web.util import url_for
from abilian.web.views import object as views
from abilian.web.views import base
from abilian.web.views.images import user_photo_url

from .forms import UserAdminForm, UserCreateForm


class JsonUsersList(base.JSONView):
    """JSON user list for datatable.
    """

    def data(self, *args, **kw):
        security = current_app.services['security']
        length = int(kw.get("iDisplayLength", 0))
        start = int(kw.get("iDisplayStart", 0))
        sort_col = int(kw.get("iSortCol_0", 1))
        sort_dir = kw.get("sSortDir_0", "asc")
        echo = int(kw.get("sEcho", 0))
        search = kw.get("sSearch", "").replace("%", "").strip().lower()

        end = start + length
        q = User.query \
          .options(sa.orm.subqueryload('groups'),
                   sa.orm.undefer('photo'), ) \
          .filter(User.id != 0)
        total_count = q.count()

        if search:
            # TODO: gérer les accents
            filter = or_(
                func.lower(User.first_name).like("%" + search + "%"),
                func.lower(User.last_name).like("%" + search + "%"),
                func.lower(User.email).like("%" + search + "%"))
            q = q.filter(filter)

        count = q.count()
        SORT_COLS = {
            1: [],  # [User.last_name, User.first_name] will be added anyway
            2: [func.lower(User.email)],
            5: [User.last_active],
        }
        columns = list(SORT_COLS.get(sort_col, []))
        columns.extend([func.lower(User.last_name), func.lower(User.first_name)
                       ])

        direction = asc if sort_dir == 'asc' else desc
        order_by = map(direction, columns)

        # sqlite does not support 'NULLS FIRST|LAST' in ORDER BY clauses
        engine = q.session.get_bind(User.__mapper__)
        if engine.name != 'sqlite':
            order_by[0] = nullslast(order_by[0])

        q = q.order_by(*order_by)

        users = q.slice(start, end).all()

        data = []
        MUGSHOT_SIZE = 45
        for user in users:
            # TODO: this should be done on the browser.
            user_url = url_for(".users_user", user_id=user.id)
            mugshot = user_photo_url(user, size=MUGSHOT_SIZE)
            name = escape(getattr(user, "name") or "")
            email = escape(getattr(user, "email") or "")
            roles = [r
                     for r in security.get_roles(user, no_group_roles=True)
                     if r.assignable]
            columns = []
            columns.append(
                u'<a href="{url}"><img src="{src}" width="{size}" height="{size}">'
                u'</a>'.format(url=user_url,
                               src=mugshot,
                               size=MUGSHOT_SIZE))
            columns.append(u'<a href="{url}">{name}</a>'.format(url=user_url,
                                                                name=name))
            columns.append(u'<a href="{url}"><em>{email}</em></a>'.format(
                url=user_url, email=email))
            columns.append(u'\u2713' if user.can_login else u'')
            columns.append(render_template_string(u'''{%- for g in groups %}
            <span class="badge badge-default">{{ g.name }}</span>
            {%- endfor %}''',
                                                  groups=sorted(user.groups)))
            columns.append(render_template_string(u'''{%- for role in roles %}
            <span class="badge badge-default">{{ role }}</span>
            {%- endfor %}''',
                                                  roles=roles))

            if user.last_active:
                last_active = format_datetime(user.last_active)
            else:
                last_active = _(u'Never logged in')
            columns.append(last_active)

            data.append(columns)

        return {
            "sEcho": echo,
            "iTotalRecords": total_count,
            "iTotalDisplayRecords": count,
            "aaData": data,
        }


# User edit / create views
class UserBase(object):
    Model = User
    pk = 'user_id'
    Form = UserAdminForm
    base_template = 'admin/_base.html'

    def index_url(self):
        return url_for('.users')

    view_url = index_url


class UserEdit(UserBase, views.ObjectEdit):

    def breadcrumb(self):
        label = render_template_string(u'<em>{{ u.email }}</em>', u=self.obj)
        return BreadcrumbItem(label=label, url=u'', description=self.obj.name)

    def get_form_kwargs(self):
        kw = super(UserEdit, self).get_form_kwargs()
        security = current_app.services['security']
        roles = security.get_roles(self.obj, no_group_roles=True)
        kw['roles'] = [r.name for r in roles if r.assignable]
        return kw

    def validate(self):
        if not super(UserEdit, self).validate():
            return False

        if current_user == self.obj:
            # self edit: don't let user shoot themself in the foot
            self.form.can_login.data = True
            roles = self.form.roles
            if Admin.name not in roles.data:
                roles.data.append(Admin.name)
        return True

    def form_valid(self):
        del self.form.confirm_password
        if self.form.password.data:
            self.obj.set_password(self.form.password.data)
        del self.form.password

        return super(UserEdit, self).form_valid()

    def after_populate_obj(self):
        security = current_app.services['security']
        current_roles = security.get_roles(self.obj, no_group_roles=True)
        current_roles = set(r for r in current_roles if r.assignable)
        new_roles = {Role(r) for r in self.form.roles.data}

        for r in (current_roles - new_roles):
            security.ungrant_role(self.obj, r)

        for r in (new_roles - current_roles):
            security.grant_role(self.obj, r)

        return super(UserEdit, self).after_populate_obj()


class UserCreate(UserBase, views.ObjectCreate):
    Form = UserCreateForm
    chain_create_allowed = True

    def get_form_kwargs(self):
        kw = super(UserCreate, self).get_form_kwargs()

        if request.method == 'GET':
            # ensure formdata is not ImmutableMultiDict (request.args)
            data = MultiDict(kw.setdefault('formdata', {}))
            kw['formdata'] = data
            data['can_login'] = True

        return kw

    def form_valid(self):
        if not self.form.password.data:
            self.form.password.data = gen_random_password()

        self.obj.set_password(self.form.password.data)
        del self.form.password
        return super(UserCreate, self).form_valid()
