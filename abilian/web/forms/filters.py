# coding=utf-8
"""Field filters for WTForm."""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from six import string_types

__all__ = ["strip", "uppercase", "lowercase"]


def strip(data):
    """Strip data if data is a string."""
    if data is None:
        return ""
    if not isinstance(data, string_types):
        return data
    return data.strip()


def uppercase(data):
    if not isinstance(data, string_types):
        return data
    return data.upper()


def lowercase(data):
    if not isinstance(data, string_types):
        return data
    return data.lower()
