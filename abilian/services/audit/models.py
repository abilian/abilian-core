"""
Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import pickle
from datetime import datetime

import six
from flask import current_app
from six import text_type
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Binary, DateTime, Integer, String, UnicodeText

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.models.subjects import User

CREATION = 0
UPDATE = 1
DELETION = 2
RELATED = 1 << 7


class Changes(object):
    """
    Trace object modifications
    """

    def __init__(self):
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

    def set_column_changes(self, name, old_value, new_value):
        self.columns[name] = (old_value, new_value)

    def set_related_changes(self, name, changes):
        assert isinstance(changes, Changes)
        self.columns[name] = changes

    def _collection_change(self, name, value, add=True):
        colls = self.collections
        to_add, to_remove = colls.setdefault(name, (set(), set()))
        if not add:
            tmp = to_remove
            to_remove = to_add
            to_add = tmp

        to_add.add(value)
        if value in to_remove:
            to_remove.remove(value)

    def collection_append(self, name, value):
        self._collection_change(name, value, add=True)

    def collection_remove(self, name, value):
        self._collection_change(name, value, add=False)

    def __nonzero__(self):
        return bool(self.columns) or bool(self.collections)

    # Py3k compat
    __bool__ = __nonzero__


class AuditEntry(db.Model):
    """
    Logs modifications to auditable classes.
    """
    id = Column(Integer, primary_key=True)
    happened_at = Column(DateTime, default=datetime.utcnow, index=True)
    type = Column(Integer)  # CREATION / UPDATE / DELETION

    # 2 entity_id columns: 1 to keep even if entity is deleted, 1 to set up
    # relation (and all audit entries will have it set to null if entity is
    # deleted)
    _fk_entity_id = Column(Integer, ForeignKey(Entity.id, ondelete="SET NULL"))
    entity = relationship(Entity, foreign_keys=[_fk_entity_id], lazy='joined')

    entity_id = Column(Integer)
    entity_type = Column(String(1000))
    entity_name = Column(UnicodeText())

    user_id = Column(Integer, ForeignKey(User.id))
    user = relationship(User, foreign_keys=user_id)

    changes_pickle = Column(Binary)

    def __repr__(self):
        return '<AuditEntry id={} op={} user={} {}entity=<{} id={}>>'.format(
            repr(self.id),
            {CREATION: "CREATION",
             DELETION: "DELETION",
             UPDATE: "UPDATE"}[self.op],
            repr(text_type(self.user)), 'related '
            if self.related else '', self.entity_type, self.entity_id)

    @property
    def op(self):
        return self.type & ~RELATED

    @property
    def related(self):
        return self.type & RELATED

    #noinspection PyTypeChecker
    def get_changes(self):
        # Using Pickle here instead of JSON because we need to pickle values
        # such as dates. This could make schema migration more difficult, though.
        if self.changes_pickle:
            changes = pickle.loads(self.changes_pickle)
            if isinstance(changes, dict):
                changes = Changes.from_legacy(changes)
        else:
            changes = Changes()

        return changes

    def set_changes(self, changes):
        changes = self._format_changes(changes)
        self.changes_pickle = pickle.dumps(changes, protocol=2)

    changes = property(get_changes, set_changes)

    def _format_changes(self, changes):
        uchanges = Changes()
        if isinstance(changes, dict):
            changes = Changes.from_legacy(changes)

        for k, v in changes.columns.items():
            k = text_type(k)
            uv = []
            if isinstance(v, Changes):
                # field k is a related model with its own changes
                uv = self._format_changes(v)
            else:
                for val in v:
                    if isinstance(val, str):
                        # TODO: Temp fix for errors that happen during
                        # migration
                        try:
                            val = val.decode('utf-8')
                        except:
                            current_app.logger.error(
                                "A Unicode error happened on changes %s",
                                repr(changes))
                            val = u"[[Somme error occurred. Working on it]]"
                    uv.append(val)
                uv = tuple(uv)
            uchanges.columns[k] = uv

        for attr_name, (appended, removed) in changes.collections.items():
            appended = sorted(text_type(i) for i in appended)
            removed = sorted(text_type(i) for i in removed)
            uchanges.collections[attr_name] = (appended, removed)

        return uchanges
