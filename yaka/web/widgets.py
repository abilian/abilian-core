"""
Reusable widgets to be included in views.
"""

import cgi
from flask import render_template, json, Markup

from yaka.core.entities import Entity
from yaka.web.filters import labelize


class Column(object):

  def __init__(self, **kw):
    for k, w in kw.items():
      setattr(self, k, w)


class TableView(object):
  """
  """
  # TODO: rewrite
  def __init__(self, columns, show_controls=False):
    self.init_columns(columns)
    self.name = id(self)
    self.show_controls = show_controls

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
    table = []
    for entity in model:
      table.append(self.render_line(entity))

    return Markup(render_template('widgets/render_table.html',
                                  table=table, show_controls=self.show_controls,
                                  columns=self.columns, table_name=self.name))

  def render_line(self, entity):
    line = []
    for col in self.columns:
      if type(col) == str:
        column_name = col
      else:
        column_name = col['name']
      value = getattr(entity, column_name)
      if value is None:
        value = ""
      if column_name == '_name':
        cell = Markup('<a href="%s">%s</a>'\
                      % (entity._url, cgi.escape(value)))
      elif isinstance(value, Entity):
        cell = Markup('<a href="%s">%s</a>'\
                      % (value._url, cgi.escape(value._name)))
      elif (isinstance(value, str) or isinstance(value, unicode))\
      and value.startswith("http://"):
        # XXX: security issue here
        cell = Markup('<a href="%s">%s</a>' % (value, value[len("http://"):]))
      else:
        cell = unicode(value)
      line.append(cell)
    return line


class AjaxTableView(object):
  """
  A table that gets its data from an AJAX call.
  """
  # TODO
  pass


class SingleView(object):
  def __init__(self, *panels):
    self.panels = panels

  def render(self, model):
    # TODO: refactor by passing a model instead
    def get(attr_name):
      return self.get(model, attr_name)

    return Markup(render_template('widgets/render_single.html',
                                  panels=self.panels, get=get))

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

  def get(self, model, attr_name):
    value = getattr(model, attr_name)
    if value is None:
      return ""
    elif isinstance(value, Entity):
      return Markup('<a href="%s">%s</a>' % (value._url, cgi.escape(value._name)))
    else:
      return unicode(value)


#
# Used to describe single entity views.
#
class Panel(object):
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
  def __init__(self, *cols):
    self.cols = cols

  def __iter__(self):
    return iter(self.cols)

  def __getitem__(self, item):
    return self.cols[item]

  def __len__(self):
    return len(self.cols)