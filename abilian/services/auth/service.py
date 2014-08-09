# coding=utf-8
"""
"""
from __future__ import absolute_import
import logging
from datetime import datetime, timedelta

from flask import current_app, g, request, url_for
from flask.ext.login import (
  current_user, user_logged_out, user_logged_in, login_user
)
from flask.ext.babel import lazy_gettext as _l

from abilian.services import Service
from abilian.core.models.subjects import User
from abilian.core.extensions import db, login_manager
from abilian.web.action import actions
from abilian.web.nav import NavItem, NavGroup

from .views import login as login_views
from .models import LoginSession

__all__ = ['AuthService', 'user_menu']

logger = logging.getLogger(__name__)


def is_anonymous(context):
  return current_user.is_anonymous()


def is_authenticated(context):
  return not is_anonymous(context)

user_menu = NavGroup(
  'user', 'authenticated', title=lambda c: current_user.name,
  icon='user',
  condition=is_authenticated,
  items=(
      NavItem('user', 'logout', title=_l(u'Logout'), icon='log-out',
              url=lambda context: url_for('login.logout'),
              divider=True),
  ))


_ACTIONS = (
  NavItem('user', 'login', title=_l(u'Login'), icon='log-in',
          url=lambda context: url_for('login.login_form'),
          condition=is_anonymous),
  user_menu,
)


class AuthService(Service):
  name = 'auth'

  def init_app(self, app):
    login_manager.init_app(app)
    login_manager.login_view = 'login.login_form'
    Service.init_app(self, app)
    self.login_url_prefix = app.config.get('LOGIN_URL', '/user')
    app.before_request(self.before_request)
    user_logged_in.connect(self.user_logged_in, sender=app)
    user_logged_out.connect(self.user_logged_out, sender=app)
    app.register_blueprint(login_views, url_prefix=self.login_url_prefix)
    with app.app_context():
      actions.register(*_ACTIONS)

  @login_manager.user_loader
  def load_user(user_id):
    try:
      user = User.query.get(user_id)

      if user and not user.can_login:
        # if a user is edited and should not have access any more, this will
        # ensure he cannot continue if he had an active session
        return None
    except:
      logger.warning("Error during login.", exc_info=True)
      session = current_app.db.session()
      if not session.is_active:
        # session is not usable, rollback should restore a usable session
        session.rollback()

      return None

    app = current_app._get_current_object()
    app.services[AuthService.name].user_logged_in(app, user)
    return user

  def user_logged_in(self, app, user):
    # `g.user` is used as `current_user`, but `current_user` is actually looking
    # for `request.user` whereas `g` is on app local stack.
    #
    # `g.logged_user` is the actual user. In the future for example we may allow
    # a manager to see site as another user (impersonate), or propose a "see as
    # anonymous" function
    g.user = g.logged_user = user
    security = app.services.get('security')
    g.is_manager = (user
                    and not user.is_anonymous()
                    and ((security.has_role(user, 'admin')
                          or security.has_role(user, 'manager'))))

  def user_logged_out(self, app, user):
    del g.user
    del g.logged_user
    del g.is_manager

  def before_request(self):
    if current_app.testing and current_app.config.get("NO_LOGIN"):
      # Special case for tests
      user = User.query.get(0)
      login_user(user, False, True)
    else:
      user = current_user._get_current_object()

    # ad-hoc security test based on requested path
    #
    # FIXME: those security checks should be made by concerned modules
    path = request.path

    # No need for authentication and loginsession time update on the login
    # screen or the static assets
    if (path.startswith(self.login_url_prefix + '/')
        or path.startswith(current_app.static_url_path + '/')):
      return

    # if you really want login required anywhere, put this in a
    # app.before_request handler:
    #
    # if not user.is_authenticated():
    #   return redirect(url_for('login.login_form', next=request.url))

    # Update last_active every 60 seconds only so as to not stress the database
    # too much.
    if user.is_anonymous():
      return

    now = datetime.utcnow()
    if (user.last_active is None or
        now - user.last_active > timedelta(minutes=1)):
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
