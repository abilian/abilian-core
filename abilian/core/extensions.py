# coding=utf-8
"""
Create all standard extensions.

Because of issues with circular dependencies, Abilian-specific extensions are
created later.
"""
import os
import importlib
from gettext import NullTranslations
from babel.support import Translations
from flask import _request_ctx_stack
import flaskext.babel
from celery import Celery

__all__ = ['db', 'babel', 'mail', 'celery', 'login_manager']

# Standard extensions.
from flask.ext.mail import Mail
mail = Mail()

from flask.ext.sqlalchemy import SQLAlchemy
db = SQLAlchemy()

# celery
#
# for defining a task:
#
# from abilian.core.extensions import celery
# @celery.task
# def ...
#
# Application should configure it (i.e. celery.config_from_object, etc)
celery = Celery()

# babel i18n
from flask.ext.babel import Babel as BabelBase


class Babel(BabelBase):
  """ Allow to load translations from other modules
  """
  _translations_paths = None

  def __init__(self, *args, **kwargs):
    BabelBase.__init__(self, *args, **kwargs)

  def init_app(self, app):
    super(Babel, self).init_app(app)
    self._translations_paths = [os.path.join(app.root_path, 'translations')]

  def add_translations(self, module_name):
    """ Add translation from external module

    babel.add_translations('abilian.core')
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
  """Returns the correct gettext translations that should be used for
    this request. This will never fail and return a dummy translation
  object if used outside of the request or if a translation cannot be
  found.
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
      trs = Translations.load(dirname, [flaskext.babel.get_locale()])

      if not trs or trs.__class__ is NullTranslations:
        # test must not use isinstance: Translations is a subclass of
        # NullTranlations
        continue
      elif translations is not None:
          translations.merge(trs)
      else:
          translations = trs

    # ensure translations is at least a NullTranslations object
    if translations is None:
      translations = trs

    ctx.babel_translations = translations

  return translations

# monkey patch flask-babel
flaskext.babel.get_translations = _get_translations_multi_paths

babel = Babel()

from flask.ext.login import LoginManager
login_manager = LoginManager()

