# coding=utf-8
"""Elements to build test cases for an :class:`abilian.app.Application`"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from sqlalchemy.exc import DatabaseError

from abilian.services import get_service

__all__ = ('stop_all_services', 'ensure_services_started', 'cleanup_db')


def cleanup_db(db):
    """Drop all the tables, in a way that doesn't raise integrity errors."""

    # Need to run this sequence twice for some reason
    _delete_tables(db)
    _delete_tables(db)
    # One more time, just in case ?
    db.drop_all()


def _delete_tables(db):
    for table in reversed(db.metadata.sorted_tables):
        try:
            db.session.execute(table.delete())
        except DatabaseError:
            pass


def ensure_services_started(services):
    for service_name in services:
        service = get_service(service_name)
        if not service.running:
            service.start()


def stop_all_services(app):
    for service in app.services.values():
        if service.running:
            service.stop()
