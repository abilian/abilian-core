# coding=utf-8
"""
"""
from __future__ import absolute_import


class ValueSingletonMeta(type):

  def __new__(cls, name, bases, dct):
    dct['__instances__'] = {}
    attr = dct.get('attr', 'value')
    priv_attr = '__' + attr
    slots = dct.get('__slots__', ())
    if priv_attr not in slots:
      slots += (priv_attr,)
    dct['__slots__'] = slots

    new_type = type.__new__(cls, name, bases, dct)
    if not hasattr(new_type, 'attr'):
      setattr(new_type, 'attr', attr)

    return new_type

  def __call__(cls, value, *args, **kwargs):
    if isinstance(value, cls):
      return value

    if value not in cls.__instances__:
      value_instance = type.__call__(cls, value, *args, **kwargs)
      cls.__instances__[getattr(value_instance, cls.attr)] = value_instance
    return cls.__instances__[value]


class UniqueName(object):
  """
  Base class to create singletons from strings.

  A subclass of :class:`UniqueName` defines a namespace.
  """
  __metaclass__ = ValueSingletonMeta
  __slots__ = ('_hash',)
  attr = 'name'

  def __init__(self, name):
    self.__name = unicode(name).strip().lower()
    self._hash = hash(self.__name)

  @property
  def name(self):
    return self.__name

  def __repr__(self):
    return '{}({})'.format(self.__class__.__name__, repr(self.name))

  def __unicode__(self):
    return self.name

  def __str__(self):
    return self.name.encode(u'utf-8')

  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self._hash == other._hash
    return self.__name == unicode(other)

  def __hash__(self):
    return self._hash
