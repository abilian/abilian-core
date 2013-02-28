# coding=utf-8

"""
Front-end for a CRM app.

This should eventually allow implementing very custom CRM-style application.
"""
import StringIO

import copy
import csv
from datetime import date
from pprint import pprint
from time import strftime, gmtime
import re

from flask import session, redirect, request, g, render_template, flash,\
  Blueprint, jsonify, abort, make_response, current_app
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql.expression import asc, desc, nullsfirst, nullslast
from sqlalchemy.exc import IntegrityError
from sqlalchemy import orm
from xlwt import Workbook, XFStyle
from yaka.core.entities import ValidationError, Entity

from yaka.core.signals import activity
from yaka.services import audit_service
from yaka.core.extensions import db

from . import search
from .decorators import templated
from .forms import ModelFieldList
from .widgets import Panel, Row, SingleView, RelatedTableView,\
  AjaxMainTableView


class BreadCrumbs(object):
  def __init__(self, l=()):
    self._bc = []
    for path, label in l:
      self.add(path, label)

  def add(self, path="", label=""):
    if path and not path.startswith("/"):
      previous = self._bc[-1]
      path = previous['path'] + "/" + path
    self._bc.append(dict(path=path, label=label))

  def __getitem__(self, item):
    return self._bc[item]

  def __add__(self, t):
    bc = self.clone()
    bc.add(t[0], t[1])
    return bc

  def clone(self):
    new = BreadCrumbs()
    new._bc = copy.copy(self._bc)
    return new


def add_to_recent_items(entity, type=None):
  if not type:
    type = entity.__class__.__name__.lower()
  g.recent_items.insert(0, dict(type=type, name=entity._name, url=entity._url))
  s = set()
  l = []
  for item in g.recent_items:
    if item['url'] in s:
      continue
    s.add(item['url'])
    l.append(item)
  if len(l) > 5:
    del l[5:]
  session['recent_items'] = g.recent_items = l


def expose(url='/', methods=('GET',)):
  """
  Use this decorator to expose views in your view classes.

  `url`
      Relative URL for the view
  `methods`
      Allowed HTTP methods. By default only GET is allowed.
  """

  def wrap(f):
    if not hasattr(f, '_urls'):
      f._urls = []
    f._urls.append((url, methods))
    return f

  return wrap


def labelize(s):
  return " ".join([w.capitalize() for w in s.split("_")])


def make_single_view(form):
  panels = []
  for g in form._groups:
    panel = Panel(g[0], *[ Row(x) for x in g[1] ])
    panels.append(panel)
  return SingleView(form, *panels)


class ModuleMeta(type):
  """
  Module metaclass.

  Does some precalculations (like getting list of view methods from the
  class) to avoid calculating them for each view class instance.
  """

  def __init__(cls, classname, bases, fields):
    type.__init__(cls, classname, bases, fields)

    # Gather exposed views
    cls._urls = []
    cls._default_view = None

    for p in dir(cls):
      attr = getattr(cls, p)

      if hasattr(attr, '_urls'):
        # Collect methods
        for url, methods in attr._urls:
          cls._urls.append((url, p, methods))

          if url == '/':
            cls._default_view = p

            # Wrap views
            #setattr(cls, p, _wrap_view(attr))


class Module(object):
  __metaclass__ = ModuleMeta

  id = None
  endpoint = None
  label = None
  managed_class = None
  list_view = None
  list_view_columns = []
  single_view = None
  edit_form_class = None
  url = None
  name = None
  static_folder = None
  related_views = []
  search_criterions = (search.TextSearchCriterion("name",
                                                  attributes=('name', 'nom')),)
  _urls = []

  def __init__(self):
    # If endpoint name is not provided, get it from the class name
    if self.endpoint is None:
      self.endpoint = self.__class__.__name__.lower()

    if self.label is None:
      self.label = labelize(self.endpoint)

    if self.id is None:
      self.id = self.managed_class.__name__.lower()

    self.single_view = make_single_view(self.edit_form_class)

    # copy criterions instances; without that they may be shared by subclasses
    self.search_criterions = tuple((copy.deepcopy(c)
                                    for c in self.search_criterions))
    for sc in self.search_criterions:
      sc.model = self.managed_class

  def create_blueprint(self, crud_app):
    """
    Create a Flask blueprint for this module.
    """
    # Store admin instance
    self.crud_app = crud_app
    self.app = crud_app.app

    # If url is not provided, generate it from endpoint name
    if self.url is None:
      self.url = '%s/%s' % (self.crud_app.url, self.endpoint)
    else:
      if not self.url.startswith('/'):
        self.url = '%s/%s' % (self.crud_app.url, self.url)

    # If name is not provided, use capitalized endpoint name
    if self.name is None:
      self.name = self._prettify_name(self.__class__.__name__)

    # Create blueprint and register rules
    self.blueprint = Blueprint(self.endpoint, __name__,
                               url_prefix=self.url,
                               template_folder='templates/crm',
                               static_folder=self.static_folder)

    for url, name, methods in self._urls:
      self.blueprint.add_url_rule(url,
                                  name,
                                  getattr(self, name),
                                  methods=methods)

    self.managed_class.base_url = self.url

    return self.blueprint

  def query(self, request):
    """ Return filtered query based on request args
    """
    args = request.args
    search = args.get("sSearch", "").replace("%", "").lower()
    q = self.managed_class.query

    for crit in self.search_criterions:
      q = crit.filter(q, self, request, search)

    return q

  def ordered_query(self, request, query=None):
    """ Order query according to request args.

    If query is None, the query is generated according to request args with
    self.query(request)
    """
    if query is None:
      query = self.query(request)
    args = request.args
    sort_col = int(args.get("iSortCol_0", 1))
    sort_dir = args.get("sSortDir_0", "asc")
    sort_col_def = self.list_view_columns[sort_col]
    sort_col_name = sort_col_def['name']

    if sort_col_name == '_name':
      sort_col_name = 'nom'

    sort_col = getattr(self.managed_class, sort_col_name)

    if isinstance(sort_col.property, orm.properties.RelationshipProperty):
      # this is a related model: find attribute to filter on
      query = query.join(sort_col_name)
      query.reset_joinpoint()
      rel_sort_name = sort_col_def.get('sort_on', 'nom')
      rel_model = sort_col.property.mapper.class_
      sort_col = getattr(rel_model, rel_sort_name)

    # XXX: Big hack, date are sorted in reverse order by default
    if isinstance(sort_col, sa.types._DateAffinity):
      sort_dir = 'asc' if sort_dir == 'desc' else 'desc'
    elif isinstance(sort_col, sa.types.String):
      sort_col = func.lower(sort_col)

    direction = desc if sort_dir == 'desc' else asc
    sort_col = direction(sort_col)

    # sqlite does not support 'NULLS FIRST|LAST' in ORDER BY clauses
    engine = query.session.get_bind(self.managed_class.__mapper__)
    if engine.name != 'sqlite':
      nullsorder = nullslast if sort_dir == 'desc' else nullsfirst
      sort_col = nullsorder(sort_col)

    return query.order_by(sort_col)

  #
  # Exposed views
  #
  @expose("/")
  @templated("crm/list_view.html")
  def list_view(self):
    bc = self.bread_crumbs()

    # TODO: should be an instance variable.
    table_view = AjaxMainTableView(columns=self.list_view_columns,
                                   ajax_source=self.url + "/json",
                                   search_criterions=self.search_criterions,)
    rendered_table = table_view.render()

    return dict(rendered_table=rendered_table, breadcrumbs=bc, module=self)

  @expose("/json")
  def list_json(self):
    """
    JSON endpoint, for AJAX-backed table views.
    """
    args = request.args
    echo = int(args.get("sEcho", 0))
    length = int(args.get("iDisplayLength", 10))
    start = int(args.get("iDisplayStart", 0))
    end = start + length

    total_count = self.managed_class.query.count()
    q = self.query(request)
    count = q.count()
    q = self.ordered_query(request, q)

    entities = q.slice(start, end).all()

    # TODO: should be an instance variable.
    table_view = AjaxMainTableView(columns=self.list_view_columns,
                                   ajax_source=self.url + "/json")

    data = [table_view.render_line(e) for e in entities]
    result = {
      "sEcho": echo,
      "iTotalRecords": total_count,
      "iTotalDisplayRecords": count,
      "aaData": data,
    }
    return jsonify(result)

  @expose("/export_xls")
  def export_to_xls(self):
    # TODO: take care of all the special cases
    wb = Workbook()
    ws = wb.add_sheet("Sheet 1")

    objects = self.ordered_query(request)
    form = self.edit_form_class()

    col_names = ['id']
    obj = objects[0]
    for field in form:
      if isinstance(field, ModelFieldList):
        continue
      if hasattr(obj, field.name):
        col_names.append(field.name)

    for c, col_name in enumerate(col_names):
      ws.write(0, c, col_name)

    for r, obj in enumerate(objects):
      for c, col_name in enumerate(col_names):
        style = None
        value = getattr(obj, col_name)
        if isinstance(value, Entity):
          value = value._name
        elif isinstance(value, list):
          value = "; ".join(value)
        elif isinstance(value, date):
          style = XFStyle()
          style.num_format_str = "D/M/Y"
        if style:
          ws.write(r+1, c, value, style)
        else:
          ws.write(r+1, c, value)

    fd = StringIO.StringIO()
    wb.save(fd)

    debug = request.args.get('debug_sql')
    if debug:
      # useful only in DEBUG mode, to get the debug toolbar in browser
      return '<html><body>Exported</body></html>'

    response = make_response(fd.getvalue())
    response.headers['content-type'] = 'application/ms-excel'
    filename = "%s-%s.xls" % (self.managed_class.__name__,
                              strftime("%d:%m:%Y-%H:%M:%S", gmtime()))
    response.headers['content-disposition'] = 'attachment;filename="%s"' % filename
    return response

  @expose("/export")
  def export_to_csv(self):
    # TODO: take care of all the special cases
    csvfile = StringIO.StringIO()
    writer = csv.writer(csvfile)

    objects = self.ordered_query(request)

    form = self.edit_form_class()
    headers = ['id']
    for field in form:
      if hasattr(objects[0], field.name):
        headers.append(field.name)
    writer.writerow(headers)

    for object in objects:
      row = [object.id]
      for field in form:
        if hasattr(object, field.name):
          value = getattr(object, field.name)
          if value is None:
            value = ""
          row.append(unicode(value).encode('utf8'))
      writer.writerow(row)

    response = make_response(csvfile.getvalue())
    response.headers['content-type'] = 'application/csv'
    filename = "%s-%s.csv" % (self.managed_class.__name__,
                              strftime("%d:%m:%Y-%H:%M:%S", gmtime()))
    response.headers['content-disposition'] = 'attachment;filename="%s"' % filename
    return response

  @expose("/json2")
  def list_json2(self):
    """
    Other JSON endpoint, this time used for filling select boxes dynamically.

    NB: not used currently.
    """
    args = request.args
    cls = self.managed_class

    q = args.get("q").replace("%", " ")
    if not q or len(q) < 2:
      abort(500)

    query = db.session.query(cls.id, cls.nom)
    query = query.filter(cls.nom.like("%" + q + "%"))
    all = query.all()

    result = {'results': [ { 'id': r[0], 'text': r[1]} for r in all ] }
    return jsonify(result)

  @expose("/<int:entity_id>")
  @templated("crm/single_view.html")
  def entity_view(self, entity_id):
    entity = self.managed_class.query.get(entity_id)
    if entity is None:
      abort(404)

    bc = self.bread_crumbs(entity._name)
    add_to_recent_items(entity)

    rendered_entity = self.single_view.render(entity)
    related_views = self.render_related_views(entity)

    audit_entries = audit_service.entries_for(entity)

    return dict(rendered_entity=rendered_entity,
                related_views=related_views,
                audit_entries=audit_entries,
                breadcrumbs=bc,
                module=self)

  @expose("/<int:entity_id>/edit")
  @templated("crm/single_view.html")
  def entity_edit(self, entity_id):
    entity = self.managed_class.query.get(entity_id)
    assert entity is not None
    bc = self.bread_crumbs(entity._name)
    add_to_recent_items(entity)

    form = self.edit_form_class(obj=entity)
    rendered_entity = self.single_view.render_form(form)

    return dict(rendered_entity=rendered_entity,
                breadcrumbs=bc,
                module=self)

  @expose("/<int:entity_id>/edit", methods=['POST'])
  def entity_edit_post(self, entity_id):
    entity = self.managed_class.query.get(entity_id)
    assert entity is not None
    form = self.edit_form_class(obj=entity)

    if request.form.get('_action') == 'cancel':
      return redirect("%s/%d" % (self.url, entity_id))
    elif form.validate():
      form.populate_obj(entity)
      activity.send(self, actor=g.user, verb="update", object=entity)
      try:
        db.session.commit()
        flash("Entity successfully edited", "success")
        return redirect("%s/%d" % (self.url, entity_id))
      except ValidationError, e:
        db.session.rollback()
        flash(e.message, "error")
      except IntegrityError, e:
        sentry = current_app.extensions.get('sentry')
        if sentry:
          sentry.captureException()
        db.session.rollback()
        flash("An entity with this name already exists in the database.", "error")
    else:
      flash("Please fix the error(s) below", "error")

    # All unhappy path should end here
    rendered_entity = self.single_view.render_form(form)
    bc = self.bread_crumbs(entity._name)
    return render_template('crm/single_view.html',
                           rendered_entity=rendered_entity,
                           breadcrumbs=bc,
                           module=self)

  @expose("/new")
  @templated("crm/single_view.html")
  def entity_new(self):
    bc = self.bread_crumbs("New %s" % self.managed_class.__name__)

    form = self.edit_form_class()
    rendered_entity = self.single_view.render_form(form, for_new=True)

    return dict(rendered_entity=rendered_entity,
                breadcrumbs=bc,
                module=self)

  @expose("/new", methods=['PUT', 'POST'])
  def entity_new_put(self):
    form = self.edit_form_class()
    entity = self.managed_class()

    if request.form.get('_action') == 'cancel':
      return redirect("%s/" % self.url)

    if form.validate():
      form.populate_obj(entity)
      db.session.add(entity)
      try:
        db.session.flush()
        activity.send(self, actor=g.user, verb="post", object=entity)
        db.session.commit()
        flash("Entity successfully added", "success")
        return redirect("%s/%d" % (self.url, entity.id))
      except ValidationError, e:
        db.session.rollback()
        flash(e.message, "error")
      except IntegrityError, e:
        db.session.rollback()
        flash("An entity with this name already exists in the database", "error")
    else:
      flash("Please fix the error(s) below", "error")

    # All unhappy paths should here here
    rendered_entity = self.single_view.render_form(form, for_new=True)
    bc = self.bread_crumbs("New %s" % self.managed_class.__name__)
    return render_template('crm/single_view.html',
                           rendered_entity=rendered_entity,
                           breadcrumbs=bc,
                           module=self)

  @expose("/<int:entity_id>/delete", methods=['POST'])
  def entity_delete(self, entity_id):
    # TODO: don't really delete, switch state to "deleted"
    entity = self.managed_class.query.get(entity_id)
    assert entity is not None
    db.session.delete(entity)
    activity.send(self, actor=g.user, verb="delete", object=entity)
    db.session.commit()
    flash("Entity deleted", "success")
    return redirect(self.url)

  #
  # Utils
  #
  def is_current(self):
    return request.path.startswith(self.url)

  def bread_crumbs(self, label=None):
    bc = BreadCrumbs([("/", "Home"), ("/crm/", "CRM")])
    if label:
      bc.add("/crm/%s/" % self.endpoint, self.label)
      bc.add("", label)
    else:
      bc.add("", self.label)
    return bc

  def render_related_views(self, entity):
    rendered = []
    for t in self.related_views:
      label, attr_name, column_names = t[0:3]
      if len(t) == 4:
        options = t[3]
      else:
        options = {}
      view = RelatedTableView(column_names, options)
      related_entities = getattr(entity, attr_name)
      obj = dict(label=label,
                 rendered=view.render(related_entities),
                 size=len(related_entities))
      rendered.append(obj)
    return rendered

  @staticmethod
  def _prettify_name(name):
    """
    Prettify class name by splitting name by capital characters.
    So, 'MySuperClass' will look like 'My Super Class'

    `name`
      String to prettify
    """
    return re.sub(r'(?<=.)([A-Z])', r' \1', name)


# TODO: rename to CRMApp ?
class CRUDApp(object):
  def __init__(self, app, modules=None):
    if modules:
      self.modules = modules
    self.app = app

    for module in self.modules:
      self.add_module(module)

  def add_module(self, module):
    self.app.register_blueprint(module.create_blueprint(self))

  @property
  def breadcrumbs(self):
    return [dict(path='/', label='Home')]
