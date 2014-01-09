# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import (current_app, render_template, request, flash,
                   redirect, url_for)
from flask.ext.babel import gettext as _, lazy_gettext as _l
from abilian.web import csrf


from ..panel import AdminPanel


class Key(object):
  def __init__(self, id, type_, label=None, description=None):
    self.id = id
    self.type = type_
    self.label = label
    self.description = description


#FIXME: the settings panel should offer hooks for external modules and thus
#provide unified interface for site settings / customization

class SettingsPanel(AdminPanel):
  id = 'settings'
  label = _l(u'Settings')
  icon = 'cog'

  # FIXME: this is very basic, and we support only "string" at this time. A form
  # shoud be used. Really.
  _keys = (
    Key('SITE_NAME', 'string', _l(u'Site name')),
    Key('MAIL_SENDER', 'string', _l(u'Mail sender')),
    )

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
        value = request.form.get(key.id).strip()
        settings.set(key.id, value, key.type)

      current_app.db.session.commit()

      # FIXME: this is weak: only this process will have its config changed;
      # full reload of app stack (web workers + celery workers) has to be done
      # manually.
      current_app.config.update(settings.as_dict())
      flash(_(u'Changes saved.'))

    return redirect(url_for('.settings'))
