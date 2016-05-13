# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app, flash, request
from flask.signals import request_started
from flask_wtf.csrf import CsrfProtect
from markupsafe import Markup
from werkzeug.exceptions import BadRequest

from abilian.i18n import _l

wtf_csrf = CsrfProtect()


class AbilianCsrf(object):
    """Csrf error handler, that allows supporting views to gracefully report error
    instead of a plain 400 error.

    views supporting this must
    """
    #: for views that gracefully support csrf errors, this message can be
    #: displayed to user. It can be changed if you have a better one for your
    #: users.
    csrf_failed_message = _l(
        u'Security informations are missing or expired. '
        u'This may happen if you have opened the form for a long time. <br /><br />'
        u'Please try to resubmit the form.')

    def init_app(self, app):
        if 'csrf' not in app.extensions:
            raise RuntimeError(
                'Please install flask_wtf.csrf.CsrfProtect() as "csrf" in extensions'
                ' before AbilianCsrf()')
        app.extensions['csrf'].error_handler(self.csrf_error_handler)
        app.extensions['csrf-handler'] = self
        request_started.connect(self.request_started, sender=app)
        app.before_request(self.before_request)

    def flash_csrf_failed_message(self):
        flash(Markup(self.csrf_failed_message), 'error')

    def request_started(self, app):
        request.csrf_failed = False

    def csrf_error_handler(self, reason):
        request.csrf_failed = reason

    def before_request(self):
        req = request._get_current_object()
        failed = req.csrf_failed

        if not failed:
            return

        rule = req.url_rule
        view = current_app.view_functions[rule.endpoint]
        if getattr(view, 'csrf_support_graceful_failure', False):
            # view can handle it nicely for the user
            return None

        if (hasattr(view, 'view_class') and
                getattr(view.view_class, 'csrf_support_graceful_failure',
                        False)):
            return None

        raise BadRequest(failed)


abilian_csrf = AbilianCsrf()
