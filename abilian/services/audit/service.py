"""
Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""

from sqlalchemy import event
from sqlalchemy.orm.attributes import NO_VALUE
from sqlalchemy.orm.session import Session

from abilian.core.entities import Entity, all_entity_classes

from .models import AuditEntry, CREATION, UPDATE, DELETION


class AuditService(object):

  running = False
  listening = False

  def __init__(self, app=None):
    self.all_model_classes = set()
    self.model_class_names = {}
    if app is not None:
      self.init_app(self.app)

  def init_app(self, app):
    self.app = app
    app.extensions['audit'] = self
    app.services['audit'] = self

  def start(self):
    assert not self.running
    self.app.logger.info("Starting audit service")
    self.running = True
    self.register_classes()

    # Workaround the fact that we can't stop listening when the service is
    # stopped.
    if not self.listening:
      event.listen(Session, "after_flush", self.create_audit_entries)
      self.listening = True

  def stop(self):
    assert self.running
    self.app.logger.info("Stopping audit service")
    self.running = False
    # One can't currently remove these events.
    #event.remove(Session, "before_commit", self.before_commit)

  def register_classes(self):
    for cls in all_entity_classes():
      self.register_class(cls)

  def register_class(self, entity_class):
    if not hasattr(entity_class, "__table__"):
      return
    if entity_class in self.all_model_classes:
      return
    self.all_model_classes.add(entity_class)

    assert entity_class.__name__ not in self.model_class_names
    self.model_class_names[entity_class.__name__] = entity_class

    mapper = entity_class.__mapper__
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
    if not isinstance(model, Entity):
      return

    entry = AuditEntry.from_model(model, type=CREATION)
    session.add(entry)

    if hasattr(model, '__changes__'):
      del model.__changes__

  def log_updated(self, session, model):
    if not (isinstance(model, Entity)
            and hasattr(model, '__changes__')):
      return

    entry = AuditEntry.from_model(model, type=UPDATE)
    entry.changes = model.__changes__
    session.add(entry)

    del model.__changes__

  def log_deleted(self, session, model):
    if not isinstance(model, Entity):
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

