import os
from pathlib import Path
from typing import Any, Dict, Text

from flask import Flask, current_app
from flask_assets import Bundle
from flask_assets import Environment as AssetsEnv

from abilian.services.security import Anonymous
from abilian.web.assets.filters import ClosureJS


class AssetManagerMixin(Flask):
    def init_assets(self) -> None:
        if self.debug:
            js_filters = None
        else:
            if os.system("java -version 2> /dev/null") == 0:
                js_filters = ("closure_js",)
            else:
                current_app.logger.warn("Java is not installed. Can't use Closure")
                js_filters = None

        self._assets_bundles = {
            "css": {
                "options": {
                    "filters": ("less", "cssmin"),
                    "output": "style-%(version)s.min.css",
                }
            },
            "js-top": {
                "options": {"output": "top-%(version)s.min.js", "filters": js_filters}
            },
            "js": {
                "options": {"output": "app-%(version)s.min.js", "filters": js_filters}
            },
        }

        # bundles for JS translations
        languages = self.config["BABEL_ACCEPT_LANGUAGES"]
        for lang in languages:
            code = "js-i18n-" + lang
            filename = "lang-" + lang + "-%(version)s.min.js"
            self._assets_bundles[code] = {
                "options": {"output": filename, "filters": js_filters}
            }

    def setup_asset_extension(self) -> None:
        assets = self.extensions["webassets"] = AssetsEnv(self)
        if self.debug:
            assets.debug = True
        assets.requirejs_config = {"waitSeconds": 90, "shim": {}, "paths": {}}

        assets_base_dir = Path(self.instance_path, "webassets")
        assets_dir = assets_base_dir / "compiled"
        assets_cache_dir = assets_base_dir / "cache"
        for path in (assets_base_dir, assets_dir, assets_cache_dir):
            if not path.exists():
                path.mkdir()

        assets.directory = str(assets_dir)
        assets.cache = str(assets_cache_dir)
        manifest_file = assets_base_dir / "manifest.json"
        assets.manifest = f"json:{manifest_file}"

        # set up load_path for application static dir. This is required
        # since we are setting Environment.load_path for other assets
        # (like core_bundle below),
        # in this case Flask-Assets uses webasssets resolvers instead of
        # Flask's one
        assets.append_path(self.static_folder, self.static_url_path)

        # filters options
        less_args = ["-ru"]
        assets.config["less_extra_args"] = less_args
        assets.config["less_as_output"] = True
        if assets.debug:
            assets.config["less_source_map_file"] = "style.map"

        # setup static url for our assets
        from abilian.web import assets as core_bundles

        core_bundles.init_app(self)

        # static minified are here
        assets.url = self.static_url_path + "/min"
        assets.append_path(str(assets_dir), assets.url)
        self.add_static_url(
            "min", str(assets_dir), endpoint="webassets_static", roles=Anonymous
        )

    def _finalize_assets_setup(self) -> None:
        assets = self.extensions["webassets"]
        assets_dir = Path(assets.directory)
        closure_base_args = [
            "--jscomp_warning",
            "internetExplorerChecks",
            "--source_map_format",
            "V3",
            "--create_source_map",
        ]

        for name, data in self._assets_bundles.items():
            bundles = data.get("bundles", [])
            options: Dict[Text, Any] = data.get("options", {})
            filters = options.get("filters") or []
            options["filters"] = []
            for f in filters:
                if f == "closure_js":
                    js_map_file = str(assets_dir / f"{name}.map")
                    f = ClosureJS(extra_args=closure_base_args + [js_map_file])
                options["filters"].append(f)

            if not options["filters"]:
                options["filters"] = None

            if bundles:
                assets.register(name, Bundle(*bundles, **options))

    def register_asset(self, type_: str, *assets: Any) -> None:
        """Register webassets bundle to be served on all pages.

        :param type_: `"css"`, `"js-top"` or `"js""`.

        :param assets:
            a path to file, a :ref:`webassets.Bundle <webassets:bundles>`
            instance or a callable that returns a
            :ref:`webassets.Bundle <webassets:bundles>` instance.

        :raises KeyError: if `type_` is not supported.
        """
        supported = list(self._assets_bundles.keys())
        if type_ not in supported:
            msg = "Invalid type: {}. Valid types: {}".format(
                repr(type_), ", ".join(sorted(supported))
            )
            raise KeyError(msg)

        for asset in assets:
            if not isinstance(asset, Bundle) and callable(asset):
                asset = asset()

            self._assets_bundles[type_].setdefault("bundles", []).append(asset)

    def register_i18n_js(self, *paths: str) -> None:
        """Register templates path translations files, like
        `select2/select2_locale_{lang}.js`.

        Only existing files are registered.
        """
        languages = self.config["BABEL_ACCEPT_LANGUAGES"]
        assets = self.extensions["webassets"]

        for path in paths:
            for lang in languages:
                filename = path.format(lang=lang)
                try:
                    assets.resolver.search_for_source(assets, filename)
                except OSError:
                    pass
                    # logger.debug('i18n JS not found, skipped: "%s"', filename)
                else:
                    self.register_asset("js-i18n-" + lang, filename)

    def register_base_assets(self) -> None:
        """Register assets needed by Abilian.

        This is done in a separate method in order to allow applications
        to redefine it at will.
        """
        from abilian.web import assets as bundles

        self.register_asset("css", bundles.LESS)
        self.register_asset("js-top", bundles.TOP_JS)
        self.register_asset("js", bundles.JS)
        self.register_i18n_js(*bundles.JS_I18N)
