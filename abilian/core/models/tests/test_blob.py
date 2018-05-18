# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import uuid
from io import StringIO

from six import text_type

from abilian.services import repository_service as repository
from abilian.services import session_repository_service as session_repository

from ..blob import Blob


#
# Unit tests
#
def test_auto_uuid():
    b = Blob()
    assert b.uuid is not None
    assert isinstance(b.uuid, uuid.UUID)

    # test provided uuid is not replaced by a new one
    u = uuid.UUID("4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9")
    b = Blob(uuid=u)
    assert isinstance(b.uuid, uuid.UUID)
    assert b.uuid, u


def test_meta():
    b = Blob()
    assert b.meta == dict()


#
# Integration tests
#
def test_md5(app, db):
    b = Blob("test md5")
    assert "md5" in b.meta
    assert b.meta["md5"] == "0e4e3b2681e8931c067a23c583c878d5"


def test_size(app, db):
    b = Blob("test")
    assert b.size == 4


def test_filename(app, db):
    content = StringIO("test")
    content.filename = "test.txt"
    b = Blob(content)
    assert "filename" in b.meta
    assert b.meta["filename"] == "test.txt"


def test_mimetype(app, db):
    content = StringIO("test")
    content.content_type = "text/plain"
    b = Blob(content)
    assert "mimetype" in b.meta
    assert b.meta["mimetype"] == "text/plain"


def test_nonzero(app, db):
    b = Blob("test md5")
    assert bool(b)

    # change uuid: repository will return None for blob.file
    b.uuid = uuid.uuid4()
    assert not bool(b)


def test_query(app, db):
    session = db.session
    content = b"content"
    b = Blob(content)
    session.add(b)
    session.flush()

    assert Blob.query.by_uuid(b.uuid) is b
    assert Blob.query.by_uuid(text_type(b.uuid)) is b

    u = uuid.uuid4()
    assert Blob.query.by_uuid(u) is None


def test_value(app, db):
    session = db.session
    content = b"content"
    b = Blob(content)

    tr = session.begin(nested=True)
    session.add(b)
    tr.commit()

    assert repository.get(b.uuid) is None
    assert session_repository.get(b, b.uuid).open("rb").read() == content
    assert b.value == content

    session.commit()
    assert repository.get(b.uuid).open("rb").read() == content
    assert b.value == content

    session.begin(nested=True)  # match session.rollback

    with session.begin(nested=True):
        session.delete(b)
        # object marked for deletion, but instance attribute should still be
        # readable
        fd = session_repository.get(b, b.uuid).open("rb")
        assert fd.read() == content

    # commit in transaction: session_repository has no content, 'physical'
    # repository still has content
    assert session_repository.get(b, b.uuid) is None
    assert repository.get(b.uuid).open("rb").read() == content

    # rollback: session_repository has content again
    session.rollback()
    assert session_repository.get(b, b.uuid).open("rb").read() == content

    session.delete(b)
    session.flush()
    assert session_repository.get(b, b.uuid) is None
    assert repository.get(b.uuid).open("rb").read() == content

    session.commit()
    assert repository.get(b.uuid) is None
