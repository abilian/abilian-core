from pathlib import Path
from typing import Any, Dict

import jinja2
from flask import Flask, current_app
from flask.helpers import locked_cached_property
from flask.templating import Environment
from flask_babel import get_locale as babel_get_locale
from jinja2.loaders import ChoiceLoader, PackageLoader
from sqlalchemy.orm.attributes import NEVER_SET, NO_VALUE

import abilian.core.util
import abilian.i18n
from abilian.web import csrf
from abilian.web.filters import init_filters
from abilian.web.util import url_for
from abilian.web.views.images import user_photo_url


class JinjaManagerMixin(Flask):
    def __init__(self) -> None:
        self._jinja_loaders = []

    #
    # Templating and context injection setup
    #
    def create_jinja_environment(self) -> Environment:
        env = Flask.create_jinja_environment(self)
        env.globals.update(
            app=current_app,
            csrf=csrf,
            get_locale=babel_get_locale,
            local_dt=abilian.core.util.local_dt,
            _n=abilian.i18n._n,
            url_for=url_for,
            user_photo_url=user_photo_url,
            NO_VALUE=NO_VALUE,
            NEVER_SET=NEVER_SET,
        )
        init_filters(env)
        return env

    @locked_cached_property
    def jinja_options(self) -> Dict[str, Any]:
        options = dict(Flask.jinja_options)

        jinja_exts = options.setdefault("extensions", [])
        ext = "abilian.core.extensions.jinjaext.DeferredJSExtension"
        if ext not in jinja_exts:
            jinja_exts.append(ext)

        if "bytecode_cache" not in options:
            cache_dir = Path(self.instance_path, "cache", "jinja")
            if not cache_dir.exists():
                cache_dir.mkdir(0o775, parents=True)

            options["bytecode_cache"] = jinja2.FileSystemBytecodeCache(
                str(cache_dir), "%s.cache"
            )

        if self.debug and self.config.get("TEMPLATE_DEBUG", False):
            options["undefined"] = jinja2.StrictUndefined
        return options

    def register_jinja_loaders(self, *loaders: PackageLoader) -> None:
        """Register one or many `jinja2.Loader` instances for templates lookup.

        During application initialization plugins can register a loader so that
        their templates are available to jinja2 renderer.

        Order of registration matters: last registered is first looked up (after
        standard Flask lookup in app template folder). This allows a plugin to
        override templates provided by others, or by base application. The
        application can override any template from any plugins from its template
        folder (See `Flask.Application.template_folder`).

        :raise: `ValueError` if a template has already been rendered
        """
        if not hasattr(self, "_jinja_loaders"):
            raise ValueError(
                "Cannot register new jinja loaders after first template rendered"
            )

        self._jinja_loaders.extend(loaders)

    @locked_cached_property
    def jinja_loader(self) -> ChoiceLoader:
        """Search templates in custom app templates dir (default Flask
        behaviour), fallback on abilian templates."""
        loaders = self._jinja_loaders
        del self._jinja_loaders
        loaders.append(Flask.jinja_loader.func(self))
        loaders.reverse()
        return jinja2.ChoiceLoader(loaders)
