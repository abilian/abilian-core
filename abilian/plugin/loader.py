"""
Plugin loader, initially from Flask-Foundation.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from importlib import import_module

from straight.plugin.loaders import ModuleLoader


class AppLoader(ModuleLoader):

    def __init__(self, subtype=None):
        self.subtype = None
        self._cache = []
        super(AppLoader, self).__init__()

    def _fill_cache(self, namespace):
        super(AppLoader, self)._fill_cache(namespace)
        self._cache = filter(self._meta, self._cache)

    def register(self, app, *args, **kwargs):
        """Load and register modules.
        """
        result = []

        submodule = kwargs.pop('submodule', None)
        logger = kwargs.pop('logger', None)

        for mod in self:

            if logger:
                logger.info("Register module: %s" % mod.__name__)

            if submodule:
                mod = self.import_module('%s.%s' % (mod.__name__, submodule))

            meta = self._meta(mod)

            if meta:
                app.logger.info("Loading plugin {}.".format(mod))
                meta(app, *args, **kwargs)

            result.append(mod)

        return result

    def __iter__(self):
        return iter(self._cache)

    def _meta(self, plugin):
        return getattr(plugin, 'register_plugin', None)

    @staticmethod
    def import_module(path):
        try:
            return import_module(path)
        except ImportError:
            return None

# pymode:lint_ignore=F0401
