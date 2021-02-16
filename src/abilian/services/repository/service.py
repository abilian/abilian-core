""""""
import shutil
import typing
import weakref
from pathlib import Path
from typing import IO, Any, Dict, Optional, Set, Union
from uuid import UUID, uuid1

import sqlalchemy as sa
import sqlalchemy.event
from flask import _app_ctx_stack
from flask.globals import _lookup_app_object
from sqlalchemy.engine.base import Connection
from sqlalchemy.orm.session import Session, SessionTransaction
from sqlalchemy.orm.unitofwork import UOWTransaction

from abilian.core.extensions import db
from abilian.core.models import Model
from abilian.core.models.blob import Blob
from abilian.services import Service, ServiceState

if typing.TYPE_CHECKING:
    from abilian.app import Application

_NULL_MARK = object()


def _assert_uuid(uuid: Any) -> None:
    if not isinstance(uuid, UUID):
        raise ValueError("Not an uuid.UUID instance", uuid)


class RepositoryServiceState(ServiceState):
    #: :class:`Path` path to application repository
    path: Optional[Path] = None


class RepositoryService(Service):
    """Service for storage of binary objects referenced in database."""

    name = "repository"
    AppStateClass = RepositoryServiceState

    def init_app(self, app: "Application") -> None:
        super().init_app(app)

        path = app.data_dir / "files"
        if not path.exists():
            path.mkdir(mode=0o775, parents=True)

        with app.app_context():
            self.app_state.path = path.resolve()

    # data management: paths and accessors
    def rel_path(self, uuid: UUID) -> Path:
        """Contruct relative path from repository top directory to the file
        named after this uuid.

        :param:uuid: :class:`UUID` instance
        """
        _assert_uuid(uuid)
        filename = str(uuid)
        return Path(filename[0:2], filename[2:4], filename)

    def abs_path(self, uuid: UUID) -> Path:
        """Return absolute :class:`Path` object for given uuid.

        :param:uuid: :class:`UUID` instance
        """
        top = self.app_state.path
        rel_path = self.rel_path(uuid)
        dest = top / rel_path
        assert top in dest.parents
        return dest

    def get(self, uuid: UUID, default: Optional[Path] = None) -> Optional[Path]:
        """Return absolute :class:`Path` object for given uuid, if this uuid
        exists in repository, or `default` if it doesn't.

        :param:uuid: :class:`UUID` instance
        """
        path = self.abs_path(uuid)
        if not path.exists():
            return default
        return path

    def set(self, uuid: UUID, content: Any, encoding: str = "utf-8") -> None:
        """Store binary content with uuid as key.

        :param:uuid: :class:`UUID` instance
        :param:content: string, bytes, or any object with a `read()` method
        :param:encoding: encoding to use when content is Unicode
        """
        dest = self.abs_path(uuid)
        if not dest.parent.exists():
            dest.parent.mkdir(0o775, parents=True)

        if hasattr(content, "read"):
            content = content.read()

        mode = "tw"
        if not isinstance(content, str):
            mode = "bw"
            encoding = None

        with dest.open(mode, encoding=encoding) as f:
            f.write(content)

    def delete(self, uuid: UUID) -> None:
        """Delete file with given uuid.

        :param:uuid: :class:`UUID` instance
        :raises:KeyError if file does not exists
        """
        dest = self.abs_path(uuid)
        if not dest.exists():
            raise KeyError("No file can be found for this uuid", uuid)

        dest.unlink()

    def __getitem__(self, uuid: UUID) -> Path:
        value = self.get(uuid)
        if value is None:
            raise KeyError("No file can be found for this uuid", uuid)
        return value

    def __setitem__(self, uuid: UUID, content: Any) -> None:
        self.set(uuid, content)

    def __delitem__(self, uuid: UUID) -> None:
        self.delete(uuid)


repository = RepositoryService()

_REPOSITORY_TRANSACTION = "abilian_repository_transactions"


class SessionRepositoryState(ServiceState):
    path: Path

    @property
    def transactions(self) -> Dict[int, Any]:
        try:
            return _lookup_app_object(_REPOSITORY_TRANSACTION)
        except AttributeError:
            reg = {}
            setattr(_app_ctx_stack.top, _REPOSITORY_TRANSACTION, reg)
            return reg

    @transactions.setter
    def transactions(self, value):
        top = _app_ctx_stack.top
        if top is None:
            raise RuntimeError("working outside of application context")

        setattr(top, _REPOSITORY_TRANSACTION, value)

    # transaction <-> db session accessors
    def get_transaction(self, session: Session) -> Optional["RepositoryTransaction"]:
        if isinstance(session, sa.orm.scoped_session):
            session = session()

        s_id = id(session)
        default = (weakref.ref(session), None)
        s_ref, transaction = self.transactions.get(s_id, default)
        s = s_ref()

        if s is None or s is not session:
            # old session with same id, maybe not yet garbage collected
            transaction = None
        return transaction

    def set_transaction(
        self, session: Session, transaction: "RepositoryTransaction"
    ) -> None:
        """
        :param:session: :class:`sqlalchemy.orm.session.Session` instance
        :param:transaction: :class:`RepositoryTransaction` instance
        """
        if isinstance(session, sa.orm.scoped_session):
            session = session()

        s_id = id(session)
        self.transactions[s_id] = (weakref.ref(session), transaction)

    def create_transaction(
        self, session: Session, transaction: "RepositoryTransaction"
    ) -> None:
        if not self.running:
            return

        parent = self.get_transaction(session)
        root_path = self.path
        transaction = RepositoryTransaction(root_path, parent)
        self.set_transaction(session, transaction)

    def end_transaction(
        self, session: Session, transaction: "RepositoryTransaction"
    ) -> None:
        if not self.running:
            return

        tr = self.get_transaction(session)
        if tr is not None:
            if not tr.cleared:
                # root and nested transactions emit "commit", but
                # subtransactions don't
                tr.commit(session)
            self.set_transaction(session, tr._parent)

    def begin(self, session: Session) -> Optional[Any]:
        if not self.running:
            return None

        tr = self.get_transaction(session)
        if tr is None:
            # FIXME: return or create a new one?
            return None

        return tr.begin(session)

    def commit(self, session: Session) -> None:
        if not self.running:
            return

        tr = self.get_transaction(session)
        if tr is None:
            return

        tr.commit(session)

    def flush(self, session: Session, flush_context: UOWTransaction) -> None:
        # when sqlalchemy is flushing it is done in a sub-transaction,
        # not the root one. So when calling our 'commit' from here
        # we are not in our root transaction, so changes will not be
        # written to repository.
        self.commit(session)

    def rollback(self, session: Session) -> None:
        if not self.running:
            return

        tr = self.get_transaction(session)
        if tr is None:
            return

        tr.rollback(session)


class SessionRepositoryService(Service):
    """A repository service that is session aware, i.e content is actually
    written or delete at commit time.

    All content is stored using the main :class:`RepositoryService`.
    """

    name = "session_repository"
    AppStateClass = SessionRepositoryState

    def __init__(self, *args, **kwargs) -> None:
        self.__listening = False
        super().__init__(*args, **kwargs)

    def init_app(self, app: "Application") -> None:
        super().init_app(app)

        path = Path(app.instance_path, "tmp", "files_transactions")
        if not path.exists():
            path.mkdir(0o775, parents=True)

        with app.app_context():
            self.app_state.path = path.resolve()

        if not self.__listening:
            self.start_listening()

    def start_listening(self) -> None:
        self.__listening = True
        listen = sa.event.listen
        listen(Session, "after_transaction_create", self.create_transaction)
        listen(Session, "after_transaction_end", self.end_transaction)
        listen(Session, "after_begin", self.begin)
        listen(Session, "after_commit", self.commit)
        listen(Session, "after_flush", self.flush)
        listen(Session, "after_rollback", self.rollback)
        # appcontext_tearing_down.connect(self.clear_transaction, app)

    def _session_for(self, model_or_session: Union[Model, Session]) -> Session:
        """Return session instance for object parameter.

        If parameter is a session instance, it is return as is.
        If parameter is a registered model instance, its session will be used.

        If parameter is a detached model instance, or None, application scoped
        session will be used (db.session())

        If parameter is a scoped_session instance, a new session will be
        instanciated.
        """
        session = model_or_session
        if not isinstance(session, (Session, sa.orm.scoped_session)):
            if session is not None:
                session = sa.orm.object_session(model_or_session)

            if session is None:
                session = db.session

        if isinstance(session, sa.orm.scoped_session):
            session = session()

        return session

    # repository interface
    def get(
        self, session: Union[Session, Blob], uuid: UUID, default: Any = None
    ) -> Union[None, object, Path]:
        # assert isinstance(session, Session)
        # assert isinstance(uuid, UUID)
        session = self._session_for(session)
        transaction = self.app_state.get_transaction(session)
        try:
            val = transaction.get(uuid)
        except KeyError:
            return default

        if val is _NULL_MARK:
            val = repository.get(uuid, default)

        return val

    def set(
        self,
        session: Union[Session, Blob],
        uuid: UUID,
        content: Union[IO, bytes, str],
        encoding: str = "utf-8",
    ) -> None:
        session = self._session_for(session)
        transaction = self.app_state.get_transaction(session)
        transaction.set(uuid, content, encoding)

    def delete(self, session: Union[Session, Blob], uuid: UUID) -> None:
        session = self._session_for(session)
        transaction = self.app_state.get_transaction(session)
        if self.get(session, uuid) is not None:
            transaction.delete(uuid)

    # session event handlers
    @Service.if_running
    def create_transaction(
        self, session: Session, transaction: SessionTransaction
    ) -> Optional[Any]:
        return self.app_state.create_transaction(session, transaction)

    @Service.if_running
    def end_transaction(
        self, session: Session, transaction: SessionTransaction
    ) -> Optional[Any]:
        return self.app_state.end_transaction(session, transaction)

    @Service.if_running
    def begin(
        self, session: Session, transaction: SessionTransaction, connection: Connection
    ) -> Optional[Any]:
        return self.app_state.begin(session)

    @Service.if_running
    def commit(self, session: Session) -> None:
        return self.app_state.commit(session)

    @Service.if_running
    def flush(self, session: Session, flush_context: UOWTransaction) -> None:
        return self.app_state.flush(session, flush_context)

    @Service.if_running
    def rollback(self, session: Session) -> None:
        return self.app_state.rollback(session)


session_repository = SessionRepositoryService()


class RepositoryTransaction:
    def __init__(
        self, root_path: Path, parent: Optional["RepositoryTransaction"] = None
    ) -> None:
        self.path = root_path / str(uuid1())
        # if parent is not None and parent.cleared:
        #   parent = None

        self._parent = parent
        self._deleted = set()
        self._set = set()
        self.__cleared = False

    @property
    def cleared(self) -> bool:
        return self.__cleared

    def __del__(self) -> None:
        if not self.cleared:
            self._clear()

    def _clear(self) -> None:
        if self.__cleared:
            return

        # make sure transaction is not usable anymore
        if self.path.exists():
            shutil.rmtree(str(self.path))

        del self.path
        del self._deleted
        del self._set
        self.__cleared = True

    def begin(self, session: Optional[Session] = None) -> None:
        if not self.path.exists():
            self.path.mkdir(0o700)

    def rollback(self, session: Optional[Session] = None) -> None:
        self._clear()

    def commit(self, session: Optional[Session] = None) -> None:
        """Merge modified objects into parent transaction.

        Once commited a transaction object is not usable anymore

        :param:session: current sqlalchemy Session
        """
        if self.__cleared:
            return

        if self._parent:
            # nested transaction
            self._commit_parent()
        else:
            self._commit_repository()
        self._clear()

    def _commit_repository(self) -> None:
        assert self._parent is None

        for uuid in self._deleted:
            try:
                repository.delete(uuid)
            except KeyError:
                pass

        for uuid in self._set:
            content = self.path / str(uuid)
            repository.set(uuid, content.open("rb"))

    def _commit_parent(self) -> None:
        p = self._parent
        assert p
        p._deleted |= self._deleted
        p._deleted -= self._set

        p._set |= self._set
        p._set -= self._deleted

        if self._set:
            p.begin()  # ensure p.path exists

        for uuid in self._set:
            content_path = self.path / str(uuid)
            # content_path.replace is not available with python < 3.3.
            content_path.rename(p.path / str(uuid))

    def _add_to(self, uuid: UUID, dest: Set[UUID], other: Set[UUID]) -> None:
        """Add `item` to `dest` set, ensuring `item` is not present in `other`
        set."""
        _assert_uuid(uuid)
        try:
            other.remove(uuid)
        except KeyError:
            pass
        dest.add(uuid)

    def delete(self, uuid: UUID) -> None:
        self._add_to(uuid, self._deleted, self._set)

    def set(
        self, uuid: UUID, content: Union[IO, bytes, str], encoding: str = "utf-8"
    ) -> None:
        self.begin()
        self._add_to(uuid, self._set, self._deleted)

        if hasattr(content, "read"):
            content = content.read()

        if isinstance(content, bytes):
            mode = "wb"
            encoding = None
        else:
            mode = "wt"

        dest = self.path / str(uuid)
        with dest.open(mode, encoding=encoding) as f:
            f.write(content)

    def get(self, uuid: UUID) -> Any:
        if uuid in self._deleted:
            raise KeyError(uuid)

        if uuid in self._set:
            path = self.path / str(uuid)
            assert path.exists()
            return path

        if self._parent:
            return self._parent.get(uuid)

        return _NULL_MARK
