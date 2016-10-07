# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import g, json, jsonify, redirect, render_template_string, request
from flask.views import MethodView as BaseView
from six import PY2
from werkzeug.exceptions import HTTPException

from ..action import actions


class Redirect(HTTPException):
    pass


class View(BaseView):
    """Base class to use for all class based views.

    The view instance is accessible in :data:`g <flask.g>` and is set in
    :meth:`actions context <abilian.web.action.ActionRegistry.context>`.
    """

    @classmethod
    def as_view(cls, name, *class_args, **class_kwargs):
        if PY2:
            name = bytes(name)
        return super(View, cls).as_view(name, *class_args, **class_kwargs)

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        # if the request method is HEAD and we don't have a handler for it
        # retry with GET
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)
            assert meth is not None, 'Unimplemented method %r' % request.method

        g.view = actions.context['view'] = self
        try:
            args, kwargs = self.prepare_args(args, kwargs)
            return meth(*args, **kwargs)
        except Redirect as exc:
            return exc.response

    def prepare_args(self, args, kwargs):
        """
        If view arguments need to be prepared it can be done here.

        A typical use case is to take an identifier, convert it to an object
        instance and maybe store it on view instance and/or replace
        identifier by object in arguments.
        """
        return args, kwargs

    def redirect(self, url):
        """
        Shortcut all call stack and return response.

        usage: `self.response(url_for(...))`
        """
        raise Redirect(response=redirect(url))


_JSON_HTML = u'''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="{{ url_for('abilian_static', filename="highlightjs/default.min.css") }}" />
</head>
<body>
  <pre>
  <code class="json">
{{ content|escape }}
  </code>
  </pre>

  <script src="{{ url_for('abilian_static', filename="highlightjs/highlight.min.js")  }}" ></script>
  <script>hljs.initHighlightingOnLoad();</script>
</body>
</html>
'''


class JSONView(View):
    """Base view for JSON GET.

    Renders as JSON when requested by Ajax, renders as HTML when requested
    from browser.
    """

    def prepare_args(self, args, kwargs):
        kwargs.update({k: v for k, v in request.args.items()})
        return args, kwargs

    def data(self, *args, **kwargs):
        """This method should return data to be serialized using JSON
        """
        raise NotImplementedError

    def get(self, *args, **kwargs):
        data = self.data(*args, **kwargs)
        best_mime = request.accept_mimetypes.best_match(
            ['text/html', 'application/json'])
        if best_mime == 'application/json':
            return jsonify(data)

        # dev requesting from browser? serve html, let debugtoolbar show up, etc...
        content = json.dumps(data, indent=2)
        return render_template_string(_JSON_HTML, content=content)
