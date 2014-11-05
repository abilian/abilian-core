# coding=utf-8
"""
"""
from __future__ import absolute_import

from unittest import TestCase
import uuid

from abilian.testing import BaseTestCase as AbilianTestCase
from abilian.services import (
  repository_service as repository,
  session_repository_service as session_repository
)
from ..blob import Blob


class BlobUnitTestCase(TestCase):

  def test_auto_uuid(self):
    b = Blob()
    self.assertIsNot(b.uuid, None)
    self.assertTrue(isinstance(b.uuid, uuid.UUID))

    # test provided uuid is not replaced by a new one
    u = uuid.UUID('4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
    b = Blob(uuid=u)
    self.assertTrue(isinstance(b.uuid, uuid.UUID))
    self.assertEquals(b.uuid, u)


class BlobTestCase(AbilianTestCase):

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
