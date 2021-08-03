from __future__ import annotations

import uuid
from pathlib import Path

from pytest import raises
from sqlalchemy.orm import Session

from . import repository

UUID_STR = "4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9"
UUID = uuid.UUID(UUID_STR)


def test_rel_path(session: Session):
    p = repository.rel_path(UUID)
    expected = Path("4f", "80", "4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9")
    assert isinstance(p, Path)
    assert p == expected


def test_abs_path(session: Session):
    p = repository.abs_path(UUID)
    assert isinstance(p, Path)

    # FIXME: fails on a Mac due to symlinks /var@ -> /private/var
    # expected = Path(self.app.instance_path, 'data', 'files',
    #                 '4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
    # self.assertEquals(p, expected)


def test_get_with_some_content(session: Session):
    p = repository.abs_path(UUID)
    if not p.parent.exists():
        p.parent.mkdir(parents=True)
    p.open("wb").write(b"my file content")

    val = repository.get(UUID)
    assert val == p
    assert val.open("rb").read() == b"my file content"

    # __getitem__
    val = repository[UUID]
    assert val == p
    assert val.open("rb").read() == b"my file content"


def test_get_with_non_existing_content(session: Session):
    # non-existent
    u = uuid.UUID("bcdc32ac-498d-4544-9e7f-fb2c75097011")
    default_path = Path("/tmp/default-path")
    assert repository.get(u) is None
    assert repository.get(u, default=default_path) is default_path

    # __getitem__ non-existent
    with raises(KeyError):
        assert repository[u]


def test_set(session: Session):
    u1 = uuid.uuid4()
    p = repository.abs_path(u1)
    repository.set(u1, b"my file content")
    assert p.open("rb").read() == b"my file content"


def test_setitem(session: Session):
    u1 = uuid.uuid4()
    p = repository.abs_path(u1)
    repository[u1] = b"my file content"
    assert p.open("rb").read() == b"my file content"
    # FIXME: test Unicode content


def test_delete(session: Session):
    u1 = uuid.uuid4()
    repository.set(u1, b"my file content")
    p = repository.abs_path(u1)
    assert p.exists()

    repository.delete(u1)
    assert not p.exists()


def test_delitem(session: Session):
    u1 = uuid.uuid4()
    repository.set(u1, b"my file content")
    p = repository.abs_path(u1)
    assert p.exists()

    del repository[u1]
    assert not p.exists()


def test_delete_non_existent(session: Session):
    # non-existent
    u1 = uuid.uuid4()
    with raises(KeyError):
        repository.delete(u1)

    # same w/ __delitem__
    with raises(KeyError):
        del repository[u1]
