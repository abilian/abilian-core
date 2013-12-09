# coding=utf-8

"""
Front-end for a CRM app.

This should eventually allow implementing very custom CRM-style application.
"""
import StringIO
import logging
import copy
import csv
from datetime import date
from time import strftime, gmtime
import re

from flask import (session, redirect, request, g, render_template, flash,
                   Blueprint, jsonify, abort, make_response, url_for)
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql.expression import asc, desc, nullsfirst, nullslast
from sqlalchemy.exc import IntegrityError
from sqlalchemy import orm
from xlwt import Workbook, XFStyle

from flask.ext.babel import gettext as _

from abilian.core.entities import ValidationError, Entity
from abilian.core.signals import activity
from abilian.core.extensions import db
from abilian.services import audit_service

from . import search
from .decorators import templated
from .forms.fields import ModelFieldList
from .forms.widgets import Panel, Row, SingleView, RelatedTableView,\
  AjaxMainTableView

logger = logging.getLogger(__name__)


def add_to_recent_items(entity, type=None):
  if not type:
    type = entity.__class__.__name__.lower()
  if not hasattr(g, 'recent_items'):
    g.recent_items = []
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


def make_single_view(form, **options):
  panels = []
  for g in form._groups:
    panel = Panel(g[0], *[ Row(x) for x in g[1] ])
    panels.append(panel)
  return SingleView(form, *panels, **options)


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
  view_form_class = None  # by default, same as edit_form_class
  url = None
  name = None
  view_new_save_and_add = False  # show 'save and add new' button in /new form
  static_folder = None
  view_template = None
  view_options = None
  related_views = []
  blueprint = None
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

    view_options = self.view_options if self.view_options is not None else {}
    self.single_view = make_single_view(self.edit_form_class,
                                        view_template=self.view_template,
                                        **view_options)
    if self.view_form_class is None:
      self.view_form_class = self.edit_form_class

    self.init_related_views()

    # copy criterions instances; without that they may be shared by subclasses
    self.search_criterions = tuple((copy.deepcopy(c)
                                    for c in self.search_criterions))
    for sc in self.search_criterions:
      sc.model = self.managed_class

  def init_related_views(self):
    related_views = []
    for view in self.related_views:
      if not isinstance(view, RelatedView):
        view = DefaultRelatedView(*view)
      related_views.append(view)
    self.related_views = related_views

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
    table_view = AjaxMainTableView(
      name=self.managed_class.__name__.lower(),
      columns=self.list_view_columns,
      ajax_source=url_for('.list_json'),
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
                                   name=self.managed_class.__name__.lower(),
                                   ajax_source=url_for('.list_json'))

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

    DATE_STYLE = XFStyle()
    DATE_STYLE.num_format_str = "DD/MM/YYYY"

    col_names = ['id']
    for field in form:
      if isinstance(field, ModelFieldList):
        continue
      if hasattr(self.managed_class, field.name):
        col_names.append(field.name)

    for c, col_name in enumerate(col_names):
      ws.write(0, c, col_name)

    for r, obj in enumerate(objects):
      for c, col_name in enumerate(col_names):
        style = None
        value = obj.display_value(col_name)

        if isinstance(value, Entity):
          value = value._name
        elif isinstance(value, list):
          if all(isinstance(x, basestring) for x in value):
            value = "; ".join(value)
          elif all(isinstance(x, Entity) for x in value):
            value = "; ".join([x._name for x in value])
          else:
            raise Exception("I don't know how to export column {}".format(col_name))
        elif isinstance(value, date):
          style = DATE_STYLE
        if style:
          ws.write(r + 1, c, value, style)
        else:
          ws.write(r + 1, c, value)

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
          value = object.display_value(field.name)
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

    rendered_entity = self.render_entity_view(entity)
    related_views = [v.render(entity) for v in self.related_views]
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
      try:
        db.session.flush()
        activity.send(self, actor=g.user, verb="update", object=entity)
        db.session.commit()
        flash(_(u"Entity successfully edited"), "success")
        return redirect("%s/%d" % (self.url, entity_id))
      except ValidationError, e:
        db.session.rollback()
        flash(e.message, "error")
      except IntegrityError, e:
        db.session.rollback()
        logger.error(e)
        flash(_(u"An entity with this name already exists in the database."),
              "error")
    else:
      flash(_(u"Please fix the error(s) below"), "error")

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
    rendered_entity = self.single_view.render_form(
      form,
      for_new=True,
      has_save_and_add_new=self.view_new_save_and_add,)

    return dict(rendered_entity=rendered_entity,
                breadcrumbs=bc,
                module=self)

  @expose("/new", methods=['PUT', 'POST'])
  def entity_new_put(self):
    form = self.edit_form_class()
    entity = self.managed_class()
    action = request.form.get('_action')

    if action == 'cancel':  # FIXME: what if action is None?
      return redirect("%s/" % self.url)

    if form.validate():
      form.populate_obj(entity)
      db.session.add(entity)
      try:
        db.session.flush()
        activity.send(self, actor=g.user, verb="post", object=entity)
        db.session.commit()
      except ValidationError, e:
        db.session.rollback()
        flash(e.message, "error")
      except IntegrityError, e:
        db.session.rollback()
        flash(_(u"An entity with this name already exists in the database"),
              "error")
      else:
        flash(_(u"Entity successfully added"), "success")
        if self.view_new_save_and_add and action == 'save_and_add_new':
          return redirect(url_for('.entity_new'))
        return redirect(url_for('.entity_view', entity_id=entity.id))

    else:
      flash(_(u"Please fix the error(s) below"), "error")

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
    flash(_(u"Entity deleted"), "success")
    return redirect(self.url)

  #
  # Utils
  #
  def is_current(self):
    return request.path.startswith(self.url)

  # FIXME: breadcrumb is handled with g.breadcrumbs, which is a list of
  # abilian.web.nav.BreadCrumbItem instances
  #
  # def bread_crumbs(self, label=None):
  #   bc = BreadCrumbs([("/", "Home"), ("/crm/", "CRM")])
  #   if label:
  #     bc.add("/crm/%s/" % self.endpoint, self.label)
  #     bc.add("", label)
  #   else:
  #     bc.add("", self.label)
  #   return bc

  def render_entity_view(self, entity):
    form = self.view_form_class(obj=entity)
    return self.single_view.render(entity, form)

  @staticmethod
  def _prettify_name(name):
    """
    Prettify class name by splitting name by capital characters.
    So, 'MySuperClass' will look like 'My Super Class'

    `name`
      String to prettify
    """
    return re.sub(r'(?<=.)([A-Z])', r' \1', name)


class RelatedView(object):
  """ A base class for related views
  """
  def render(self, entity):
    """ Return a dict with keys 'label', 'attr_name', 'rendered', 'size'
    """
    raise NotImplementedError


class DefaultRelatedView(RelatedView):
  """ Default view used by Module for items directly related to entity
  """

  def __init__(self, label, attr, column_names, options=None):
    self.label = label
    self.attr = attr
    self.column_names = column_names
    self.options = {}
    if options is not None:
      self.options.update(options)

  def render(self, entity):
    view = RelatedTableView(self.column_names, self.options)
    related_entities = getattr(entity, self.attr)
    return dict(label=self.label,
                attr_name=self.attr,
                rendered=view.render(related_entities, related_to=entity),
                size=len(related_entities))


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
