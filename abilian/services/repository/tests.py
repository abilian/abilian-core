# coding=utf-8
"""
"""
from __future__ import absolute_import
import uuid
from pathlib import Path

from abilian.testing import BaseTestCase
from . import repository

class TestRepository(BaseTestCase):

  UUID_STR = '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9'
  UUID = uuid.UUID(UUID_STR)

  def setUp(self):
    repository.start()
    BaseTestCase.setUp(self)

  def tearDown(self):
    BaseTestCase.tearDown(self)
    if repository.running:
      repository.stop()

  def test_rel_path(self):
    self.assertRaises(ValueError, repository.rel_path, self.UUID_STR)
    p = repository.rel_path(self.UUID)
    expected = Path('4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
    self.assertTrue(isinstance(p, Path))
    self.assertEquals(p, expected)

  def test_abs_path(self):
    self.assertRaises(ValueError, repository.abs_path, self.UUID_STR)
    p = repository.abs_path(self.UUID)
    expected = Path(self.app.instance_path, 'data', 'files',
                    '4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
    self.assertTrue(isinstance(p, Path))
    self.assertEquals(p, expected)

  def test_get(self):
    self.assertRaises(ValueError, repository.get, self.UUID_STR)
    self.assertRaises(ValueError, repository.__getitem__, self.UUID_STR)
    p = repository.abs_path(self.UUID)
    if not p.parent.exists():
      p.parent.mkdir(parents=True)
    p.open('bw').write(b'my file content')

    val = repository.get(self.UUID)
    self.assertEquals(val, p)
    self.assertEquals(val.open('rb').read(), b'my file content')

    # non-existent
    u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
    null = object()
    self.assertIs(repository.get(u), None)
    self.assertIs(repository.get(u, default=null), null)

    # __getitem__
    val = repository[self.UUID]
    self.assertEquals(val, p)
    self.assertEquals(val.open('rb').read(), b'my file content')

    # __getitem__ non-existent
    self.assertRaises(KeyError, repository.__getitem__, u)


  def test_set(self):
    self.assertRaises(ValueError, repository.set, self.UUID_STR, '')
    self.assertRaises(ValueError, repository.__setitem__,
                      self.UUID_STR, '')
    p = repository.abs_path(self.UUID)
    repository.set(self.UUID, b'my file content')
    self.assertEquals(p.open('rb').read(), b'my file content')

    # __setitem__
    p.unlink()
    self.assertEquals(p.exists(), False)
    repository[self.UUID] = b'my file content'
    self.assertEquals(p.open('rb').read(), b'my file content')
    # FIXME: test unicode content


  def test_delete(self):
    self.assertRaises(ValueError, repository.delete, self.UUID_STR)
    self.assertRaises(ValueError, repository.__delitem__, self.UUID_STR)
    p = repository.abs_path(self.UUID)
    p.parent.mkdir(parents=True)
    p.open('bw').write(b'my file content')
    repository.delete(self.UUID)
    self.assertEquals(p.exists(), False)
    self.assertEquals(p.parent.exists(), True)

    # non-existent
    u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
    self.assertRaises(KeyError, repository.delete, u)

    # __delitem__
    p.open('bw').write(b'my file content')
    self.assertEquals(p.exists(), True)
    del repository[self.UUID]
    self.assertEquals(p.exists(), False)
    self.assertEquals(p.parent.exists(), True)

    # __delitem__ non-existent
    self.assertRaises(KeyError, repository.__delitem__, u)
