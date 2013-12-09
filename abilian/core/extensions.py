# coding=utf-8
"""
Create all standard extensions.

"""

# Note: Because of issues with circular dependencies, Abilian-specific extensions are
# created later.

from __future__ import absolute_import

from flask import _request_ctx_stack

__all__ = ['get_extension', 'db', 'mail', 'celery', 'login_manager']

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
from .celery import celery

# Standard extensions.
from flask.ext.mail import Mail
mail = Mail()

import sqlalchemy as sa
from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()


def get_extension(name):
  """Get the named extension from the current app, returning None if not found.
  """

  from flask import current_app
  return current_app.extensions.get(name)


def _install_get_display_value(cls):

  _MARK = object()

  def display_value(self, field_name, value=_MARK):
    """ Return display value for fields having 'choices' mapping (stored value
    -> human readable value). For other fields it will simply return field
    value.

    `display_value` should be used instead of directly getting field value.

    If `value` is provided it is "tranlated" to a human-readable value. This is
    useful for obtaining a human readable label from a raw value
    """
    val = getattr(self, field_name) if value is _MARK else value

    mapper = sa.orm.object_mapper(self)
    try:
      field = getattr(mapper.c, field_name)
    except AttributeError:
      pass
    else:
      if 'choices' in field.info:
        get = lambda v: field.info['choices'].get(v, v)
        if isinstance(val, list):
          val = [get(v) for v in val]
        else:
          val = get(val)

    return val

  if not hasattr(cls, 'display_value'):
    cls.display_value = display_value


sa.event.listen(db.Model, 'class_instrument', _install_get_display_value)


from flask.ext.login import LoginManager
login_manager = LoginManager()

