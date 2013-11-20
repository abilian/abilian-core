# coding=utf-8
"""
This extensions makes intersphinx work with flask.ext extensions.

For example when actual module name is `flask_babel', documented
extension name is `flask.ext.babel`
"""
from __future__ import absolute_import

def missing_reference(app, env, node, contnode):
  target = node['reftarget']
  if not target.startswith('flask_'):
    return

  node['reftarget'] = 'flask.ext.' + target[6:]
  return

def setup(app):
    app.connect('missing-reference', missing_reference)

