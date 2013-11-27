# coding=utf-8
"""
"""
from __future__ import absolute_import

from .base import View
from .registry import Registry, default_view
from .object import BaseObjectView, ObjectView, ObjectEdit, ObjectCreate, ObjectDelete

__all__ = [
    'View',
    'Registry', 'default_view',
    'BaseObjectView', 'ObjectView', 'ObjectEdit', 'ObjectCreate', 'ObjectDelete',
    ]
