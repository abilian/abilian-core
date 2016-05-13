# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app, request
from flask_login import user_logged_in
from raven.contrib.flask import Sentry as RavenExt


class Sentry(RavenExt):

    def init_app(self, app, *args, **kwargs):
        super(Sentry, self).init_app(app, *args, **kwargs)
        user_logged_in.connect(self._on_user_logged_in, sender=app)

    def _on_user_logged_in(self, app, user, *args, **kwargs):
        self.client.user_context(self.get_user_info(request))

    @property
    def raven_js_url(self):
        url = u'//cdn.ravenjs.com/{version}/{plugins}/raven.min.js'
        cfg = current_app.config
        return url.format(version=unicode(cfg['SENTRY_JS_VERSION']),
                          plugins=u','.join(cfg['SENTRY_JS_PLUGINS']))


__all__ = ['Sentry']
