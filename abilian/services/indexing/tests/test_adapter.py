# coding=utf-8
"""
"""
from __future__ import absolute_import

from unittest import TestCase
from datetime import datetime

import sqlalchemy as sa
from whoosh.fields import Schema, TEXT, NUMERIC

from abilian.services.indexing.adapter import SAAdapter
from abilian.core.extensions import db
from abilian.core.models.base import IdMixin, Indexable as CoreIndexable, \
    SEARCHABLE
from abilian.core.entities import Entity


class SANotAdaptable(object):
  pass


class SANotIndexable(IdMixin, db.Model):
  __tablename__ = 'sa_not_indexable'
  __indexable__ = False


class Indexable(IdMixin, CoreIndexable, db.Model):
  __tablename__ = 'sa_indexable'
  __indexation_args__ = dict(
    index_to=(('related.name', ('name', 'text')),
              ('related.description', 'text'),
              ),
    )

  num = sa.Column(
    sa.Integer,
    info=SEARCHABLE | dict(
      index_to=(('num', NUMERIC(numtype=int)),)
      ),
  )


class SubclassEntityIndexable(Entity):
  pass


class TestSAAdapter(TestCase):

  def test_can_adapt(self):
    assert not SAAdapter.can_adapt(SANotAdaptable)
    assert SAAdapter.can_adapt(SANotIndexable)
    assert SAAdapter.can_adapt(Indexable)
    assert SAAdapter.can_adapt(Entity)

  def test_build_attrs(self):
    schema = Schema()
    adapter = SAAdapter(SANotIndexable, schema)
    assert not adapter.indexable
    assert adapter.doc_attrs == {}

    adapter = SAAdapter(Entity, schema)
    assert adapter.indexable == False

    adapter = SAAdapter(SubclassEntityIndexable, schema)
    assert adapter.indexable
    assert set(adapter.doc_attrs) == {
      'object_key', 'id', 'name', 'slug', 'object_type',
      'text', 'created_at', 'updated_at', 'name_prefix',
      'owner', 'owner_name', 'creator_name', 'creator'}
    assert all(lambda f: callable(f) for f in adapter.doc_attrs.itervalues())

    assert set(schema.names()) == {
      'object_key', 'id', 'object_type', 'name', 'slug',
      'text', 'created_at', 'updated_at', 'name_prefix',
      'owner', 'owner_name', 'creator_name', 'creator'}

    schema = Schema(
      id=NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True),
    )
    adapter = SAAdapter(Indexable, schema)
    assert adapter.indexable
    assert set(adapter.doc_attrs) == {'id', 'text', 'num', 'name'}
    assert all(lambda f: callable(f) for f in adapter.doc_attrs.itervalues())

    assert set(schema.names()) == {'id', 'text', 'num', 'name'}
    assert isinstance(schema['text'], TEXT)
    assert isinstance(schema['num'], NUMERIC)

  def test_get_document(self):
    schema = Schema()
    adapter = SAAdapter(SubclassEntityIndexable, schema)
    expected = dict(
      id=2,
      name=u'entity name',
      created_at=datetime(2013, 11, 28, 16, 17, 0),
      updated_at=datetime(2013, 11, 29, 12, 17, 58)
    )
    obj = SubclassEntityIndexable(**expected)
    obj.slug = u'entity-name'
    expected['creator_name'] = u''
    expected['owner_name'] = u''
    expected['object_type'] = u'test_adapter.SubclassEntityIndexable'
    expected['object_key'] = u'test_adapter.SubclassEntityIndexable:2'
    expected['text'] = u'entity name'
    expected['slug'] = 'entity-name'
    expected['name_prefix'] = u'entity name'
    assert adapter.get_document(obj) == expected

    # test retrieve related attributes
    schema = Schema(
      id=NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True),
    )
    adapter = SAAdapter(Indexable, schema)
    expected = dict(id=1, num=42)
    obj = Indexable(**expected)
    obj.related = type('Related', (object,), dict(name=None))()
    expected['name'] = obj.related.name = u'related name'
    obj.related.description = u'description text'
    expected['text'] = obj.related.name + u' ' + obj.related.description
    doc = adapter.get_document(obj)

    assert set(doc) == {'id', 'name', 'num', 'text'}
    assert doc['id'] == 1
    assert doc['num'] == 42
    assert doc['name'] == u'related name'
    assert u'related name' in doc['text']
    assert u'description text' in doc['text']
