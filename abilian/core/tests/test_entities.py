""""""
from datetime import datetime

from pytest import fixture
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from abilian.core.entities import Entity
from abilian.core.models.base import AUDITABLE, NOT_SEARCHABLE, SEARCHABLE, \
    Info
from abilian.core.models.subjects import User

from .dummy import DummyContact


@fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    session_class = sessionmaker(bind=engine)
    session = session_class()

    # flask-sqlalchemy as listeners looking for this
    session._model_changes = {}

    DummyContact.metadata.create_all(engine)
    return session


def test() -> None:
    contact = DummyContact(first_name="John")
    assert contact.creator is None
    assert contact.owner is None

    user = User()
    contact.owner = user
    contact.creator = user


def test_auto_slug_property(session: Session) -> None:
    obj = DummyContact(name="a b c")
    session.add(obj)
    session.flush()
    assert obj.auto_slug == "a-b-c"

    obj.name = "C'est l'été !"
    assert obj.auto_slug == "c-est-l-ete"

    # with a special space character
    obj.name = "a_b\u205fc"  # U+205F: MEDIUM MATHEMATICAL SPACE
    assert obj.auto_slug == "a-b-c"

    # with non-ascii translatable chars, like EN DASH U+2013 (–) and EM DASH
    # U+2014 (—). Standard separator is \u002d (\x2d) "-" HYPHEN-MINUS.
    # this test may fails depending on how  Unicode normalization + char
    # substitution is done (order matters).
    obj.name = "a\u2013b\u2014c"  # u'a–b—c'
    slug = obj.auto_slug
    assert slug == "a-b-c"
    assert "\u2013" not in slug
    assert "\u002d" in slug


def test_updated_at(session: Session) -> None:
    contact = DummyContact()
    session.add(contact)
    session.commit()
    assert isinstance(contact.updated_at, datetime)

    updated = contact.updated_at
    contact.first_name = "John"
    session.commit()
    assert isinstance(contact.updated_at, datetime)
    assert contact.updated_at > updated


def test_auto_slug(session: Session) -> None:
    contact1 = DummyContact(name="Pacôme Hégésippe Adélard Ladislas")
    session.add(contact1)
    session.flush()
    assert contact1.slug == "pacome-hegesippe-adelard-ladislas"

    # test when name is None
    contact2 = DummyContact()
    session.add(contact2)
    session.flush()
    expected = f"dummycontact-{contact2.id}"
    assert contact2.slug == expected

    # test numbering if slug already exists:
    contact3 = DummyContact(name="Pacôme Hégésippe Adélard Ladislas")
    session.add(contact3)
    session.flush()
    assert contact3.slug == "pacome-hegesippe-adelard-ladislas-1"


def test_polymorphic_update_timestamp(session: Session) -> None:
    contact = DummyContact(name="Pacôme Hégésippe Adélard Ladislas")
    session.add(contact)
    session.flush()

    updated_at = contact.updated_at
    assert updated_at
    contact.email = "p@example.com"
    session.flush()
    assert contact.updated_at > updated_at


def test_meta(session: Session) -> None:
    e = DummyContact(name="test")
    e.meta["key"] = "value"
    e.meta["number"] = 42
    session.add(e)
    session.flush()
    e_id = e.id
    session.expunge(e)
    del e
    e = session.query(DummyContact).get(e_id)
    assert e.meta["key"] == "value"
    assert e.meta["number"] == 42


def test_entity_type() -> None:
    class MyType(Entity):
        pass

    expected = __name__ + ".MyType"
    assert MyType.entity_type == expected
    assert MyType._object_type() == expected

    class Fixed(Entity):
        entity_type = "some.fixed.module.fixed_type"

    assert Fixed.entity_type == "some.fixed.module.fixed_type"
    assert Fixed._object_type() == "some.fixed.module.fixed_type"

    class OtherBase(Entity):
        ENTITY_TYPE_BASE = "some.module"

    assert OtherBase.entity_type == "some.module.OtherBase"
    assert OtherBase._object_type() == "some.module.OtherBase"

    # test when ENTITY_TYPE_BASE is in ancestors
    class Base:
        ENTITY_TYPE_BASE = "from.ancestor"

    class InheritedBase(Base, Entity):
        pass

    assert InheritedBase.entity_type == "from.ancestor.InheritedBase"
    assert InheritedBase._object_type() == "from.ancestor.InheritedBase"


def test_info() -> None:
    info = SEARCHABLE
    assert info["searchable"]

    info = NOT_SEARCHABLE
    assert not info["searchable"]

    info = SEARCHABLE + AUDITABLE
    assert info["searchable"]
    assert info["auditable"]
    assert isinstance(info, Info)

    info = SEARCHABLE | AUDITABLE
    assert info["searchable"]
    assert info["auditable"]
    assert isinstance(info, Info)
