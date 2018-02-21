# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import current_app
from six import iteritems

from abilian.core.extensions import db
from abilian.services import Service

from .models import Setting


class SettingsService(Service):
    name = 'settings'

    def namespace(self, name):
        # type: (unicode) -> SettingsNamespace
        return SettingsNamespace(name, self)

    def keys(self, prefix=None):
        """List all keys, with optional prefix filtering."""
        query = Setting.query
        if prefix:
            query = query.filter(Setting.key.startswith(prefix))

        # don't use iteritems: 'value' require little processing whereas we only
        # want 'key'
        return [i[0] for i in query.yield_per(1000).values(Setting.key)]

    def iteritems(self, prefix=None):
        """Like dict.iteritems."""
        query = Setting.query
        if prefix:
            query = query.filter(Setting.key.startswith(prefix))

        for s in query.yield_per(1000):
            yield (s.key, s.value)

    items = iteritems

    def as_dict(self, prefix=None):
        """Return a mapping key -> value of settings, with optional prefix
        filtering."""
        return dict(self.iteritems(prefix))

    def _get_setting(self, key):
        s = Setting.query.get(key)
        if s is None:
            raise KeyError(key)

        return s

    def get(self, key):
        """Returns value of a previously stored key."""
        s = self._get_setting(key)
        return s.value

    def set(self, key, value, type_=None):
        try:
            s = self._get_setting(key)
        except KeyError:
            if not type_:
                raise ValueError(
                    'tried to set a new key without specifiying its type',
                )
            s = Setting(key=key, type=type_)

        # Always add to session. This covers the case delete(key);set(key).
        # Without it, Setting would still be in session 'delete' queue.
        db.session.add(s)
        s.value = value

    def delete(self, key, silent=True):
        try:
            s = self._get_setting(key)
        except KeyError:
            if not silent:
                raise
        else:
            db.session.delete(s)


class SettingsNamespace(object):
    """Allow to query :class:`SettingsService` service within a namespace.

    Basically it prefixes keys with namespace name and a colon.
    """

    def __init__(self, name, service):
        self.name = name
        self.service = service

    def namespace(self, name):
        """A namespace within this namespace."""
        return SettingsNamespace(self.ns(name), self.service)

    def ns(self, key):
        """Returns full key name for use in settings service."""
        return ':'.join((self.name, key))

    def keys(self, prefix=''):
        prefix = ':'.join((self.name, prefix))
        start = len(self.name) + 1  # +1 for colon
        return [k[start:] for k in self.service.keys(prefix=prefix)]

    def iteritems(self, prefix=''):
        prefix = ':'.join((self.name, prefix))
        start = len(self.name) + 1  # +1 for colon
        iteritems(self.service, prefix=prefix)
        for k, v in iteritems(self.service, prefix=prefix):
            yield (k[start:], v)

    def as_dict(self, prefix=''):
        return dict(self.iteritems(prefix))

    def get(self, key):
        """Proxy to :meth:`SettingsService.get`"""
        return self.service.get(self.ns(key))

    def set(self, key, *args, **kwargs):
        return self.service.set(self.ns(key), *args, **kwargs)

    def delete(self, key, silent=True):
        return self.service.delete(self.ns(key), silent=silent)
