"""
Subject classes (i.e. people, groups, etc.).

See ICOM-ics-v1.0 "Subject Branch".

TODO: I'm not a big fan of the "subject" name. Could be replaced by something
else, like "people" or "principal" ?
"""
from __future__ import absolute_import

import bcrypt
from datetime import datetime, timedelta

from flask.ext.login import UserMixin

from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy.orm.query import Query
from sqlalchemy.schema import Column, Table, ForeignKey, UniqueConstraint
from sqlalchemy.types import Integer, UnicodeText, LargeBinary, Boolean, DateTime, Text

from abilian.core.extensions import db
from .base import IdMixin, TimestampedMixin, Indexable, SEARCHABLE, SYSTEM

__all__ = ['User', 'Group', 'Principal']


# Tables for many-to-many relationships
following = Table(
  'following', db.Model.metadata,
  Column('follower_id', Integer, ForeignKey('user.id')),
  Column('followee_id', Integer, ForeignKey('user.id')),
  UniqueConstraint('follower_id', 'followee_id'),
)
membership = Table(
  'membership', db.Model.metadata,
  Column('user_id', Integer, ForeignKey('user.id')),
  Column('group_id', Integer, ForeignKey('group.id')),
  UniqueConstraint('user_id', 'group_id'),
)

# Should not be needed (?)
administratorship = Table(
  'administratorship', db.Model.metadata,
  Column('user_id', Integer, ForeignKey('user.id')),
  Column('group_id', Integer, ForeignKey('group.id')),
  UniqueConstraint('user_id', 'group_id'),
)


class UserQuery(Query):
  def get_by_email(self, email):
    return self.filter_by(email=email).one()


class Principal(IdMixin, TimestampedMixin, Indexable):
  """A principal is either a User or a Group."""
  pass


class User(Principal, UserMixin, db.Model):
  __tablename__ = 'user'
  __editable__ = ['first_name', 'last_name', 'email', 'password']
  __exportable__ = __editable__ + ['created_at', 'updated_at', 'id']

  query_class = UserQuery

  # Basic information
  first_name = Column(UnicodeText, info=SEARCHABLE)
  last_name = Column(UnicodeText, info=SEARCHABLE)
  # Should we add gender, salutation ?

  # System information
  locale = Column(Text)

  email = Column(UnicodeText, nullable=False)
  can_login = Column(Boolean, nullable=False, default=True)
  password = Column(UnicodeText, default=u"*",
                    info={'audit_hide_content': True})

  photo = deferred(Column(LargeBinary))

  last_active = Column(DateTime, info=SYSTEM)

  __table_args__ = (UniqueConstraint('email'),)

  followers = relationship("User", secondary=following,
                           primaryjoin=('User.id == following.c.follower_id'),
                           secondaryjoin=('User.id == following.c.followee_id'),
                           backref='followees')

  def __init__(self, password=None, **kwargs):
    Principal.__init__(self)
    UserMixin.__init__(self)
    db.Model.__init__(self, **kwargs)

    if self.can_login and password is not None:
      self.set_password(password)

  def authenticate(self, password):
    # crypt work only on str, not unicode
    if self.password and self.password != "*":
      current_passwd = self.password
      if isinstance(current_passwd, unicode):
        current_passwd = self.password.encode('utf-8')
      if isinstance(password, unicode):
        password = password.encode('utf-8')

      return bcrypt.hashpw(password, current_passwd) == current_passwd
    else:
      return False

  def set_password(self, password):
    """Encrypts and sets password."""
    if isinstance(password, unicode):
      password = password.encode('utf-8')

    self.password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

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
    if not group in self.groups:
      self.groups.append(group)

  def leave(self, group):
    if group in self.groups:
      del self.groups[self.groups.index(group)]

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
    return datetime.utcnow() - self.last_active <= timedelta(0, 60)

  #
  # Other properties
  #
  @property
  def username(self):
    return (self.first_name or "") + (self.last_name or "")

  @property
  def name(self):
    name = u'{first_name} {last_name}'.format(first_name=self.first_name or u'',
                                              last_name=self.last_name or u'')
    return name.strip() or u'Unknown'

  def __unicode__(self):
    return self.name

  # XXX: Should entities know about their own URL? Eventually, no.
  @property
  def _url(self):
    return "/social/users/%d" % self.id


class Group(Principal, db.Model):
  __tablename__ = 'group'
  __editable__ = ['name', 'description']
  __exportable__ = __editable__ + ['created_at', 'updated_at', 'id']

  name = Column(UnicodeText, nullable=False, info=SEARCHABLE)
  description = Column(UnicodeText, info=SEARCHABLE)

  members = relationship("User", secondary=membership,
                         backref=backref('groups', lazy='lazy'))
  admins = relationship("User", secondary=administratorship)

  photo = deferred(Column(LargeBinary))

  public = Column(Boolean, default=False, nullable=False)

  # XXX: Should entities know about their own URL? Eventually, no.
  @property
  def _url(self):
    return "/social/groups/%d" % self.id
