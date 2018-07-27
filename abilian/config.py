# coding=utf-8
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from typing import Any, Dict

from babel.dates import LOCALTZ
from flask import Flask
from werkzeug.datastructures import ImmutableDict

from abilian.core import redis
from abilian.web.action import Endpoint

default_config = dict(Flask.default_config)  # type: Dict[str, Any]
default_config.update(
    PRIVATE_SITE=False,
    TEMPLATE_DEBUG=False,
    CSRF_ENABLED=True,
    BABEL_ACCEPT_LANGUAGES=["en"],
    DEFAULT_COUNTRY=None,
    PLUGINS=(),
    ADMIN_PANELS=(
        "abilian.web.admin.panels.dashboard.DashboardPanel",
        "abilian.web.admin.panels.audit.AuditPanel",
        "abilian.web.admin.panels.login_sessions.LoginSessionsPanel",
        "abilian.web.admin.panels.settings.SettingsPanel",
        "abilian.web.admin.panels.users.UsersPanel",
        "abilian.web.admin.panels.groups.GroupsPanel",
        "abilian.web.admin.panels.sysinfo.SysinfoPanel",
        "abilian.web.admin.panels.impersonate.ImpersonatePanel",
        "abilian.services.vocabularies.admin.VocabularyPanel",
        "abilian.web.tags.admin.TagPanel",
    ),
    CELERYD_MAX_TASKS_PER_CHILD=1000,
    CELERY_ACCEPT_CONTENT=["pickle", "json", "msgpack", "yaml"],
    CELERY_TIMEZONE=LOCALTZ,
    SENTRY_USER_ATTRS=("email", "first_name", "last_name"),
    SENTRY_INSTALL_CLIENT_JS=True,  # also install client JS
    SENTRY_JS_VERSION="1.1.22",
    # TODO: remove, not needed for recent sentry-js
    SENTRY_JS_PLUGINS=("console", "jquery", "native", "require"),
    SESSION_COOKIE_NAME=None,
    SQLALCHEMY_POOL_RECYCLE=1800,  # 30min. default value in flask_sa is None
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    LOGO_URL=Endpoint("abilian_static", filename="img/logo-abilian-32x32.png"),
    ABILIAN_UPSTREAM_INFO_ENABLED=False,  # upstream info extension
    TRACKING_CODE_SNIPPET="",  # tracking code to insert before </body>
    MAIL_ADDRESS_TAG_CHAR=None,
)
default_config = ImmutableDict(default_config)


# def configure_redis(app):
#     redis.init_app(app)
#
#
# def configure_queue(app):
#     queue.init_app(app, db, sentry)
#
#
# def configure_sentry(app):
#     from flask import session
#
#     sentry.init_app(app)
#
#     @app.before_request
#     def capture_user(*args, **kwargs):
#         if 'uid' in session:
#             sentry.client.user_context({
#                 'id': session['uid'],
#                 'email': session['email'],
#             })
#
#
# def configure_sqlalchemy(app):
#     db.init_app(app)
