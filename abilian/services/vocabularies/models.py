""""""
from typing import Any, Dict, Tuple, Type

import sqlalchemy as sa
import sqlalchemy.event
import sqlalchemy.ext
import sqlalchemy.ext.declarative
import sqlalchemy.orm
from flask_sqlalchemy import BaseQuery, Model
from sqlalchemy import Column

from abilian.core.extensions import db
from abilian.core.util import slugify

_BaseMeta = db.Model.__class__


class VocabularyQuery(BaseQuery):
    def active(self) -> "VocabularyQuery":
        """Returns only valid vocabulary items."""
        return self.filter_by(active=True)

    def by_label(self, label):
        """Like `.get()`, but by label."""
        # don't use .first(), so that MultipleResultsFound can be raised
        try:
            return self.filter_by(label=label).one()
        except sa.orm.exc.NoResultFound:
            return None

    def by_position(self, position: int) -> None:
        """Like `.get()`, but by position number."""
        # don't use .first(), so that MultipleResultsFound can be raised
        try:
            return self.filter_by(position=position).one()
        except sa.orm.exc.NoResultFound:
            return None


class _VocabularyMeta(_BaseMeta):
    """Metaclass for vocabularies.

    Enforces `__tablename__`.
    """

    def __new__(
        cls: Type["_VocabularyMeta"],
        name: str,
        bases: Tuple[Type[Model], ...],
        d: Dict[str, Any],
    ) -> Type["BaseVocabulary"]:
        meta = d.get("Meta")
        tblprefix = "vocabulary_"

        group = slugify(meta.group or "", "_")
        if group:
            tblprefix += group + "_"

        if not hasattr(meta, "name"):
            vocname = name.lower().replace("vocabulary", "")
            meta.name = vocname
        d["__tablename__"] = tblprefix + meta.name
        return _BaseMeta.__new__(cls, name, bases, d)


class BaseVocabulary(db.Model, metaclass=_VocabularyMeta):
    """Base abstract class for vocabularies."""

    __abstract__ = True
    query_class = VocabularyQuery

    id = Column(sa.Integer(), primary_key=True, autoincrement=True, nullable=False)
    label = Column(sa.UnicodeText(), nullable=False, unique=True)
    active = Column(
        sa.Boolean(), nullable=False, server_default=sa.sql.true(), default=True
    )
    default = Column(
        sa.Boolean(), nullable=False, server_default=sa.sql.false(), default=False
    )
    position = Column(sa.Integer, nullable=False, unique=True)

    __table_args__ = (sa.CheckConstraint(sa.sql.func.trim(sa.sql.text("label")) != ""),)

    @sa.ext.declarative.declared_attr
    def __mapper_args__(cls):
        return {"order_by": [cls.__table__.c.position.asc()]}

    class Meta:
        label = None
        group = None

    def __str__(self):
        return self.label

    def __repr__(self):
        tpl = (
            "<{module}.{cls} id={id} label={label} position={position} "
            "active={active} default={default} at 0x{addr:x}>"
        )
        cls = self.__class__
        return tpl.format(
            module=cls.__module__,
            cls=cls.__name__,
            id=self.id,
            label=repr(self.label),
            position=repr(self.position),
            active=repr(self.active),
            default=repr(self.default),
            addr=id(self),
        )


@sa.event.listens_for(BaseVocabulary, "before_insert", propagate=True)
@sa.event.listens_for(BaseVocabulary, "before_update", propagate=True)
def strip_label(mapper, connection, target):
    """Strip labels at ORM level so the unique=True means something."""
    if target.label is not None:
        target.label = target.label.strip()


@sa.event.listens_for(BaseVocabulary, "before_insert", propagate=True)
def _before_insert(mapper, connection, target):
    """Set item to last position if position not defined."""
    if target.position is None:
        func = sa.sql.func
        stmt = sa.select([func.coalesce(func.max(mapper.mapped_table.c.position), -1)])
        target.position = connection.execute(stmt).scalar() + 1


# this is used to hold a reference to Vocabularies generated from
# :func:`Vocabulary`. We use BaseVocabulary._decl_class_registry to find
# existing vocabulary, but it's a WeakValueDictionary. When using model
# generators and reloader the weak ref may be lost, leading to errors such as::
#
# InvalidRequestError: Table 'vocabulary_xxxx' is already defined for this
# MetaData instance.  Specify 'extend_existing=True' to redefine options and
# columns on an existing Table object.
_generated_vocabularies = []


def Vocabulary(name, label=None, group=None):
    assert isinstance(name, str)

    cls_name = "Vocabulary" + name.capitalize()
    _name, _label, _group = name.lower(), label, group

    class Meta:
        name = _name
        label = _label
        group = _group

    cls = type(cls_name, (BaseVocabulary,), {"Meta": Meta})
    _generated_vocabularies.append(cls)
    return cls
