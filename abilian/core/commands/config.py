# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging
import os
from pathlib import Path

from flask import current_app
from flask_script import Manager
from jinja2 import Environment, Markup, PackageLoader

from .base import log_config, logger

#: sub-manager for config commands
manager = Manager(
    description="Show config / create default config",
    help="Show config / create default config",
)


@manager.command
def show(only_path=False):
    """Show the current config."""
    logger.setLevel(logging.INFO)
    infos = [
        "\n",
        'Instance path: "{}"'.format(current_app.instance_path),
        'CONFIG_ENVVAR: "{}"'.format(current_app.CONFIG_ENVVAR),
    ]

    logger.info("\n  ".join(infos))

    if not only_path:
        log_config(current_app.config)


class DefaultConfig(object):
    SQLALCHEMY_DATABASE_URI = ""

    PRODUCTION = False
    LOGGING_CONFIG_FILE = "logging.yml"

    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ECHO = False
    REDIS_URI = "redis://localhost:6379/1"

    DEBUG = True
    ASSETS_DEBUG = True
    DEBUG_TB_ENABLED = True
    TEMPLATE_DEBUG = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PROFILER_ENABLED = False

    BROKER_URL = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

    CELERYD_PREFETCH_MULTIPLIER = 1
    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    WHOOSH_BASE = "whoosh"

    SITE_NAME = ""
    MAIL_SENDER = ""
    UNOCONV_LOCATION = "/usr/bin/unoconv"

    def __init__(self, logging_file=None):
        self.SESSION_COOKIE_NAME = "{}-session".format(current_app.name)
        self.SECRET_KEY = os.urandom(24)

        db_dir = Path(current_app.instance_path) / "data"
        if not db_dir.exists():
            db_dir.mkdir()
        self.SQLALCHEMY_DATABASE_URI = "sqlite:///{}/data/db.sqlite".format(
            current_app.instance_path
        )

        if logging_file:
            self.LOGGING_CONFIG_FILE = str(logging_file)


class ReprProxy(object):
    """Proxy an object and apply repr() + Mark safe when accesing an attribute.

    Used in jinja templates.
    """

    def __init__(self, obj):
        self.__obj = obj

    def __getattr__(self, name):
        return Markup(repr(self.__obj.__getattribute__(name)))


def write_config(config_file, config):
    jinja_env = Environment(loader=PackageLoader(__name__))
    template = jinja_env.get_template("config.py.jinja2")

    with Path(config_file).open("w") as f:
        f.write(template.render(cfg=ReprProxy(config)))
    logger.info('Generated "%s"', config_file)


def maybe_write_logging(logging_file):
    if Path(logging_file).exists():
        logger.info(
            'Logging config file "%s" already exists, skipping creation.', logging_file
        )
        return

    jinja_env = Environment(loader=PackageLoader(__name__))
    template = jinja_env.get_template("logging.yml.jinja2")

    with Path(logging_file).open("w") as f:
        f.write(template.render())
    logger.info('Generated "%s"', logging_file)


@manager.command
def init(filename="config.py", logging_config="logging.yml"):
    """Create default config files in instance folder.

    * [FILENAME] (default: "config.py")
    * [LOGGING_CONFIG] (default: logging.yml)

    Defaults are tailored for development.
    """
    config_file = Path(current_app.instance_path) / filename
    logging_file = Path(current_app.instance_path) / logging_config

    if config_file.exists():
        logger.info('Config file  "%s" already exists! Abort.', config_file)
        return 1

    config = DefaultConfig(logging_file=logging_config)
    write_config(config_file, config)
    maybe_write_logging(logging_file)
