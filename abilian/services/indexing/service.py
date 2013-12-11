"""
Indexing service for Abilian.

Adds Whoosh indexing capabilities to SQLAlchemy models.

Based on Flask-whooshalchemy by Karl Gyllstrom.

:copyright: (c) 2012 by Stefane Fermigier
:copyright: (c) 2012 by Karl Gyllstrom
:license: BSD (see LICENSE.txt)
"""
import os
from shutil import rmtree

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm.session import Session

import whoosh.index
from whoosh import sorting
from whoosh.writing import AsyncWriter
from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer, CharsetFilter
import whoosh.query as wq
from whoosh import sorting
from whoosh.support.charset import accent_map

from flask import (
    current_app,
    _app_ctx_stack, appcontext_pushed,
)
from flask.globals import _lookup_app_object

from abilian.services import Service, ServiceState
from abilian.core.util import fqcn
from abilian.core.entities import all_entity_classes
from abilian.core.extensions import celery, db

from .adapter import SchemaAdapter, SAAdapter
from .schema import DefaultSearchSchema

_TEXT_ANALYZER = StemmingAnalyzer() | CharsetFilter(accent_map)

_pending_indexation_attr = 'abilian_pending_indexation'

class IndexServiceState(ServiceState):
  whoosh_base = None
  indexes = None
  indexed_classes = None

  def __init__(self, *args, **kwargs):
    ServiceState.__init__(self, *args, **kwargs)
    self.indexes = {}
    self.indexed_classes = set()

  @property
  def to_update(self):
    return _lookup_app_object(_pending_indexation_attr)

  @to_update.setter
  def to_update(self, value):
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError('working outside of application context')

    setattr(top, _pending_indexation_attr, value)


class WhooshIndexService(Service):
  name = 'indexing'
  AppStateClass = IndexServiceState

  _listening = False

  def __init__(self, *args, **kwargs):
    Service.__init__(self, *args, **kwargs)
    self.adapters_cls = [SAAdapter]
    self.adapted = {}
    self.schemas = { 'default': DefaultSearchSchema() }

  def init_app(self, app):
    Service.init_app(self, app)
    state = app.extensions[self.name]

    whoosh_base = app.config.get("WHOOSH_BASE")
    if not whoosh_base:
      whoosh_base = "whoosh"  # Default value

    if not os.path.isabs(whoosh_base):
      whoosh_base = os.path.join(app.instance_path, whoosh_base)

    state.whoosh_base = os.path.abspath(whoosh_base)

    if not self._listening:
      event.listen(Session, "after_flush", self.after_flush)
      event.listen(Session, "after_commit", self.after_commit)
      self._listening = True

    appcontext_pushed.connect(self.clear_update_queue, app)

  def clear_update_queue(self, app=None):
    self.app_state.to_update = []

  def start(self):
    Service.start(self)
    self.register_classes()
    self.init_indexes()
    self.clear_update_queue()

  def init_indexes(self):
    """
    Create indexes for schemas.
    """
    state = self.app_state

    for name, schema in self.schemas.iteritems():
      index_path = os.path.join(state.whoosh_base, name)

      if whoosh.index.exists_in(index_path):
        index = whoosh.index.open_dir(index_path)
      else:
        if not os.path.exists(index_path):
          os.makedirs(index_path)
        index = whoosh.index.create_in(index_path, schema)

      state.indexes[name] = index

  def clear(self):
    current_app.logger.info("Resetting indexes")
    assert not self.running

    state = self.app_state

    for cls in state.indexed_classes:
      index_path = os.path.join(state.whoosh_base, cls.__name__)
      try:
        rmtree(index_path)
      except OSError:
        pass

    state.indexes = {}
    state.indexed_classes = set()
    self.clear_update_queue()

  def search(self, q, index='default', Models=(), get_models=False, **search_args):
    """
    Interface to search indexes.

    :param q: unparsed search string.
    :param index: name of index to use for search.
    :param Models: list of Model classes to limit search on.
    :param limit: maximum number of results.
    :param search_args: any valid parameter for
        :meth:`whoosh.searching.Search.search`.
    """
    index = self.app_state.indexes[index]
    fields = set(index.schema.names()) - set(['id'])
    if Models:
      fields.discard('object_type')

    parser = MultifieldParser(list(fields), index.schema)
    query = parser.parse(q)

    if Models:
      # limit object_type
      filtered_models = []
      for m in Models:
        object_type = m.object_type
        if not object_type:
          continue
        filtered_models.append(wq.Term('object_type', object_type))

      if filtered_models:
        filtered_models = (wq.Or(*filtered_models)
                           if len(filtered_models) > 1
                           else filtered_models[0])
        query = wq.And(query, filtered_models)

    with index.searcher(closereader=False) as searcher:
      # 'closereader' is needed, else results cannot by used outside 'with'
      # statement
      results = searcher.search(query, **search_args)

      if get_models:
        # FIXME: get_models is not a good idea in the general case (inefficient,
        # potentially many results), search results should be self-sufficients
        res = []
        for r in results:
          adapter = self.adapted.get(r['object_type'])
          if adapter:
            r.model = adapter.retrieve(r['id'])
            res.append(r)
        results = res

    return results

  def search_for_class(self, query, cls, index='default', **search_args):
    return self.search(query, Models=(cls,), index=index, **search_args)

  def register_classes(self):
    state = self.app_state
    for cls in all_entity_classes():
      if not cls in state.indexed_classes:
        self.register_class(cls, app_state=state)

  def register_class(self, cls, app_state=None):
    """
    Registers a model class
    """
    state = app_state if app_state is not None else self.app_state

    for Adapter in self.adapters_cls:
      if Adapter.can_adapt(cls):
        break
    else:
      return

    self.adapted[fqcn(cls)] = Adapter(cls, self.schemas['default'])
    state.indexed_classes.add(cls)

  def after_flush(self, session, flush_context):
    if not self.running or session is not db.session():
      return

    to_update = self.app_state.to_update
    session_objs = (
      ('new', session.new),
      ('deleted', session.deleted),
      ('changed', session.dirty),
    )
    for key, objs in session_objs:
      for obj in objs:
        model_name = fqcn(obj.__class__)
        adapter = self.adapted.get(model_name)

        if adapter is None or not adapter.indexable:
          continue

        to_update.append((key, obj))

  def after_commit(self, session):
    """
    Any db updates go through here. We check if any of these models have
    ``__searchable__`` fields, indicating they need to be indexed. With these
    we update the whoosh index for the model. If no index exists, it will be
    created here; this could impose a penalty on the initial commit of a model.
    """
    if not self.running or session is not db.session():
      return

    primary_field = 'id'
    state = self.app_state
    items = []
    for op, obj in state.to_update:
      model_name = fqcn(obj.__class__)
      if model_name not in self.adapted or not self.adapted[model_name].indexable:
        # safeguard
        continue

      if sa.orm.object_session(obj) is not None: # safeguard against DetachedInstanceError
        items.append((op, model_name, getattr(obj, primary_field), {}))

    index_update.apply_async(kwargs=dict(index='default', items=items))
    self.clear_update_queue()

  def index_objects(self, objects):
    """
    Bulk index a list of objets, that must be not indexed yet, and all of the
    same class.
    """
    if not objects:
      return

    model_class = objects[0].__class__
    assert all(m.__class__ is model_class for m in objects),\
      "All objects must be of the same class."

    index = self.index_for_model_class(model_class)
    with index.writer() as writer:
      primary_field = model_class.search_query.primary
      indexed_fields = model_class.whoosh_schema.names()

      for model in objects:
        document = self.make_document(model, indexed_fields, primary_field)
        writer.add_document(**document)

  def make_document(self, model, indexed_fields, primary_field):
    attrs = {}
    for key in indexed_fields:
      value = getattr(model, key)
      if hasattr(value, '_name'):
        value = value._name
      elif isinstance(value, (str, int, db.Model)):
        value = unicode(value)

      attrs[key] = value
    attrs[primary_field] = unicode(getattr(model, primary_field))
    return attrs


class Searcher(object):
  """
  Assigned to a Model class as ``search_query``, which enables text-querying.
  """

  def __init__(self, model_class, primary, index):
    self.model_class = model_class
    self.primary = primary
    self.index = index
    self.searcher = index.searcher()
    fields = set(index.schema._fields.keys()) - set([self.primary])
    self.parser = MultifieldParser(list(fields), schema=index.schema)

  def search(self, query, limit=None, get_models=False):
    """
    Returns a standard Whoosh search query result set. Optionally, if
    `get_models` is True, will add the original SQLA models to the Whoosh
    records, using only one SQL query.
    """

    hits = self.index.searcher().search(self.parser.parse(query), limit=limit)

    if not get_models:
      return hits

    ids = [ hit[self.primary] for hit in hits ]

    if not ids:
      # don't query with empty 'in_(ids)'
      return []

    primary_column = getattr(self.model_class, self.primary)
    session = self.model_class.query.session
    query = session.query(self.model_class)

    # Don't remove. Loads all the models at once in session identity map, so one
    # can perform a `get` later on the session without issuing a query.
    models = query.filter(primary_column.in_(ids)).all()

    hits_with_models = []
    for hit in hits:
      pk = hit[self.primary]
      try:
        # session identity lookup needs exact type, else DB is issued
        pk = int(pk)
      except:
        pass
      model = query.get(pk)
      if model:
        hit.model = model
        hits_with_models.append(hit)

    return hits_with_models

service = WhooshIndexService()


@celery.task(ignore_result=True)
def index_update(index, items):
  """
  :param:index: index name
  :param:items: list of (operation, model key, primary key, data) tuples.
  """
  index_name = index
  index = service.app_state.indexes[index_name]
  adapted = service.adapted
  # indexed_fields = index.schema.names()

  primary_field = 'id'
  session = Session(bind=db.session.get_bind(None, None), autocommit=True)

  with AsyncWriter(index) as writer:
    for op, cls_name, pk, data in items:
      if pk is None:
        continue
      # delete everything. stuff that's updated or inserted will get
      # added as a new doc. Could probably replace this with a whoosh
      # update.
      writer.delete_by_term(primary_field, pk)

      adapter = adapted.get(cls_name)
      if not adapter:
        # FIXME: log to sentry?
        continue

      if op in ("new", "changed"):
        with session.begin():
          obj = adapter.retrieve(pk, _session=session, **data)

        if obj is None:
          # deleted after task queued, but before task run
          continue

        # # Hack: Load lazy fields
        # # This prevents a transaction error in get_document
        # # FIXME: really required?
        # for key in indexed_fields:
        #   getattr(obj, key, None)

        document = adapter.get_document(obj)
        writer.add_document(**document)

  session.close()
