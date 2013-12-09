# coding=utf-8
"""
"""
from __future__ import absolute_import

import json
import sqlalchemy as sa
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
    assert type_ and any((encoder, decoder))
    if encoder:
      self.encoders[type_] = encoder
    if decoder:
      self.decoders[type_] = decoder


_transformers = TransformerRegistry()


class _EmptyValue(object):

  def __nonzero__(self):
    return False

  def __repr__(self):
    return '<Empty Value>'

#: marker for emptyness, to distinguish from None
EmptyValue = _EmptyValue()


class Setting(db.Model):
  """A Setting is a very simple key/value object, key being a string
    identifier and the primary key.

    value must be stored as unicode.
  """
  transformers = _transformers
  key = sa.Column('key', sa.String(length=1000), primary_key=True)

  # type: string (unicode), int, bool, json... or even a long dotted name if that's
  # what you need. Type must be set before setting `value`
  _type = sa.Column('type', sa.String(length=1000), nullable=False)

  @property
  def type(self):
    return self._type

  @type.setter
  def type(self, type_):
    if not (type_ in self.transformers.encoders
            and type_ in self.transformers.decoders):
      raise ValueError(
        'Invalid type "{}": not encoder and/or decoder registered'.format(type_))
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
register('int', bytes, int)


def from_bool(b):
  return 'true' if b else 'false'


def to_bool(s):
  return s == 'true'

register('bool', from_bool, to_bool)


def from_unicode(s):
  return unicode(s).encode('utf-8')


def to_unicode(s):
  return s.decode('utf-8')

register('string', from_unicode, to_unicode)
register('json', json.dumps, json.loads)  # FIXME: checks for dump/load?

del register
