# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime

import six
import sqlalchemy as sa
from whoosh.fields import NUMERIC, TEXT, Schema

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.base import SEARCHABLE, IdMixin
from abilian.core.models.base import Indexable as CoreIndexable
from abilian.services.indexing.adapter import SAAdapter


class SANotAdaptable(object):
    pass


class SANotIndexable(IdMixin, db.Model):
    __tablename__ = "sa_not_indexable"
    __indexable__ = False


class Indexable(IdMixin, CoreIndexable, db.Model):
    __tablename__ = "sa_indexable"
    __indexation_args__ = dict(
        index_to=(("related.name", ("name", "text")), ("related.description", "text"))
    )

    num = sa.Column(
        sa.Integer, info=SEARCHABLE | dict(index_to=(("num", NUMERIC(numtype=int)),))
    )


class SubclassEntityIndexable(Entity):
    pass


def test_can_adapt():
    assert not SAAdapter.can_adapt(SANotAdaptable)
    assert SAAdapter.can_adapt(SANotIndexable)
    assert SAAdapter.can_adapt(Indexable)
    assert SAAdapter.can_adapt(Entity)


def test_build_attrs():
    schema = Schema()
    adapter = SAAdapter(SANotIndexable, schema)
    assert not adapter.indexable
    assert adapter.doc_attrs == {}

    adapter = SAAdapter(Entity, schema)
    assert adapter.indexable == False

    adapter = SAAdapter(SubclassEntityIndexable, schema)
    assert adapter.indexable
    assert set(adapter.doc_attrs) == {
        "object_key",
        "id",
        "name",
        "slug",
        "object_type",
        "text",
        "created_at",
        "updated_at",
        "name_prefix",
        "owner",
        "owner_name",
        "creator_name",
        "creator",
        "allowed_roles_and_users",
        "tag_ids",
        "tag_text",
    }
    assert all(lambda f: callable(f) for f in six.itervalues(adapter.doc_attrs))

    assert set(schema.names()) == {
        "object_key",
        "id",
        "object_type",
        "name",
        "slug",
        "text",
        "created_at",
        "updated_at",
        "name_prefix",
        "owner",
        "owner_name",
        "creator_name",
        "creator",
        "allowed_roles_and_users",
        "tag_ids",
        "tag_text",
    }

    schema = Schema(
        id=NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True)
    )
    adapter = SAAdapter(Indexable, schema)
    assert adapter.indexable
    assert set(adapter.doc_attrs) == {"id", "text", "num", "name"}
    assert all(lambda f: callable(f) for f in six.itervalues(adapter.doc_attrs))

    assert set(schema.names()) == {"id", "text", "num", "name"}
    assert isinstance(schema["text"], TEXT)
    assert isinstance(schema["num"], NUMERIC)


def test_get_document(app, db):
    schema = Schema()
    adapter = SAAdapter(SubclassEntityIndexable, schema)
    expected = {
        "id": 2,
        "name": "entity name",
        "created_at": datetime(2013, 11, 28, 16, 17, 0),
        "updated_at": datetime(2013, 11, 29, 12, 17, 58),
    }
    obj = SubclassEntityIndexable(**expected)
    obj.slug = "entity-name"

    expected["object_type"] = "test_adapter.SubclassEntityIndexable"
    expected["object_key"] = "test_adapter.SubclassEntityIndexable:2"
    expected["text"] = "entity name"
    expected["slug"] = "entity-name"
    expected["name_prefix"] = "entity name"
    expected["allowed_roles_and_users"] = "role:admin"

    with app.test_request_context():
        assert adapter.get_document(obj) == expected


def test_get_document_with_schema():
    # test retrieve related attributes
    schema = Schema(
        id=NUMERIC(numtype=int, bits=64, signed=False, stored=True, unique=True)
    )
    adapter = SAAdapter(Indexable, schema)
    expected = dict(id=1, num=42)
    obj = Indexable(**expected)
    obj.related = type(str("Related"), (object,), dict(name=None))()
    expected["name"] = obj.related.name = "related name"
    obj.related.description = "description text"
    expected["text"] = obj.related.name + " " + obj.related.description
    doc = adapter.get_document(obj)

    assert set(doc) == {"id", "name", "num", "text"}
    assert doc["id"] == 1
    assert doc["num"] == 42
    assert doc["name"] == "related name"
    assert "related name" in doc["text"]
    assert "description text" in doc["text"]
