# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import current_app
from raven.contrib.flask import Sentry as RavenExt

class Sentry(RavenExt):

  @property
  def raven_js_url(self):
    url = u'//cdn.ravenjs.com/{version}/{plugins}/raven.min.js'
    cfg = current_app.config
    return url.format(
        version=unicode(cfg['SENTRY_JS_VERSION']),
        plugins=u','.join(cfg['SENTRY_JS_PLUGINS'])
    )


__all__ = ['Sentry']
