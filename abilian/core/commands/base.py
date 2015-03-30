# coding=utf-8
from __future__ import absolute_import

import os
import logging
import runpy
from pprint import pformat

import sqlalchemy as sa

from flask import current_app
from flask.ext.script import Manager, prompt_pass

from abilian.core.logging import patch_logger
from abilian.core.extensions import db
from abilian.core.models.subjects import User
from abilian.services import get_service
from abilian.services.security import Role

__all__ = ['manager', 'logger']

# Setup basic logging capabilities in case logging is not yet set up. From doc:
# This function does nothing if the root logger already has handlers configured
# for it.
# Allow "print" statements to be replaced by a logging statements
logging.basicConfig()
logger = logging.getLogger('')

# PATCH flask.ext.script.Manager.run to force creation of app before run() is
# called. In default implementation, the arg parser is created before the Flask
# application. So we can't use app.script_manager to add commands from
# plugins. If app is created before the arg parser, plugin commands are properly
# registered
_flask_script_manager_run = Manager.run
def _manager_run(self, *args, **kwargs):
  self()
  return _flask_script_manager_run(self, *args, **kwargs)

patch_logger.info(Manager.run)
Manager.run = _manager_run

#: ``flask.ext.script.Manager`` instance for abilian commands
manager = Manager(usage='Abilian base commands')


def _log_config(config):
  lines = ["Application configuration:"]

  if config.get('CONFIGURED'):
    try:
      db_settings = set(current_app.services['settings'].namespace('config').keys())
    except sa.exc.ProgrammingError:
      # there is config.py, db uri, but maybe "initdb" has yet to be run
      db_settings = {}
  else:
    db_settings = {}

  for k, v in sorted(config.items()):
    prefix = '    '
    if k in db_settings:
      prefix = '  * '
    indent = len(k) + 3
    width = 80 - indent
    v = pformat(v, width=width).replace('\n', '\n' + ' ' * indent)
    lines.append("{}{}: {}".format(prefix, k, v))
  logger.info('\n'.join(lines))

  from abilian.services import conversion
  unoconv = conversion._unoconv_handler.unoconv
  logger.info(
    "Unoconv: {configured_path} ({abspath})\n"
    "Version: {version}".format(
      configured_path=unoconv,
      abspath=os.path.abspath(unoconv),
      version=conversion._unoconv_handler.unoconv_version))


def log_config(config):
  original_level = logger.level
  logger.setLevel(logging.INFO)
  try:
    return _log_config(config)
  finally:
    logger.setLevel(original_level)


@manager.option('-p', '--port', dest='port', help='listening port',
                default=5000)
@manager.option('--hide-config', dest='hide_config', action='store_const',
                 const=True, default=False,
                help='don\'t show application configuration on startup')
def run(port, hide_config):
  """
  Like runserver, also print application configuration.
  """
  app = current_app
  if not hide_config:
    log_config(app.config)

  # TODO: pass host and debug as params to
  host = "0.0.0.0"
  debug = app.config.get('DEBUG')
  port = int(port or app.config.get('PORT', 5000))
  app.run(host=host, debug=debug, port=port)


@manager.command
def initdb():
  """
  Creates application DB.
  """
  current_app.create_db()


@manager.command
def dropdb():
  """
  Drops the application DB.
  """
  confirm = raw_input("Are you sure you want to drop the database? (Y/N) ")
  if confirm.lower() == 'y':
    with current_app.app_context():
      current_app.db.drop_all()


@manager.command
def dumproutes():
  """
  Dumps all the routes registered in Flask.
  """
  rules = list(current_app.url_map.iter_rules())
  rules.sort(key=lambda x: x.rule)
  for rule in rules:
    print "{} ({}) -> {}".format(rule, " ".join(rule.methods), rule.endpoint)


# user commands
email_opt = manager.option('email', help='user\'s email')
password_opt = manager.option(
    '-p', '--password', dest='password', default=None,
    help='If absent, a prompt will ask for password',)
role_opt = manager.option(
    '-r', '--role', dest='role',
    choices=[r.name for r in Role.assignable_roles()],
)
name_opt = manager.option(
    '-n', '--name', dest='name', default=None,
    help='Last name (e.g "Smith")')
firstname_opt = manager.option(
    '-f', '--firstname', dest='first_name', default=None,
    help='Fist name (e.g. "John")')

@email_opt
@password_opt
@role_opt
@name_opt
@firstname_opt
def createuser(email, password, role=None, name=None, first_name=None):
  """
  Create new user.
  """
  user = User(email=email, password=password,
              last_name=name, first_name=first_name,
              can_login=True)
  db.session.add(user)

  if password is None:
    password = prompt_pass(u'Password: ')

  if role in ('admin',):
    # FIXME: add other valid roles
    security = get_service('security')
    security.grant_role(user, role)

  db.session.commit()
  print "User {} added".format(email)


@email_opt
@password_opt
@name_opt
@firstname_opt
def createadmin(email, password, name=None, first_name=None):
  """
  Create new administrator.

  Same as `createuser --role='admin'`.
  """
  createuser(email, password, role='admin', name=name, first_name=first_name)


@email_opt
@password_opt
def passwd(email, password=None):
  """
  Changes the password for the given user.
  """
  user = User.query.filter(User.email==email).one()
  if password is None:
    password = prompt_pass(u'New password: ')

  user.set_password(password)
  db.session.commit()
  print "Password updated for user {}".format(email)


@manager.command
def script(path):
  """
  Run given script in the app context.
  """
  runpy.run_path(path, run_name='__main__')
