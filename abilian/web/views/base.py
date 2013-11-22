# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import request, g
from flask.views import MethodView as BaseView

from ..action import actions

class View(BaseView):
  """
  Base class to use for all class based views.

  The view instance is accessible in :data:`g <flask.g>` and is set in
  :meth:`actions context <abilian.web.action.ActionRegistry.context>`.
  """

  def dispatch_request(self, *args, **kwargs):
    meth = getattr(self, request.method.lower(), None)
    # if the request method is HEAD and we don't have a handler for it
    # retry with GET
    if meth is None and request.method == 'HEAD':
      meth = getattr(self, 'get', None)
      assert meth is not None, 'Unimplemented method %r' % request.method

    g.view = actions.context['view'] = self
    args, kwargs = self.prepare_args(args, kwargs)
    return meth(*args, **kwargs)

  def prepare_args(self, args, kwargs):
    """
    If view arguments need to be prepared it can be done here.

    A typical use case is to take an identifier, convert it to an object
    instance and maybe store it on view instance and/or replace
    identifier by object in arguments.
    """
    return args, kwargs
