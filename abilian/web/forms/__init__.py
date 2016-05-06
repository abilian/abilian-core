# coding=utf-8
"""
Extensions to WTForms fields, widgets and validators.
"""
from __future__ import absolute_import, print_function, division

import logging
from functools import partial
from collections import OrderedDict

from wtforms.fields import HiddenField
from wtforms.fields.core import Field
from wtforms_alchemy import model_form_factory
from flask import current_app, has_app_context, g
from flask_login import current_user
from flask_wtf.form import Form as BaseForm

from abilian.i18n import _, _n
from abilian.services.security import READ, WRITE, CREATE, Role, Anonymous
from abilian.core.logging import patch_logger
from abilian.core.entities import Entity

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
    """Form role/permission manager
    """

    def __init__(self,
                 default=Anonymous,
                 read=None,
                 write=None,
                 fields_read=None,
                 fields_write=None,
                 existing=None):
        """
        :param default: default roles when not specified for field. Can be:

            * a :class:`Role` or an iterable of :class:`Role`

            * a callable that returns a :class:`Role` or an iterable of
              :class:`Role`

            * a `dict` with :class:`Permission` instances for keys and one of other
              acceptable role spec.; a default entry `"default"` is required.

        :param read: global roles required for `READ` permission for whole form.

        :param write: global roles required for `WRITE` permission for whole form.
        """
        if isinstance(default, Role):
            default = {'default': (default,)}
        elif isinstance(default, dict):
            if 'default' not in default:
                raise ValueError(
                    '`default` parameter must have a "default" key')
        elif callable(default):
            default = {'default': default}
        else:
            raise ValueError(
                "No valid value for `default`. Use a Role, an iterable "
                "of Roles, a callable, or a dict.")

        self.default = default
        self.form = dict()
        self.fields = dict()

        if existing is not None:
            # copy existing formpermissions instance
            # maybe overwrite later with our definitions
            assert isinstance(existing, FormPermissions)
            for permission in (READ, WRITE):
                if permission in existing.form:
                    self.form[permission] = existing.form[permission]

            for field, mapping in existing.fields.items():
                f_map = self.fields[field] = dict()
                for permission, roles in mapping.items():
                    f_map[permission] = roles

        for permission, roles in ((READ, read), (WRITE, write)):
            if roles is None:
                continue
            if isinstance(roles, Role):
                roles = (roles,)
            self.form[permission] = roles

        fields_defs = ((fields_read, READ),
                       (fields_write, WRITE),
                       (fields_write, CREATE),
                      )  # checking against CREATE permission
        # at field level is the same as
        # WRITE permisssion
        for fields, permission in fields_defs:
            if fields:
                for field_name, allowed_roles in fields.items():
                    if isinstance(allowed_roles, Role):
                        allowed_roles = (allowed_roles,)
                    self.fields.setdefault(field_name,
                                           dict())[permission] = allowed_roles

    def has_permission(
            self, permission,
            field=None,
            obj=None, user=current_user):
        if obj is not None and not isinstance(obj, Entity):
            # permission/role can be set only on entities
            return True

        allowed_roles = (self.default[permission] if permission in self.default
                         else self.default['default'])
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
        return svc.has_role(user, role=roles, object=obj,)


class FormContext(object):
    """
    Allows :class:`forms <Form>` to set a context during instanciation, so that
    subforms used in formfields / listformfields / etc can perform proper field
    filtering according to original permission and user passed to top form
    __init__ method.
    """
    permission = None
    user = None

    def __init__(self, permission=None, user=None, obj=None):
        self.permission = permission
        self.user = user
        self.obj = obj

    def __enter__(self):
        if not has_app_context():
            return self

        self.__existing = getattr(g, '__form_ctx__', None)
        if self.__existing:
            if self.permission is None:
                self.permission = self.__existing.permission

            if self.user is None:
                self.user = self.__existing.user

            if self.obj is None:
                self.obj = self.__existing.obj
            elif not isinstance(self.obj, Entity):
                self.obj = self.__existing.obj

        if self.user is None:
            self.user = current_user

        setattr(g, '__form_ctx__', self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not has_app_context():
            return

        setattr(g, '__form_ctx__', self.__existing)


class Form(BaseForm):

    _groups = OrderedDict()
    #: :class:`FormPermissions` instance
    _permissions = None

    def __init__(self, *args, **kwargs):
        permission = kwargs.pop('permission', None)
        user = kwargs.pop('user', None)
        obj = kwargs.get('obj')
        form_ctx = FormContext(permission=permission, user=user, obj=obj)

        if kwargs.get('csrf_enabled') is None and not has_app_context():
            # form instanciated without app context and without explicit csrf
            # parameter: disable csrf since it requires current_app.
            #
            # If there is a prefix, it's probably a subform (in a fieldform of
            # fieldformlist): csrf is not required. If there is no prefix: let error
            # happen.
            if kwargs.get('prefix'):
                kwargs['csrf_enabled'] = False

        with form_ctx as ctx:
            super(Form, self).__init__(*args, **kwargs)
            self._field_groups = {}  # map field -> group

            if not isinstance(self.__class__._groups, OrderedDict):
                self.__class__._groups = OrderedDict(self.__class__._groups)

            for label, fields in self._groups.items():
                self._groups[label] = list(fields)
                self._field_groups.update(dict.fromkeys(fields, label))

            if ctx.permission and self._permissions is not None:
                # we are going to alter groups: copy dict on instance to preserve class
                # definition
                self._groups = OrderedDict()
                for label, fields in self.__class__._groups.items():
                    self._groups[label] = list(fields)

                has_permission = partial(self._permissions.has_permission,
                                         ctx.permission,
                                         obj=ctx.obj,
                                         user=ctx.user)
                empty_form = not has_permission()

                for field_name in list(self._fields):
                    if empty_form or not has_permission(field=field_name):
                        logger.debug('{}(permission={!r}): field {!r}: removed'
                                     ''.format(self.__class__.__name__,
                                               ctx.permission, field_name))
                        del self[field_name]
                        group = self._field_groups.get(field_name)
                        if group:
                            self._groups[group].remove(field_name)

    def _get_translations(self):
        return BabelTranslation

    def _fields_for_group(self, group):
        for group_name, field_names in self._groups:
            if group == group_name:
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

# PATCH wtforms.field.core.Field ####################
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

    def _core_field_repr(self):
        """
        __repr__ that shows the name of the field instance. Useful for tracing field
        errors (like in sentry)
        """
        return '<{}.{} at 0x{:x} name={!r}>'.format(self.__class__.__module__,
                                                    self.__class__.__name__,
                                                    id(self),
                                                    self.name,)

    patch_logger.info(Field.__module__ + '.Field.__repr__')
    Field.__repr__ = _core_field_repr
    del _core_field_repr

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
        """Render data.
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
        return (self.flags.hidden or isinstance(self, HiddenField))

    patch_logger.info('Add method %s.Field.is_hidden' % Field.__module__)
    Field.is_hidden = property(is_hidden)
    del is_hidden

    _PATCHED = True
# END PATCH wtforms.field.core.Field #################
