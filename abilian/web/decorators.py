# coding=utf-8
"""
Useful decorators for web views.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import warnings
from functools import wraps


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
            lineno=func.__code__.co_firstlineno + 1,
        )
        return func(*args, **kwargs)

    return new_func
