# coding=utf-8
"""
Jinja2 extensions
"""
from __future__ import absolute_import

from functools import partial

import lxml.html
from jinja2.ext import Extension
from jinja2 import nodes

from werkzeug.local import LocalProxy
from flask import current_app
from flask.globals import _request_ctx_stack, _lookup_req_object

deferred_js = LocalProxy(partial(_lookup_req_object, 'deferred_js'))

class DeferredJS(object):
  """
  Flask extentions for use with DeferredJSExtension for jinja
  """
  name = 'deferred_js'

  def __init__(self, app=None):
    if app is not None:
      self.init_app(app)

  def init_app(self, app):
    if self.name in app.extensions:
      return

    app.extensions[self.name] = self
    app.before_request(self.reset_deferred)

  def reset_deferred(self):
    _request_ctx_stack.top.deferred_js = []


class DeferredJSExtension(Extension):
  """
  Put JS fragment at the end of the document in a script tag.

  The JS fragment can contains <script> tag so that your favorite editor
  keeps doing proper indentation, syntax highlighting...
  """
  tags = set(['deferJS', 'deferredJS'])

  def parse(self, parser):
    token = next(parser.stream)
    tag = token.value
    lineno = token.lineno

    # now we parse body of the block
    body = parser.parse_statements(['name:enddeferJS', 'name:enddeferredJS'],
                                   drop_needle=True)

    method = 'defer_nodes' if tag == 'deferJS' else 'collect_deferred'
    return nodes.CallBlock(self.call_method(method, []),
                           [], [], body).set_lineno(lineno)

  def defer_nodes(self, caller):
    body = u'<div>{}</div>'.format(caller().strip())

    # remove 'script' tag in immediate children, if any
    fragment = lxml.html.fragment_fromstring(body)
    for child in fragment:
      if child.tag == 'script':
        child.drop_tag() # side effect on fragment.text or previous_child.tail!

    body = [fragment.text]
    for child in fragment:
      body.append(lxml.html.tostring(child))
      body.append(child.tail)
    body = u''.join(body)

    deferred_js.append(body)
    return u''

  def collect_deferred(self, caller):
    result = u'\n'.join(
      u'{{\n{}\n}};'.format(js)
      for js in deferred_js)
    current_app.extensions[DeferredJS.name].reset_deferred()
    return result
