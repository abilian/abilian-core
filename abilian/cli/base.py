import runpy

import click
from flask.cli import with_appcontext

from abilian.core.extensions import db
from abilian.core.models.subjects import User
from abilian.services import get_service


@click.command()
def initdb():
    db.create_all()


@click.command()
def dropdb():
    """Drop the application DB."""
    confirm = input("Are you sure you want to drop the database? (Y/N) ")
    print(f"Dropping DB using engine: {db}")
    if confirm.lower() == "y":
        # with current_app.app_context():
        db.drop_all()


@click.command()
@click.argument("path", type=click.Path(exists=True))
@with_appcontext
def script(path):
    """Run given script in the app context."""
    runpy.run_path(path, run_name="__main__")


@click.command()
@click.argument("email")
@click.argument("password")
@click.option("--role")
@click.option("--name")
@click.option("--first_name")
@with_appcontext
def createuser(email, password, role=None, name=None, first_name=None):
    """Create new user."""

    if User.query.filter(User.email == email).count() > 0:
        print(f"A user with email '{email}' already exists, aborting.")
        return

    # if password is None:
    #     password = prompt_pass("Password")

    user = User(
        email=email,
        password=password,
        last_name=name,
        first_name=first_name,
        can_login=True,
    )
    db.session.add(user)

    if role in ("admin",):
        # FIXME: add other valid roles
        security = get_service("security")
        security.grant_role(user, role)

    db.session.commit()
    print(f"User {email} added")


# def createadmin(email, password, name=None, first_name=None):
#     """Create new administrator.
#
#     Same as `createuser --role='admin'`.
#     """
#     createuser(email, password, role="admin", name=name, first_name=first_name)


#
# # coding=utf-8
# import logging
# import runpy
# from pprint import pformat
#
# import click
# import sqlalchemy as sa
# import sqlalchemy.exc
# from flask import current_app
# from flask.cli import AppGroup, FlaskGroup, with_appcontext
# from flask_script import Manager, prompt_pass
# from six import text_type
# from six.moves import input, urllib
#
# from abilian.core.extensions import db
# from abilian.core.logging import patch_logger
# from abilian.core.models.subjects import User
# from abilian.services import get_service
# from abilian.services.security import Role
#
# __all__ = ["manager", "logger"]
#
# # Setup basic logging capabilities in case logging is not yet set up. From doc:
# # This function does nothing if the root logger already has handlers configured
# # for it.
# # Allow "print" statements to be replaced by a logging statements
# logging.basicConfig()
# logger = logging.getLogger("")
#
# # PATCH flask_script.Manager.run to force creation of app before run() is
# # called. In default implementation, the arg parser is created before the Flask
# # application. So we can't use app.script_manager to add commands from
# # plugins. If app is created before the arg parser, plugin commands are properly
# # registered
# _flask_script_manager_run = Manager.run
#
#
# def _manager_run(self, *args, **kwargs):
#     self()
#     if "sentry" in self.app.extensions:
#         client = self.app.extensions["sentry"].client
#         client.tags["process_type"] = "shell"
#
#     return _flask_script_manager_run(self, *args, **kwargs)
#
#
# patch_logger.info(Manager.run)
# Manager.run = _manager_run
#
# #: ``flask_script.Manager`` instance for abilian commands
# manager = Manager(usage="Abilian base commands")
#
#
# def _log_config(config):
#     lines = ["Application configuration:"]
#
#     if config.get("CONFIGURED"):
#         settings = get_service("settings")
#         try:
#             db_settings = set(settings.namespace("config").keys())
#         except sa.exc.ProgrammingError:
#             # there is config.py, db uri, but maybe "initdb" has yet to be run
#             db_settings = {}
#     else:
#         db_settings = {}
#
#     for k, v in sorted(config.items()):
#         prefix = "    "
#         if k in db_settings:
#             prefix = "  * "
#         indent = len(k) + 3
#         width = 80 - indent
#         v = pformat(v, width=width).replace("\n", "\n" + " " * indent)
#         lines.append(f"{prefix}{k}: {v}")
#     logger.info("\n".join(lines))
#
#
# def log_config(config):
#     original_level = logger.level
#     logger.setLevel(logging.INFO)
#     try:
#         return _log_config(config)
#     finally:
#         logger.setLevel(original_level)
#
#
# @manager.option("-p", "--port", dest="port", help="listening port", default=5000)
# @manager.option(
#     "--show-config",
#     dest="show_config",
#     action="store_const",
#     const=True,
#     default=False,
#     help="show application configuration on startup",
# )
# @manager.option(
#     "--ssl",
#     dest="ssl",
#     action="store_const",
#     default=False,
#     const=True,
#     help="Enable werkzeug SSL",
# )
# def run(port, show_config, ssl):
#     """Like runserver.
#
#     May also print application configuration if used with
#     --show-config.
#     """
#     app = current_app
#     options = {}
#     if show_config:
#         log_config(app.config)
#
#     # TODO: pass host and debug as params to
#     host = "0.0.0.0"
#     debug = app.config.get("DEBUG")
#     port = int(port or app.config.get("PORT", 5000))
#
#     if ssl:
#         options["ssl_context"] = "adhoc"
#
#     app.run(host=host, debug=debug, port=port, **options)
#
#
# @manager.command
# def routes():
#     """Show all the routes registered in Flask."""
#     output = []
#     for rule in current_app.url_map.iter_rules():
#         methods = ",".join(rule.methods)
#         path = urllib.parse.unquote(rule.rule)
#         output.append((rule.endpoint, methods, path))
#
#     for endpoint, methods, path in sorted(output):
#         print(f"{endpoint:40s} {methods:25s} {path}")
#
#
# @email_opt
# @password_opt
# def passwd(email, password=None):
#     """Change the password for the given user."""
#     user = User.query.filter(User.email == email).one()
#     if password is None:
#         password = prompt_pass("New password: ")
#
#     user.set_password(password)
#     db.session.commit()
#     print(f"Password updated for user {email}")
#
