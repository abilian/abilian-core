# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from six import python_2_unicode_compatible, text_type, with_metaclass
from sqlalchemy.types import String, TypeDecorator


class ValueSingletonMeta(type):

    def __new__(cls, name, bases, dct):
        dct['__instances__'] = {}
        dct.setdefault('__slots__', ())
        new_type = type.__new__(cls, name, bases, dct)
        return new_type

    def __call__(cls, value, *args, **kwargs):
        if isinstance(value, cls):
            return value

        if value not in cls.__instances__:
            value_instance = type.__call__(cls, value, *args, **kwargs)
            cls.__instances__[getattr(value_instance,
                                      cls.attr)] = value_instance
        return cls.__instances__[value.lower()]


@python_2_unicode_compatible
class UniqueName(with_metaclass(ValueSingletonMeta, object)):
    """Base class to create singletons from strings.

    A subclass of :class:`UniqueName` defines a namespace.
    """
    # __metaclass__ = ValueSingletonMeta
    __slots__ = ('_hash', '__name')
    attr = 'name'

    def __init__(self, name):
        self.__name = text_type(name).strip().lower()
        self._hash = hash(self.__name)

    @property
    def name(self):
        return self.__name

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, repr(self.name))

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._hash == other._hash
        return self.__name == text_type(other)

    def __hash__(self):
        return self._hash


class UniqueNameType(TypeDecorator):
    """Sqlalchemy type that stores a subclass of :class:`UniqueName`

    Usage::
    class MySingleton(UniqueName):
        pass

    class MySingletonType(UniqueNameType):
        Type = MySingleton
    """
    impl = String
    Type = None
    default_max_length = 100

    def __init__(self, *args, **kwargs):
        assert self.Type is not None
        kwargs.setdefault('length', self.default_max_length)
        TypeDecorator.__init__(self, *args, **kwargs)

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = self.Type(value)
        return value
