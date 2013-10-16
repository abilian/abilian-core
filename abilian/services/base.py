# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import current_app


class ServiceState(object):
  service = None
  running = False

  def __init__(self, service, running=False):
    self.service = service
    self.running = running


class Service(object):
  """
  """
  AppStateClass = ServiceState

  #: service name in Application.extensions / Application.services
  name = None

  def __init__(self, app=None):
    if app:
      self.init_app(app)

  def init_app(self, app):
    app.extensions[self.name] = self.AppStateClass(self)
    app.services[self.name] = self

  def start(self, ignore_state=False):
    """Starts the service.
    """
    self._toggle_running(True, ignore_state)

  def stop(self, ignore_state=False):
    """Stops the service.
    """
    self._toggle_running(False, ignore_state)

  def _toggle_running(self, run_state, ignore_state=False):
    state = self.app_state
    run_state = bool(run_state)
    if not ignore_state:
        assert run_state ^ state.running
    state.running = run_state

  @property
  def app_state(self):
    """ Current service state in current application.
    """
    return current_app.extensions[self.name]

  @property
  def running(self):
    return self.app_state.running

