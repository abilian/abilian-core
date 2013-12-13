# coding=utf-8
"""
I18n.

To mark strings for transalation::

    from abilian.i18n import _
    _(u'message to translate')

Use :data:`_` for gettext, :data:`_l` for lazy_gettext, :data:`_n` for
ngettext.

:data:`Babel extension<babel>` support multiple translation paths. This
allows to add more catalogs to search for translations, in LIFO
order. This feature can be used to override some translations in a
custom application, be providing a catalog with messages to override::

    current_app.extensions['babel'].add_translations('abilian.core')

See :meth:`add_translations<Babel.add_translations>`.

To extract messages to build the message catalog template (.pot), use the
following "`-k`" parameters:

.. code-block:: bash

    $ pybabel extract -F babel.cfg -k "_n:1,2" -k "_l" -o "msg.pot" "src"

"""
from __future__ import absolute_import

import os
import importlib
from flask import _request_ctx_stack

from babel.support import Translations
import flask.ext.babel
from flask.ext.babel import (
    Babel as BabelBase,
    gettext, lazy_gettext, ngettext,
)

__all__ = [
  'babel',
  'gettext', '_',
  'lazy_gettext', '_l',
  'ngettext', '_n',
]

#:gettext alias
_ = gettext

#: lazy_gettext alias
_l = lazy_gettext
#: ngettext alias
_n = ngettext


class Babel(BabelBase):
  """
  Allow to load translations from other modules
  """
  _translations_paths = None

  def __init__(self, *args, **kwargs):
    BabelBase.__init__(self, *args, **kwargs)

  def init_app(self, app):
    super(Babel, self).init_app(app)
    self._translations_paths = [os.path.join(app.root_path, 'translations')]

  def add_translations(self, module_name):
    """
    Adds translations from external module. For example::

        babel.add_translations('abilian.core')

    Will add translations files from `abilian.core` module.
    """
    module = importlib.import_module(module_name)
    for path in (os.path.join(p, 'translations') for p in module.__path__):
      if not (os.path.exists(path) and os.path.isdir(path)):
        continue

      if not os.access(path, os.R_OK):
        self.app.logger.warning("Babel translations: read access not "
                                "allowed \"{}\", skipping.".format(path))
        continue

      self._translations_paths.append(path)


def _get_translations_multi_paths():
  """
  Returns the correct gettext translations that should be used for this
  request. This will never fail and return a dummy translation object
  if used outside of the request or if a translation cannot be found.
  """
  ctx = _request_ctx_stack.top
  if ctx is None:
      return None

  translations = getattr(ctx, 'babel_translations', None)
  if translations is None:
    translations = None
    trs = None

    # reverse order: thus the application catalog is loaded last, so that
    # translations from libraries can be overriden
    for dirname in reversed(ctx.app.extensions['babel']._translations_paths):
      trs = Translations.load(dirname, [flask.ext.babel.get_locale()])

      # babel.support.Translations is a subclass of
      # babel.support.NullTranslations, so we test if object has a 'merge'
      # method

      if not trs or not hasattr(trs, 'merge'):
        # got None or NullTranslations instance
        continue
      elif (translations is not None and hasattr(translations, 'merge')):
          translations.merge(trs)
      else:
          translations = trs

    # ensure translations is at least a NullTranslations object
    if translations is None:
      translations = trs

    ctx.babel_translations = translations

  return translations

# monkey patch flask-babel
flask.ext.babel.get_translations = _get_translations_multi_paths

#: importable instance of :class:`Babel`
babel = Babel()
