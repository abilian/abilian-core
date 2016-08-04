# coding=utf-8
""" Additional data types for sqlalchemy
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import json
import logging
import sys
import uuid

import babel
import flask_sqlalchemy as flask_sa
import pytz
import sqlalchemy as sa
from flask_sqlalchemy import SQLAlchemy as SAExtension
from six import string_types, text_type
from sqlalchemy.event import listens_for
from sqlalchemy.ext.mutable import Mutable

from .logging import patch_logger

logger = logging.getLogger(__name__)


@listens_for(sa.pool.Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    """Ensure connections are valid.

    From: `http://docs.sqlalchemy.org/en/rel_0_8/core/pooling.html`

    In case db has been restarted pool may return invalid connections.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise sa.exc.DisconnectionError()
    cursor.close()


class SQLAlchemy(SAExtension):
    """Base subclass of :class:`flask_sqlalchemy.SQLAlchemy`.

    Add our custom driver hacks.
    """

    def apply_driver_hacks(self, app, info, options):
        SAExtension.apply_driver_hacks(self, app, info, options)

        if info.drivername == 'sqlite':
            connect_args = options.setdefault('connect_args', {})

            if 'isolation_level' not in connect_args:
                # required to support savepoints/rollback without error. It disables
                # implicit BEGIN/COMMIT statements made by pysqlite (a COMMIT kills all
                # savepoints made).
                connect_args['isolation_level'] = None
        elif info.drivername.startswith('postgres'):
            options.setdefault('client_encoding', 'utf8')


# PATCH flask_sqlalchemy for proper info in debug toolbar.
#
# Original code works only when current app code is involved. If using 3rd party
# app the query is logged but source is marked "unknown". Our patch is a "best
# guess".
def _calling_context(app_path):
    frm = sys._getframe(1)
    entered_sa_code = exited_sa_code = False
    sa_caller = '<unknown>'
    format_name = ('{frm.f_code.co_filename}:{frm.f_lineno} '
                   '({frm.f_code.co_name})'.format)

    while frm.f_back is not None:
        name = frm.f_globals.get('__name__')
        if name and (name == app_path or name.startswith(app_path + '.') or
                     name.startswith('abilian.')):
            return format_name(frm=frm)

        if not exited_sa_code:
            in_sa_code = name and (name == 'sqlalchemy' or
                                   name.startswith('sqlalchemy.'))
            if not entered_sa_code:
                entered_sa_code = in_sa_code
            elif not in_sa_code:
                # exited from sa stack: retain name
                sa_caller = format_name(frm=frm)
                exited_sa_code = True

        frm = frm.f_back

    return sa_caller


patch_logger.info(flask_sa._calling_context)
flask_sa._calling_context = _calling_context
del flask_sa

# END PATCH


def filter_cols(model, *filtered_columns):
    """Return columnsnames for a model except named ones.

    Useful for defer() for example to retain only columns of interest
    """
    m = sa.orm.class_mapper(model)
    return list(
        set(p.key for p in m.iterate_properties
            if hasattr(p, 'columns')).difference(filtered_columns))


class MutationDict(Mutable, dict):
    """Provides a dictionary type with mutability support."""

    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionaries to MutationDict."""
        if not isinstance(value, MutationDict):
            if isinstance(value, dict):
                return MutationDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    #  pickling support. see:
    #  http://docs.sqlalchemy.org/en/rel_0_8/orm/extensions/mutable.html#supporting-pickling
    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)

    # dict methods
    def __setitem__(self, key, value):
        """Detect dictionary set events and emit change events."""
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """Detect dictionary del events and emit change events."""
        dict.__delitem__(self, key)
        self.changed()

    def clear(self):
        dict.clear(self)
        self.changed()

    def update(self, other):
        dict.update(self, other)
        self.changed()

    def setdefault(self, key, failobj=None):
        if key not in self:
            self.changed()
        return dict.setdefault(self, key, failobj)

    def pop(self, key, *args):
        self.changed()
        return dict.pop(self, key, *args)

    def popitem(self):
        self.changed()
        return dict.popitem(self)


class MutationList(Mutable, list):
    """
    Provides a list type with mutability support.
    """

    @classmethod
    def coerce(cls, key, value):
        """Convert list to MutationList."""
        if not isinstance(value, MutationList):
            if isinstance(value, list):
                return MutationList(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    #  pickling support. see:
    #  http://docs.sqlalchemy.org/en/rel_0_8/orm/extensions/mutable.html#supporting-pickling
    def __getstate__(self):
        d = self.__dict__.copy()
        d.pop('_parents', None)
        return d

    # list methods
    def __setitem__(self, idx, value):
        list.__setitem__(self, idx, value)
        self.changed()

    def __delitem__(self, idx):
        list.__delitem__(self, idx)
        self.changed()

    def insert(self, idx, value):
        list.insert(self, idx, value)
        self.changed()

    def __setslice__(self, i, j, other):
        list.__setslice__(self, i, j, other)
        self.changed()

    def __delslice__(self, i, j):
        list.__delslice__(self, i, j)
        self.changed()

    def __iadd__(self, other):
        l = list.__iadd__(self, other)
        self.changed()
        return l

    def __imul__(self, n):
        l = list.__imul__(self, n)
        self.changed()
        return l

    def append(self, item):
        list.append(self, item)
        self.changed()

    def pop(self, i=-1):
        item = list.pop(self, i)
        self.changed()
        return item

    def remove(self, item):
        list.remove(self, item)
        self.changed()

    def reverse(self):
        list.reverse(self)
        self.changed()

    def sort(self, *args, **kwargs):
        list.sort(self, *args, **kwargs)
        self.changed()

    def extend(self, other):
        list.extend(self, other)
        self.changed()


class JSON(sa.types.TypeDecorator):
    """Stores any structure serializable with json.

    Usage
    JSON()
    Takes same parameters as sqlalchemy.types.Text
    """
    impl = sa.types.Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JSONUniqueListType(JSON):
    """Store a list in JSON format, with items made unique and sorted.
    """

    @property
    def python_type(self):
        return MutationList

    def process_bind_param(self, value, dialect):
        # value may be a simple string used in a LIKE clause for instance, so we
        # must ensure we uniquify/sort only for list-like values
        if value is not None and isinstance(value, (tuple, list)):
            value = sorted(set(value))

        return JSON.process_bind_param(self, value, dialect)


def JSONDict(*args, **kwargs):
    """Stores a dict as JSON on database, with mutability support.
    """
    return MutationDict.as_mutable(JSON(*args, **kwargs))


def JSONList(*args, **kwargs):
    """Stores a list as JSON on database, with mutability support.

    If kwargs has a param `unique_sorted` (which evaluated to True), list values
    are made unique and sorted.
    """
    type_ = JSON
    try:
        if kwargs.pop('unique_sorted'):
            type_ = JSONUniqueListType
    except KeyError:
        pass

    return MutationList.as_mutable(type_(*args, **kwargs))


class UUID(sa.types.TypeDecorator):
    """Platform-independent UUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    From SQLAlchemy documentation.
    """
    impl = sa.types.CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(sa.dialects.postgresql.UUID())
        else:
            return dialect.type_descriptor(sa.types.CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            # hexstring
            return value.hex

    def process_result_value(self, value, dialect):
        return value if value is None else uuid.UUID(value)

    def compare_against_backend(self, dialect, conn_type):
        if dialect.name == 'postgresql':
            return isinstance(conn_type, sa.dialects.postgresql.UUID)
        else:
            return isinstance(conn_type, sa.types.CHAR)


class Locale(sa.types.TypeDecorator):
    """Store a :class:`babel.Locale` instance
    """
    impl = sa.types.UnicodeText

    @property
    def python_type(self):
        return babel.Locale

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if not isinstance(value, babel.Locale):
            if not isinstance(value, string_types):
                raise ValueError("Unknown locale value: %s" % repr(value))
            if not value.strip():
                return None
            value = babel.Locale.parse(value)

        code = text_type(value.language)
        if value.territory:
            code += u'_' + text_type(value.territory)
        elif value.script:
            code += u'_' + text_type(value.territory)

        return code

    def process_result_value(self, value, dialect):
        return None if value is None else babel.Locale.parse(value)


class Timezone(sa.types.TypeDecorator):
    """Store a :class:`pytz.tzfile.DstTzInfo` instance
    """
    impl = sa.types.UnicodeText

    @property
    def python_type(self):
        return pytz.tzfile.DstTzInfo

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        if not isinstance(value, pytz.tzfile.DstTzInfo):
            if not isinstance(value, string_types):
                raise ValueError("Unknown timezone value: %s" % repr(value))
            if not value.strip():
                return None
            value = babel.dates.get_timezone(value)

        return value.zone

    def process_result_value(self, value, dialect):
        return None if value is None else babel.dates.get_timezone(value)

# SQLAlchemy > 0.9 has a function generator that forget to set __module__
# attributes in 0.9.x series. This is fixed in 1.0.x. Sphinx will try to include
# those symbols in documentation, and this may break since we don't have
# sphinx's extensions used by sqlalchemy author.
#
# Ref: https://bitbucket.org/zzzeek/sqlalchemy/issues/3218/__module__-should-be-set-on-functions
if not sa.orm.relationship.__module__:
    sa.orm.relationship.__module__ = 'sqlalchemy.orm'
