# coding=utf-8
"""
Create all standard extensions.

"""

# Note: Because of issues with circular dependencies, Abilian-specific extensions are
# created later.

from __future__ import absolute_import

__all__ = ['get_extension', 'db', 'mail', 'celery', 'login_manager', 'csrf']

from .logging import patch_logger
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

from flask import current_app

# Standard extensions.
import flask.ext.mail as flask_mail


# patch flask.ext.mail.Message.send to always set enveloppe_from default mail
# sender
def _message_send(self, connection):
  sender = current_app.config['MAIL_SENDER']
  enveloppe_from = current_app.config['MAIL_SENDER']
  if not self.extra_headers:
    self.extra_headers = {}
  self.extra_headers['Sender'] = sender
  connection.send(self, sender)

patch_logger.info(flask_mail.Message.send)
flask_mail.Message.send = _message_send

# patch connection.send from flask-mail 0.9.0 with upstream code
def _connection_send(self, message, envelope_from=None):
  """Verifies and sends message.

  :param message: Message instance.
  :param envelope_from: Email address to be used in MAIL FROM command.
  """
  assert message.send_to, "No recipients have been added"

  assert message.sender, (
    "The message does not specify a sender and a default sender "
    "has not been configured")

  if message.has_bad_headers():
    raise BadHeaderError

  if message.date is None:
    message.date = time.time()

  if self.host:
    self.host.sendmail(sanitize_address(envelope_from or message.sender),
                       message.send_to,
                       message.as_string(),
                       message.mail_options,
                       message.rcpt_options)

  flask_mail.email_dispatched.send(
    message,
    app=current_app._get_current_object())

  self.num_emails += 1

  if self.num_emails == self.mail.max_emails:
    self.num_emails = 0
    if self.host:
      self.host.quit()
      self.host = self.configure_host()

patch_logger.info(flask_mail.Connection.send)
flask_mail.Connection.send = _connection_send

mail = flask_mail.Mail()
del flask_mail

import sqlalchemy as sa
from .sqlalchemy import SQLAlchemy
db = SQLAlchemy()


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
