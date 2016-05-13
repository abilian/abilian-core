# coding=utf-8
"""
Blob. References to files stored in a on-disk repository
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import hashlib
import uuid

import sqlalchemy as sa
from flask_sqlalchemy import BaseQuery
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer

from abilian.core.models.base import Model
from abilian.core.sqlalchemy import UUID, JSONDict


class BlobQuery(BaseQuery):
    """Query class for :class:`Blob` objects
    """

    def by_uuid(self, uuid):
        """
    Like `.get()` but by uuid

    :param uuid: a `string` or an `uuid`.
    """
        try:
            return self.filter_by(uuid=uuid).one()
        except sa.orm.exc.NoResultFound:
            return None


class Blob(Model):
    """Model for storing large file content.

    Files are stored on-disk, named after their uuid. Repository is located in
    instance folder/data/files.
    """
    __tablename__ = "blob"
    query_class = BlobQuery

    id = Column(Integer(), primary_key=True, autoincrement=True)
    uuid = Column(UUID(), unique=True, nullable=False, default=uuid.uuid4)
    meta = Column(JSONDict(), nullable=False, default=dict)

    def __init__(self, value=None, *args, **kwargs):
        super(Blob, self).__init__(*args, **kwargs)
        if self.uuid is None:
            self.uuid = uuid.uuid4()

        if self.meta is None:
            self.meta = dict()

        if value is not None:
            self.value = value

    @property
    def file(self):
        """Return :class:`pathlib.Path` object used for storing value.
        """
        from abilian.services.repository import session_repository as repository
        return repository.get(self, self.uuid)

    @property
    def size(self):
        """Return size in bytes of value.
        """
        f = self.file
        return f.stat().st_size if f is not None else 0

    @property
    def value(self):
        """Binary value content.
        """
        v = self.file
        return v.open('rb').read() if v is not None else v

    @value.setter
    def value(self, value, encoding='utf-8'):
        """Store binary content to applications's repository and update
        `self.meta['md5']`.

        :param:content: string, bytes, or any object with a `read()` method
        :param:encoding: encoding to use when content is unicode
        """
        from abilian.services.repository import session_repository as repository
        repository.set(self, self.uuid, value)
        self.meta['md5'] = unicode(hashlib.md5(self.value).hexdigest())

        if hasattr(value, 'filename'):
            filename = getattr(value, 'filename')
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8')
            self.meta['filename'] = filename

        if hasattr(value, 'content_type'):
            self.meta['mimetype'] = getattr(value, 'content_type')

    @value.deleter
    def value(self):
        """Remove value from repository.
        """
        from abilian.services.repository import session_repository as repository
        repository.delete(self, self.uuid)

    @property
    def md5(self):
        """Return md5 from meta, or compute it if absent.
        """
        md5 = self.meta.get('md5')
        if md5 is None:
            md5 = unicode(hashlib.md5(self.value).hexdigest())

        return md5

    def __nonzero__(self):
        """A blob is considered null if it has no file.
        """
        return self.file is not None and self.file.exists()


@sa.event.listens_for(sa.orm.Session, 'after_flush')
def _blob_propagate_delete_content(session, flush_context):
    deleted = (obj for obj in session.deleted if isinstance(obj, Blob))
    for blob in deleted:
        del blob.value
