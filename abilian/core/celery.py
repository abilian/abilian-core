# coding=utf-8
"""
"""
from __future__ import absolute_import

from celery import Celery
from celery.loaders.base import BaseLoader
from celery.utils.imports import symbol_by_name


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
  _flask_app = None
  app_context = None

  @property
  def flask_app(self):
    if self._flask_app is None:
      self.flask_app_factory = symbol_by_name(self.flask_app_factory)
      app = self._flask_app = self.flask_app_factory()
      self.app_context = app.app_context()

      if 'sentry' in app.extensions:
        from raven.contrib.celery import register_signal, register_logger_signal
        client = app.extensions['sentry'].client
        client.tags['process_type'] = 'celery task'
        register_signal(client)
        register_logger_signal(client)

    return self._flask_app

  def read_configuration(self):
    app = self.flask_app
    cfg = {k: v for k, v in app.config.items() if is_celery_setting(k)}
    self.configured = True
    return cfg

  def on_task_init(self, task_id, task):
    """This method is called before a task is executed."""
    if self.app_context:
      # when CELERY_ALWAYS_EAGER is True: we are not in a worker process but in
      # application process, app_context is not managed by us
      self.app_context.push()

  def on_process_cleanup(self):
    """This method is called after a task is executed."""
    if self.app_context:
      self.app_context.pop()

  def on_worker_init(self):
    """This method is called when the worker (:program:`celeryd`)
    starts."""

  def on_worker_process_init(self):
    """This method is called when a child process starts."""
    pass


class FlaskCelery(Celery):
  # can be overriden on command line with --loader
  loader_cls = __name__ + '.' + FlaskLoader.__name__

# celery
#
# for defining a task:
#
# from abilian.core.extensions import celery
# @celery.task
# def ...
#
# Application should set flask_app and configure celery
# (i.e. celery.config_from_object, etc)
celery = FlaskCelery()
