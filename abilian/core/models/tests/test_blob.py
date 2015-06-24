# coding=utf-8
"""
"""
from __future__ import absolute_import

import uuid
from StringIO import StringIO

from abilian.testing import BaseTestCase as AbilianTestCase
from abilian.services import (
  repository_service as repository,
  session_repository_service as session_repository
)
from ..blob import Blob

#
# Unit tests
#
def test_auto_uuid():
  b = Blob()
  assert b.uuid is not None
  assert isinstance(b.uuid, uuid.UUID)

  # test provided uuid is not replaced by a new one
  u = uuid.UUID('4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
  b = Blob(uuid=u)
  assert isinstance(b.uuid, uuid.UUID)
  assert b.uuid, u


def test_meta():
  b = Blob()
  assert b.meta == dict()

#
# Integration tests
#
class BlobTestCase(AbilianTestCase):

  def test_md5(self):
    b = Blob(u'test md5')
    assert 'md5' in b.meta
    assert b.meta['md5'] == u'0e4e3b2681e8931c067a23c583c878d5'

  def test_size(self):
    b = Blob(u'test')
    assert b.size == 4

  def test_filename(self):
    content = StringIO(u'test')
    setattr(content, 'filename', 'test.txt')
    b = Blob(content)
    assert 'filename' in b.meta
    assert b.meta['filename'] == u'test.txt'

  def test_mimetype(self):
    content = StringIO(u'test')
    setattr(content, 'content_type', 'text/plain')
    b = Blob(content)
    assert 'mimetype' in b.meta
    assert b.meta['mimetype'] == u'text/plain'

  def test_nonzero(self):
    b = Blob(u'test md5')
    assert bool(b)

    # change uuid: repository will return None for blob.file
    b.uuid = uuid.uuid4()
    assert not bool(b)

  def test_query(self):
    session = self.session
    content = b'content'
    b = Blob(content)
    session.add(b)
    session.flush()

    b.uuid
    assert Blob.query.by_uuid(b.uuid) is b
    assert Blob.query.by_uuid(unicode(b.uuid)) is b

    u = uuid.uuid4()
    assert Blob.query.by_uuid(u) is None

  def test_value(self):
    session = self.session
    content = b'content'
    b = Blob(content)

    tr = session.begin(nested=True)
    session.add(b)
    tr.commit()

    self.assertIs(repository.get(b.uuid), None)
    self.assertEquals(session_repository.get(b, b.uuid).open('rb').read(),
                      content)
    self.assertEquals(b.value, content)

    session.commit()
    self.assertEquals(repository.get(b.uuid).open('rb').read(), content)
    self.assertEquals(b.value, content)

    tr = session.begin(nested=True)
    session.delete(b)
    # object marked for deletion, but instance attribute should still be
    # readable
    self.assertEquals(session_repository.get(b, b.uuid).open('rb').read(),
                      content)
    tr.commit()

    self.assertIs(session_repository.get(b, b.uuid), None)
    self.assertEquals(repository.get(b.uuid).open('rb').read(), content)

    session.rollback()
    self.assertEquals(session_repository.get(b, b.uuid).open('rb').read(),
                      content)

    session.delete(b)
    session.flush()
    self.assertIs(session_repository.get(b, b.uuid), None)
    self.assertEquals(repository.get(b.uuid).open('rb').read(), content)

    session.commit()
    self.assertIs(repository.get(b.uuid), None)
