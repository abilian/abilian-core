# coding=utf-8
"""
Abilian script commands to be used in a project. See `Flask-Script documentation
<http://flask-script.readthedocs.org>`_ for full documentation.

Here is how a `manage.py` can include these commands::

     from flask.ext.script import Manager
     from abilian.commands import setup_abilian_commands

     my_manager = Manager(app)
     setup_abilian_commands(my_manager)

You can also include abilian commands as sub commands::

     from abilian.commands import manager as abilian_manager
     my_manager.add_command('abilian', abilian_manager)

Extensions can add their own commands to :py:data:`~abilian.core.commands.manager`::

     from flask.ext.script import Manager
     from abilian.commands import manager

     @manager.command
     def hello():
         print u"hello"

     # or install subcommands
     sub_manager = Manager(usage='Little extension')
     abilian_manager.add_command('special_commands', sub_manager)
"""
from __future__ import absolute_import
import os
import logging

from flask import current_app
from flask.ext.script import Manager
from abilian.core.extensions import db
from abilian.core.subjects import User
from abilian.services import get_service

from .assets import ManageAssets

__all__ = ['manager', 'setup_abilian_commands']

# Setup basic logging capabilities in case logging is not yet set up. From doc:
# This function does nothing if the root logger already has handlers configured
# for it.
# Allow to remplace "print" statements to be replaced by a logging statements
logging.basicConfig()
logger = logging.getLogger('')

#: ``flask.ext.script.Manager`` instance for abilian commands
manager = Manager(usage='Abilian base commands')


def setup_abilian_commands(manager):
  """
  Register abilian commands on ``manager``.

  :param manager: ``flask.ext.script.Manager`` instance to add commands onto

  Usage exemple::

      from flask.ext.script import Manager
      from abilian.commands import setup_abilian_commands

      my_manager = Manager(app)
      setup_abilian_commands(my_manager)
  """
  abilian_manager = globals()['manager']
  manager._options.extend(abilian_manager._options)

  for name, command in abilian_manager._commands.items():
    manager.add_command(name, command)

  manager.add_command("assets", ManageAssets()) # flask-assets
  return manager


def print_config(config):
  lines = ["Application configuration:"]

  for k, v in sorted(config.items()):
    lines.append("    {}: {}".format(k, v))
  logger.info('\n'.join(lines))

  from abilian.services import conversion
  unoconv = conversion._unoconv_handler.unoconv
  logger.info(
    "Unoconv: {configured_path} ({abspath})\n"
    "Version: {version}".format(
      configured_path=unoconv,
      abspath=os.path.abspath(unoconv),
      version=conversion._unoconv_handler.unoconv_version))


@manager.command
def run():
  """ Likes runserver, also print application configuration.
  """
  app = current_app
  print_config(app.config)

  DEBUG = app.config.get('DEBUG')
  PORT = app.config.get('PORT', 5000)
  app.run(host="0.0.0.0", debug=DEBUG, port=PORT)


@manager.command
def initdb():
  """ Creates application DB.
  """
  current_app.create_db()


@manager.command
def dropdb():
  """ Drops the application DB.
  """
  confirm = raw_input("Are you sure you want to drop the database? (Y/N) ")
  if confirm.lower() == 'y':
    with current_app.app_context():
      current_app.db.drop_all()


@manager.command
def dumproutes():
  """ Dumps all the routes registered in Flask.
  """
  rules = list(current_app.url_map.iter_rules())
  rules.sort(key=lambda x: x.rule)
  for rule in rules:
    print "{} ({}) -> {}".format(rule, " ".join(rule.methods), rule.endpoint)


@manager.command
def createadmin(email, password, name=None, first_name=None):
  """ Adds an admin user with given email and password.
  """
  user = User(email=email, password=password,
              last_name=name, first_name=first_name,
              can_login=True)
  security = get_service('security')
  security.grant_role(user, "admin")
  db.session.add(user)
  db.session.commit()
  print "User {} added".format(email)


@manager.command
def changepassword(email, password):
  """ Changes the password of the given user.
  """
  user = User.query.filter(User.email==email).one()
  user.password = password
  db.session.commit()
  print "Password updated for user {}".format(email)
