# coding=utf-8
"""
Front-end for a CRM app.

This should eventually allow implementing very custom CRM-style application.
"""
import logging
import copy
import re
from collections import OrderedDict

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql.expression import asc, desc, nullsfirst, nullslast
from sqlalchemy import orm
from werkzeug.exceptions import BadRequest

from flask import (session, redirect, request, g,
                   Blueprint, jsonify, url_for,
                   current_app, render_template)

from abilian.i18n import _l
from abilian.core.extensions import db
from abilian.core.entities import Entity
from abilian.services import audit_service
from .action import actions, Action, FAIcon

from . import search
from .nav import BreadcrumbItem, Endpoint
from .views import (
    default_view, ObjectView, ObjectEdit, ObjectCreate,
    ObjectDelete, JSONView, JSONWhooshSearch,
)
from .forms.widgets import (
  Panel, Row, SingleView, RelatedTableView, AjaxMainTableView,
)

logger = logging.getLogger(__name__)


class ModuleAction(Action):
  """
  Base action class for :class:`Module` actions.

  Basic condition is simple: :attr:`category` must match the string
  `'module:{module.endpoint}'`
  """
  def __init__(self, module, group, name, *args, **kwargs):
    self.group = group
    super(ModuleAction, self).__init__(module.action_category, name,
                                       *args, **kwargs)

  def pre_condition(self, context):
    module = actions.context.get('module')
    if not module:
      return False

    return self.category == module.action_category


def add_to_recent_items(entity, type='ignored'):
  if not isinstance(entity, Entity):
    return
  object_type = entity.object_type
  url = current_app.default_view.url_for(entity)
  if not hasattr(g, 'recent_items'):
    g.recent_items = []
  g.recent_items.insert(0, dict(type=object_type, name=entity.name, url=url))
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
  for gr in form._groups.items():
    panel = Panel(gr[0], *[Row(x) for x in gr[1]])
    panels.append(panel)
  return SingleView(form, *panels, **options)


class BaseEntityView(object):
  module = None
  pk = 'entity_id'

  def __init__(self, module, *args, **kwargs):
    self.module = module
    super(BaseEntityView, self).__init__(*args, **kwargs)

  def breadcrumb(self):
    return BreadcrumbItem(label=self.obj.name or self.obj.id,
                          url=Endpoint('.entity_view', entity_id=self.obj.id))

  def prepare_args(self, args, kwargs):
    args, kwargs = super(BaseEntityView, self).prepare_args(args, kwargs)
    actions.context['module'] = self.module
    add_to_recent_items(self.obj)
    return args, kwargs

  def redirect_to_index(self):
    return redirect(self.module.url)

  @property
  def single_view(self):
    return make_single_view(self.form,
                            view_template=self.module.view_template,
                            **self.module.view_options)


class EntityView(BaseEntityView, ObjectView):
  template = 'default/single_view.html'

  @property
  def template_kwargs(self):
    module = self.module
    rendered_entity = self.single_view.render(self.obj, self.form)
    related_views = [v.render(self.obj) for v in module.related_views]
    audit_entries = audit_service.entries_for(self.obj)

    return dict(rendered_entity=rendered_entity,
                related_views=related_views,
                audit_entries=audit_entries,
                module=self.module)


class EntityEdit(BaseEntityView, ObjectEdit):
  template = 'default/single_view.html'

  @property
  def template_kwargs(self):
    rendered_entity = self.single_view.render_form(self.form)
    return dict(rendered_entity=rendered_entity,
                module=self.module)


class EntityCreate(BaseEntityView, ObjectCreate):
  template = 'default/single_view.html'

  prepare_args = ObjectCreate.prepare_args
  breadcrumb = ObjectCreate.breadcrumb

  @property
  def template_kwargs(self):
    rendered_entity = self.single_view.render_form(self.form)
    return dict(rendered_entity=rendered_entity,
                for_new=True,
                module=self.module)


class EntityDelete(BaseEntityView, ObjectDelete):
  pass


class ListJson(JSONView):
  """
  JSON endpoint, for AJAX-backed table views.
  """
  def __init__(self, module, *args, **kwargs):
    JSONView.__init__(self, *args, **kwargs)
    self.module = module

  def data(self, *args, **kwargs):
    echo = int(kwargs.get("sEcho", 0))
    length = int(kwargs.get("iDisplayLength", 10))
    start = int(kwargs.get("iDisplayStart", 0))
    end = start + length

    total_count = self.module.managed_class.query.count()
    q = self.module.query(request)
    count = q.count()
    q = self.module.ordered_query(request, q)

    entities = q.slice(start, end).all()
    table_view = AjaxMainTableView(
        columns=self.module.list_view_columns,
        name=self.module.managed_class.__name__.lower(),
        ajax_source=url_for('.list_json'))

    data = [table_view.render_line(e) for e in entities]
    result = {
        "sEcho": echo,
        "iTotalRecords": total_count,
        "iTotalDisplayRecords": count,
        "aaData": data,
    }
    return result


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

  # class based views. If not provided will be automaticaly created from
  # EntityView etc defined above
  base_template = 'base.html'
  view_cls = EntityView
  edit_cls = EntityEdit
  create_cls = EntityCreate
  delete_cls = EntityDelete
  json_search_cls = JSONWhooshSearch

  # form_class. Used when view_cls/edit_cls are not provided
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
  tableview_options = {}  # used mostly to change datatable search_label
  _urls = []

  def __init__(self):
    # If endpoint name is not provided, get it from the class name
    if self.endpoint is None:
      self.endpoint = self.__class__.__name__.lower()

    if self.label is None:
      self.label = labelize(self.endpoint)

    if self.id is None:
      self.id = self.managed_class.__name__.lower()

    # If name is not provided, use capitalized endpoint name
    if self.name is None:
      self.name = self._prettify_name(self.__class__.__name__)

    if self.view_options is None:
      self.view_options = {}

    # self.single_view = make_single_view(self.edit_form_class,
    #                                     view_template=self.view_template,
    #                                     **self.view_options)
    if self.view_form_class is None:
      self.view_form_class = self.edit_form_class

    # init class based views
    kw = dict(Model=self.managed_class,
              pk='entity_id',
              module=self,
              base_template=self.base_template)
    self._setup_view("/<int:entity_id>",
                     'entity_view',
                     self.view_cls,
                     Form=self.view_form_class,
                     **kw)
    view_endpoint = self.endpoint + '.entity_view'

    self._setup_view("/<int:entity_id>/edit",
                     'entity_edit',
                     self.edit_cls,
                     Form=self.edit_form_class,
                     view_endpoint=view_endpoint,
                     **kw)

    self._setup_view("/new",
                     'entity_new',
                     self.create_cls,
                     Form=self.edit_form_class,
                     chain_create_allowed=self.view_new_save_and_add,
                     view_endpoint=view_endpoint,
                     **kw)

    self._setup_view("/<int:entity_id>/delete",
                     'entity_delete',
                     self.delete_cls,
                     Form=self.edit_form_class,
                     **kw)

    self._setup_view("/json", 'list_json', ListJson, module=self)

    self._setup_view('/json_search', 'json_search', self.json_search_cls,
                     Model=self.managed_class)

    self.init_related_views()

    # copy criterions instances; without that they may be shared by subclasses
    self.search_criterions = tuple((copy.deepcopy(c)
                                    for c in self.search_criterions))
    for sc in self.search_criterions:
      sc.model = self.managed_class

  def _setup_view(self, url, attr, cls, *args, **kwargs):
    """
    Register class based views
    """
    view = cls.as_view(attr, *args, **kwargs)
    setattr(self, attr, view)
    self._urls.append((url, attr, view.methods))

  def init_related_views(self):
    related_views = []
    for view in self.related_views:
      if not isinstance(view, RelatedView):
        view = DefaultRelatedView(*view)
      related_views.append(view)
    self.related_views = related_views

  @property
  def action_category(self):
    return u'module:{}'.format(self.endpoint)

  def get_grouped_actions(self):
    items = actions.for_category(self.action_category)
    groups = OrderedDict()
    for action in items:
      groups.setdefault(action.group, []).append(action)

    return groups

  def register_actions(self):
    ACTIONS = [
      ModuleAction(self, u'entity', u'create',
                   title=_l(u'Create New'), icon=FAIcon('plus'),
                   endpoint=Endpoint(self.endpoint + '.entity_new'),
                   button='default',),
    ]
    actions.register(*ACTIONS)

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

    # Create blueprint and register rules
    self.blueprint = Blueprint(self.endpoint, __name__,
                               url_prefix=self.url)

    for url, name, methods in self._urls:
      self.blueprint.add_url_rule(url,
                                  name,
                                  getattr(self, name),
                                  methods=methods)

    # run default_view decorator
    default_view(self.blueprint,
                 self.managed_class,
                 id_attr='entity_id')(self.entity_view)

    # delay registration of our breadcrumbs to when registered on app; thus
    # 'parents' blueprint can register theirs befores ours
    self.blueprint.record_once(self._setup_breadcrumb_preprocessors)

    return self.blueprint

  def _setup_breadcrumb_preprocessors(self, state):
    self.blueprint.url_value_preprocessor(self._add_breadcrumb)

  def _add_breadcrumb(self, endpoint, values):
    g.breadcrumb.append(BreadcrumbItem(label=self.name,
                        url=Endpoint('.list_view')))

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
  def list_view(self):
    actions.context['module'] = self
    table_view = AjaxMainTableView(
      name=self.managed_class.__name__.lower(),
      columns=self.list_view_columns,
      ajax_source=url_for('.list_json'),
      search_criterions=self.search_criterions,
      options=self.tableview_options)
    rendered_table = table_view.render()

    ctx = dict(rendered_table=rendered_table,
               module=self,
               base_template=self.base_template
               )
    return render_template("default/list_view.html", **ctx)

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
      raise BadRequest()

    query = db.session.query(cls.id, cls.name)
    query = query.filter(cls.name.ilike("%" + q + "%"))\
                 .distinct()\
                 .order_by(cls.name)\
                 .limit(50)
    all = query.all()

    result = {'results': [ { 'id': r[0], 'text': r[1]} for r in all ] }
    return jsonify(result)

  #
  # Utils
  #
  def is_current(self):
    return request.path.startswith(self.url)

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
    self.app.register_blueprint(self.create_blueprint(module))
    module.register_actions()

  def create_blueprint(self, module):
    return module.create_blueprint(self)
