# coding=utf-8
"""
Jinja2 extensions
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from functools import partial

import lxml.html
from flask import current_app
from flask.globals import _lookup_req_object, _request_ctx_stack
from flask.signals import got_request_exception, request_started
from jinja2 import nodes
from jinja2.ext import Extension
from werkzeug.local import LocalProxy


deferred_js = LocalProxy(partial(_lookup_req_object, 'deferred_js'))


class DeferredJS(object):
    """Flask extentions for use with DeferredJSExtension for jinja
    """
    name = 'deferred_js'

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if self.name in app.extensions:
            return

        app.extensions[self.name] = self
        request_started.connect(self.reset_request, app)
        got_request_exception.connect(self.reset_request, app)

    def reset_request(self, sender, **extra):
        self.reset_deferred()

    def reset_deferred(self):
        _request_ctx_stack.top.deferred_js = []


class DeferredJSExtension(Extension):
    """Put JS fragment at the end of the document in a script tag.

    The JS fragment can contains <script> tag so that your favorite editor
    keeps doing proper indentation, syntax highlighting...
    """
    tags = {'deferJS', 'deferredJS'}

    def parse(self, parser):
        token = next(parser.stream)
        tag = token.value
        lineno = token.lineno

        # now we parse body of the block
        body = parser.parse_statements(
            ['name:enddeferJS', 'name:enddeferredJS'], drop_needle=True)

        method = 'defer_nodes' if tag == 'deferJS' else 'collect_deferred'
        return nodes.CallBlock(self.call_method(method, []), [], [],
                               body).set_lineno(lineno)

    def defer_nodes(self, caller):
        body = '<div>{}</div>'.format(caller().strip())

        # remove 'script' tag in immediate children, if any
        fragment = lxml.html.fragment_fromstring(body)
        for child in fragment:
            if child.tag == 'script':
                # side effect on fragment.text or previous_child.tail!
                child.drop_tag()

        body = []
        if fragment.text:
            body.append(fragment.text)

        for child in fragment:
            body.append(lxml.html.tostring(child))
            body.append(child.tail)
        body = u''.join(body)

        deferred_js.append(body)
        return u''

    def collect_deferred(self, caller):
        result = '\n'.join('(function(){{\n{}\n}})();'.format(js)
                           for js in deferred_js)
        current_app.extensions[DeferredJS.name].reset_deferred()
        return result
