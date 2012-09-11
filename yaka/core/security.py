"""
Catchall module for security related stuff.

TODO: split later.
"""
from functools import wraps
from flask import g, make_response


class SecurityManager(object):
  # TODO

  def __init__(self):
    pass


  def check(self):
    pass


def login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if g.user is None:
      return make_response("", 401)
    return f(*args, **kwargs)
  return decorated_function

