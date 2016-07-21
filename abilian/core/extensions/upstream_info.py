# coding=utf-8
"""
Extension for sending informations to upstream server
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import _request_ctx_stack
from flask.signals import request_finished, request_started

from abilian.core.signals import user_loaded


class UpstreamInfo(object):
    """Extension for sending informations to upstream server
    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions['upstream'] = self
        request_started.connect(self.request_started, sender=app)
        request_finished.connect(self.request_finished, sender=app)
        user_loaded.connect(self.user_loaded, sender=app)

        config = app.config
        config.setdefault('ABILIAN_UPSTREAM_INFO_ENABLED', False)
        for key in ('ABILIAN_UPSTREAM_INFO_DISCARD',
                    'ABILIAN_UPSTREAM_INFO_INCLUDE'):
            val = config.get(key, ())
            if val is not None:
                val = frozenset(val)
            config[key] = val

    def request_started(self, app):
        _request_ctx_stack.top.upstream_info = {'Username': 'Anonymous',}

    def request_finished(self, app, response):
        info = _request_ctx_stack.top.upstream_info
        config = app.config
        default_enabled = bool(config['ABILIAN_UPSTREAM_INFO_ENABLED'])
        disabled = config['ABILIAN_UPSTREAM_INFO_DISCARD']
        enabled = config['ABILIAN_UPSTREAM_INFO_INCLUDE']

        for key, val in info.items():
            if (default_enabled and key in disabled or not default_enabled and
                    key not in enabled):
                continue

            header = 'X-' + key
            response.headers[header] = val

    def user_loaded(self, app, user, *args, **kwargs):
        _request_ctx_stack.top.upstream_info['Username'] = user.email


extension = UpstreamInfo()
