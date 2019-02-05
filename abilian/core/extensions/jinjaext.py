# coding=utf-8
"""Jinja2 extensions."""
import lxml.html
from flask import current_app, g
from flask.signals import got_request_exception, request_started
from jinja2 import nodes
from jinja2.ext import Extension as JinjaExtension


class DeferredJS:
    """Flask extension for use with DeferredJSExtension for jinja."""

    name = "deferred_js"

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

    @staticmethod
    def reset_deferred():
        g.deferred_js = []


class DeferredJSExtension(JinjaExtension):
    """Put JS fragment at the end of the document in a script tag.

    The JS fragment can contains <script> tag so that your favorite
    editor keeps doing proper indentation, syntax highlighting...
    """

    tags = {"deferJS", "deferredJS"}

    def parse(self, parser):
        token = next(parser.stream)
        tag = token.value
        lineno = token.lineno

        # now we parse body of the block
        body = parser.parse_statements(
            ["name:enddeferJS", "name:enddeferredJS"], drop_needle=True
        )

        method = "defer_nodes" if tag == "deferJS" else "collect_deferred"
        return nodes.CallBlock(self.call_method(method, []), [], [], body).set_lineno(
            lineno
        )

    @staticmethod
    def defer_nodes(caller):
        body = "<div>{}</div>".format(caller().strip())

        # remove 'script' tag in immediate children, if any
        fragment = lxml.html.fragment_fromstring(body)
        for child in fragment:
            if child.tag == "script":
                # side effect on fragment.text or previous_child.tail!
                child.drop_tag()

        body = []
        if fragment.text:
            body.append(fragment.text)

        for child in fragment:
            body.append(lxml.html.tostring(child))
            body.append(child.tail)
        body = "".join(body)

        g.deferred_js.append(body)
        return ""

    @staticmethod
    def collect_deferred(caller):
        result = "\n".join(f"(function(){{\n{js}\n}})();" for js in g.deferred_js)
        flask_ext = current_app.extensions[DeferredJS.name]
        flask_ext.reset_deferred()
        return result
