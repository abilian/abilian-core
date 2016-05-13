"""
audit Service: logs modifications to audited objects.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
from inspect import isclass

import sqlalchemy as sa
from flask import current_app, g
from sqlalchemy import event
from sqlalchemy.orm.attributes import NEVER_SET
from sqlalchemy.orm.session import Session

from abilian.core.entities import Entity
from abilian.services import Service, ServiceState

from .models import CREATION, DELETION, RELATED, UPDATE, AuditEntry, Changes

log = logging.getLogger(__name__)


class AuditableMeta(object):
    name = None
    id_attr = None
    related = None
    backref_attr = None
    audited_attrs = None
    collection_attrs = None
    enduser_ids = None

    def __init__(self, name=None, id_attr=None, related=False):
        self.name = name
        self.id_attr = id_attr
        self.related = related
        self.audited_attrs = set()
        self.collection_attrs = set()


class AuditServiceState(ServiceState):

    all_model_classes = None
    model_class_names = None

    # set to True when creating audit entries, to avoid examining a session full
    # of audit entries
    creating_entries = False

    def __init__(self, *args, **kwargs):
        ServiceState.__init__(self, *args, **kwargs)
        self.all_model_classes = set()
        self.model_class_names = {}


class AuditService(Service):
    name = 'audit'
    AppStateClass = AuditServiceState

    _listening = False

    def init_app(self, app):
        Service.init_app(self, app)

        if not self._listening:
            event.listen(Session, "after_flush", self.create_audit_entries)
            self._listening = True

    def start(self):
        Service.start(self)
        self.register_classes()

    def is_auditable(self, model_or_class):
        if hasattr(model_or_class, '__auditable_entity__'):
            return True

        if isclass(model_or_class):
            return issubclass(model_or_class, Entity)
        else:
            return isinstance(model_or_class, Entity)

    def register_classes(self):
        state = self.app_state
        BaseModel = current_app.db.Model
        all_models = (cls for cls in BaseModel._decl_class_registry.values()
                      if isclass(cls) and self.is_auditable(cls))
        for cls in all_models:
            self.register_class(cls, app_state=state)

    def register_class(self, entity_class, app_state=None):
        if not hasattr(entity_class, "__table__"):
            return

        state = app_state if app_state is not None else self.app_state
        if entity_class in state.all_model_classes:
            return

        state.all_model_classes.add(entity_class)
        self.setup_auditable_entity(entity_class)

        assert entity_class.__name__ not in state.model_class_names
        state.model_class_names[entity_class.__name__] = entity_class

        mapper = sa.orm.class_mapper(entity_class)
        for column in mapper.columns:
            props = mapper.get_property_by_column(column)
            attr = getattr(entity_class, props.key)
            info = column.info

            if info.get('auditable', True):
                entity_class.__auditable__.audited_attrs.add(attr)
                event.listen(attr,
                             "set",
                             self.set_attribute,
                             active_history=True)

        for relation in mapper.relationships:
            if relation.direction is not sa.orm.interfaces.MANYTOMANY:
                continue
            attr = getattr(entity_class, relation.key)
            entity_class.__auditable__.collection_attrs.add(attr)
            event.listen(attr,
                         "append",
                         self.collection_append,
                         active_history=True)
            event.listen(attr,
                         "remove",
                         self.collection_remove,
                         active_history=True)

    def setup_auditable_entity(self, entity_class):
        meta = AuditableMeta(entity_class.__name__, 'id')
        entity_class.__auditable__ = meta

        if not hasattr(entity_class, '__auditable_entity__'):
            return

        related_attr, backref_attr, enduser_ids = entity_class.__auditable_entity__
        related_path = related_attr.split('.')
        inferred_backref = []
        mapper = sa.orm.class_mapper(entity_class)
        for attr in related_path:
            relation = mapper.relationships.get(attr)
            if not relation:
                raise ValueError(
                    'Invalid relation: "{}", invalid attribute is "{}"'
                    ''.format(related_attr, attr))

            mapper = relation.mapper
            if inferred_backref is not None:
                try:
                    inferred_backref.append(relation.back_populates)
                except AttributeError:
                    inferred_backref = None

        try:
            meta.name = mapper.entity.__name__
        except AttributeError:
            return

        if not backref_attr:
            if inferred_backref is not None:
                backref_attr = '.'.join(inferred_backref)
            else:
                raise ValueError(
                    'Audit setup class<{cls}: Could not guess backref name'
                    ' of relationship "{related_attr}", please use tuple annotation '
                    'on __auditable_entity__'.format(cls=entity_class.__name__,
                                                     related_attr=related_attr))

        meta.related = related_path
        meta.backref_attr = backref_attr
        meta.enduser_ids = [attr_name.split('.') for attr_name in enduser_ids]

    def _get_changes_for(self, entity):
        changes = getattr(entity, "__changes__", None)
        if not changes:
            changes = entity.__changes__ = Changes()
        return changes

    def set_attribute(self, entity, new_value, old_value, initiator):
        attr_name = initiator.key
        if old_value == new_value:
            return

        # We don't log a few trivial cases so as not to overflow the audit log.
        if not old_value and not new_value:
            return

        changes = self._get_changes_for(entity)
        if attr_name in changes.columns:
            old_value = changes.columns[attr_name][0]

        # Hide content if needed (like password columns)
        # FIXME: we can only handle the simplest case: 1 attribute => 1 column
        columns = initiator.parent_token.columns
        if (len(columns) == 1 and columns[0].info.get('audit_hide_content')):
            old_value = new_value = u'******'

        old_value = format_large_value(old_value)
        new_value = format_large_value(new_value)
        changes.set_column_changes(attr_name, old_value, new_value)

    def collection_append(self, entity, value, initiator):
        changes = self._get_changes_for(entity)
        changes.collection_append(initiator.key, value)

    def collection_remove(self, entity, value, initiator):
        changes = self._get_changes_for(entity)
        changes.collection_remove(initiator.key, value)

    def create_audit_entries(self, session, flush_context):
        if not self.running or self.app_state.creating_entries:
            return

        self.app_state.creating_entries = True
        try:
            # if an error happens during audit creation it should not break the rest of
            # the application, and db session should be left clean. Only the developper
            # (and raven/sentry/whatever) should know
            entries = []
            for identity_set, op in ((session.new, CREATION),
                                     (session.deleted, DELETION),
                                     (session.dirty, UPDATE)):
                for model in identity_set:
                    try:
                        entry = self.log(session, model, op)
                        if entry:
                            entries.append(entry)
                    except:
                        if current_app.config.get(
                                'DEBUG') or current_app.config.get('TESTING'):
                            raise
                        log.error('Exception during entry creation',
                                  exc_info=True)

                session.add_all(entries)
        finally:
            self.app_state.creating_entries = False

    def log(self, session, model, op_type):
        if not self.is_auditable(model):
            return

        entity = model
        try:
            user_id = g.user.id
        except:
            user_id = 0

        meta = model.__auditable__
        if meta.related:
            op_type |= RELATED
            entity = model
            for attr in meta.related:
                entity = getattr(entity, attr)
                if entity is None:
                    return

        entry = AuditEntry(type=op_type, user_id=user_id)
        if op_type != DELETION:
            # DELETION|RELATED: deletion of a related model is ok: entity is still
            # here
            entry.entity = entity

        entry.entity_id = entity.id
        entry.entity_type = entity.entity_type

        entity_name = u''
        for attr_name in ('name', 'path', '__path_before_delete'):
            if hasattr(entity, attr_name):
                entity_name = getattr(entity, attr_name)
        entry.entity_name = entity_name

        changes = Changes()
        op = entry.op
        if op == CREATION:
            for instrumented_attr in meta.audited_attrs:
                value = getattr(model, instrumented_attr.key)
                self.set_attribute(model, value, NEVER_SET,
                                   instrumented_attr.impl)

            for instrumented_attr in meta.collection_attrs:
                for obj in getattr(model, instrumented_attr.key):
                    self.collection_append(model, obj, instrumented_attr.impl)

            changes = getattr(model, '__changes__', changes)
        elif op == UPDATE:
            changes = getattr(model, '__changes__', changes)
            if not changes:
                return

        if hasattr(model, '__changes__'):
            del model.__changes__

        if meta.related:
            enduser_ids = []
            for path in meta.enduser_ids:
                item = model
                for attr in path:
                    item = getattr(item, attr)
                enduser_ids.append(unicode(item))

            related_name = u'{} {}'.format(meta.backref_attr,
                                           u' '.join(enduser_ids))
            related_changes = changes
            log.debug('related changes: %s', repr(related_changes))
            changes = Changes()
            changes.set_related_changes(related_name, related_changes)

        entry.changes = changes
        return entry

    def entries_for(self, entity, limit=None):
        q = AuditEntry.query.filter(AuditEntry.entity == entity)
        q = q.order_by(AuditEntry.happened_at.desc())

        if limit is not None:
            q = q.limit(limit)

        return q.all()


audit_service = AuditService()


def format_large_value(value):
    try:
        if len(value) > 1000:
            return "<<large value>>"
    except TypeError:
        # object of type '...' has no len()
        pass
    return value
