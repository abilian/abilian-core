# coding=utf-8
"""
"""
from __future__ import absolute_import

from unittest import TestCase
import uuid

from ..blob import Blob

class BlobTestCase(TestCase):

  def test_auto_uuid(self):
    b = Blob()
    self.assertIsNot(b.uuid, None)
    self.assertTrue(isinstance(b.uuid, uuid.UUID))

    # test provided uuid is not replaced by a new one
    u = uuid.UUID('4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
    b = Blob(uuid=u)
    self.assertTrue(isinstance(b.uuid, uuid.UUID))
    self.assertEquals(b.uuid, u)
