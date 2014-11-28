# coding=utf-8
"""
Create all standard extensions.

"""

# Note: Because of issues with circular dependencies, Abilian-specific
# extensions are created later.

from __future__ import absolute_import

__all__ = ['get_extension', 'db', 'mail', 'celery', 'login_manager', 'csrf',
           'upstream_info']

from abilian.core.logging import patch_logger

from . import upstream_info

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
from ..celery import celery

from flask import current_app

# Standard extensions.
import flask.ext.mail as flask_mail


# patch flask.ext.mail.Message.send to always set enveloppe_from default mail
# sender
# FIXME: we'ld rather subclass Message and update all imports
def _message_send(self, connection):
  """
  Sends a single message instance. If TESTING is True the message will
  not actually be sent.

  :param message: a Message instance.
  """
  sender = current_app.config['MAIL_SENDER']
  if not self.extra_headers:
    self.extra_headers = {}
  self.extra_headers['Sender'] = sender
  connection.send(self, sender)

patch_logger.info(flask_mail.Message.send)
flask_mail.Message.send = _message_send


mail = flask_mail.Mail()


import sqlalchemy as sa
from ..sqlalchemy import SQLAlchemy
db = SQLAlchemy()

@sa.event.listens_for(db.metadata, 'before_create')
@sa.event.listens_for(db.metadata, 'before_drop')
def _filter_metadata_for_connection(target, connection, **kw):
  """
  listener to control what indexes get created.

  Useful for skipping postgres-specific indexes on a sqlite for example.

  It's looking for info entry `engines` on an index
  (`Index(info=dict(engines=['postgresql']))`), an iterable of engine names.
  """
  engine = connection.engine.name
  default_engines = (engine,)
  tables = target if isinstance(target, sa.Table) else kw.get('tables', [])
  for table in tables:
    indexes = list(table.indexes)
    for idx in indexes:
      if engine not in idx.info.get('engines', default_engines):
        table.indexes.remove(idx)


# csrf
from flask.ext.wtf.csrf import CsrfProtect
csrf = CsrfProtect()


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
