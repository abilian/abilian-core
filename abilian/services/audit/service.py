"""
Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm.attributes import NO_VALUE
from sqlalchemy.orm.session import Session

from abilian.services import Service, ServiceState
from abilian.core.entities import Entity, all_entity_classes

from .models import AuditEntry, CREATION, UPDATE, DELETION


class AuditServiceState(ServiceState):

  all_model_classes = None
  model_class_names = None

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

  def is_auditable(self, model):
    return isinstance(model, Entity)

  def register_classes(self):
    state = self.app_state
    for cls in all_entity_classes():
      self.register_class(cls, app_state=state)

  def register_class(self, entity_class, app_state=None):
    if not hasattr(entity_class, "__table__"):
      return

    state = app_state if app_state is not None else self.app_state
    if entity_class in state.all_model_classes:
      return

    state.all_model_classes.add(entity_class)

    assert entity_class.__name__ not in state.model_class_names
    state.model_class_names[entity_class.__name__] = entity_class

    mapper = sa.orm.class_mapper(entity_class)
    for column in mapper.columns:
      props = mapper.get_property_by_column(column)
      attr = getattr(entity_class, props.key)
      info = column.info

      if info.get('auditable', True):
        #print "I will now audit attribute %s for class %s" % (name, entity_class)
        event.listen(attr, "set", self.set_attribute)

  def set_attribute(self, entity, new_value, old_value, initiator):
    attr_name = initiator.key
    if old_value == new_value:
      return

    # We don't log a few trivial cases so as not to overflow the audit log.
    if not old_value and not new_value:
      return
    if old_value == NO_VALUE:
      return

    #print "set_atttribute called for: %s, key: %s" % (entity, attr_name)
    #print "old value: %s, new value: %s" % (old_value, new_value)
    changes = getattr(entity, "__changes__", None)
    if not changes:
      changes = entity.__changes__ = {}
    if changes.has_key(attr_name):
      old_value = changes[attr_name][0]
    if old_value == NO_VALUE:
      old_value = None
    # FIXME: a bit hackish

    # Hide content if needed (like password columns)
    # FIXME: we can only handle the simplest case: 1 attribute => 1 column
    columns = initiator.parent_token.columns
    if (len(columns) == 1 and
        columns[0].info.get('audit_hide_content')):
      old_value = new_value = u'******'

    try:
      if len(old_value) > 1000:
        old_value = "<<large value>>"
      if len(new_value) > 1000:
        new_value = "<<large value>>"
    except:
      pass
    changes[attr_name] = (old_value, new_value)

  def create_audit_entries(self, session, flush_context):
    if not self.running:
      return

    transaction = session.begin(subtransactions=True)

    for model in session.new:
      self.log_new(session, model)

    for model in session.deleted:
      self.log_deleted(session, model)

    for model in session.dirty:
      self.log_updated(session, model)

    transaction.commit()

  def log_new(self, session, model):
    if not self.is_auditable(model):
      return

    entry = AuditEntry.from_model(model, type=CREATION)
    session.add(entry)

    if hasattr(model, '__changes__'):
      del model.__changes__

  def log_updated(self, session, model):
    if not (self.is_auditable(model)
            and hasattr(model, '__changes__')):
      return

    entry = AuditEntry.from_model(model, type=UPDATE)
    entry.changes = model.__changes__
    session.add(entry)
    del model.__changes__

  def log_deleted(self, session, model):
    if not self.is_auditable(model):
      return

    entry = AuditEntry.from_model(model, type=DELETION)
    session.add(entry)

  def entries_for(self, entity, limit=None):
    q =AuditEntry.query.filter(
      AuditEntry.entity_class == entity.__class__.__name__,
      AuditEntry.entity_id == entity.id)
    q = q.order_by(AuditEntry.happened_at.desc())

    if limit is not None:
      q = q.limit(limit)

    return q.all()

audit_service = AuditService()

