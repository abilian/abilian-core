"""A few utility functions.

See https://docs.djangoproject.com/en/dev/topics/http/shortcuts/ for
more ideas of stuff to implement.
"""
from typing import Any

from flask import current_app
from flask import url_for as flask_url_for
from flask.helpers import send_from_directory
from werkzeug.routing import BuildError


def url_for(obj: Any, **kw: Any) -> str:
    """Polymorphic variant of Flask's `url_for` function.

    Behaves like the original function when the first argument is a
    string. When it's an object, it
    """
    if isinstance(obj, str):
        return flask_url_for(obj, **kw)

    try:
        return current_app.default_view.url_for(obj, **kw)
    except KeyError:
        if hasattr(obj, "_url"):
            return obj._url
        elif hasattr(obj, "url"):
            return obj.url

    raise BuildError(repr(obj), kw, "GET")


def get_object_or_404(cls, *args):
    """Shorthand similar to Django's `get_object_or_404`."""

    return cls.query.filter(*args).first_or_404()


def send_file_from_directory(filename, directory, app=None):
    """Helper to add static rules, like in `abilian.app`.app.

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
    return send_from_directory(directory, filename, cache_timeout=cache_timeout)
