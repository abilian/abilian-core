# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging
from datetime import datetime, timedelta

from flask import current_app, g, redirect, request, url_for
from flask_babel import lazy_gettext as _l
from flask_login import current_user, login_user, user_logged_in, \
    user_logged_out
from werkzeug.exceptions import Forbidden

from abilian.core.extensions import db, login_manager
from abilian.core.models.subjects import User
from abilian.core.signals import user_loaded
from abilian.services import Service, ServiceState
from abilian.web.action import DynamicIcon, actions
from abilian.web.nav import NavGroup, NavItem

from .models import LoginSession
from .views import login as login_views

__all__ = ['AuthService', 'user_menu']

logger = logging.getLogger(__name__)


def is_anonymous(context):
    return current_user.is_anonymous


def is_authenticated(context):
    return not is_anonymous(context)


def _user_photo_endpoint():
    from abilian.web.views import images  # late import: avoid circular import
    return images.user_url_args(current_user, 16)[0]


def _user_photo_icon_args(icon, url_args):
    from abilian.web.views import images  # late import avoid circular import
    return images.user_url_args(current_user, max(icon.width, icon.height))[1]


user_menu = NavGroup(
    'user',
    'authenticated',
    title=lambda c: current_user.name,
    icon=DynamicIcon(
        endpoint=_user_photo_endpoint,
        css='avatar',
        size=20,
        url_args=_user_photo_icon_args,
    ),
    condition=is_authenticated,
    items=(
        NavItem(
            'user',
            'logout',
            title=_l('Logout'),
            icon='log-out',
            url=lambda context: url_for('login.logout'),
            divider=True,
        ),
    ),
)

_ACTIONS = (
    NavItem(
        'user',
        'login',
        title=_l('Login'),
        icon='log-in',
        url=lambda context: url_for('login.login_form'),
        condition=is_anonymous,
    ),
    user_menu,
)


class AuthServiceState(ServiceState):
    """State class for :class:`AuthService`"""

    def __init__(self, *args, **kwargs):
        super(AuthServiceState, self).__init__(*args, **kwargs)
        self.bp_access_controllers = {None: []}
        self.endpoint_access_controllers = {}

    def add_bp_access_controller(self, blueprint, func):
        self.bp_access_controllers.setdefault(blueprint, []).append(func)

    def add_endpoint_access_controller(self, endpoint, func):
        self.endpoint_access_controllers.setdefault(endpoint, []).append(func)


class AuthService(Service):
    name = 'auth'
    AppStateClass = AuthServiceState

    def init_app(self, app):
        login_manager.init_app(app)
        login_manager.login_view = 'login.login_form'
        Service.init_app(self, app)
        self.login_url_prefix = app.config.get('LOGIN_URL', '/user')
        app.before_request(self.do_access_control)
        app.before_request(self.update_user_session_data)
        user_logged_in.connect(self.user_logged_in, sender=app)
        user_logged_out.connect(self.user_logged_out, sender=app)
        app.register_blueprint(login_views, url_prefix=self.login_url_prefix)
        with app.app_context():
            actions.register(*_ACTIONS)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user = User.query.get(user_id)

            if not user or not user.can_login:
                # if a user is edited and should not have access any more, this
                # will ensure they cannot continue if he had an active session
                return None
        except BaseException:
            logger.warning("Error during login.", exc_info=True)
            session = db.session()
            if not session.is_active:
                # session is not usable, rollback should restore a usable
                # session
                session.rollback()

            return None

        app = current_app._get_current_object()
        app.services[AuthService.name].user_logged_in(app, user)
        user_loaded.send(app, user=user)
        return user

    def user_logged_in(self, app, user):
        # `g.user` is used as `current_user`, but `current_user` is actually looking
        # for `request.user` whereas `g` is on app local stack.
        #
        # `g.logged_user` is the actual user. In the future for example we may allow
        # a manager to see site as another user (impersonate), or propose a "see as
        # anonymous" function
        g.user = g.logged_user = user
        is_anonymous = user is None or user.is_anonymous
        security = app.services.get('security')
        g.is_manager = (
            user and not is_anonymous and ((
                security.has_role(user, 'admin') or
                security.has_role(user, 'manager')
            ))
        )

    def user_logged_out(self, app, user):
        if hasattr(g, 'user'):
            del g.user
            del g.logged_user
            del g.is_manager

    def redirect_to_login(self, next_url=True):
        kw = {}
        if next_url is not False:
            kw['next'] = request.url if next_url is True else next_url

        return redirect(url_for(login_manager.login_view, **kw))

    def do_access_control(self):
        """`before_request` handler to check if user should be redirected to
        login page."""
        from abilian.services import get_service

        if current_app.testing and current_app.config.get("NO_LOGIN"):
            # Special case for tests
            user = User.query.get(0)
            login_user(user, force=True)
            return

        state = self.app_state
        user = current_user._get_current_object()

        # Another special case for tests
        if current_app.testing and getattr(user, 'is_admin', False):
            return

        security = get_service('security')
        user_roles = frozenset(security.get_roles(user))
        endpoint = request.endpoint
        blueprint = request.blueprint

        access_controllers = []
        access_controllers.extend(state.bp_access_controllers.get(None, []))

        if blueprint and blueprint in state.bp_access_controllers:
            access_controllers.extend(state.bp_access_controllers[blueprint])

        if endpoint and endpoint in state.endpoint_access_controllers:
            access_controllers.extend(state.endpoint_access_controllers[endpoint])

        for access_controller in reversed(access_controllers):
            verdict = access_controller(user=user, roles=user_roles)
            if verdict is None:
                continue
            elif verdict is True:
                return
            else:
                if user.is_anonymous:
                    return self.redirect_to_login()
                raise Forbidden()

        # default policy
        if current_app.config.get('PRIVATE_SITE') and user.is_anonymous:
            return self.redirect_to_login()

    def update_user_session_data(self):
        user = current_user
        if current_user.is_anonymous:
            return

        # Update last_active every 60 seconds only so as to not stress
        # the database too much.
        now = datetime.utcnow()
        if (
            user.last_active is None or
            (now - user.last_active) > timedelta(minutes=1)
        ):
            user.last_active = now
            db.session.add(user)
            db.session.commit()

        refresh_login_session(user)


def refresh_login_session(user):
    now = datetime.utcnow()
    session = LoginSession.query.get_active_for(user)
    if not session:
        return

    from_now = now - session.last_active_at

    if from_now > timedelta(hours=1):
        session.ended_at = session.last_active_at
        session = LoginSession.new()
        db.session.add(session)
        db.session.commit()
    elif from_now > timedelta(minutes=1):
        session.last_active_at = now
        db.session.commit()
