# coding=utf-8
from functools import wraps
from werkzeug.exceptions import Forbidden
from flask.ext.wtf import Form


def field():
  """
  Return an instance of `wtforms.ext.csrf.fields.CSRFTokenField`, suitable for
  rendering. Renders an empty string if `config.CSRF_ENABLED` is not set.
  """
  return Form().csrf_token


def name():
  """
  Field name expected to have CSRF token. Useful for passing it to
  JavaScript for instance.
  """
  return u'csrf_token'


def token():
  """
  Value of current csrf token. Useful for passing it to JavaScript for
  instance.
  """
  return field().current_token or u''


def protect(view):
  """
  Protects a view agains CSRF attacks by checking `csrf_token` value in
  submitted values. Do nothing if `config.CSRF_ENABLED` is not set.

  Raises `werkzeug.exceptions.Forbidden` if validation fails.
  """
  @wraps(view)
  def csrf_check(*args, **kwargs):
    # an empty form is used to validate current csrf token and only that!
    if not Form().validate():
      raise Forbidden('CSRF validation failed.')

    return view(*args, **kwargs)
  return csrf_check
