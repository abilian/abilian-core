"""Base class for entities, objects that are managed by the Abilian framwework
(unlike SQLAlchemy models which are considered lower-level)."""
import collections
import re
from datetime import datetime
from inspect import isclass
from typing import TYPE_CHECKING, Any, Dict, FrozenSet, List, Optional, \
    Tuple, Type, cast

import sqlalchemy as sa
from flask import current_app
from sqlalchemy import event
from sqlalchemy.engine.base import Connection
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Mapper, Session, mapper
from sqlalchemy.orm.unitofwork import UOWTransaction
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, String, UnicodeText

from .extensions import db
from .models import BaseMixin
from .models.base import EDITABLE, SEARCHABLE, SYSTEM, Indexable, Model
from .sqlalchemy import JSONDict
from .util import friendly_fqcn, memoized, slugify

if TYPE_CHECKING:
    from abilian.core.models.subjects import User
    from abilian.core.models.tag import Tag
    from abilian.services.security import Permission

__all__ = (
    "Entity",
    "EntityQuery",
    "Indexable",
    "all_entity_classes",
    "db",
    "ValidationError",
)


#
# Manual validation
#
class ValidationError(Exception):
    pass


def validation_listener(mapper: Mapper, connection: Connection, target: Any) -> None:
    if hasattr(target, "_validate"):
        target._validate()


event.listen(mapper, "before_insert", validation_listener)
event.listen(mapper, "before_update", validation_listener)


#
# CRUD events. TODO: connect to signals instead?
#
def before_insert_listener(mapper: Mapper, connection: Connection, target: Any) -> None:
    if hasattr(target, "_before_insert"):
        target._before_insert()


def before_update_listener(mapper: Mapper, connection: Connection, target: Any) -> None:
    if hasattr(target, "_before_update"):
        target._before_update()


def before_delete_listener(mapper: Mapper, connection: Connection, target: Any) -> None:
    if hasattr(target, "_before_delete"):
        target._before_delete()


event.listen(mapper, "before_insert", before_insert_listener)
event.listen(mapper, "before_update", before_update_listener)
event.listen(mapper, "before_delete", before_delete_listener)


def auto_slug_on_insert(mapper: Mapper, connection: Connection, target: Any) -> None:
    """Generate a slug from :prop:`Entity.auto_slug` for new entities, unless
    slug is already set."""
    if target.slug is None and target.name:
        target.slug = target.auto_slug


def auto_slug_after_insert(mapper: Mapper, connection: Connection, target: Any) -> None:
    """Generate a slug from entity_type and id, unless slug is already set."""
    if target.slug is None:
        target.slug = f"{target.entity_class.lower()}{target.SLUG_SEPARATOR}{target.id}"


@event.listens_for(Session, "after_attach")
def setup_default_permissions(session: Session, instance: Any) -> None:
    """Setup default permissions on newly created entities according to.

    :attr:`Entity.__default_permissions__`.
    """
    if instance not in session.new or not isinstance(instance, Entity):
        return

    if not current_app:
        # working outside app_context. Raw object manipulation
        return

    _setup_default_permissions(instance)


def _setup_default_permissions(instance: Any) -> None:
    """Separate method to conveniently call it from scripts for example."""
    from abilian.services import get_service
    from abilian.services.security import SecurityService

    security = cast(SecurityService, get_service("security"))
    for permission, roles in instance.__default_permissions__:
        if permission == "create":
            # use str for comparison instead of `abilian.services.security.CREATE`
            # symbol to avoid imports that quickly become circular.
            #
            # FIXME: put roles and permissions in a separate, isolated module.
            continue
        for role in roles:
            security.add_permission(permission, role, obj=instance)


class _EntityInherit:
    """Mixin for Entity subclasses.

    Entity meta-class takes care of inserting it in base classes.
    """

    __indexable__ = True

    @declared_attr
    def id(cls) -> Column:
        return Column(
            Integer,
            ForeignKey("entity.id", use_alter=True, name="fk_inherited_entity_id"),
            primary_key=True,
            info=SYSTEM | SEARCHABLE,
        )

    @declared_attr
    def __mapper_args__(cls):
        return {
            "polymorphic_identity": cls.entity_type,
            "inherit_condition": cls.id == Entity.id,
        }


BaseMeta = db.Model.__class__


class EntityQuery(db.Model.query_class):
    def with_permission(
        self, permission: "Permission", user: Optional["User"] = None
    ) -> "EntityQuery":
        from abilian.services import get_service

        security = get_service("security")
        if hasattr(self, "_query_entity_zero"):
            # SQLAlchemy 1.1+
            model = self._query_entity_zero().entity_zero.entity
        else:
            # SQLAlchemy 1.0
            model = self._entity_zero().entity_zero.entity
        expr = security.query_entity_with_permission(permission, user, Model=model)
        return self.filter(expr)


class EntityMeta(BaseMeta):
    """Metaclass for Entities. It properly sets up subclasses by adding
    _EntityInherit to `__bases__`.

    `_EntityInherit` provides `id` attibute and `__mapper_args__`
    """

    def __new__(
        mcs: Type["EntityMeta"],
        classname: str,
        bases: Tuple[Type, ...],
        d: Dict[str, Any],
    ) -> Any:
        if d["__module__"] != EntityMeta.__module__ or classname != "Entity":
            if not any(issubclass(b, _EntityInherit) for b in bases):
                bases = (_EntityInherit,) + bases
                d["id"] = _EntityInherit.id

            if d.get("entity_type") is None:
                entity_type_base = d.get("ENTITY_TYPE_BASE")
                if not entity_type_base:
                    for base in bases:
                        entity_type_base = getattr(base, "ENTITY_TYPE_BASE", None)
                        if entity_type_base:
                            break
                    else:
                        # no break happened during loop: use default type base
                        entity_type_base = d["__module__"]

                d["entity_type"] = entity_type_base + "." + classname

            default_permissions = d.get("__default_permissions__")
            if default_permissions is not None:
                if isinstance(default_permissions, collections.Mapping):
                    default_permissions = default_permissions.items()
                elif not isinstance(default_permissions, collections.Set):
                    raise TypeError(
                        "__default_permissions__ is neither a dict or set, "
                        "cannot create class {}".format(classname)
                    )

                # also ensure that `roles` set is immutable, too
                default_permissions = frozenset(
                    (permission, frozenset(roles))
                    for permission, roles in default_permissions
                )
                d["__default_permissions__"] = default_permissions

            d["SLUG_SEPARATOR"] = str(d.get("SLUG_SEPARATOR", Entity.SLUG_SEPARATOR))

        cls = BaseMeta.__new__(mcs, classname, bases, d)

        if not issubclass(cls.query_class, EntityQuery):
            raise TypeError(
                f"query_class is not a subclass of EntityQuery: {cls.query_class!r}"
            )

        event.listen(cls, "before_insert", auto_slug_on_insert)
        event.listen(cls, "after_insert", auto_slug_after_insert)
        return cls

    def __init__(
        cls, classname: str, bases: Tuple[Type, ...], d: Dict[str, Any]
    ) -> None:
        bases = cls.__bases__
        BaseMeta.__init__(cls, classname, bases, d)


class Entity(Indexable, BaseMixin, Model, metaclass=EntityMeta):
    """Base class for Abilian entities.

    From Sqlalchemy POV, Entities use `Joined-Table inheritance
    <http://docs.sqlalchemy.org/en/rel_0_8/orm/inheritance.html#joined-table-inheritance>`_,
    thus entities subclasses cannot use inheritance themselves (as of 2013
    Sqlalchemy does not support multi-level inheritance)

    The metaclass automatically sets up polymorphic inheritance parameters by
    inserting a mixin class in parent classes. If you need to pass additional
    parameters to `__mapper_args__`, do it as follow:

    .. code-block:: python

      class MyContent(Entity):

          @sqlalchemy.ext.declarative.declared_attr
          def __mapper_args__(cls):
              # super(Mycontent, cls).__mapper_args__ would be prettier, but
              # `MyContent` is not defined at this stage.
              args = Entity.__dict__['__mapper_args__'].fget(cls)
              args['order_by'] = cls.created_at # for example
              return args
    """

    __indexable__ = False
    __index_to__ = (
        ("_indexable_roles_and_users", ("allowed_roles_and_users",)),
        ("_indexable_tag_ids", ("tag_ids",)),
        ("_indexable_tag_text", ("tag_text", "text")),
    )

    __default_permissions__ = frozenset()
    """
    Permission to roles mapping to set at object creation time.

    Default permissions can be declared as a :py:class:`dict` on classes, the final
    datastructure will changed by metaclass to a :py:class:`frozenset` of
    :py:meth:`dict.items`. This is made to garantee the immutability of definition
    on parent classes.

    Exemple definition:

    .. code-block:: python

     __default_permissions__ = {
         READ: {Owner, Authenticated},
         WRITE: {Owner},
     }


    To alter inherited default permissions:

    .. code-block:: python

     class Child(Parent):
         __default_permissions__ = dp = dict(ParentClass.__default_permissions__)
         dp[READ] = dp[READ] - {Authenticated} + {Anonymous}
         del dp
    """

    SLUG_SEPARATOR = "-"  # \x2d \u002d HYPHEN-MINUS

    query_class = EntityQuery

    @declared_attr
    def __mapper_args__(cls) -> Dict[str, Any]:
        if cls.__module__ == __name__ and cls.__name__ == "Entity":
            return {"polymorphic_on": "_entity_type"}

        else:
            return {
                "polymorphic_identity": cls.entity_type,
                "inherit_condition": cls.id == Entity.id,
            }

    #: The name is a string that is shown to the user; it could be a title
    #: for document, a folder name, etc.
    name = Column("name", UnicodeText())
    name.info = EDITABLE | SEARCHABLE | {"index_to": ("name", "name_prefix", "text")}

    slug = Column("slug", UnicodeText(), info=SEARCHABLE)
    """
    The slug attribute may be used in URLs to reference the entity, but
    uniqueness is not enforced, even within same entity type. For example
    if an entity class represent folders, one could want uniqueness only
    within same parent folder.

    If slug is empty at first creation, its is derived from the name. When name
    changes the slug is not updated. If name is also empty, the slug will be the
    friendly entity_type with concatenated with entity's id.
    """

    _entity_type = Column("entity_type", String(1000), nullable=False)
    entity_type = ""

    meta = Column(JSONDict(), nullable=False, default=dict, server_default="{}")
    """
    A dictionnary of simple values (JSON-serializable) to conveniently annotate
    the entity.

    It is recommanded to keep it lighwight and not store large objects in it.
    """

    @property
    def object_type(self) -> str:
        return str(self.entity_type)

    @classmethod
    def _object_type(cls) -> str:
        # overriden from Indexable
        return cls.entity_type

    @property
    def entity_class(self) -> str:
        return self.entity_type and friendly_fqcn(self.entity_type)

    # Default magic metadata, should not be necessary
    # TODO: remove
    __editable__: FrozenSet = frozenset()
    __searchable__: FrozenSet = frozenset()
    __auditable__: FrozenSet = frozenset()

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self, *args, **kwargs)
        BaseMixin.__init__(self)

        if self.meta is None:
            self.meta = {}

    @property
    def auto_slug(self) -> str:
        """This property is used to auto-generate a slug from the name
        attribute.

        It can be customized by subclasses.
        """
        slug = self.name
        if slug is not None:
            slug = slugify(slug, separator=self.SLUG_SEPARATOR)
            session = sa.orm.object_session(self)
            if not session:
                return ""
            query = session.query(Entity.slug).filter(
                Entity._entity_type == self.object_type
            )
            if self.id is not None:
                query = query.filter(Entity.id != self.id)
            slug_re = re.compile(re.escape(slug) + r"-?(-\d+)?")
            results = [
                int(m.group(1) or 0)  # 0: for the unnumbered slug
                for m in (slug_re.match(s.slug) for s in query.all() if s.slug)
                if m
            ]

            max_id = max(-1, -1, *results) + 1
            if max_id:
                slug = f"{slug}-{max_id}"
        return slug

    @property
    def _indexable_roles_and_users(self) -> str:
        """Return a string made for indexing roles having :any:`READ`
        permission on this object."""
        from abilian.services import get_service
        from abilian.services.indexing import indexable_role
        from abilian.services.security import READ, Admin, Anonymous, \
            Creator, Owner, SecurityService

        result = []
        security = cast(SecurityService, get_service("security"))

        # roles - required to match when user has a global role
        assignments = security.get_permissions_assignments(permission=READ, obj=self)
        allowed_roles = assignments.get(READ, set())
        allowed_roles.add(Admin)

        for r in allowed_roles:
            result.append(indexable_role(r))

        for role, attr in ((Creator, "creator"), (Owner, "owner")):
            if role in allowed_roles:
                user = getattr(self, attr)
                if user:
                    result.append(indexable_role(user))

        # users and groups
        principals = set()
        for user, role in security.get_role_assignements(self):
            if role in allowed_roles:
                principals.add(user)

        if Anonymous in principals:
            # it's a role listed in role assignments - legacy when there wasn't
            # permission-role assignments
            principals.remove(Anonymous)

        for p in principals:
            result.append(indexable_role(p))

        return " ".join(result)

    @property
    def _indexable_tags(self) -> List["Tag"]:
        """Index tag ids for tags defined in this Entity's default tags
        namespace."""
        tags = current_app.extensions.get("tags")
        if not tags or not tags.supports_taggings(self):
            return []

        default_ns = tags.entity_default_ns(self)
        return [t for t in tags.entity_tags(self) if t.ns == default_ns]

    @property
    def _indexable_tag_ids(self) -> str:
        return " ".join(str(t.id) for t in self._indexable_tags)

    @property
    def _indexable_tag_text(self) -> str:
        return " ".join(str(t.label) for t in self._indexable_tags)

    def clone(self):
        """Copy an entity: copy every field, except the id and sqlalchemy
        internals, without forgetting about the n-n relationships.

        - return: the newly created entity

        Example::

            def clone(self):
                old_attrs = self.__dict__.copy()
                del old_attrs['_sa_instance_state']
                if 'id' in old_attrs:
                    del old_attrs['id']
                new = AnEntity(**old_attrs)
                # Needs special treatment for n-n relationship
                new.related_projects = self.related_projects
                new.ancestor = self
                return new
        """
        raise NotImplementedError


# TODO: make this unecessary
@event.listens_for(Entity, "class_instrument", propagate=True)
def register_metadata(cls: Type[Entity]) -> None:
    cls.__editable__ = set()

    # TODO: use SQLAlchemy 0.8 introspection
    if hasattr(cls, "__table__"):
        columns = cls.__table__.columns
    else:
        columns = [v for k, v in vars(cls).items() if isinstance(v, Column)]

    for column in columns:
        name = column.name
        info = column.info

        if info.get("editable", True):
            cls.__editable__.add(name)


@event.listens_for(Session, "before_flush")
def polymorphic_update_timestamp(
    session: Session, flush_context: UOWTransaction, instances: Any
) -> None:
    """This listener ensures an update statement is emited for "entity" table
    to update 'updated_at'.

    With joined-table inheritance if the only modified attributes are
    subclass's ones, then no update statement will be emitted.
    """
    for obj in session.dirty:
        if not isinstance(obj, Entity):
            continue
        state = sa.inspect(obj)
        history = state.attrs["updated_at"].history
        if not any((history.added, history.deleted)):
            obj.updated_at = datetime.utcnow()


@memoized
def all_entity_classes():
    """Return the list of all concrete persistent classes that are subclasses
    of Entity."""
    persistent_classes = Entity._decl_class_registry.values()
    # with sqlalchemy 0.8 _decl_class_registry holds object that are not
    # classes
    return [
        cls for cls in persistent_classes if isclass(cls) and issubclass(cls, Entity)
    ]
