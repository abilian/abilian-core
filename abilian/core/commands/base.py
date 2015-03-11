# coding=utf-8
from __future__ import absolute_import
import os
import logging
from pprint import pformat

import sqlalchemy as sa

from flask import current_app
from flask.ext.script import Manager, prompt_pass

from abilian.core.logging import patch_logger
from abilian.core.extensions import db
from abilian.core.models.subjects import User
from abilian.services import get_service

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


@manager.command
def run(port=None):
  """
  Like runserver, also print application configuration.
  """
  app = current_app
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


@manager.command
def createuser(email, password, role=None, name=None, first_name=None):
  """
  Adds an admin user with given email and password.
  """
  user = User(email=email, password=password,
              last_name=name, first_name=first_name,
              can_login=True)
  db.session.add(user)

  if role in ('admin',):
    # FIXME: add other valid roles
    security = get_service('security')
    security.grant_role(user, role)

  db.session.commit()
  print "User {} added".format(email)


@manager.command
def createadmin(email, password, name=None, first_name=None):
  createuser(email, password, role='admin', name=name, first_name=first_name)


@manager.command
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
