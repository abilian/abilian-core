"""
Reusable widgets to be included in views.

NOTE: code is currently quite messy. Needs to be refactored.
"""

import cgi
import urlparse
import re
import bleach

import wtforms
from flask import render_template, json, Markup
from flaskext.babel import gettext as _

from yaka.core.entities import Entity
from yaka.web.filters import labelize
from yaka.core.extensions import db

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

  def __init__(self, columns):
    self.init_columns(columns)
    self.name = id(self)

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

  def render(self, model):
    aoColumns = [{'asSorting': [] }] if self.show_controls else []
    aoColumns += [ { 'asSorting': [ "asc", "desc" ] }
                   for i in range(0, len(self.columns)) ]
    datatable_options = {
      'aoColumns': aoColumns,
      'bFilter': self.show_controls,
      'oLanguage': {
        'sSearch': "Filter records:"
      },
      'bPaginate': self.paginate,
      'sPaginationType': "bootstrap",
      'bLengthChange': False,
      'iDisplayLength': 50
    }
    js = "$('#%s').dataTable(%s);" % (self.name, json.dumps(datatable_options))

    table = []
    for entity in model:
      table.append(self.render_line(entity))

    return Markup(render_template('widgets/render_table.html',
                                  table=table, js=Markup(js), view=self))

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

  def __init__(self, column_names, options):
    BaseTableView.__init__(self, column_names)
    self.options = options


class AjaxMainTableView(object):
  """
  Variant of the MainTableView that gets content from AJAX requests.

  TODO: refactor all of this (currently code is copy/pasted!).
  """
  show_controls = False
  paginate = True

  def __init__(self, columns, ajax_source, search_criterions=()):
    self.init_columns(columns)
    self.ajax_source = ajax_source
    self.search_criterions = search_criterions
    self.name = id(self)

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
# Single object view + helper class
#
class ModelWrapper(object):
  """
  Decorator / proxy (I've never really understood the difference in the GoF
  patterns book) which mostly adds a few convenience methods to a model, like
  a custom `__getitem__`.
  """

  def __init__(self, model):
    self.model = model
    self.cls = model.__class__

  def filter_non_empty_panels(self, panels):
    non_empty_panels = []

    for panel in panels:
      names = []
      for row in panel.rows:
        for name in row:
          names.append(name)

      for name in names:
        if not self[name]['skip']:
          non_empty_panels.append(panel)
          break

    return non_empty_panels

  def __getitem__(self, name):
    try:
      info = self.cls.__mapper__.c[name].info
      label = info['label']
    except (AttributeError, KeyError):
      try:
        label = _(name)
      except KeyError:
        # i18n may be not initialized (in some unit tests for example)
        label = name

    value = getattr(self.model, name)

    # Massage the values a little bit
    skip = False
    rendered = ""

    if value in (None, False, 0, 0.0):
      skip = True
    elif value in ("", "-"):
      skip = True

    elif value is True:
      rendered = u"\u2713" # Unicode "Check mark"
    elif isinstance(value, Entity):
      rendered = Markup('<a href="%s">%s</a>'
                        % (value._url, cgi.escape(value._name)))

    elif isinstance(value, list):
      if any((isinstance(v, db.Model) for v in value)):
        # at least one of the value is a model
        columns = [c for c in value[0].__table__.columns
                   if c.info.get('editable', True)]
        attributes = [c.name for c in columns]
        labels = [c.info.get(label, c.name) for c in columns]
        rendered = Markup(
              render_template('widgets/horizontal_table.html',
                              values=value, labels=labels,
                              attributes=attributes,)
              )
      else:
        rendered = "; ".join(value)

    # XXX: Several hacks. Needs to be moved somewhere else.
    elif name == 'siret' and value:
      siret = unicode(value)
      if len(siret) > 9:
        siren = siret[0:9]
      else:
        siren = siret
      url = "http://societe.com/cgi-bin/recherche?rncs=%s" % siren
      rendered = Markup('<a href="%s">%s</a><i class="icon-share-alt"></i>'
                        % (url, siret))

    elif name == 'email' and value:
      rendered = Markup(bleach.linkify(value, parse_email=True)
                        + '&nbsp;<i class="icon-envelope"></i>')

    elif name == 'site_web' and value:
      rendered = Markup(linkify_url(value))

    # Default cases come last
    elif isinstance(value, basestring):
      rendered = text2html(value)
    else:
      rendered = unicode(value)

    return dict(name=name, rendered=rendered, label=label, skip=skip)


class SingleView(object):
  """View on a single object."""

  def __init__(self, *panels):
    self.panels = panels

  def render(self, model):
    wrapped_model = ModelWrapper(model)
    return Markup(render_template('widgets/render_single.html',
                                  panels=self.panels, model=wrapped_model))

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

class TabularFieldListWidget(object):
  """ For list of formfields
  """

  def __call__(self, field, **kwargs):
    assert isinstance(field, wtforms.fields.FieldList)
    labels = None

    if len(field):
      assert isinstance(field[0], wtforms.fields.FormField)
      labels = [f.label for f in field[0] if not f.flags.hidden]

    return Markup(
      render_template('widgets/tabular_fieldlist_widget.html',
                      labels=labels, field=field))
