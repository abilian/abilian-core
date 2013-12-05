"""
A few utility functions.

See https://docs.djangoproject.com/en/dev/topics/http/shortcuts/ for more ideas
of stuff to implement.
"""
from flask import current_app, url_for as flask_url_for
from flask.helpers import send_from_directory


def url_for(obj, **kw):
  if isinstance(obj, str):
    return flask_url_for(obj, **kw)
  elif hasattr(obj, "_url"):
    return obj._url
  elif hasattr(obj, "url"):
    return obj.url


def get_object_or_404(cls, *args):
  """
  Shorthand similar to Django's `get_object_or_404`.
  """

  return cls.query.filter(*args).first_or_404()


def send_file_from_directory(filename, directory, app=None):
  """
  Helper to add static rules, like in `abilian.app`.app

  Example use::

       app.add_url_rule(
          app.static_url_path + '/abilian/<path:filename>',
          endpoint='abilian_static',
          view_func=partial(send_file_from_directory,
                            directory='/path/to/static/files/dir'))
  """
  if app is None:
    app = current_app
  cache_timeout = app.get_send_file_max_age(filename)
  return send_from_directory(directory, filename,
                             cache_timeout=cache_timeout)
