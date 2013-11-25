# coding=utf-8
"""
"""
from __future__ import absolute_import

import operator
from functools import partial
import datetime

from wtforms import (
    ValidationError,
    Field,
    SelectMultipleField,
    SelectField,
    SelectFieldBase,
    FormField,
)
from wtforms.compat import string_types, text_type
from wtforms.ext.sqlalchemy.fields import get_pk_from_identity, has_identity_key
from wtforms_alchemy import ModelFieldList as BaseModelFieldList

from flask.ext.wtf.file import FileField as BaseFileField
from flask.ext.babel import get_locale, format_date, format_datetime

from .widgets import DateTimeInput, DateInput, Select2, Select2Ajax, FileInput
from .util import babel2datetime

__all__ = ['ModelFieldList', 'FileField', 'DateField', 'Select2Field',
           'Select2MultipleField', 'QuerySelect2Field', 'JsonSelect2Field']


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
  """ support 'multiple' attribute, enabling html5 multiple file input in widget
  """
  multiple = False
  widget = FileInput()

  def __init__(self, *args, **kwargs):
    try:
      self.multiple = kwargs.pop('multiple')
    except KeyError:
      pass

    BaseFileField.__init__(self, *args, **kwargs)

  def __call__(self, **kwargs):
    if 'multiple' not in kwargs and self.multiple:
      kwargs['multiple'] = 'multiple'
    return BaseFileField.__call__(self, **kwargs)


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
      return format_datetime(self.data) if self.data else ''

  def process_formdata(self, valuelist):
    if valuelist:
      date_str = ' '.join(valuelist)
      locale = get_locale()
      date_fmt = locale.date_formats['short']
      date_fmt = babel2datetime(date_fmt)
      date_fmt = date_fmt.replace('%B', '%m').replace('%b', '%m') # force numerical months

      time_fmt = locale.time_formats['short']
      time_fmt = babel2datetime(time_fmt)

      datetime_fmt = u'{} | {}'.format(date_fmt, time_fmt)
      try:
        self.data = datetime.datetime.strptime(date_str, datetime_fmt)
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
      return format_date(self.data) if self.data else ''

  def process_formdata(self, valuelist):
    if valuelist:
      date_str = ' '.join(valuelist)
      date_fmt = get_locale().date_formats['short']
      date_fmt = babel2datetime(date_fmt)
      date_fmt = date_fmt.replace('%B', '%m').replace('%b', '%m') # force numerical months

      try:
        self.data = datetime.datetime.strptime(date_str, date_fmt).date()
      except ValueError:
        self.data = None
        raise ValueError(self.gettext('Not a valid datetime value'))


class Select2Field(SelectField):
  widget = Select2()


class Select2MultipleField(SelectMultipleField):
  widget = Select2(multiple=True)


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

  If `allow_blank` is set to `True`, then a blank choice will be added to the
  top of the list. Selecting this choice will result in the `data` property
  being `None`. The label for this blank choice can be set by specifying the
  `blank_text` parameter.
  """
  def __init__(self, label=None, validators=None, query_factory=None,
               get_pk=None, get_label=None, allow_blank=False,
               blank_text='', widget=None, multiple=False, **kwargs):
    if widget is None:
      widget = Select2(multiple=multiple)
    kwargs['widget'] = widget
    self.multiple = multiple
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
      if all(hasattr(x, '_name') for x in data):
        data = sorted(data, key=lambda x: x._name)
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
    if self.allow_blank:
      yield ('__None', self.blank_text, self.data is None)

    predicate = (operator.contains
                 if (self.multiple and self.data is not None)
                 else operator.eq)
    # remember: operator.contains(b, a) ==> a in b
    # so: obj in data ==> contains(data, obj)
    predicate = partial(predicate, self.data)

    for pk, obj in self._get_object_list():
      yield (pk, self.get_label(obj), predicate(obj))

  def process_formdata(self, valuelist):
    if not valuelist or valuelist[0] == '__None':
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
  """
  widget = Select2Ajax()

  def __init__(self, label=None, validators=None, ajax_source=None,
               blank_text='', model_class=None, **kwargs):
    super(JsonSelect2Field, self).__init__(label, validators, **kwargs)
    self.ajax_source = ajax_source
    self.model_class = model_class

    self.allow_blank = not self.is_required()
    self.blank_text = blank_text
    self._object_list = None

  # Another ad-hoc hack.
  def is_required(self):
    for validator in self.validators:
      rule = getattr(validator, "rule", {})
      if rule is not None and 'required' in rule:
        return True
    return False

  def _get_data(self):
    if self._formdata:
      id = int(self._formdata)
      obj = self.model_class.query.get(id)
      self._set_data(obj)
    return self._data

  def _set_data(self, data):
    self._data = data
    self._formdata = None

  data = property(_get_data, _set_data)

  def process_formdata(self, valuelist):
    if valuelist:
      if self.allow_blank and valuelist[0] == '':
        self.data = None
      else:
        self._data = None
        self._formdata = valuelist[0]

   # TODO really validate.
#  def pre_validate(self, form):
#    if not self.allow_blank or self.data is not None:
#      for pk, obj in self._get_object_list():
#        if self.data == obj:
#          break
#      else:
#        raise ValidationError(self.gettext('Not a valid choice'))

