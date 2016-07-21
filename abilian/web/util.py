"""
A few utility functions.

See https://docs.djangoproject.com/en/dev/topics/http/shortcuts/ for more ideas
of stuff to implement.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging
import sys

from flask import url_for as flask_url_for
from flask import current_app, session, stream_with_context
from flask.helpers import send_from_directory
from six import string_types
from werkzeug.routing import BuildError

try:
    import ipdb as pdb
except ImportError:
    import pdb


def url_for(obj, **kw):
    """Polymorphic variant of Flask's `url_for` function.

    Behaves like the original function when the first argument is a string.
    When it's an object, it
    """
    if isinstance(obj, string_types):
        return flask_url_for(obj, **kw)

    try:
        return current_app.default_view.url_for(obj, **kw)
    except KeyError:
        if hasattr(obj, "_url"):
            return obj._url
        elif hasattr(obj, "url"):
            return obj.url

    raise BuildError(repr(obj), kw, 'GET')


def get_object_or_404(cls, *args):
    """Shorthand similar to Django's `get_object_or_404`.
    """

    return cls.query.filter(*args).first_or_404()


def send_file_from_directory(filename, directory, app=None):
    """Helper to add static rules, like in `abilian.app`.app

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


def capture_stream_errors(logger, msg):
    """Decorator that capture and log errors during streamed response.

    Decorated function is automatically decorated with
    :func:<`Flask.stream_with_context`>.

    @param logger: a logger name or logger instance
    @param msg: message to log
    """
    if isinstance(logger, string_types):
        logger = logging.getLogger(logger)

    def decorator(fun):

        @stream_with_context
        def wrapper(*args, **kwargs):
            # this is for developpers convenience. The debugger middleware doesn't
            # work when using streamed responses.
            should_pdb = current_app.debug and session.get(
                'pdb_streamed_responses')
            try:
                generator = fun(*args, **kwargs)
                for chunk in generator:
                    yield chunk
            except Exception:
                # Anonymous "except" would also capture GeneratorExit that is not a
                # subclass of Exception. GeneratorExit happens when user stop download
                # during generation: it's not an error that should be logged
                type_, value, tb = sys.exc_info()
                if tb.tb_next is not None:
                    # error has happened inside decorated function, remove us from top
                    # stack: better readability in logs, accurate label in sentry
                    tb = tb.tb_next

                logger.error(msg, exc_info=(type_, value, tb))
                if should_pdb:
                    pdb.post_mortem(tb)

                raise

        return wrapper

    return decorator
