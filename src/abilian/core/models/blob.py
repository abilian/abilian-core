"""Blob.

References to files stored in a on-disk repository
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import Optional, Union
from typing.io import IO

import sqlalchemy as sa
from sqlalchemy.event import listens_for
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session
from sqlalchemy.orm.unitofwork import UOWTransaction
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer

from abilian.core.models.base import Model
from abilian.core.sqlalchemy import UUID, JSONDict


class Blob(Model):
    """Model for storing large file content.

    Files are stored on-disk, named after their uuid. Repository is
    located in instance folder/data/files.
    """

    __tablename__ = "blob"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    uuid = Column(UUID(), unique=True, nullable=False, default=uuid.uuid4)
    meta = Column(JSONDict(), nullable=False, default=dict)

    def __init__(self, value=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.uuid is None:
            self.uuid = uuid.uuid4()

        if self.meta is None:
            self.meta = {}

        if value is not None:
            self.value = value

    @property
    def file(self) -> Path | None:
        """Return :class:`pathlib.Path` object used for storing value."""
        from abilian.services.repository import session_repository as repository

        return repository.get(self, self.uuid)

    @property
    def size(self) -> int:
        """Return size in bytes of value."""
        f = self.file
        return f.stat().st_size if f is not None else 0

    @property
    def value(self) -> bytes | None:
        """Binary value content."""
        v = self.file
        if v is None:
            return None
        return v.open("rb").read()

    @value.setter
    def value(self, value: bytes | str | IO):
        """Store binary content to applications's repository and update
        `self.meta['md5']`.

        :param:content: bytes, or any object with a `read()` method
        :param:encoding: encoding to use when content is Unicode
        """
        from abilian.services.repository import session_repository as repository

        repository.set(self, self.uuid, value)
        if self.value:
            self.meta["md5"] = str(hashlib.md5(self.value).hexdigest())

        filename = getattr(value, "filename", None)
        if filename:
            if isinstance(filename, bytes):
                filename = filename.decode("utf-8")
            self.meta["filename"] = filename

        content_type = getattr(value, "content_type", None)
        if content_type:
            self.meta["mimetype"] = content_type

    @value.deleter
    def value(self):
        """Remove value from repository."""
        from abilian.services.repository import session_repository as repository

        repository.delete(self, self.uuid)

    @property
    def md5(self) -> str:
        """Return md5 from meta, or compute it if absent."""
        md5 = self.meta.get("md5")
        if md5 is None:
            if self.value:
                md5 = str(hashlib.md5(self.value).hexdigest())

        return md5

    def __bool__(self) -> bool:
        """A blob is considered falsy if it has no file."""
        return self.file is not None and self.file.exists()

    # Py3k compat
    __nonzero__ = __bool__


@listens_for(sa.orm.Session, "after_flush")
def _blob_propagate_delete_content(session: Session, flush_context: UOWTransaction):
    deleted = (obj for obj in session.deleted if isinstance(obj, Blob))
    for blob in deleted:
        del blob.value
