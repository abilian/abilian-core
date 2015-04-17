# coding=utf-8
"""
"""
from __future__ import absolute_import

from celery import task, Celery
from celery.app.task import Task
from celery.task import PeriodicTask as CeleryPeriodicTask
from celery.loaders.base import BaseLoader
from celery.utils.imports import symbol_by_name

from flask import has_app_context, current_app as flask_current_app
from flask.helpers import locked_cached_property


def default_app_factory():
  from abilian.app import Application
  return Application()


def is_celery_setting(key):
  return key.startswith('CELERY') \
    or key in ('BROKER_URL',)


class FlaskLoader(BaseLoader):
  """
  """
  #: override this in your project
  #: this can be a function or a class
  flask_app_factory = "abilian.core.celery.default_app_factory"
  app_context = None

  @locked_cached_property
  def flask_app(self):
    if has_app_context():
      return flask_current_app._get_current_object()

    self.flask_app_factory = symbol_by_name(self.flask_app_factory)
    app = self.flask_app_factory()

    if 'sentry' in app.extensions:
      from raven.contrib.celery import register_signal, register_logger_signal
      client = app.extensions['sentry'].client
      client.tags['process_type'] = 'celery task'
      register_signal(client)
      register_logger_signal(client)

    return app

  def read_configuration(self):
    app = self.flask_app
    cfg = {k: v for k, v in app.config.items() if is_celery_setting(k)}
    self.configured = True
    return cfg


class FlaskTask(Task):
  """
  Base Task class for :FlaskCelery: based applications.
  """
  abstract = True
  def __call__(self, *args, **kwargs):
    if self.request.is_eager:
      # this is here mainly because flask_sqlalchemy (as of 2.0) will remove
      # session on app context teardown.
      #
      # Unfortunatly when using eager tasks (during dev and tests, mostly),
      # calling apply_async() during after_commit() will remove session because
      # app_context would be pushed and popped. The TB looks like:
      #
      # sqlalchemy/orm/session.py: in transaction.commit:
      #     if self.session._enable_transaction_accounting:
      # AttributeError: 'NoneType' object has no attribute
      #                 '_enable_transaction_accounting'
      #
      # FIXME: also test has_app_context()?
      return super(FlaskTask, self).__call__(*args, **kwargs)

    with self.app.loader.flask_app.app_context():
      return super(FlaskTask, self).__call__(*args, **kwargs)


class PeriodicTask(FlaskTask, CeleryPeriodicTask):
  __doc__ = CeleryPeriodicTask.__doc__
  abstract = True


def periodic_task(*args, **options):
  """Deprecated decorator, please use :setting:`CELERYBEAT_SCHEDULE`."""
  return task(**dict({'base': PeriodicTask}, **options))


class FlaskCelery(Celery):
  # can be overriden on command line with --loader
  loader_cls = FlaskLoader
  task_cls = FlaskTask
