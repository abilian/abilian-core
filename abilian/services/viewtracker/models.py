from datetime import datetime

from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import DateTime, Integer

from abilian.core.entities import Entity, db
from abilian.core.models.subjects import User


# TODO: remove duplicate
def _default_from(column):
    """Helper for default and onupdates parameters in a Column definitions.

    Returns a `context-sensitive default function
    <http://docs.sqlalchemy.org/en/rel_0_8/core/defaults.html#context-
    sensitive-default-functions>`_ to set value from another column.
    """

    def _default_value(context):
        return context.current_parameters[column]

    return _default_value


class View(db.Model):
    __tablename__ = "view"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    #: viewed entity id
    entity_id = Column(Integer, default=_default_from("_fk_entity_id"), nullable=False)
    _fk_entity_id = Column(Integer, ForeignKey(Entity.id, ondelete="SET NULL"))
    entity = relationship(Entity, foreign_keys=_fk_entity_id)

    #: user id
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = relationship(User, foreign_keys=user_id)

    hits = db.relationship(
        "Hit", backref="view", order_by="Hit.viewed_at", lazy="dynamic"
    )


class Hit(db.Model):
    __tablename__ = "hit"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)

    view_id = db.Column(db.Integer, db.ForeignKey(View.id))

    #: time of view
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=True)
