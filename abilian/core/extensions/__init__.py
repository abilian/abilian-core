# coding=utf-8
"""
Create all standard extensions.

"""

# Note: Because of issues with circular dependencies, Abilian-specific
# extensions are created later.

from __future__ import absolute_import, print_function, division

from abilian.core.logging import patch_logger
from sqlalchemy.engine import Engine

from flask import current_app
from . import upstream_info
from .login import login_manager
import flask_mail
import sqlalchemy as sa
from ..sqlalchemy import SQLAlchemy
from .csrf import wtf_csrf as csrf, abilian_csrf

__all__ = ['get_extension', 'db', 'mail', 'login_manager', 'csrf',
           'upstream_info']


# patch flask.ext.mail.Message.send to always set enveloppe_from default mail
# sender
# FIXME: we'ld rather subclass Message and update all imports
def _message_send(self, connection):
    """Send a single message instance.

    If TESTING is True the message will not actually be sent.

    :param message: a Message instance.
    """
    sender = current_app.config['MAIL_SENDER']
    if not self.extra_headers:
        self.extra_headers = {}
    self.extra_headers['Sender'] = sender
    connection.send(self, sender)


patch_logger.info(flask_mail.Message.send)
flask_mail.Message.send = _message_send

mail = flask_mail.Mail()

db = SQLAlchemy()


@sa.event.listens_for(db.metadata, 'before_create')
@sa.event.listens_for(db.metadata, 'before_drop')
def _filter_metadata_for_connection(target, connection, **kw):
    """Listener to control what indexes get created.

    Useful for skipping postgres-specific indexes on a sqlite for example.

    It's looking for info entry `engines` on an index
    (`Index(info=dict(engines=['postgresql']))`), an iterable of engine names.
    """
    engine = connection.engine.name
    default_engines = (engine,)
    tables = target if isinstance(target, sa.Table) else kw.get('tables', [])
    for table in tables:
        indexes = list(table.indexes)
        for idx in indexes:
            if engine not in idx.info.get('engines', default_engines):
                table.indexes.remove(idx)

# csrf


def get_extension(name):
    """Get the named extension from the current app, returning None if not found.
    """
    return current_app.extensions.get(name)


def _install_get_display_value(cls):

    _MARK = object()

    def display_value(self, field_name, value=_MARK):
        """ Return display value for fields having 'choices' mapping (stored value
        -> human readable value). For other fields it will simply return field
        value.

        `display_value` should be used instead of directly getting field value.

        If `value` is provided it is "tranlated" to a human-readable value. This is
        useful for obtaining a human readable label from a raw value
        """
        val = getattr(self, field_name) if value is _MARK else value

        mapper = sa.orm.object_mapper(self)
        try:
            field = getattr(mapper.c, field_name)
        except AttributeError:
            pass
        else:
            if 'choices' in field.info:
                get = lambda v: field.info['choices'].get(v, v)
                if isinstance(val, list):
                    val = [get(v) for v in val]
                else:
                    val = get(val)

        return val

    if not hasattr(cls, 'display_value'):
        cls.display_value = display_value


sa.event.listen(db.Model, 'class_instrument', _install_get_display_value)


#
# Make Sqlite a bit more well-behaved.
#
@sa.event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    from sqlite3 import Connection as SQLite3Connection
    if isinstance(dbapi_connection, SQLite3Connection):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
