# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import logging
import operator
from functools import partial

import babel
import sqlalchemy as sa
from flask import current_app
from flask.helpers import locked_cached_property
from flask_babel import format_date, format_datetime, get_locale, get_timezone
from flask_login import current_user
from flask_wtf.file import FileField as BaseFileField
from future.utils import string_types
from wtforms import FieldList as BaseFieldList
from wtforms import FormField as BaseFormField
from wtforms import (Field, SelectField, SelectFieldBase, SelectMultipleField,
                     ValidationError)
from wtforms.compat import text_type
from wtforms.ext.csrf import SecureForm
from wtforms.ext.sqlalchemy.fields import (get_pk_from_identity,
                                           has_identity_key)
from wtforms.validators import DataRequired, Optional
from wtforms_alchemy import ModelFieldList as BaseModelFieldList
from wtforms_alchemy import ModelFormField as BaseModelFormField

from abilian import i18n
from abilian.core.extensions import db
from abilian.core.util import utc_dt

from .util import babel2datetime
from .widgets import DateInput, DateTimeInput, FileInput, Select2, Select2Ajax

__all__ = ['ModelFieldList', 'FileField', 'DateField', 'Select2Field',
           'Select2MultipleField', 'QuerySelect2Field', 'JsonSelect2Field',
           'JsonSelect2MultipleField', 'FormField']


class FormField(BaseFormField):
    """
    Discard csrf_token on subform
    """

    def process(self, *args, **kwargs):
        super(FormField, self).process(*args, **kwargs)
        if isinstance(self.form, SecureForm):
            # don't create errors because of subtoken
            self._subform_csrf = self.form['csrf_token']
            del self.form['csrf_token']

    @property
    def data(self):
        if not isinstance(self.form, SecureForm):
            return self.form.data

        # SecureForm will try to pop 'csrf_token', but we removed it during process
        self.form._fields['csrf_token'] = self._subform_csrf
        data = self.form.data
        del self.form['csrf_token']
        return data


class ModelFormField(FormField, BaseModelFormField):
    """
    Discard csrf_token on subform
    """


class FilterFieldListMixin(object):

    def validate(self, form, extra_validators=tuple()):
        to_remove = []
        for field in self.entries:
            is_subform = isinstance(field, BaseFormField)
            data = field.data.values() if is_subform else [field.data]

            if not any(data):
                # all inputs empty: discard row
                to_remove.append(field)

        for field in to_remove:
            self.entries.remove(field)

        if self.entries:
            # setting raw_data enables validator to function properly
            # 1) we have entries so a subfield is not empty
            # 2) FieldList by default has an optional() validator
            # 3) by setting raw_data optional() does not reset the errors dict
            # -> subfields errors are propagated
            self.raw_data = [True]
        return super(FilterFieldListMixin, self).validate(form,
                                                          extra_validators)


class FieldList(FilterFieldListMixin, BaseFieldList):
    pass


class ModelFieldList(FilterFieldListMixin, BaseModelFieldList):
    """
    Filter empty entries before saving and refills before displaying
    """

    def __init__(self, *args, **kwargs):
        super(ModelFieldList, self).__init__(*args, **kwargs)

        # build visible field list for widget. We must do it during form
        # instanciation so as to have permission filtering
        field_names = []
        labels = []
        fieldsubform = self.unbound_field.bind(
            form=None, name='dummy', _meta=self.meta)
        subform = fieldsubform.form_class(csrf_enabled=False)
        for f in subform:
            if f.is_hidden:
                continue
            name = f.short_name
            field_names.append(name)
            labels.append(f.label.text if f.label else f.name)

        self._field_names = field_names
        self._field_labels = labels
        self._field_nameTolabel = dict(zip(self._field_names,
                                           self._field_labels))

    def __call__(self, **kwargs):
        """
        Refill with default min_entry, which were possibly
        removed by FilterFieldListMixin.

        Mandatory for proper function of DynamicRowWidget which clones an existing
        field
        """
        while len(self) < self.min_entries:
            self.append_entry()
        return super(ModelFieldList, self).__call__(**kwargs)


class FileField(BaseFileField):
    """
    Support 'multiple' attribute, enabling html5 multiple file input in widget.

    Can store file using a related model.

    :param blob_attr: attribute name to store / retrieve value on related model.
      Used if `name` is a relationship on model. Defauts to `'value'`
    """
    multiple = False
    widget = FileInput()
    blob = None
    blob_attr = 'value'

    def __init__(self, *args, **kwargs):
        try:
            self.multiple = kwargs.pop('multiple')
        except KeyError:
            self.multiple = False

        self.blob_attr = kwargs.pop('blob_attr', self.__class__.blob_attr)
        allow_delete = kwargs.pop('allow_delete', None)
        validators = list(kwargs.get('validators', []))
        self.upload_handles = []
        self.delete_files_index = []
        self._has_uploads = False

        if allow_delete is not None:
            if any(isinstance(v, DataRequired if allow_delete else Optional)
                   for v in validators):
                raise ValueError(
                    "Field validators are conflicting with `allow_delete`,"
                    "validators={!r}, allow_delete={!r}".format(validators,
                                                                allow_delete))
            if not allow_delete:
                validators.append(DataRequired())

        kwargs['validators'] = validators
        BaseFileField.__init__(self, *args, **kwargs)

    @property
    def allow_delete(self):
        """Property for legacy code.

        Test `field.flags.required` instead.
        """
        return not self.flags.required

    def __call__(self, **kwargs):
        if 'multiple' not in kwargs and self.multiple:
            kwargs['multiple'] = 'multiple'
        return BaseFileField.__call__(self, **kwargs)

    def has_file(self):
        return self._has_uploads

    def process(self, formdata, *args, **kwargs):
        delete_arg = u'__{name}_delete__'.format(name=self.name)
        self.delete_files_index = (formdata.getlist(delete_arg) if formdata and
                                   delete_arg in formdata else [])

        return super(FileField, self).process(formdata, *args, **kwargs)

    def process_data(self, value):
        if isinstance(value, db.Model):
            self.blob = value
            value = getattr(value, self.blob_attr)

        self.object_data = value
        return super(FileField, self).process_data(value)

    def process_formdata(self, valuelist):
        uploads = current_app.extensions['uploads']
        if self.delete_files_index:
            self.data = None
            return

        if valuelist:
            self.upload_handles = valuelist
            handle = valuelist[0]
            fileobj = uploads.get_file(current_user, handle)

            if fileobj is None:
                # FIXME: this is a validation task
                raise ValueError('File with handle {!r} not found'.format(
                    handle))

            meta = uploads.get_metadata(current_user, handle)
            filename = meta.get('filename', handle)
            mimetype = meta.get('mimetype')
            stream = fileobj.open('rb')
            stream.filename = filename
            if mimetype:
                stream.content_type = mimetype
                stream.mimetype = mimetype
            self.data = stream
            self._has_uploads = True

    def populate_obj(self, obj, name):
        """Store file.
        """
        from abilian.core.models.blob import Blob
        delete_value = self.allow_delete and self.delete_files_index

        if not self.has_file() and not delete_value:
            # nothing uploaded, and nothing to delete
            return

        state = sa.inspect(obj)
        mapper = state.mapper
        if name not in mapper.relationships:
            # directly store in database
            return super(FileField, self).populate_obj(obj, name)

        rel = getattr(mapper.relationships, name)
        if rel.uselist:
            raise ValueError(
                "Only single target supported; else use ModelFieldList")

        if delete_value:
            setattr(obj, name, None)
            return

        #  FIXME: propose option to always create a new blob
        cls = rel.mapper.class_
        val = getattr(obj, name)

        if val is None:
            val = cls()
            setattr(obj, name, val)

        data = u''
        if self.has_file():
            data = self.data
            if not issubclass(cls, Blob):
                data = data.read()

        setattr(val, self.blob_attr, data)


class DateTimeField(Field):
    widget = DateTimeInput()

    def __init__(self, label=None, validators=None, use_naive=True, **kwargs):
        """
        :param use_naive: if `False`, dates are considered entered using user's
        timezone; different users with different timezones will see corrected
        date/time. For storage dates are always stored using UTC.
        """
        self.raw_data = kwargs.pop('raw_data', None)
        super(DateTimeField, self).__init__(label, validators, **kwargs)
        self.use_naive = use_naive

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            locale = get_locale()
            date_fmt = locale.date_formats['short'].pattern
            # force numerical months and 4 digit years
            date_fmt = date_fmt \
                .replace('MMMM', 'MM') \
                .replace('MMM', 'MM') \
                .replace('yyyy', 'y') \
                .replace('yy', 'y') \
                .replace('y', 'yyyy')
            time_fmt = locale.time_formats['short']
            dt_fmt = locale.datetime_formats['short'].format(time_fmt, date_fmt)
            return format_datetime(self.data, dt_fmt) if self.data else ''

    def process_data(self, value):
        if value is not None:
            if not value.tzinfo:
                if self.use_naive:
                    value = get_timezone().localize(value)
                else:
                    value = utc_dt(value)
            if not self.use_naive:
                value = value.astimezone(get_timezone())

        super(DateTimeField, self).process_data(value)

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist)
            locale = get_locale()
            date_fmt = locale.date_formats['short']
            date_fmt = babel2datetime(date_fmt)
            date_fmt = date_fmt \
                .replace('%B', '%m') \
                .replace('%b', '%m')  # force numerical months
            time_fmt = locale.time_formats['short']
            time_fmt = babel2datetime(time_fmt)
            datetime_fmt = u'{} | {}'.format(date_fmt, time_fmt)
            try:
                self.data = datetime.datetime.strptime(date_str, datetime_fmt)
                if not self.use_naive:
                    tz = get_timezone()
                    if self.data.tzinfo:
                        self.data = self.data.astimezone(tz)
                    else:
                        self.data = tz.localize(self.data)

                # convert to UTC
                self.data = utc_dt(self.data)
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))

    def populate_obj(self, obj, name):
        dt = self.data
        if dt and self.use_naive:
            dt = dt.replace(tzinfo=None)

        setattr(obj, name, dt)


class DateField(Field):
    """
    A text field which stores a `datetime.date` matching a format.
    """
    widget = DateInput()

    def __init__(self, label=None, validators=None, **kwargs):
        super(DateField, self).__init__(label, validators, **kwargs)

    def _value(self):
        if self.raw_data:
            return ' '.join(self.raw_data)
        else:
            date_fmt = get_locale().date_formats['short'].pattern
            # force numerical months and 4 digit years
            date_fmt = date_fmt \
                .replace('MMMM', 'MM') \
                .replace('MMM', 'MM') \
                .replace('yyyy', 'y') \
                .replace('yy', 'y') \
                .replace('y', 'yyyy')
            return format_date(self.data, date_fmt) if self.data else ''

    def process_formdata(self, valuelist):
        valuelist = [i for i in valuelist if i.strip()]

        if valuelist:
            date_str = ' '.join(valuelist)
            date_fmt = get_locale().date_formats['short']
            date_fmt = babel2datetime(date_fmt)
            date_fmt = date_fmt \
                .replace('%B', '%m') \
                .replace('%b', '%m')

            try:
                self.data = datetime.datetime.strptime(date_str,
                                                       date_fmt).date()
            except ValueError:
                self.data = None
                raise ValueError(self.gettext('Not a valid datetime value'))


class Select2Field(SelectField):
    """Allows choices to be a function instead of an iterable.
    """
    widget = Select2()

    @property
    def choices(self):
        choices = self._choices
        return choices() if callable(choices) else choices

    @choices.setter
    def choices(self, choices):
        self._choices = choices


class Select2MultipleField(SelectMultipleField):
    widget = Select2(multiple=True)
    multiple = True

    @property
    def choices(self):
        choices = self._choices
        return choices() if callable(choices) else choices

    @choices.setter
    def choices(self, choices):
        self._choices = choices


class QuerySelect2Field(SelectFieldBase):
    """
    COPY/PASTED (and patched) from WTForms!

    Will display a select drop-down field to choose between ORM results in a
    sqlalchemy `Query`.  The `data` property actually will store/keep an ORM
    model instance, not the ID. Submitting a choice which is not in the query
    will result in a validation error.

    This field only works for queries on models whose primary key column(s)
    have a consistent string representation. This means it mostly only works
    for those composed of string, unicode, and integer types. For the most
    part, the primary keys will be auto-detected from the model, alternately
    pass a one-argument callable to `get_pk` which can return a unique
    comparable key.

    The `query` property on the field can be set from within a view to assign
    a query per-instance to the field. If the property is not set, the
    `query_factory` callable passed to the field constructor will be called to
    obtain a query.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    :param allow_blank: DEPRECATED. Use optional()/required() validators instead.
    """

    def __init__(self,
                 label=None,
                 validators=None,
                 query_factory=None,
                 get_pk=None,
                 get_label=None,
                 allow_blank=False,
                 blank_text='',
                 widget=None,
                 multiple=False,
                 collection_class=list,
                 **kwargs):

        if widget is None:
            widget = Select2(multiple=multiple)

        kwargs['widget'] = widget
        self.multiple = multiple
        self.collection_class = collection_class

        if validators is None:
            validators = []

        if not any(isinstance(v, (Optional, DataRequired)) for v in validators):
            logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
            logger.warning(
                u'Use deprecated parameter `allow_blank` for field "{}".'
                .format(label))
            if not allow_blank:
                validators.append(DataRequired())

        super(QuerySelect2Field, self).__init__(label, validators, **kwargs)

        # PATCHED!
        if query_factory:
            self.query_factory = query_factory

        if get_pk is None:
            if not has_identity_key:
                raise Exception(
                    'The sqlalchemy identity_key function could not be imported.')
            self.get_pk = get_pk_from_identity
        else:
            self.get_pk = get_pk

        if get_label is None:
            self.get_label = lambda x: x
        elif isinstance(get_label, string_types):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self.query = None
        self._object_list = None

    def _get_data(self):
        formdata = self._formdata
        if formdata is not None:
            if not self.multiple:
                formdata = [formdata]
            formdata = set(formdata)
            data = [obj for pk, obj in self._get_object_list()
                    if pk in formdata]
            if all(hasattr(x, 'name') for x in data):
                data = sorted(data, key=lambda x: x.name)
            else:
                data = sorted(data)
            if data:
                if not self.multiple:
                    data = data[0]
                self._set_data(data)
        return self._data

    def _set_data(self, data):
        if self.multiple and not isinstance(data, self.collection_class):
            data = self.collection_class(
                data) if data else self.collection_class()
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def _get_object_list(self):
        if self._object_list is None:
            query = self.query or self.query_factory()
            get_pk = self.get_pk
            self._object_list = list((text_type(get_pk(obj)), obj)
                                     for obj in query)
        return self._object_list

    def iter_choices(self):
        if not self.flags.required:
            yield (None,
                   None,
                   self.data == [] if self.multiple else self.data is None,)

        predicate = (operator.contains if
                     (self.multiple and self.data is not None) else operator.eq)
        # remember: operator.contains(b, a) ==> a in b
        # so: obj in data ==> contains(data, obj)
        predicate = partial(predicate, self.data)

        for pk, obj in self._get_object_list():
            yield (pk, self.get_label(obj), predicate(obj))

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = [] if self.multiple else None
        else:
            self._data = None
            if not self.multiple:
                valuelist = valuelist[0]
            self._formdata = valuelist

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            data = self.data
            if not self.multiple:
                data = [data] if data is not None else []
            elif not data:
                # multiple values: ensure empty list (data may be None)
                data = []

            data = set(data)
            valid = {obj for pk, obj in self._get_object_list()}
            if (data - valid):
                raise ValidationError(self.gettext('Not a valid choice'))


class JsonSelect2Field(SelectFieldBase):
    """
    TODO: rewrite this docstring. This is copy-pasted from QuerySelectField

    Will display a select drop-down field to choose between ORM results in a
    sqlalchemy `Query`.  The `data` property actually will store/keep an ORM
    model instance, not the ID. Submitting a choice which is not in the query
    will result in a validation error.

    This field only works for queries on models whose primary key column(s)
    have a consistent string representation. This means it mostly only works
    for those composed of string, unicode, and integer types. For the most
    part, the primary keys will be auto-detected from the model, alternately
    pass a one-argument callable to `get_pk` which can return a unique
    comparable key.

    The `query` property on the field can be set from within a view to assign
    a query per-instance to the field. If the property is not set, the
    `query_factory` callable passed to the field constructor will be called to
    obtain a query.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__str__` or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`. The label for this blank choice can be set by specifying the
    `blank_text` parameter.

    :param model_class: can be an sqlalchemy model, or a string with model
    name. The model will be looked up in sqlalchemy class registry on first
    access. This allows to use a model when it cannot be imported during field
    declaration.
    """

    def __init__(self,
                 label=None,
                 validators=None,
                 ajax_source=None,
                 widget=None,
                 blank_text='',
                 model_class=None,
                 multiple=False,
                 **kwargs):

        self.multiple = multiple

        if widget is None:
            widget = Select2Ajax(multiple=self.multiple)

        kwargs['widget'] = widget
        super(JsonSelect2Field, self).__init__(label, validators, **kwargs)
        self.ajax_source = ajax_source
        self._model_class = model_class

        self.allow_blank = not self.flags.required
        self.blank_text = blank_text

    @locked_cached_property
    def model_class(self):
        cls = self._model_class
        if isinstance(cls, type) and issubclass(cls, db.Model):
            return cls

        reg = db.Model._decl_class_registry
        return reg[cls]

    def iter_choices(self):
        if not self.flags.required:
            yield (None, None, self.data is None,)

        data = self.data
        if not self.multiple:
            if data is None:
                raise StopIteration
            data = [data]
        elif not data:
            raise StopIteration

        for obj in data:
            yield (obj.id, obj.name, True)

    def _get_data(self):
        formdata = self._formdata
        if formdata:
            if not self.multiple:
                formdata = [formdata]
            data = [self.model_class.query.get(int(pk)) for pk in formdata
                    if pk not in (u'', None)]
            if not self.multiple:
                data = data[0] if data else None
            self._set_data(data)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def process_formdata(self, valuelist):
        if not valuelist:
            self.data = [] if self.multiple else None
        else:
            self._data = None

            if hasattr(self.widget, 'process_formdata'):
                # might need custom deserialization, i.e  Select2 3.x with multiple +
                # ajax
                valuelist = self.widget.process_formdata(valuelist)

            if not self.multiple:
                valuelist = valuelist[0]
            self._formdata = valuelist

    def populate_obj(self, obj, name):
        data = self.data

        try:
            state = sa.inspect(obj)
        except sa.exc.NoInspectionAvailable:
            return super(JsonSelect2Field, self).populate_obj(obj, name)

        relations = state.mapper.relationships

        if self.multiple and name in relations:
            prop = relations[name]
            if prop.collection_class:
                # data is a list, try to convert to actual type; generally `set()`
                data = prop.collection_class(data)

        setattr(obj, name, data)


class JsonSelect2MultipleField(JsonSelect2Field):
    # legacy class, now use JsonSelect2Field(multiple=True)
    pass


class LocaleSelectField(SelectField):
    widget = Select2()

    def __init__(self, *args, **kwargs):
        kwargs['coerce'] = LocaleSelectField.coerce
        kwargs['choices'] = (locale_info
                             for locale_info in i18n.supported_app_locales())
        super(LocaleSelectField, self).__init__(*args, **kwargs)

    @staticmethod
    def coerce(value):
        if isinstance(value, babel.Locale):
            return value
        elif isinstance(value, string_types):
            return babel.Locale.parse(value)
        elif value is None:
            return None

        raise ValueError(
            'Value cannot be converted to Locale(), or is not None, {!r}'.format(
                value))

    def iter_choices(self):
        if not self.flags.required:
            yield (None, None, self.data is None,)

        for locale, label in i18n.supported_app_locales():
            yield (locale.language, label.capitalize(), locale == self.data)


class TimezoneField(SelectField):
    widget = Select2()

    def __init__(self, *args, **kwargs):
        kwargs['coerce'] = babel.dates.get_timezone
        kwargs['choices'] = (tz_info for tz_info in i18n.timezones_choices())
        super(TimezoneField, self).__init__(*args, **kwargs)

    def iter_choices(self):
        if not self.flags.required:
            yield (None, None, self.data is None,)

        for tz, label in i18n.timezones_choices():
            yield (tz.zone, label, tz == self.data)
