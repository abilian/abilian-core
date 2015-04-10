# coding=utf-8
"""
"""
from __future__ import absolute_import

import operator
import logging
from functools import partial
import datetime

import sqlalchemy as sa

from wtforms import (
    ValidationError,
    Field,
    SelectMultipleField,
    SelectField,
    SelectFieldBase,
    FormField,
)
from wtforms.validators import required, optional
from wtforms.compat import string_types, text_type
from wtforms.ext.sqlalchemy.fields import get_pk_from_identity, has_identity_key
from wtforms_alchemy import ModelFieldList as BaseModelFieldList
import babel

from flask.helpers import locked_cached_property
from flask_wtf.file import FileField as BaseFileField
from flask_babel import (
  get_locale, get_timezone,
  format_date, format_datetime
  )

from abilian import i18n
from abilian.core.util import utc_dt
from abilian.core.extensions import db

from .widgets import DateTimeInput, DateInput, Select2, Select2Ajax, FileInput
from .util import babel2datetime

__all__ = ['ModelFieldList', 'FileField', 'DateField', 'Select2Field',
           'Select2MultipleField', 'QuerySelect2Field', 'JsonSelect2Field',
           'JsonSelect2MultipleField']


class ModelFieldList(BaseModelFieldList):
  """ Filter empty entries
  """

  def validate(self, form, extra_validators=tuple()):
    for field in self.entries:
      is_subform = isinstance(field, FormField)
      data = field.data.values() if is_subform else [field.data]

      if not any(data):
        # all inputs empty: discard row
        self.entries.remove(field)

    return super(ModelFieldList, self).validate(form, extra_validators)


class FileField(BaseFileField):
  """
  support 'multiple' attribute, enabling html5 multiple file input in widget.

  can store file using a related model

  :param blob_attr: attribute name to store / retrieve value on related model.
      Used if `name` is a relationship on model. Defauts to `'value'`
  """
  multiple = False
  widget = FileInput()
  blob_attr = 'value'
  allow_delete = True

  def __init__(self, *args, **kwargs):
    try:
      self.multiple = kwargs.pop('multiple')
    except KeyError:
      pass

    self.blob_attr = kwargs.pop('blob_attr', self.__class__.blob_attr)
    self.allow_delete = kwargs.pop('allow_delete', self.__class__.allow_delete)

    BaseFileField.__init__(self, *args, **kwargs)

  def __call__(self, **kwargs):
    if 'multiple' not in kwargs and self.multiple:
      kwargs['multiple'] = 'multiple'
    return BaseFileField.__call__(self, **kwargs)

  def process(self, formdata, *args, **kwargs):
    delete_arg = u'__{name}_delete__'.format(name=self.name)
    self._delete_file = formdata and delete_arg in formdata

    return super(FileField, self).process(formdata, *args, **kwargs)

  def process_data(self, value):
    if isinstance(value, db.Model):
      value = getattr(value, self.blob_attr)

    return super(FileField, self).process_data(value)

  def populate_obj(self, obj, name):
    """
    Store file
    """
    if not self.has_file() and not (self.allow_delete and self._delete_file):
      return

    state = sa.inspect(obj)
    mapper = state.mapper
    if name not in mapper.relationships:
      # directly store in database
      return super(FileField, self).populate_obj(obj, name)

    rel = getattr(mapper.relationships, name)
    if rel.uselist:
      raise ValueError("Only single target supported; else use ModelFieldList")

    val = getattr(obj, name)
    if val is None:
      val = rel.mapper.class_()
      setattr(obj, name, val)

    data = self.data.read() if self.has_file() else u''
    setattr(val, self.blob_attr, data)


class DateTimeField(Field):
  """
  """
  widget = DateTimeInput()

  def __init__(self, label=None, validators=None, **kwargs):
    super(DateTimeField, self).__init__(label, validators, **kwargs)

  def _value(self):
    if self.raw_data:
      return ' '.join(self.raw_data)
    else:
      locale = get_locale()
      date_fmt = locale.date_formats['short'].pattern
      # force numerical months and 4 digit years
      date_fmt = date_fmt.replace('MMMM', 'MM')\
                         .replace('MMM', 'MM')\
                         .replace('yyyy', 'y')\
                         .replace('yy', 'y')\
                         .replace('y', 'yyyy')
      time_fmt = locale.time_formats['short']
      dt_fmt = locale.datetime_formats['short'].format(time_fmt, date_fmt)
      return format_datetime(self.data, dt_fmt) if self.data else ''

  def process_formdata(self, valuelist):
    if valuelist:
      date_str = ' '.join(valuelist)
      locale = get_locale()
      date_fmt = locale.date_formats['short']
      date_fmt = babel2datetime(date_fmt)
      date_fmt = date_fmt.replace('%B', '%m')\
                         .replace('%b', '%m')  # force numerical months
      time_fmt = locale.time_formats['short']
      time_fmt = babel2datetime(time_fmt)
      datetime_fmt = u'{} | {}'.format(date_fmt, time_fmt)
      try:
        self.data = datetime.datetime.strptime(date_str, datetime_fmt)
        if not self.data.tzinfo:
          self.data = utc_dt(get_timezone().localize(self.data))
      except ValueError:
        self.data = None
        raise ValueError(self.gettext('Not a valid datetime value'))


class DateField(DateTimeField):
  """
  A text field which stores a `datetime.datetime` matching a format.
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
      date_fmt = date_fmt.replace('MMMM', 'MM')\
                         .replace('MMM', 'MM')\
                         .replace('yyyy', 'y')\
                         .replace('yy', 'y')\
                         .replace('y', 'yyyy')
      return format_date(self.data, date_fmt) if self.data else ''

  def process_formdata(self, valuelist):
    if valuelist:
      date_str = ' '.join(valuelist)
      date_fmt = get_locale().date_formats['short']
      date_fmt = babel2datetime(date_fmt)
      date_fmt = date_fmt.replace('%B', '%m')\
                         .replace('%b', '%m')

      try:
        self.data = datetime.datetime.strptime(date_str, date_fmt).date()
      except ValueError:
        self.data = None
        raise ValueError(self.gettext('Not a valid datetime value'))


class Select2Field(SelectField):
  """
  Allow choices to be a function instead of an iterable
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
  def __init__(self, label=None, validators=None, query_factory=None,
               get_pk=None, get_label=None, allow_blank=False,
               blank_text='', widget=None, multiple=False, **kwargs):
    if widget is None:
      widget = Select2(multiple=multiple)
    kwargs['widget'] = widget
    self.multiple = multiple

    if (validators is None
        or not any(isinstance(v, (optional, required)) for v in validators)):
      logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
      logger.warning('Use deprecated paramater `allow_blank`.')
      validators.append(optional() if allow_blank else required())

    super(QuerySelect2Field, self).__init__(label, validators, **kwargs)

    # PATCHED!
    if query_factory:
      self.query_factory = query_factory

    if get_pk is None:
      if not has_identity_key:
        raise Exception('The sqlalchemy identity_key function could not be imported.')
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
    self._data = data
    self._formdata = None

  data = property(_get_data, _set_data)

  def _get_object_list(self):
    if self._object_list is None:
      query = self.query or self.query_factory()
      get_pk = self.get_pk
      self._object_list = list((text_type(get_pk(obj)), obj) for obj in query)
    return self._object_list

  def iter_choices(self):
    if not self.flags.required:
      yield (None,
             None,
             self.data == [] if self.multiple else self.data is None,)

    predicate = (operator.contains
                 if (self.multiple and self.data is not None)
                 else operator.eq)
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
      data = set(self.data if self.multiple else [self.data])
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
  def __init__(self, label=None, validators=None, ajax_source=None, widget=None,
               blank_text='', model_class=None, multiple=False, **kwargs):

    self.multiple = multiple

    if widget is None:
      widget = Select2Ajax(self.multiple)

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
      yield(obj.id, obj.name, True)

  def _get_data(self):
    formdata = self._formdata
    if formdata:
      if not self.multiple:
        formdata = [formdata]
      data = [self.model_class.query.get(int(pk)) for pk in formdata]
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


class JsonSelect2MultipleField(JsonSelect2Field):
  # legacy class, now use JsonSelect2Field(multiple=True)
  pass


class LocaleSelectField(SelectField):
  widget = Select2()

  def __init__(self, *args, **kwargs):
    kwargs['coerce'] = babel.Locale.parse
    kwargs['choices'] = (locale_info
                         for locale_info in i18n.supported_app_locales())
    super(LocaleSelectField, self).__init__(*args, **kwargs)

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
