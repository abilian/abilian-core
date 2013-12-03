# coding=utf-8
"""
"""
from __future__ import absolute_import

from unittest import TestCase
from datetime import datetime

import sqlalchemy as sa
from whoosh.fields import (
  Schema,
  ID, DATETIME, TEXT, NUMERIC
)

from abilian.services.indexing.adapter import SAAdapter
from abilian.core.extensions import db
from abilian.core.entities import (
  Entity, IdMixin, Indexable as CoreIndexable, SEARCHABLE,
)

class SANotAdaptable(object):
  pass


class SANotIndexable(IdMixin, db.Model):
  __tablename__ = 'sa_not_indexable'
  __indexation_args__ = dict(searchable=False)


class Indexable(IdMixin, CoreIndexable, db.Model):
  __tablename__ = 'sa_indexable'
  __indexation_args__ = dict(
    searchable=True,
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


class TestSAAdapter(TestCase):

  def test_can_adapt(self):
    self.assertFalse(SAAdapter.can_adapt(SANotAdaptable))
    self.assertTrue(SAAdapter.can_adapt(SANotIndexable))
    self.assertTrue(SAAdapter.can_adapt(Indexable))
    self.assertTrue(SAAdapter.can_adapt(Entity))

  def test_build_attrs(self):
    schema = Schema()
    adapter = SAAdapter(SANotIndexable, schema)
    self.assertEquals(adapter.indexable, False)
    self.assertEquals(adapter.doc_attrs, {})

    adapter = SAAdapter(Entity, schema)
    self.assertEquals(adapter.indexable, True)
    self.assertEquals(set(adapter.doc_attrs),
                      set(('id', 'name', 'object_type', 'created_at', 'updated_at')))
    self.assert_(all(lambda f: callable(f) for f in adapter.doc_attrs.itervalues()))

    self.assertEquals(set(schema.names()),
                      set(('id', 'object_type', 'name', 'created_at', 'updated_at')))

    schema = Schema(
      id=NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True),
    )
    adapter = SAAdapter(Indexable, schema)
    self.assertEquals(adapter.indexable, True)
    self.assertEquals(set(adapter.doc_attrs),
                      set(('id', 'text', 'num', 'name')))
    self.assert_(all(lambda f: callable(f) for f in adapter.doc_attrs.itervalues()))

    self.assertEquals(set(schema.names()),
                      set(('id', 'text', 'num', 'name')))
    self.assertTrue(isinstance(schema['text'], TEXT))
    self.assertTrue(isinstance(schema['num'], NUMERIC))

  def test_get_document(self):
    schema = Schema()
    adapter = SAAdapter(Entity, schema)
    expected = dict(
      id=2,
      name=u'entity',
      created_at=datetime(2013, 11, 28, 16, 17, 0),
      updated_at=datetime(2013, 11, 29, 12, 17, 58)
    )
    obj = Entity(**expected)
    expected['object_type'] = u'None'
    self.assertEquals(adapter.get_document(obj), expected)

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

    self.assertEquals(set(doc), set(('id', 'name', 'num', 'text')))
    self.assertEquals(doc['id'], 1)
    self.assertEquals(doc['num'], 42)
    self.assertEquals(doc['name'], u'related name')
    self.assertTrue(u'related name' in doc['text'])
    self.assertTrue(u'description text' in doc['text'])
