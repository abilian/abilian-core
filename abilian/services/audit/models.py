"""
Audit Service: logs modifications to audited objects.

Only subclasses of Entity are auditable, at this point.

TODO: In the future, we may decide to:

- Make Models that have the __auditable__ property (set to True) auditable.
- Make Entities that have the __auditable__ property set to False not auditable.
"""

from datetime import datetime
import pickle
from flask import g, current_app

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, Unicode, DateTime, Text, Binary

from abilian.core.subjects import User
from abilian.core.extensions import db


CREATION = 0
UPDATE   = 1
DELETION = 2


class AuditEntry(db.Model):
  """
  Logs modifications to auditable classes.
  """

  id = Column(Integer, primary_key=True)
  happened_at = Column(DateTime, default=datetime.utcnow)
  type = Column(Integer) # CREATION / UPDATE / DELETION

  entity_id = Column(Integer)
  entity_class = Column(Text)
  entity_name = Column(Unicode(length=255))

  user_id = Column(Integer, ForeignKey(User.id))
  user = relationship(User)

  changes_pickle = Column(Binary)

  @staticmethod
  def from_model(model, type):
    try:
      user_id = g.user.id
    except:
      user_id = 0

    entry = AuditEntry()
    entry.type = type
    entry.entity_id = model.id
    entry.entity_class = model.__class__.__name__
    entry.user_id = user_id
    for attr_name in ('_name', 'path', '__path_before_delete'):
      if hasattr(model, attr_name):
        try:
          entry.entity_name = getattr(model, attr_name)
        except:
          raise

    return entry

  def __repr__(self):
    return "<AuditEntry id=%s type=%s user=%s entity=<%s id=%s>>" % (
      self.id,
      {CREATION: "CREATION", DELETION: "DELETION", UPDATE: "UPDATE"}[self.type],
      self.user,
      self.entity_class, self.entity_id)

  #noinspection PyTypeChecker
  def get_changes(self):
    # Using Pickle here instead of JSON because we need to pickle values
    # such as dates. This could make schema migration more difficult, though.
    if self.changes_pickle:
      return pickle.loads(self.changes_pickle)
    else:
      return {}

  def set_changes(self, changes):
    # for strings: store only unicode values
    uchanges = {}
    for k, v in changes.iteritems():
      k = unicode(k)
      uv = []
      for val in v:
        if isinstance(val, str):
          # TODO: Temp fix for errors that happen during migration
          try:
            val = val.decode('utf-8')
          except:
            current_app.logger.error("A unicode error happened on changes %s",
                                     repr(changes))
            val = u"[[Somme error occurred. Working on it]]"
        uv.append(val)
      uchanges[k] = tuple(uv)
    self.changes_pickle = pickle.dumps(uchanges)

  changes = property(get_changes, set_changes)

  # FIXME: extremely innefficient
  @property
  def entity(self):
    # Avoid circular import
    from .service import audit_service

    #noinspection PyTypeChecker
    if not self.entity_class or not self.entity_id:
      return None
    cls = audit_service.model_class_names.get(self.entity_class)
    return cls.query.get(self.entity_id) if cls is not None else None
