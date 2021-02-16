"""Jinja2 extensions."""
from typing import Any

import lxml.html
from flask import Flask, current_app, g
from flask.signals import got_request_exception, request_started
from jinja2 import nodes
from jinja2.ext import Extension as JinjaExtension
from jinja2.nodes import CallBlock
from jinja2.parser import Parser
from jinja2.runtime import Macro


class DeferredJS:
    """Flask extension for use with DeferredJSExtension for jinja."""

    name = "deferred_js"

    def __init__(self, app: None = None) -> None:
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if self.name in app.extensions:
            return

        app.extensions[self.name] = self
        request_started.connect(self.reset_request, app)
        got_request_exception.connect(self.reset_request, app)

    def reset_request(self, sender: Flask, **extra: Any) -> None:
        self.reset_deferred()

    @staticmethod
    def reset_deferred() -> None:
        g.deferred_js = []


class DeferredJSExtension(JinjaExtension):
    """Put JS fragment at the end of the document in a script tag.

    The JS fragment can contains <script> tag so that your favorite
    editor keeps doing proper indentation, syntax highlighting...
    """

    tags = {"deferJS", "deferredJS"}

    def parse(self, parser: Parser) -> CallBlock:
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
    def defer_nodes(caller: Macro) -> str:
        body = f"<div>{caller().strip()}</div>"

        # remove 'script' tag in immediate children, if any
        fragment = lxml.html.fragment_fromstring(body)
        for child in fragment:
            if child.tag == "script":
                # side effect on fragment.text or previous_child.tail!
                child.drop_tag()

        body_list = []
        if fragment.text:
            body_list.append(fragment.text)

        for child in fragment:
            body_list.append(lxml.html.tostring(child))
            body_list.append(child.tail)
        body_str = "".join(body_list)

        g.deferred_js.append(body_str)
        return ""

    @staticmethod
    def collect_deferred(caller: Macro) -> str:
        result = "\n".join(f"(function(){{\n{js}\n}})();" for js in g.deferred_js)
        flask_ext = current_app.extensions[DeferredJS.name]
        flask_ext.reset_deferred()
        return result
