# coding=utf-8
"""
Extensions to WTForms fields, widgets and validators.
"""
from __future__ import absolute_import

import logging
from functools import partial
from collections import OrderedDict

from wtforms.fields import HiddenField
from wtforms.fields.core import Field
from wtforms_alchemy import model_form_factory
from flask import current_app
from flask_login import current_user
from flask_wtf.form import Form as BaseForm

from abilian.i18n import _, _n
from abilian.services.security import READ, WRITE, Role, Anonymous
from abilian.core.logging import patch_logger

from .fields import *  # noqa
from .filters import *  # noqa
from .validators import *  # noqa
from .widgets import *  # noqa

logger = logging.getLogger(__name__)


#  setup Form class with babel support
class _BabelTranslation(object):
  def gettext(self, string):
    return _(string)

  def ngettext(self, singular, plural, n):
    return _n(singular, plural, n)


BabelTranslation = _BabelTranslation()


class FormPermissions(object):
  """
  Form role/permission manager
  """
  def __init__(self, default=Anonymous, read=None, write=None,
               fields_read=None, fields_write=None):
    """
    """
    if isinstance(default, Role):
      default = (default,)

    self.default = default
    self.form = dict()
    self.fields = dict()

    for permission, roles in ((READ, read), (WRITE, write)):
      if roles is None:
        continue
      if isinstance(roles, Role):
        roles = (roles,)
      self.form[permission] = roles

    for fields, permission in ((fields_read, READ), (fields_write, WRITE)):
      if fields:
        for field_name, allowed_roles in fields.items():
          if isinstance(allowed_roles, Role):
            allowed_roles = (allowed_roles,)
          self.fields.setdefault(field_name, dict())[permission] = allowed_roles

  def has_permission(self, permission, field=None, obj=None, user=current_user):
    """
    """
    allowed_roles = self.default
    definition = None
    eval_roles = lambda fun: fun(permission=permission,
                                 field=field,
                                 obj=obj)

    if field is None:
      definition = self.form
    else:
      if isinstance(field, Field):
        field = field.name
      if field in self.fields:
        definition = self.fields[field]

    if definition and permission in definition:
      allowed_roles = definition[permission]

    if callable(allowed_roles):
      allowed_roles = eval_roles(allowed_roles)

    roles = []
    for r in allowed_roles:
      if callable(r):
        r = eval_roles(r)

      if isinstance(r, (Role, bytes, unicode)):
        roles.append(r)
      else:
        roles.extend(r)

    svc = current_app.services['security']
    return svc.has_permission(user,
                              permission,
                              obj=obj,
                              roles=roles)

class Form(BaseForm):

  _groups = OrderedDict()
  #: :class:`FormPermissions` instance
  _permissions = None

  def __init__(self, *args, **kwargs):
    permission = kwargs.pop('permission', None)
    user= kwargs.pop('user', current_user)
    super(Form, self).__init__(*args, **kwargs)
    self._field_groups = {} # map field -> group

    if not isinstance(self.__class__._groups, OrderedDict):
      self.__class__._groups = OrderedDict(self.__class__._groups)

    for label, fields in self._groups.items():
      self._groups[label] = list(fields)
      self._field_groups.update(dict.fromkeys(fields, label))

    obj = kwargs.get('obj')

    if permission and self._permissions is not None:
      # we are going to alter groups: copy dict on instance to preserve class
      # definition
      self._groups = OrderedDict()
      for label, fields in self.__class__._groups.items():
        self._groups[label] = list(fields)

      has_permission = partial(self._permissions.has_permission,
                               permission,
                               obj=obj, user=user)
      empty_form = not has_permission()

      for field_name in list(self._fields):
        if empty_form or not has_permission(field=field_name):
          logger.debug('{}(permission={!r}): field {!r}: removed'
                       ''.format(self.__class__.__name__, permission,
                                 field_name))
          del self[field_name]
          group = self._field_groups.get(field_name)
          if group:
            self._groups[group].remove(field_name)

  def _get_translations(self):
    return BabelTranslation

  def _fields_for_group(self, group):
      for g, field_names in self._groups:
        if group == g:
          fields = field_names
          break
      else:
        raise ValueError("Group %s not found", repr(group))
      return fields

  def _has_required(self, group=None, fields=()):
    if group is not None:
      fields = self._fields_for_group(group)
    return any(self[f].flags.required for f in fields)

  def _count_errors(self, group=None, fields=()):
    if group is not None:
      fields = self._fields_for_group(group)
    return len([1 for f in fields if self[f].errors])


ModelForm = model_form_factory(Form)

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
