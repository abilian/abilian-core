# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import uuid
from pathlib import Path

import pytest

from abilian.testing import BaseTestCase

from . import repository, session_repository
from .service import RepositoryTransaction


class TestRepository(BaseTestCase):

    UUID_STR = '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9'
    UUID = uuid.UUID(UUID_STR)

    def test_rel_path(self):
        with pytest.raises(ValueError):
            repository.rel_path(self.UUID_STR)

        p = repository.rel_path(self.UUID)
        expected = Path('4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
        assert isinstance(p, Path)
        assert p == expected

    def test_abs_path(self):
        with pytest.raises(ValueError):
            repository.abs_path(self.UUID_STR)

        p = repository.abs_path(self.UUID)
        assert isinstance(p, Path)

        # FIXME: fails on a Mac due to symlinks /var@ -> /private/var
        # expected = Path(self.app.instance_path, 'data', 'files',
        #                 '4f', '80', '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9')
        # self.assertEquals(p, expected)

    def test_get(self):
        with pytest.raises(ValueError):
            repository.get(self.UUID_STR)

        with pytest.raises(ValueError):
            repository[self.UUID_STR]

        p = repository.abs_path(self.UUID)
        if not p.parent.exists():
            p.parent.mkdir(parents=True)
        p.open('bw').write(b'my file content')

        val = repository.get(self.UUID)
        assert val == p
        assert val.open('rb').read() == b'my file content'

        # non-existent
        u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
        null = object()
        assert repository.get(u) is None
        assert repository.get(u, default=null) is null

        # __getitem__
        val = repository[self.UUID]
        assert val == p
        assert val.open('rb').read() == b'my file content'

        # __getitem__ non-existent
        with pytest.raises(KeyError):
            repository[u]

    def test_set(self):
        with pytest.raises(ValueError):
            repository.set(self.UUID_STR, '')
        with pytest.raises(ValueError):
            repository[self.UUID_STR] = ''

        p = repository.abs_path(self.UUID)
        repository.set(self.UUID, b'my file content')
        assert p.open('rb').read() == b'my file content'

        # __setitem__
        p.unlink()
        assert p.exists() == False

        repository[self.UUID] = b'my file content'
        assert p.open('rb').read() == b'my file content'
        # FIXME: test Unicode content

    def test_delete(self):
        with pytest.raises(ValueError):
            repository.delete(self.UUID_STR)
        with pytest.raises(ValueError):
            del repository[self.UUID_STR]

        p = repository.abs_path(self.UUID)
        p.parent.mkdir(parents=True)
        p.open('bw').write(b'my file content')
        repository.delete(self.UUID)
        assert not p.exists()
        assert p.parent.exists()

        # non-existent
        u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
        with pytest.raises(KeyError):
            repository.delete(u)

        # __delitem__
        p.open('bw').write(b'my file content')
        assert p.exists()

        del repository[self.UUID]
        assert not p.exists()
        assert p.parent.exists()

        # __delitem__ non-existent
        with pytest.raises(KeyError):
            del repository[u]


class TestSessionRepository(BaseTestCase):

    UUID_STR = '4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9'
    UUID = uuid.UUID(UUID_STR)

    def setUp(self):
        BaseTestCase.setUp(self)
        self.svc = session_repository

    def test_transaction_lifetime(self):
        state = self.svc.app_state
        root_transaction = state.get_transaction(self.session)
        assert isinstance(root_transaction, RepositoryTransaction)
        assert root_transaction._parent is None

        # create sub-transaction (db savepoint)
        self.session.begin(nested=True)
        transaction = state.get_transaction(self.session)
        assert isinstance(transaction, RepositoryTransaction)
        assert transaction._parent is root_transaction

        self.session.flush()
        transaction = state.get_transaction(self.session)
        assert transaction is root_transaction

        # create subtransaction (sqlalchemy)
        self.session.begin(subtransactions=True)
        transaction = state.get_transaction(self.session)
        assert isinstance(transaction, RepositoryTransaction)
        assert transaction._parent is root_transaction

        self.session.flush()
        transaction = state.get_transaction(self.session)
        assert transaction is root_transaction

    def test_accessors(self):
        session = self.session
        with pytest.raises(ValueError):
            self.svc.get(session, self.UUID_STR)
        with pytest.raises(ValueError):
            self.svc.set(session, self.UUID_STR, '')
        with pytest.raises(ValueError):
            self.svc.delete(session, self.UUID_STR)

        # non-existent
        u = uuid.UUID('bcdc32ac-498d-4544-9e7f-fb2c75097011')
        null = object()
        assert self.svc.get(session, u) is None
        assert self.svc.get(session, u, default=null) is null

        # set
        self.svc.set(session, self.UUID, b'my file content')
        assert self.svc.get(session, self.UUID).open('rb').read() == \
            b'my file content'
        assert repository.get(self.UUID) is None

        # delete
        self.svc.delete(session, self.UUID)
        assert self.svc.get(session, self.UUID) is None

        u = uuid.UUID('2532e752-611d-469c-999a-74f651757dff')
        repository.set(u, b'existing content')
        assert self.svc.get(session, u) is not None

        self.svc.delete(session, u)
        assert self.svc.get(session, u) is None
        assert repository.get(u) is not None

    def test_transaction(self):
        session = self.session
        repository.set(self.UUID, b'first draft')
        assert self.svc.get(session, self.UUID).open('rb').read() == \
            b'first draft'

        self.svc.set(session, self.UUID, b'new content')

        # test nested (savepoint)
        # delete content but rollback transaction
        db_tr = session.begin(nested=True)
        self.svc.delete(session, self.UUID)
        assert self.svc.get(session, self.UUID) is None

        db_tr.rollback()
        assert self.svc.get(session, self.UUID).open('rb').read() == \
            b'new content'

        # delete and commit
        with session.begin(nested=True):
            self.svc.delete(session, self.UUID)
            assert self.svc.get(session, self.UUID) is None

        assert self.svc.get(session, self.UUID) is None
        assert repository.get(self.UUID) is not None

        session.commit()
        assert repository.get(self.UUID) is None

        # delete: now test subtransactions (sqlalchemy)
        repository.set(self.UUID, b'first draft')
        db_tr = session.begin(subtransactions=True)
        self.svc.delete(session, self.UUID)
        assert self.svc.get(session, self.UUID) is None

        db_tr.rollback()
        assert self.svc.get(session, self.UUID).open('rb').read() == \
            b'first draft'

        session.rollback()

        with session.begin(subtransactions=True):
            self.svc.delete(session, self.UUID)
            assert self.svc.get(session, self.UUID) is None

        assert self.svc.get(session, self.UUID) is None
        assert repository.get(self.UUID) is not None

        session.commit()
        assert repository.get(self.UUID) is None

        # now test 'set'
        self.svc.set(session, self.UUID, b'new content')
        session.commit()
        assert repository.get(self.UUID) is not None

        # test "set" in two nested transactions. This tests a specific code branch,
        # when a subtransaction overwrite data set in parent transaction
        with session.begin(nested=True):
            self.svc.set(session, self.UUID, b'transaction 1')

            with session.begin(nested=True):
                self.svc.set(session, self.UUID, b'transaction 2')

            assert self.svc.get(session, self.UUID).open('rb').read() == \
                b'transaction 2'

    def test_transaction_path(self):
        """Test RepositoryTransaction create storage only when needed."""
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
