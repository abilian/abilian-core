"""Subject classes (i.e. people, groups, etc.).

See ICOM-ics-v1.0 "Subject Branch".

TODO: I'm not a big fan of the "subject" name. Could be replaced by something
else, like "people" or "principal" ?
"""
import random
import string
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from typing import Type, Union

import bcrypt
import sqlalchemy as sa
from flask_login import UserMixin
from flask_sqlalchemy import BaseQuery
from sqlalchemy.event import listens_for
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, deferred, relationship
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Boolean, DateTime, Integer, LargeBinary, \
    UnicodeText

from abilian.core import sqlalchemy as sa_types
from abilian.core.util import fqcn

from .base import SEARCHABLE, SYSTEM, IdMixin, Indexable, TimestampedMixin, db

__all__ = (
    "User",
    "Group",
    "Principal",
    "ClearPasswordStrategy",
    "gen_random_password",
    "create_root_user",
)

# Tables for many-to-many relationships
following = db.Table(
    "following",
    db.Model.metadata,
    Column("follower_id", Integer, ForeignKey("user.id")),
    Column("followee_id", Integer, ForeignKey("user.id")),
    UniqueConstraint("follower_id", "followee_id"),
)

membership = db.Table(
    "membership",
    db.Model.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    Column(
        "group_id",
        Integer,
        ForeignKey("group.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    UniqueConstraint("user_id", "group_id"),
)

# Should not be needed (?)
administratorship = db.Table(
    "administratorship",
    db.Model.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("user.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    Column(
        "group_id",
        Integer,
        ForeignKey("group.id", onupdate="CASCADE", ondelete="CASCADE"),
    ),
    UniqueConstraint("user_id", "group_id"),
)

_RANDOM_PASSWORD_CHARS = string.ascii_letters + string.digits + string.punctuation


def gen_random_password(length=15):
    rg = random.SystemRandom()
    return "".join(rg.choice(_RANDOM_PASSWORD_CHARS) for i in range(length))


class PasswordStrategy(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self):
        """Strategy name."""

    @abstractmethod
    def authenticate(self, user, password):
        """Predicate to tell wether password match user's or not."""

    @abstractmethod
    def process(self, user, password):
        """Return a string to be stored as user password."""


class ClearPasswordStrategy(PasswordStrategy):
    """Don't encrypt at all.

    This strategy should not ever be used elsewhere than in tests. It's
    useful in tests since a hash like bcrypt is designed to be slow.
    """

    @property
    def name(self):
        return "clear"

    def authenticate(self, user, password):
        return user.password == password

    def process(self, user, password):
        if not isinstance(password, str):
            password = password.decode("utf-8")
        return password


class BcryptPasswordStrategy(PasswordStrategy):
    """Hash passwords using bcrypt."""

    @property
    def name(self):
        return "bcrypt"

    def authenticate(self, user: "User", password: str) -> bool:
        current_passwd = user.password
        # crypt work only on bytes, not str (Unicode)
        if isinstance(current_passwd, str):
            current_passwd = current_passwd.encode("utf-8")
        if isinstance(password, str):
            password = password.encode("utf-8")

        return bcrypt.hashpw(password, current_passwd) == current_passwd

    def process(self, user: "User", password: str) -> str:
        if isinstance(password, str):
            password = password.encode("utf-8")
        return bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")


class UserQuery(BaseQuery):
    def get_by_email(self, email):
        return self.filter_by(email=email).one()


class Principal(IdMixin, TimestampedMixin, Indexable):
    """A principal is either a User or a Group."""

    __index_to__ = (("name", ("name", "name_prefix", "text")),)

    def has_role(self, role, context=None):
        from abilian.services import get_service

        security = get_service("security")
        return security.has_role(self, role, context)


def set_entity_type(
    cls: Union[Type["User"], Type["Group"]]
) -> Union[Type["User"], Type["Group"]]:
    """Decorator used to set the class' entity_type after the class has been
    declared.

    Actually, it works using __module__ during class declaration, but
    linters (Flake8, PyCharm) complain.
    """
    cls.entity_type = fqcn(cls)
    return cls


@set_entity_type
class User(Principal, UserMixin, db.Model):
    __tablename__ = "user"
    __editable__ = ["first_name", "last_name", "email", "password"]
    __exportable__ = __editable__ + ["created_at", "updated_at", "id"]

    __password_strategy__ = BcryptPasswordStrategy()

    query_class = UserQuery
    query: UserQuery

    # Basic information
    first_name = Column(UnicodeText, info=SEARCHABLE)
    last_name = Column(UnicodeText, info=SEARCHABLE)
    # Should we add gender, salutation ?

    # System information
    email = Column(UnicodeText, nullable=False)
    can_login = Column(Boolean, nullable=False, default=True)
    password = Column(UnicodeText, default="*", info={"audit_hide_content": True})

    photo = deferred(Column(LargeBinary))

    last_active = Column(DateTime, info=SYSTEM)
    locale = Column(sa_types.Locale, nullable=True, default=None)
    timezone = Column(sa_types.Timezone, nullable=True, default=None)

    __table_args__ = (UniqueConstraint("email"),)

    followers = relationship(
        "User",
        secondary=following,
        primaryjoin="User.id == following.c.follower_id",
        secondaryjoin="User.id == following.c.followee_id",
        backref="followees",
    )

    def __init__(self, password=None, **kwargs):
        Principal.__init__(self)
        UserMixin.__init__(self)
        db.Model.__init__(self, **kwargs)

        if self.can_login and password is not None:
            self.set_password(password)
            self._password = password

    def authenticate(self, password: str) -> bool:
        if self.password and self.password != "*":
            return self.__password_strategy__.authenticate(self, password)
        else:
            return False

    def set_password(self, password: str) -> None:
        """Encrypts and sets password."""
        self.password = self.__password_strategy__.process(self, password)

    def follow(self, followee):
        if followee == self:
            raise Exception("User can't follow self")
        self.followees.append(followee)

    def unfollow(self, followee):
        if followee == self:
            raise Exception("User can't follow self")
        i = self.followees.index(followee)
        del self.followees[i]

    def join(self, group):
        self.groups.add(group)

    def leave(self, group):
        if group in self.groups:
            self.groups.remove(group)

    #
    # Boolean properties
    #
    def is_following(self, other):
        return other in self.followees

    def is_member_of(self, group):
        return self in group.members

    def is_admin_of(self, group):
        return self in group.admins

    @property
    def is_online(self):
        if self.last_active is None:
            return False
        return datetime.utcnow() - self.last_active <= timedelta(minutes=1)

    #
    # Other properties
    #
    @property
    def name(self) -> str:
        name = f"{(self.first_name or '')} {(self.last_name or '')}"
        return name.strip() or "Unknown"

    @property
    def short_name(self):
        first_name = self.first_name or ""
        last_name = self.last_name[0:1] + "." if self.last_name else ""
        name = f"{first_name} {last_name}"
        return name.strip() or "Unknown"

    def __str__(self) -> str:
        return self.name

    def __repr__(self):
        cls = self.__class__
        return "<{mod}.{cls} id={id!r} email={email!r} at 0x{addr:x}>".format(
            mod=cls.__module__,
            cls=cls.__name__,
            id=self.id,
            email=self.email,
            addr=id(self),
        )


@listens_for(User, "mapper_configured", propagate=True)
def _add_user_indexes(mapper: Mapper, class_: type) -> None:
    # this is a functional index (indexes on a function result), we cannot define
    # it in __table_args__.
    #
    # see: https://groups.google.com/d/msg/sqlalchemy/CgSJUlelhGs/_Nj3f201hs4J
    idx = sa.schema.Index(
        "user_unique_lowercase_email", sa.sql.func.lower(class_.email), unique=True
    )
    idx.info["engines"] = ("postgresql",)


@set_entity_type
class Group(Principal, db.Model):
    __indexable__ = False
    __tablename__ = "group"
    __editable__ = ["name", "description"]
    __exportable__ = __editable__ + ["created_at", "updated_at", "id"]

    name = Column(UnicodeText, nullable=False, info=SEARCHABLE)
    description = Column(UnicodeText, info=SEARCHABLE)

    members = relationship(
        "User",
        collection_class=set,
        secondary=membership,
        backref=backref("groups", lazy="select", collection_class=set),
    )
    admins = relationship("User", collection_class=set, secondary=administratorship)

    photo = deferred(Column(LargeBinary))

    public = Column(Boolean, default=False, nullable=False)

    @hybrid_property
    def members_count(self):
        return len(self.members)

    @members_count.expression
    def members_count(cls):
        return (
            sa.sql.select([sa.sql.func.count(membership.c.user_id)])
            .where(membership.c.group_id == cls.id)
            .group_by(membership.c.group_id)
            .label("members_count")
        )


def create_root_user() -> User:
    user = User.query.get(0)
    if user is None:
        user = User(
            id=0, last_name="SYSTEM", email="system@example.com", can_login=False
        )
        db.session.add(user)
        db.session.commit()
    return user
