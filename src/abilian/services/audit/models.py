"""Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""
import logging
import pickle
from datetime import datetime
from typing import Any

from flask import current_app
from flask_sqlalchemy import BaseQuery
from sqlalchemy import LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.orm.base import NEVER_SET
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import DateTime, Integer, String, UnicodeText

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User

CREATION = 0
UPDATE = 1
DELETION = 2
RELATED = 1 << 7

logger = logging.getLogger(__name__)


class Changes:
    """Trace object modifications."""

    def __init__(self) -> None:
        self.columns = {}
        self.collections = {}

    @staticmethod
    def from_legacy(changes):
        c = Changes()
        c.columns = changes
        # upgrade related change objects
        for key in c.columns:
            value = c.columns[key]
            if isinstance(value, dict):
                value = Changes.from_legacy(value)
                c.columns[key] = value

        return c

    def set_column_changes(self, name: str, old_value: Any, new_value: Any) -> None:
        self.columns[name] = (old_value, new_value)

    def set_related_changes(self, name: str, changes: "Changes") -> None:
        assert isinstance(changes, Changes)
        self.columns[name] = changes

    def _collection_change(self, name: str, value: Any, add: bool) -> None:
        colls = self.collections
        to_add, to_remove = colls.setdefault(name, (set(), set()))
        if not add:
            tmp = to_remove
            to_remove = to_add
            to_add = tmp

        to_add.add(value)
        if value in to_remove:
            to_remove.remove(value)

    def collection_append(self, name: str, value: Any) -> None:
        self._collection_change(name, value, add=True)

    def collection_remove(self, name: str, value: Any):
        self._collection_change(name, value, add=False)

    def __bool__(self) -> bool:
        return bool(self.columns) or bool(self.collections)


class AuditEntry(db.Model):
    """Logs modifications to auditable classes."""

    id = Column(Integer, primary_key=True)
    happened_at = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(Integer)  # CREATION / UPDATE / DELETION

    # 2 entity_id columns: 1 to keep even if entity is deleted, 1 to set up
    # relation (and all audit entries will have it set to null if entity is
    # deleted)
    _fk_entity_id = Column(Integer, ForeignKey(Entity.id, ondelete="SET NULL"))
    entity = relationship(Entity, foreign_keys=[_fk_entity_id], lazy="joined")

    entity_id = Column(Integer)
    entity_type = Column(String(1000))
    entity_name = Column(UnicodeText())

    user_id = Column(Integer, ForeignKey(User.id))
    user = relationship(User, foreign_keys=user_id)

    changes_pickle = Column(LargeBinary)

    query: BaseQuery

    def __repr__(self):
        return "<AuditEntry id={} op={} user={} {}entity=<{} id={}>>".format(
            repr(self.id),
            {CREATION: "CREATION", DELETION: "DELETION", UPDATE: "UPDATE"}[self.op],
            repr(str(self.user)),
            "related " if self.related else "",
            self.entity_type,
            self.entity_id,
        )

    @property
    def op(self) -> int:
        return self.type & ~RELATED

    @property
    def related(self) -> int:
        return self.type & RELATED

    def get_changes(self) -> Changes:
        # Using Pickle here instead of JSON because we need to pickle values
        # such as dates. This could make schema migration more difficult,
        # though.
        #
        # Convoluted and buggy code below to manage the PY2 -> PY3 transition
        if self.changes_pickle:
            # XXX: this workaround may or may not work
            try:
                changes = pickle.loads(self.changes_pickle, encoding="utf-8")
            except (UnicodeDecodeError, TypeError):
                try:
                    changes = pickle.loads(self.changes_pickle, encoding="bytes")
                except Exception:
                    logger.warning("migration error on audit entry:", exc_info=True)
                    changes = Changes()

            if isinstance(changes, dict):
                changes = Changes.from_legacy(changes)

            def fix_migration(changes):
                # Fix for migration Python 2 -> Python 3
                items = list(vars(changes).items())
                for k, v in items:
                    if isinstance(k, bytes):
                        setattr(changes, k.decode(), v)
                        del changes.__dict__[k]

                for k in changes.columns:
                    v = changes.columns[k]
                    if isinstance(v, Changes):
                        fix_migration(v)

            fix_migration(changes)

        else:
            changes = Changes()

        columns = changes.columns
        clean_columns = {}
        for key, value in columns.items():
            if isinstance(value, tuple):
                old_value, new_value = value
                if old_value == NEVER_SET and new_value in (None, ""):
                    continue

            clean_columns[key] = value

        changes.columns = clean_columns

        return changes

    def set_changes(self, changes: Changes) -> None:
        changes = self._format_changes(changes)
        self.changes_pickle = pickle.dumps(changes, protocol=2)

    changes = property(get_changes, set_changes)

    def _format_changes(self, changes: Changes) -> Changes:
        uchanges = Changes()
        if isinstance(changes, dict):
            changes = Changes.from_legacy(changes)

        for k, v in changes.columns.items():
            k = str(k)
            uv = []
            if isinstance(v, Changes):
                # field k is a related model with its own changes
                uv = self._format_changes(v)
            else:
                for val in v:
                    if isinstance(val, bytes):
                        # TODO: Temp fix for errors that happen during
                        # migration
                        try:
                            val = val.decode("utf-8")
                        except UnicodeDecodeError:
                            current_app.logger.error(
                                "A Unicode error happened on changes %s", repr(changes)
                            )
                            val = "[[Somme error occurred. Working on it]]"
                    uv.append(val)
                uv = tuple(uv)
            uchanges.columns[k] = uv

        for attr_name, (appended, removed) in changes.collections.items():
            appended = sorted(str(i) for i in appended)
            removed = sorted(str(i) for i in removed)
            uchanges.collections[attr_name] = (appended, removed)

        return uchanges
