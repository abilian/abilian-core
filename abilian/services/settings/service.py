# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import current_app
from abilian.services import Service

from .models import Setting


class SettingsService(Service):
  name = 'settings'

  def namespace(self, name):
    return SettingsNamespace(name, self)

  def keys(self, prefix=None):
    """ List all keys, with optional prefix
    """
    q = Setting.query

    if prefix:
      q = q.filter(Setting.key.startswith(prefix))

    return [i[0] for i in q.values(Setting.key)]

  def _get_setting(self, key):
    s = Setting.query.get(key)
    if s is None:
      raise KeyError(key)

    return s

  def get(self, key):
    """ Returns value of a previously stored key
    """
    s = self._get_setting(key)
    return s.value

  def set(self, key, value, type_=None):
    """
    """
    try:
      s = self._get_setting(key)
    except KeyError:
      if not type_:
        raise ValueError('tried to set a new key without specifiying its type')
      s = Setting(key=key, type=type_)

    # always add to session. This covers the case delete(key);set(key). Without
    # it Setting would still be in session 'delete' queue
    current_app.db.session.add(s)
    s.value = value

  def delete(self, key, silent=True):
    try:
      s = self._get_setting(key)
    except KeyError:
      if not silent:
        raise
    else:
      current_app.db.session.delete(s)


class SettingsNamespace(object):
  """Allow to query :class:`SettingsService` service within a
  namespace. Basically it prefixes keys with namespace name and a colon.
  """
  def __init__(self, name, service):
    self.name = name
    self.service = service

  def namespace(self, name):
    """ A namespace within this namespace
    """
    return SettingsNamespace(self.ns(name), self.service)

  def ns(self, key):
    """ Returns full key name for use in settings service
    """
    return ':'.join((self.name, key))

  def keys(self, prefix=''):
    prefix = ':'.join((self.name, prefix))
    start = len(self.name) + 1 # +1 for colon
    return [ k[start:] for k in self.service.keys(prefix=prefix)]

  def get(self, key):
    """ Proxy to :meth:`SettingsService.get`
    """
    return self.service.get(self.ns(key))

  def set(self, key, *args, **kwargs):
    return self.service.set(self.ns(key), *args, **kwargs)

  def delete(self, key, silent=True):
    return self.service.delete(self.ns(key), silent=silent)
