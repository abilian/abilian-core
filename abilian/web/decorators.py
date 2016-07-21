"""
Useful decorators for web views.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import warnings
from functools import wraps

from flask import render_template, request

__all__ = ['templated']


# Copy/pasted from: http://flask.pocoo.org/docs/patterns/viewdecorators/
def templated(template=None):
    """The idea of this decorator is that you return a dictionary with the values
    passed to the template from the view function and the template is automatically rendered.

    @deprecated
    """

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint.replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            return render_template(template_name, **ctx)

        return decorated_function

    return decorator


# Copy/pasted from:
# https://wiki.python.org/moin/PythonDecoratorLibrary#Generating_Deprecation_Warnings
def deprecated(func):
    """This decorator can be used to mark functions as deprecated.

    It will result in a warning being emitted when the function is used.
    """

    @wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            filename=func.__code__.co_filename,
            lineno=func.__code__.co_firstlineno + 1)
        return func(*args, **kwargs)

    return new_func
