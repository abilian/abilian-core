# coding=utf-8
"""
"""
from __future__ import absolute_import
import urllib

from flask import current_app

from .base import manager


@manager.command
def list_routes():
  output = []
  for rule in current_app.url_map.iter_rules():
    methods = ','.join(rule.methods)
    path = urllib.unquote(rule.rule)
    #line = urllib.unquote()
    output.append((rule.endpoint, methods, path))

  for endpoint, methods, path in sorted(output):
    print '{:40s} {:25s} {}'.format(endpoint, methods, path)
