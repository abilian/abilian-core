# coding=utf-8
"""
"""
from __future__ import absolute_import
import uuid
from pathlib import Path

import sqlalchemy as sa

from abilian.testing import BaseTestCase
from . import repository, session_repository
from .service import RepositoryTransaction

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


class TestSessionRepository(BaseTestCase):

  UUID_STR = '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9'
  UUID = uuid.UUID(UUID_STR)

  def setUp(self):
    repository.start()
    session_repository.start()
    BaseTestCase.setUp(self)
    self.svc = session_repository
    self.session() # side-effect: instanciate a session. Seems required with
                   # flask-sqlalchemy < 1.0

  def tearDown(self):
    BaseTestCase.tearDown(self)
    if session_repository.running:
      session_repository.stop()

    if repository.running:
      repository.stop()

  def test_transaction_lifetime(self):
    state = self.svc.app_state
    root_transaction = state.transaction
    self.assertTrue(isinstance(root_transaction, RepositoryTransaction))
    self.assertIs(root_transaction._parent, None)

    # create sub-transaction
    self.session.begin(nested=True)
    self.assertTrue(isinstance(state.transaction, RepositoryTransaction))
    self.assertIs(state.transaction._parent, root_transaction)

    self.session.commit()
    self.assertIs(state.transaction, root_transaction)


  def test_accessors(self):
    self.assertRaises(ValueError, self.svc.get, self.UUID_STR)
    self.assertRaises(ValueError, self.svc.__getitem__, self.UUID_STR)
    self.assertRaises(ValueError, self.svc.set, self.UUID_STR, '')
    self.assertRaises(ValueError, self.svc.__setitem__, self.UUID_STR, '')
    self.assertRaises(ValueError, self.svc.delete, self.UUID_STR)
    self.assertRaises(ValueError, self.svc.__delitem__, self.UUID_STR)

    # non-existent
    u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
    null = object()
    self.assertIs(self.svc.get(u), None)
    self.assertIs(self.svc.get(u, default=null), null)

    # set
    self.svc.set(self.UUID, b'my file content')
    self.assertEquals(self.svc.get(self.UUID).open('rb').read(),
                      b'my file content')
    self.assertIs(repository.get(self.UUID), None)

    # delete
    self.svc.delete(self.UUID)
    self.assertIs(self.svc.get(self.UUID), None)

    u = uuid.UUID('2532e752-611d-469c-999a-74f651757dff')
    repository.set(u, b'existing content')
    self.assertIsNot(self.svc.get(u), None)
    self.svc.delete(u)
    self.assertIs(self.svc.get(u), None)
    self.assertIsNot(repository.get(u), None)


  def test_transaction(self):
    repository.set(self.UUID, b'first draft')
    self.assertEquals(self.svc.get(self.UUID).open('rb').read(),
                      b'first draft')

    self.svc.set(self.UUID, b'new content')

    # delete content but rollback transaction
    db_tr = self.session.begin(nested=True)
    self.svc.delete(self.UUID)
    self.assertIs(self.svc.get(self.UUID), None)
    db_tr.rollback()
    self.assertEquals(self.svc.get(self.UUID).open('rb').read(),
                      b'new content')

    # delete and commit
    with self.session.begin(nested=True) as tr:
      self.svc.delete(self.UUID)
      self.assertIs(self.svc.get(self.UUID), None)

    self.assertIs(self.svc.get(self.UUID), None)
    self.assertIsNot(repository.get(self.UUID), None)
    self.session.commit()
    self.assertIs(repository.get(self.UUID), None)

    # now test 'set'
    self.svc.set(self.UUID, b'new content')
    self.session.commit()
    self.assertIsNot(repository.get(self.UUID), None)

    # test "set" in two nested transactions. This tests a specific code branch,
    # when a subtranscation overwrite data set in parent transaction
    with self.session.begin(nested=True):
      self.svc.set(self.UUID, b'transaction 1')

      with self.session.begin(nested=True):
        self.svc.set(self.UUID, b'transaction 2')

      self.assertEquals(self.svc.get(self.UUID).open('rb').read(),
                        b'transaction 2')
