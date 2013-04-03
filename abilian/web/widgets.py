# coding=utf-8
"""
Reusable widgets to be included in views.

NOTE: code is currently quite messy. Needs to be refactored.
"""
import cgi
import urlparse
import re
import datetime
import bleach
from itertools import ifilter
from collections import namedtuple

import wtforms
from flask import render_template, json, Markup
from flask.ext.babel import gettext as _, format_date, format_datetime
from wtforms_alchemy import ModelFieldList

from abilian.core.entities import Entity
from abilian.web.filters import labelize
from abilian.core.extensions import db

def linkify_url(value):
  """Tranform an URL pulled from the database to a safe HTML fragment."""

  value = value.strip()

  rjs = r'[\s]*(&#x.{1,7})?'.join(list('javascript:'))
  rvb = r'[\s]*(&#x.{1,7})?'.join(list('vbscript:'))
  re_scripts = re.compile('(%s)|(%s)' % (rjs, rvb), re.IGNORECASE)

  value = re_scripts.sub('', value)

  url = value
  if not url.startswith("http://") and not url.startswith("https://"):
    url = "http://" + url

  url = urlparse.urlsplit(url).geturl()
  if '"' in url:
    url = url.split('"')[0]
  if '<' in url:
    url = url.split('<')[0]

  if value.startswith("http://"):
    value = value[len("http://"):]
  elif value.startswith("https://"):
    value = value[len("https://"):]

  if value.count("/") == 1 and value.endswith("/"):
    value = value[0:-1]

  return '<a href="%s">%s</a><i class="icon-share-alt"></i>' % (url, value)


def text2html(text):
  text = text.strip()
  if re.search('<(p|br)>', text.lower()):
    return text
  if not '\n' in text:
    return text

  lines = text.split("\n")
  lines = [ line for line in lines if line ]
  paragraphs = ['<p>%s</p>' % line for line in lines]
  return Markup(bleach.clean("\n".join(paragraphs), tags=['p']))


class Column(object):

  def __init__(self, **kw):
    for k, w in kw.items():
      setattr(self, k, w)


# TODO: rewrite
class BaseTableView(object):
  """
  """
  show_controls = False
  paginate = False
  options = {}

  def __init__(self, columns, options=None):
    self.init_columns(columns)
    self.name = id(self)
    if options is not None:
      self.options = options

  def init_columns(self, columns):
    # TODO
    self.columns = []
    default_width = 0.99 / len(columns)
    for col in columns:
      if type(col) == str:
        col = dict(name=col, width=default_width)
      assert type(col) == dict
      if not col.has_key('label'):
        col['label'] = labelize(col['name'])
      self.columns.append(col)

  def render(self, entities, **kwargs):
    aoColumns = [{'asSorting': [] }] if self.show_controls else []
    aoColumns += [ { 'asSorting': [ "asc", "desc" ] }
                   for i in range(0, len(self.columns)) ]
    datatable_options = {
      'aoColumns': aoColumns,
      'bFilter': self.show_controls,
      'oLanguage': {
        'sSearch': _("Filter records:"),
      },
      'bStateSave': False,
      'bPaginate': self.paginate,
      'sPaginationType': "bootstrap",
      'bLengthChange': False,
      'iDisplayLength': 50
    }
    js = "$('#%s').dataTable(%s);" % (self.name, json.dumps(datatable_options))

    table = []
    for entity in entities:
      table.append(self.render_line(entity))

    template = (self.options.get('template', ''), 'widgets/render_table.html')
    return Markup(render_template(template,
                                  table=table, js=Markup(js), view=self,
                                  **kwargs))

  def render_line(self, entity):
    line = []
    make_link_on = self.options.get("make_link_on")

    for col in self.columns:
      if type(col) == str:
        column_name = col
      else:
        column_name = col['name']
      value = getattr(entity, column_name)


      # Manual massage.
      if value is None:
        value = ""
      if column_name == make_link_on or column_name == '_name' or \
         col.get('linkable'):
        cell = Markup('<a href="%s">%s</a>'\
                      % (entity._url, cgi.escape(unicode(value))))
      elif isinstance(value, Entity):
        cell = Markup('<a href="%s">%s</a>'\
                      % (value._url, cgi.escape(value._name)))
      elif isinstance(value, basestring) \
          and (value.startswith("http://") or value.startswith("www.")):
        cell = Markup(linkify_url(value))
      elif isinstance(value, list):
        cell = "; ".join(value)
      else:
        cell = unicode(value)

      line.append(cell)
    return line


class MainTableView(BaseTableView):
  """
  Table view for main objects list.
  """
  show_controls = True
  paginate = True


class RelatedTableView(BaseTableView):
  """
  Table view for related objects list.
  """
  show_controls = False
  paginate = False

class AjaxMainTableView(object):
  """
  Variant of the MainTableView that gets content from AJAX requests.

  TODO: refactor all of this (currently code is copy/pasted!).
  """
  show_controls = False
  paginate = True

  def __init__(self, columns, ajax_source, search_criterions=(), name=None):
    self.init_columns(columns)
    self.ajax_source = ajax_source
    self.search_criterions = search_criterions
    self.name = name if name is not None else id(self)
    self.save_state = name is not None

  def init_columns(self, columns):
    # TODO: compute the correct width for each column.
    self.columns = []
    default_width = 0.99 / len(columns)
    for col in columns:
      if type(col) == str:
        col = dict(name=col, width=default_width)
      assert type(col) == dict
      if not col.has_key('label'):
        col['label'] = labelize(col['name'])
      self.columns.append(col)

  def render(self):
    aoColumns = [{'asSorting': [] }] if self.show_controls else []
    aoColumns += [ { 'asSorting': [ "asc", "desc" ] }
                   for i in range(0, len(self.columns)) ]

    datatable_options = {
      'sDom': 'lfFrtip',
      'aoColumns': aoColumns,
      'bFilter': True,
      'oLanguage': {
        'sSearch': _("Filter records:"),
        'sPrevious': _("Previous"),
        'sNext': _("Next"),
        'sInfo': _("Showing _START_ to _END_ of _TOTAL_ entries"),
        'sInfoFiltered': _("(filtered from _MAX_ total entries)"),
        'sAdvancedSearch': _("Advanced filtering"),
      },
      'bPaginate': self.paginate,
      'sPaginationType': "bootstrap",
      'bLengthChange': False,
      'iDisplayLength': 25,

      'bStateSave': self.save_state,
      'bProcessing': True,
      'bServerSide': True,
      'sAjaxSource': self.ajax_source,
    }

    advanced_search_filters = [dict(name=c.name,
                                    label=unicode(c.label),
                                    type=c.form_filter_type,
                                    args=c.form_filter_args)
                               for c in self.search_criterions
                               if c.has_form_filter]
    if advanced_search_filters:
      datatable_options['aoAdvancedSearchFilters'] = advanced_search_filters

    return Markup(render_template('widgets/render_ajax_table.html',
                                  datatable_options=datatable_options,
                                  view=self))

  def render_line(self, entity):
    line = []
    for col in self.columns:
      if type(col) == str:
        column_name = col
      else:
        column_name = col['name']
      value = getattr(entity, column_name)

      # Manual massage.
      if value is None:
        value = ""
      elif 'display_fmt' in col:
        value = col['display_fmt'](value)

      if column_name == '_name':
        cell = Markup('<a href="%s">%s</a>'\
                      % (entity._url, cgi.escape(value)))
      elif isinstance(value, Entity):
        cell = Markup('<a href="%s">%s</a>'\
                      % (value._url, cgi.escape(value._name)))
      elif isinstance(value, basestring)\
        and (value.startswith("http://") or value.startswith("www.")):
          cell = Markup(linkify_url(value))
      elif col.get('linkable'):
        cell = Markup('<a href="%s">%s</a>'\
                      % (entity._url, cgi.escape(unicode(value))))
      else:
        cell = unicode(value)

      line.append(cell)
    return line


#
# Single object view
#
class SingleView(object):
  """View on a single object."""

  def __init__(self, form, *panels):
    self.form = form
    self.panels = panels

  def render(self, model):
    form = self.form(obj=model)
    mapper = model.__class__.__mapper__
    panels = []
    _to_skip = (None, False, 0, 0.0, '', u'-')

    for panel in self.panels:
      data = {}
      field_name_iter = (fn for row in panel.rows
                         for fn in row)

      for name in field_name_iter:
        field = form._fields[name]
        if field.flags.hidden:
          continue

        value = field.object_data
        if value in _to_skip:
          continue

        value = Markup(field.render_view())
        if value == u'':
          # related models may have [] as value, but we don't discard this type
          # of value in order to let widget a chance to render something useful
          # like an 'add model' button.
          #
          # if it renders an empty string, there's really no point in rendering
          # a line for this empty field
          continue

        label = self.label_for(field, mapper, name)
        data[name] = (label,value,)

      if data:
        panels.append((panel, data,))

    return Markup(render_template('widgets/render_single.html',
                                  panels=panels))

  def render_form(self, form, for_new=False):
    # Client-side rules for jQuery.validate
    # See: http://docs.jquery.com/Plugins/Validation/Methods#Validator
    rules = {}
    for field in form:
      rules_for_field = {}
      for validator in field.validators:
        rule_for_validator = getattr(validator, "rule", None)
        if rule_for_validator:
          rules_for_field.update(rule_for_validator)
      if rules_for_field:
        rules[field.name] = rules_for_field
    if rules:
      rules = Markup(json.dumps(rules))
    else:
      rules = None

    return Markup(render_template('widgets/render_for_edit.html',
                                  form=form, for_new=for_new, rules=rules))

  def label_for(self, field, mapper, name):
    label = field.label
    if label is None:
      try:
        info = mapper.c[name].info
        label = info['label']
      except (AttributeError, KeyError):
        pass

    if label is None:
      try:
        label = _(name)
      except KeyError:
        # i18n may be not initialized (in some unit tests for example)
        label = name

    return label

#
# Used to describe single entity views.
#
class Panel(object):
  """
  `Panel` and `Row` classes help implement a trivial internal DSL for
  specifying multi-column layouts in forms or object views.

  They are currently not really used, since we went with 1-column designs
  eventually.
  """

  def __init__(self, label=None, *rows):
    self.label = label
    self.rows = rows

  def __iter__(self):
    return iter(self.rows)

  def __getitem__(self, item):
    return self.rows[item]

  def __len__(self):
    return len(self.rows)


class Row(object):
  """
  `Panel` and `Row` classes help implement a trivial internal DSL for
  specifying multi-column layouts in forms or object views.

  They are currently not really used, since we went with 1-column designs
  eventually.
  """

  def __init__(self, *cols):
    self.cols = cols

  def __iter__(self):
    return iter(self.cols)

  def __getitem__(self, item):
    return self.cols[item]

  def __len__(self):
    return len(self.cols)

# Form field widgets ###########################################################
class DefaultViewWidget(object):
  def render_view(self, field, **kwargs):
    value = field.object_data
    if isinstance(value, basestring):
      return text2html(value)
    else:
      return unicode(value or u'') # [], None and other must be rendered using
                                   # empty string

class BooleanWidget(wtforms.widgets.CheckboxInput):
  def render_view(self, field):
    return u'\u2713' if field.object_data else u'' # Unicode "Check mark"

class FloatWidget(wtforms.widgets.TextInput):
  """ in view mode, format float number to 'precision' decimal
  """
  def __init__(self, precision=None):
    self.precision = precision
    if precision is not None:
        self._fmt = '.{:d}f'.format(precision)

  def render_view(self, field):
    data = field.object_data
    if data is None:
      return u''

    return format(data, self._fmt)


class DateWidget(wtforms.widgets.TextInput):
  def render_view(self, field):
    return (format_date(field.object_data)
            if field.object_data else u'')

class DateTimeWidget(DateWidget):
  def render_view(self, field):
    return (format_datetime(field.object_data)
            if field.object_data else u'')

class EntityWidget(object):
  def render_view(self, field):
    obj = field.object_data
    return (u'<a href="{}">{}</a>'.format(obj._url, cgi.escape(obj._name))
            if obj else u'')

class MoneyWidget(wtforms.widgets.Input):
  """ Widget used to show / enter money amount.
  Currently hardcoded to € / k€
  """
  input_type = 'number'

  def render_view(self, field):
    val = field.object_data
    unit = u'€'

    if val is None:
      return u''

    if val > 1000:
      unit = u'k€'
      val = int(round(val / 1000.0))

    # \u00A0: non-breakable whitespace
    return u'{value}\u00A0{unit}'.format(value=val, unit=unit)

class EmailWidget(object):
  def render_view(self, field):
    link = bleach.linkify(field.object_data, parse_email=True)
    return (u'{}&nbsp;<i class="icon-envelope"></i>'.format(link)
            if link else u'')

class URLWidget(object):
  def render_view(self, field):
    return (linkify_url(field.object_data)
            if field.object_data else u'')

class ListWidget(wtforms.widgets.ListWidget):
  """ display field label is optionnal
  """

  def __init__(self, html_tag='ul', prefix_label=True, show_label=True):
    wtforms.widgets.ListWidget.__init__(self, html_tag, prefix_label)
    self.show_label = show_label

  def __call__(self, field, **kwargs):
    if self.show_label:
      return super(ListWidget, self)(field, **kwargs)

    kwargs.setdefault('id', field.id)
    html = [u'<%s %s>' % (self.html_tag, wtforms.widgets.html_params(**kwargs))]
    for subfield in field:
      html.append(u'<li>{}</li>'.format(subfield()))

    html.append(u'</%s>' % self.html_tag)
    return wtforms.widgets.HTMLString(''.join(html))

  def render_view(self, field):
    return u'; '.join(field.object_data)

class TabularFieldListWidget(object):
  """ For list of formfields
  """
  def __init__(self, template='widgets/tabular_fieldlist_widget.html'):
    self.template = template

  def __call__(self, field, **kwargs):
    assert isinstance(field, wtforms.fields.FieldList)
    labels = None

    if len(field):
      assert isinstance(field[0], wtforms.fields.FormField)
      field_names = [f.short_name for f in field[0] if not f.is_hidden]
      data_type = field.entries[0].__class__.__name__ + 'Data'
      Data = namedtuple(data_type, field_names)
      labels = Data(*[f.label for f in field[0] if not f.is_hidden])

    return Markup(render_template(self.template, labels=labels, field=field))

class ModelListWidget(object):

  def __init__(self, template='widgets/horizontal_table.html'):
    self.template = template

  def render_view(self, field, **kwargs):
    assert isinstance(field, ModelFieldList)
    value = field.object_data
    if not value:
      return render_template(self.template, field=field,  labels=(),
                             rows=(), **kwargs)

    mapper = value[0].__mapper__
    field_names = []
    labels = []

    for f in field.entries[0].form:
      if f.is_hidden:
        continue
      name = f.short_name
      field_names.append(name)
      col_label = u''
      col = mapper.c.get(name)
      if col is not None:
        col_label = col.info.get('label', name)
      labels.append(f.label.text if f.label else col_label)

    data_type = field.entries[0].object_data.__class__.__name__ + 'Data'
    Data = namedtuple(data_type, field_names)
    labels = Data(*labels)

    rows = []
    for entry in field.entries:
      row = []
      for f in ifilter(lambda f: not f.is_hidden, entry.form):
        row.append(Markup(f.render_view()))

      rows.append(Data(*row))

    rendered = render_template(self.template, field=field,  labels=labels,
                               rows=rows, **kwargs)
    return rendered
