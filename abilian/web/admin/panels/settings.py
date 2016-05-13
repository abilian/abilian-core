# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from datetime import timedelta

from flask import (current_app, flash, redirect, render_template, request,
                   url_for)
from flask_babel import gettext as _
from flask_babel import lazy_gettext as _l
from jinja2 import Template

from abilian.web import csrf

from ..panel import AdminPanel


class Key(object):

    template = Template(u'<input type="text" class="form-control" '
                        u'name="{{ key.id }}" value="{{ config[key.id] }}" />')

    def __init__(self, id, type_, label=None, description=None):
        self.id = id
        self.type = type_
        self.label = label
        self.description = description

    def __html__(self):
        return render_template(self.template,
                               key=self,
                               config=current_app.config)

    def value_from_request(self):
        return request.form.get(self.id).strip()


class SessionLifeTimeKey(Key):

    template = 'admin/settings_session_lifetime.html'

    def __init__(self):
        Key.__init__(
            self,
            'PERMANENT_SESSION_LIFETIME',
            'timedelta',
            label=_l(u'Session lifetime'),
            description=_l(u'Session expiration time after last visit. '
                           u'When session is expired user must login again.'))

    def value_from_request(self):
        form = request.form
        days = max(0, int(form.get(self.id + ':days') or 0))
        hours = min(23, max(0, int(form.get(self.id + ':hours') or 0)))
        minutes = min(59, max(0, int(form.get(self.id + ':minutes') or 0)))

        if (days + hours) == 0 and minutes < 10:
            # avoid dummy sessions durations: minimum is 10 minutes
            flash(_(u'Minimum session lifetime is 10 minutes. '
                    u'Value has been adjusted.'),
                  'warning',)
            minutes = 10

        return timedelta(days=days, hours=hours, minutes=minutes)

    def _get_current(self, field):
        td = current_app.config.get(self.id)
        if td:
            if field == 'days':
                return td.days
            elif field == 'hours':
                return int(td.seconds / 3600)
            elif field == 'minutes':
                return int(td.seconds % 3600 / 60)
        return 0

    @property
    def days(self):
        return self._get_current('days')

    @property
    def hours(self):
        return self._get_current('hours')

    @property
    def minutes(self):
        return self._get_current('minutes')

#FIXME: the settings panel should offer hooks for external modules and thus
#provide unified interface for site settings / customization


class SettingsPanel(AdminPanel):
    id = 'settings'
    label = _l(u'Settings')
    icon = 'cog'

    # FIXME: this is very basic, and we support only "string" at this time. A form
    # shoud be used. Really.
    _keys = (Key('SITE_NAME', 'string', _l(u'Site name')),
             Key('MAIL_SENDER', 'string', _l(u'Mail sender')),
             SessionLifeTimeKey(),)

    @property
    def settings(self):
        return current_app.services.get('settings').namespace('config')

    def get(self):
        return render_template('admin/settings.html', keys=self._keys,)

    @csrf.protect
    def post(self):
        action = request.form.get("action")

        if action == u'save':
            settings = self.settings
            for key in self._keys:
                value = key.value_from_request()
                settings.set(key.id, value, key.type)

            current_app.db.session.commit()

            # FIXME: this is weak: only this process will have its config changed;
            # full reload of app stack (web workers + celery workers) has to be done
            # manually.
            current_app.config.update(settings.as_dict())
            flash(_(u'Changes saved.'))

        return redirect(url_for('.settings'))
