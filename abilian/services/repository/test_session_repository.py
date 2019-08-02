""""""
import uuid

from pytest import raises
from sqlalchemy.orm import Session

from . import repository, session_repository
from .service import RepositoryTransaction


def test_transaction_lifetime(session: Session) -> None:
    state = session_repository.app_state
    root_transaction = state.get_transaction(session)
    assert isinstance(root_transaction, RepositoryTransaction)
    assert root_transaction._parent is None

    # create sub-transaction (db savepoint)
    session.begin(nested=True)
    transaction = state.get_transaction(session)
    assert isinstance(transaction, RepositoryTransaction)
    assert transaction._parent is root_transaction

    session.flush()
    transaction = state.get_transaction(session)

    # FIXME
    # assert transaction is root_transaction
    #
    # # create subtransaction (sqlalchemy)
    # session.begin(subtransactions=True)
    # transaction = state.get_transaction(session)
    # assert isinstance(transaction, RepositoryTransaction)
    # assert transaction._parent is root_transaction
    #
    # session.flush()
    # transaction = state.get_transaction(session)
    # assert transaction is root_transaction


def test_accessors_bad_uuid_type(session: Session) -> None:
    uuid_str = b"4f80f02f-52e3-4fe2-b9f2-2c3e99449ce9"

    with raises(ValueError):
        session_repository.get(session, uuid_str)
    with raises(ValueError):
        session_repository.set(session, uuid_str, "")
    with raises(ValueError):
        session_repository.delete(session, uuid_str)


def test_accessors_non_existent_entry(session: Session) -> None:
    # non-existent
    u = uuid.uuid4()
    null = object()
    assert session_repository.get(session, u) is None
    assert session_repository.get(session, u, default=null) is null


def test_accessors_set_get_delete(session: Session) -> None:
    # set
    content = b"my file content"
    u1 = uuid.uuid4()
    session_repository.set(session, u1, content)
    assert session_repository.get(session, u1).open("rb").read() == content
    assert repository.get(u1) is None

    # delete
    session_repository.delete(session, u1)
    assert session_repository.get(session, u1) is None

    u2 = uuid.uuid4()
    repository.set(u2, b"existing content")
    assert session_repository.get(session, u2) is not None

    session_repository.delete(session, u2)
    assert session_repository.get(session, u2) is None
    assert repository.get(u2) is not None


def test_transaction(session: Session) -> None:
    u = uuid.uuid4()
    repository.set(u, b"first draft")
    assert session_repository.get(session, u).open("rb").read() == b"first draft"

    session_repository.set(session, u, b"new content")

    # test nested (savepoint)
    # delete content but rollback transaction
    db_tr = session.begin(nested=True)
    session_repository.delete(session, u)
    assert session_repository.get(session, u) is None

    db_tr.rollback()
    assert session_repository.get(session, u).open("rb").read() == b"new content"

    # delete and commit
    with session.begin(nested=True):
        session_repository.delete(session, u)
        assert session_repository.get(session, u) is None

    assert session_repository.get(session, u) is None
    assert repository.get(u) is not None

    session.commit()
    assert repository.get(u) is None

    # delete: now test subtransactions (sqlalchemy)
    repository.set(u, b"first draft")
    db_tr = session.begin(subtransactions=True)
    session_repository.delete(session, u)
    assert session_repository.get(session, u) is None

    db_tr.rollback()
    assert session_repository.get(session, u).open("rb").read() == b"first draft"

    session.rollback()

    with session.begin(subtransactions=True):
        session_repository.delete(session, u)
        assert session_repository.get(session, u) is None

    assert session_repository.get(session, u) is None
    assert repository.get(u) is not None

    session.commit()
    assert repository.get(u) is None

    # now test 'set'
    session_repository.set(session, u, b"new content")
    session.commit()
    assert repository.get(u) is not None

    # test "set" in two nested transactions. This tests a specific code
    # branch, when a subtransaction overwrite data set in parent
    # transaction
    with session.begin(nested=True):
        session_repository.set(session, u, b"transaction 1")

        with session.begin(nested=True):
            session_repository.set(session, u, b"transaction 2")

        assert session_repository.get(session, u).open("rb").read() == b"transaction 2"


def test_transaction_path(session: Session) -> None:
    """Test RepositoryTransaction create storage only when needed."""
    u = uuid.uuid4()

    state = session_repository.app_state
    root_transaction = state.get_transaction(session)

    # assert not root_transaction.path.exists()

    with session.begin(subtransactions=True):
        transaction = state.get_transaction(session)
        assert not transaction.path.exists()

        session_repository.set(session, u, b"my file content")
        assert transaction.path.exists()

    assert root_transaction.path.exists()

    content = session_repository.get(session, u).open("rb").read()
    assert content == b"my file content"
    assert root_transaction.path.exists()
