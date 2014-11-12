# coding=utf-8
"""
Extensions to WTForms fields, widgets and validators.
"""
from __future__ import absolute_import

import logging

from flask.ext.babel import gettext as _, ngettext as _n

from wtforms.fields import HiddenField
from wtforms.fields.core import Field
from flask.ext.wtf.form import Form as BaseForm

from abilian.core.logging import patch_logger

from .fields import *
from .filters import *
from .validators import *
from .widgets import *

logger = logging.getLogger(__name__)


#  setup Form class with babel support
class _BabelTranslation(object):
  def gettext(self, string):
    return _(string)

  def ngettext(self, singular, plural, n):
    return _n(singular, plural, n)


BabelTranslation = _BabelTranslation()


class Form(BaseForm):
  def _get_translations(self):
    return BabelTranslation

  _groups = ()

  def _has_required(self, group=None, fields=()):
    if group is not None:
      for g, field_names in self._groups:
        if group == g:
          fields = field_names
          break
      else:
        raise ValueError("Group %s not found", repr(group))

    return any(self[f].flags.required for f in fields)


### PATCH wtforms.field.core.Field ####################
_PATCHED = False

if not _PATCHED:
  Field.view_template = None

  _wtforms_Field_init = Field.__init__
  def _core_field_init(self, *args, **kwargs):
    view_widget = None
    if 'view_widget' in kwargs:
      view_widget = kwargs.pop('view_widget')

    _wtforms_Field_init(self, *args, **kwargs)
    if view_widget is None:
      view_widget = self.widget

    self.view_widget = view_widget

  patch_logger.info(Field.__init__)
  Field.__init__ = _core_field_init
  del _core_field_init

  #  support 'widget_options' for some custom widgets
  _wtforms_Field_render = Field.__call__
  def _core_field_render(self, **kwargs):
    if 'widget_options' in kwargs and not kwargs['widget_options']:
      kwargs.pop('widget_options')

    return _wtforms_Field_render(self, **kwargs)

  patch_logger.info(Field.__call__)
  Field.__call__ = _core_field_render
  del _core_field_render

  def render_view(self, **kwargs):
    """
    Render data
    """
    if 'widget_options' in kwargs and not kwargs['widget_options']:
      kwargs.pop('widget_options')

    if hasattr(self.view_widget, 'render_view'):
      return self.view_widget.render_view(self, **kwargs)

    return DefaultViewWidget().render_view(self, **kwargs)

  patch_logger.info('Add method %s.Field.render_view' % Field.__module__)
  Field.render_view = render_view
  del render_view

  def is_hidden(self):
    """
    WTForms is not consistent with hidden fields, since `flags.hidden` is not
    set on `HiddenField` :-(
    """
    return (self.flags.hidden
            or isinstance(self, HiddenField))

  patch_logger.info('Add method %s.Field.is_hidden' % Field.__module__)
  Field.is_hidden = property(is_hidden)
  del is_hidden

  _PATCHED = True
### END PATCH wtforms.field.core.Field #################
