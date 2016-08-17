# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import json
from datetime import timedelta

import six
import sqlalchemy as sa
from six import text_type

from abilian.core.extensions import db

__all__ = ['Setting']


class TransformerRegistry(object):

    def __init__(self):
        self.encoders = {}
        self.decoders = {}

    def encode(self, type_, value):
        # bytes is str for python2
        return self.encoders.get(type_, bytes)(value)

    def decode(self, type_, value):
        dec = self.decoders.get(type_)
        if dec is not None:
            value = dec(value)
        return value

    def register(self, type_, encoder=None, decoder=None):
        assert type_
        assert any((encoder, decoder))
        if encoder:
            self.encoders[type_] = encoder
        if decoder:
            self.decoders[type_] = decoder


_transformers = TransformerRegistry()


class _EmptyValue(object):

    def __nonzero__(self):
        return False

    # Py3k compat
    __bool__ = __nonzero__

    def __repr__(self):
        return '<Empty Value>'

#: marker for emptyness, to distinguish from None
EmptyValue = _EmptyValue()


class Setting(db.Model):
    """A Setting is a very simple key/value object, key being a string
    identifier and the primary key.

    value must be stored as Unicode.
    """
    transformers = _transformers
    key = sa.Column('key', sa.String(length=1000), primary_key=True)

    #: Can be a string (unicode), int, bool, json... or even a long dotted name
    #: if that's what you need. Type must be set before setting `value`
    _type = sa.Column('type', sa.String(length=1000), nullable=False)

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type_):
        if not (type_ in self.transformers.encoders and
                type_ in self.transformers.decoders):
            raise ValueError(
                'Invalid type "{}": not encoder and/or decoder registered'.
                format(type_))
        self._type = type_

    _value = sa.Column('value', sa.Text())

    @property
    def value(self):
        if self._value is None:
            return EmptyValue
        return self.transformers.decode(self.type, self._value)

    @value.setter
    def value(self, value):
        assert self.type
        self._value = self.transformers.encode(self.type, value)


register = _transformers.register


def from_int(i):
    return "{}".format(i).encode()


register('int', from_int, int)


def from_bool(b):
    return 'true' if b else 'false'


def to_bool(s):
    return s == 'true'


register('bool', from_bool, to_bool)


def from_unicode(s):
    return text_type(s).encode('utf-8')


def to_unicode(s):
    return s.decode('utf-8')


register('string', from_unicode, to_unicode)
register('json', json.dumps, json.loads)  # FIXME: checks for dump/load?


def from_timedelta(s):
    return json.dumps(dict(days=s.days, seconds=s.seconds))


def to_timedelta(s):
    return timedelta(**json.loads(s))


register('timedelta', from_timedelta, to_timedelta)
