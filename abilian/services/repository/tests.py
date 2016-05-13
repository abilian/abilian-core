# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import uuid

from pathlib import Path

from abilian.testing import BaseTestCase

from . import repository, session_repository
from .service import RepositoryTransaction


class TestRepository(BaseTestCase):

    UUID_STR = '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9'
    UUID = uuid.UUID(UUID_STR)

    def test_rel_path(self):
        self.assertRaises(ValueError, repository.rel_path, self.UUID_STR)

        p = repository.rel_path(self.UUID)
        expected = Path('4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
        self.assertTrue(isinstance(p, Path))
        self.assertEquals(p, expected)

    def test_abs_path(self):
        self.assertRaises(ValueError, repository.abs_path, self.UUID_STR)

        p = repository.abs_path(self.UUID)
        self.assertTrue(isinstance(p, Path))

        # FIXME: fails on a Mac due to symlinks /var@ -> /private/var
        # expected = Path(self.app.instance_path, 'data', 'files',
        #                 '4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
        # self.assertEquals(p, expected)

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
        self.assertRaises(ValueError, repository.__setitem__, self.UUID_STR, '')

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
        BaseTestCase.setUp(self)
        self.svc = session_repository

    def test_transaction_lifetime(self):
        state = self.svc.app_state
        root_transaction = state.get_transaction(self.session)
        self.assertTrue(isinstance(root_transaction, RepositoryTransaction))
        self.assertIs(root_transaction._parent, None)

        # create sub-transaction (db savepoint)
        self.session.begin(nested=True)
        transaction = state.get_transaction(self.session)
        self.assertTrue(isinstance(transaction, RepositoryTransaction))
        self.assertIs(transaction._parent, root_transaction)

        self.session.commit()
        transaction = state.get_transaction(self.session)
        self.assertIs(transaction, root_transaction)

        # create subtransaction (sqlalchemy)
        self.session.begin(subtransactions=True)
        transaction = state.get_transaction(self.session)
        self.assertTrue(isinstance(transaction, RepositoryTransaction))
        self.assertIs(transaction._parent, root_transaction)
        self.session.commit()
        transaction = state.get_transaction(self.session)
        self.assertIs(transaction, root_transaction)

    def test_accessors(self):
        session = self.session
        self.assertRaises(ValueError, self.svc.get, session, self.UUID_STR)
        self.assertRaises(ValueError, self.svc.set, session, self.UUID_STR, '')
        self.assertRaises(ValueError, self.svc.delete, session, self.UUID_STR)

        # non-existent
        u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
        null = object()
        self.assertIs(self.svc.get(session, u), None)
        self.assertIs(self.svc.get(session, u, default=null), null)

        # set
        self.svc.set(session, self.UUID, b'my file content')
        self.assertEquals(
            self.svc.get(session, self.UUID).open('rb').read(),
            b'my file content')
        self.assertIs(repository.get(self.UUID), None)

        # delete
        self.svc.delete(session, self.UUID)
        self.assertIs(self.svc.get(session, self.UUID), None)

        u = uuid.UUID('2532e752-611d-469c-999a-74f651757dff')
        repository.set(u, b'existing content')
        self.assertIsNot(self.svc.get(session, u), None)
        self.svc.delete(session, u)
        self.assertIs(self.svc.get(session, u), None)
        self.assertIsNot(repository.get(u), None)

    def test_transaction(self):
        session = self.session
        repository.set(self.UUID, b'first draft')
        self.assertEquals(
            self.svc.get(session, self.UUID).open('rb').read(), b'first draft')

        self.svc.set(session, self.UUID, b'new content')

        # test nested (savepoint)
        # delete content but rollback transaction
        db_tr = session.begin(nested=True)
        self.svc.delete(session, self.UUID)
        self.assertIs(self.svc.get(session, self.UUID), None)
        db_tr.rollback()
        self.assertEquals(
            self.svc.get(session, self.UUID).open('rb').read(), b'new content')

        # delete and commit
        with session.begin(nested=True) as tr:
            self.svc.delete(session, self.UUID)
            self.assertIs(self.svc.get(session, self.UUID), None)

        self.assertIs(self.svc.get(session, self.UUID), None)
        self.assertIsNot(repository.get(self.UUID), None)
        session.commit()
        self.assertIs(repository.get(self.UUID), None)

        # delete: now test subtransactions (sqlalchemy)
        repository.set(self.UUID, b'first draft')
        db_tr = session.begin(subtransactions=True)
        self.svc.delete(session, self.UUID)
        self.assertIs(self.svc.get(session, self.UUID), None)
        db_tr.rollback()
        self.assertEquals(
            self.svc.get(session, self.UUID).open('rb').read(), b'first draft')
        session.rollback()

        with session.begin(subtransactions=True) as tr:
            self.svc.delete(session, self.UUID)
            self.assertIs(self.svc.get(session, self.UUID), None)

        self.assertIs(self.svc.get(session, self.UUID), None)
        self.assertIsNot(repository.get(self.UUID), None)
        session.commit()
        self.assertIs(repository.get(self.UUID), None)

        # now test 'set'
        self.svc.set(session, self.UUID, b'new content')
        session.commit()
        self.assertIsNot(repository.get(self.UUID), None)

        # test "set" in two nested transactions. This tests a specific code branch,
        # when a subtransaction overwrite data set in parent transaction
        with session.begin(nested=True):
            self.svc.set(session, self.UUID, b'transaction 1')

            with session.begin(nested=True):
                self.svc.set(session, self.UUID, b'transaction 2')

            self.assertEquals(
                self.svc.get(session, self.UUID).open('rb').read(),
                b'transaction 2')

    def test_transaction_path(self):
        """
    Test RepositoryTransaction create storage only when needed
    """
        session = self.session
        state = self.svc.app_state
        root_transaction = state.get_transaction(self.session)

        assert not root_transaction.path.exists()

        with session.begin(subtransactions=True):
            transaction = state.get_transaction(self.session)
            assert not transaction.path.exists()
            self.svc.set(session, self.UUID, b'my file content')
            assert transaction.path.exists()

        assert root_transaction.path.exists()
        content = self.svc.get(session, self.UUID).open('rb').read()
        assert content == b'my file content'
        assert root_transaction.path.exists()
