import copy
import re

from flask import session, redirect, request, g, render_template, flash,\
  Blueprint

from yaka.web.decorators import templated
from yaka.core.extensions import db


#
# Helper classes
#
from yaka.web.widgets import Panel, Row, SingleView, TableView


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
  if len(l) > 10:
    del l[10:]
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
  return SingleView(*panels)


class ModuleMeta(type):
  """
      Module metaclass.

      Does some precalculations (like getting list of view methods from the class) to avoid
      calculating them for each view class instance.
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

  def create_blueprint(self, crud_app):
    """
        Create Flask blueprint.
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

  #
  # Exposed views
  #
  @expose("/")
  @templated("crm/list_view.html")
  def list_view(self):
    bc = self.bread_crumbs()

    entities = self.get_entities()

    table_view = TableView(self.list_view_columns, show_controls=True)
    rendered_table = table_view.render(entities)

    return dict(rendered_table=rendered_table, breadcrumbs=bc, module=self)

  @expose("/<int:entity_id>")
  @templated("crm/single_view.html")
  def entity_view(self, entity_id):
    entity = self.managed_class.query.get(entity_id)
    assert entity is not None
    bc = self.bread_crumbs(entity._name)
    add_to_recent_items(entity)

    rendered_entity = self.single_view.render(entity)
    related_views = self.render_related_views(entity)

    audit_entries = self.app.extensions['audit'].entries_for(entity)

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
      flash("Entity successfully edited", "success")
      form.populate_obj(entity)
      db.session.commit()
      return redirect("%s/%d" % (self.url, entity_id))
    else:
      flash("Please fix the error below", "error")
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
    elif form.validate():
      flash("Entity successfully added", "success")
      form.populate_obj(entity)
      db.session.add(entity)
      db.session.commit()
      return redirect("%s/%d" % (self.url, entity.id))
    else:
      flash("Error", "error")
      rendered_entity = self.single_view.render_form(form, for_new=True)
      bc = self.bread_crumbs("New %s" % self.managed_class.__name__)
      return render_template('crm/single_view.html',
                             rendered_entity=rendered_entity,
                             breadcrumbs=bc,
                             module=self)

  @expose("/<int:entity_id>/delete")
  def entity_delete(self, entity_id):
    # TODO: don't really delete, switch state to "deleted"
    entity = self.managed_class.query.get(entity_id)
    assert entity is not None
    db.session.delete(entity)
    db.session.commit()
    flash("Entity deleted", "success")
    return redirect(self.url)

  #
  # Override in subclasses
  #
  def get_entities(self):
    return self.managed_class.query.all()

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
    for label, attr_name, column_names in self.related_views:
      view = TableView(column_names)
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


class CRUDApp(object):
  def __init__(self, app, modules=None):
    if modules:
      self.modules = modules
    self.app = app

    for module in self.modules:
      self.add_module(module)

  def add_module(self, module):
    self.app.register_blueprint(module.create_blueprint(self))
    #self._add_view_to_menu(view)

  @property
  def breadcrumbs(self):
    return [dict(path='/', label='Home')]
