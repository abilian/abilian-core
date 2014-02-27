"""
Indexing service for Abilian.

Adds Whoosh indexing capabilities to SQLAlchemy models.

Based on Flask-whooshalchemy by Karl Gyllstrom.

:copyright: (c) 2012 by Stefane Fermigier
:copyright: (c) 2012 by Karl Gyllstrom
:license: BSD (see LICENSE.txt)
"""
import os
import logging
from inspect import isclass

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm.session import Session

import whoosh.index
from whoosh.filedb.filestore import RamStorage, FileStorage
from whoosh.writing import AsyncWriter, CLEAR
from whoosh.qparser import DisMaxParser
from whoosh.analysis import StemmingAnalyzer, CharsetFilter
import whoosh.query as wq
from whoosh.support.charset import accent_map

from flask import (current_app, g,
    _app_ctx_stack, appcontext_pushed,
)
from flask.ext.login import current_user
from flask.globals import _lookup_app_object

from abilian.services import Service, ServiceState
from abilian.services.security import Role, Anonymous, Authenticated
from abilian.core.models.subjects import User, Group
from abilian.core.util import fqcn, friendly_fqcn
from abilian.core.entities import Indexable
from abilian.core.extensions import celery, db

from .adapter import SAAdapter
from .schema import DefaultSearchSchema, indexable_role

logger = logging.getLogger(__name__)
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
      if current_app.testing:
        storage = RamStorage()
      else:
        index_path = os.path.join(state.whoosh_base, name)
        if not os.path.exists(index_path):
          os.makedirs(index_path)
        storage = FileStorage(index_path)

      index = whoosh.index.FileIndex.create(storage, schema, name)
      state.indexes[name] = index

  def clear(self):
    logger.info('Resetting indexes')
    state = self.app_state

    for name, idx in state.indexes.iteritems():
      writer = AsyncWriter(idx)
      writer.commit(merge=True, optimize=True, mergetype=CLEAR)

    state.indexes = {}
    state.indexed_classes = set()
    self.clear_update_queue()

  def index(self, name='default'):
    return self.app_state.indexes[name]

  @property
  def default_search_fields(self):
    """
    Return default field names and boosts to be used for searching. Can be
    configured with `SEARCH_DEFAULT_BOOSTS`
    """
    config = current_app.config.get('SEARCH_DEFAULT_BOOSTS')
    if not config:
     config = dict(
         name=1.5,
         name_prefix=1.3,
         description=1.3,
         text=1.0,)
     return config

  def searchable_object_types(self):
    """
    List of (object_types, friendly name) present in the index.
    """
    try:
      idx = self.index()
    except KeyError:
      # index does not exists: service never started, may happens during tests
      return []

    with idx.reader() as r:
      indexed = sorted(set(r.field_terms('object_type')))

    return [(name, friendly_fqcn(name)) for name in indexed]

  def search(self, q, index='default', fields=None, Models=(),
             object_types=(), prefix=True, facet_by_type=None,
             **search_args):
    """
    Interface to search indexes.

    :param q: unparsed search string.
    :param index: name of index to use for search.
    :param fields: optionnal mapping of field names -> boost factor?
    :param Models: list of Model classes to limit search on.
    :param object_types: same as `Models`, but directly the model string.
    :param prefix: enable or disable search by prefix
    :param facet_by_type: if set, returns a dict of object_type: results with a
         max of `limit` matches for each type.
    :param search_args: any valid parameter for
        :meth:`whoosh.searching.Search.search`. This includes `limit`,
        `groupedby` and `sortedby`
    """
    index = self.app_state.indexes[index]
    if not fields:
      fields = self.default_search_fields

    valid_fields = set(f for f in index.schema.names(check_names=fields)
                       if prefix or not f.endswith('_prefix'))

    for invalid in set(fields) - valid_fields:
      del fields[invalid]

    parser = DisMaxParser(fields, index.schema)
    query = parser.parse(q)

    if not hasattr(g, 'is_manager') or not g.is_manager:
      # security access filter
      user = current_user
      roles = [indexable_role(user)]
      if not user.is_anonymous():
        roles.append(indexable_role(Anonymous))
        roles.append(indexable_role(Authenticated))
        roles.extend([indexable_role(group) for group in user.groups])

      filter_q = wq.Or([wq.Term('allowed_roles_and_users', role)
                        for role in roles])
      if 'filter' in search_args:
        filter_q = wq.And(search_args['filter'], filter_q)
      search_args['filter'] = filter_q

    object_types = set(object_types)
    for m in Models:
      object_type = m.object_type
      if not object_type:
        continue
      object_types.add(object_type)

    if object_types:
      # limit object_type
      filtered_models = wq.Or(wq.Term('object_type', t)
                              for t in object_types)
      filter_q = wq.And(search_args['filter'], filtered_models)

      if 'filter' in search_args:
        filter_q = wq.And(search_args['filter'], filter_q)
      search_args['filter'] = filter_q

    if facet_by_type:
      if not object_types:
        object_types = [t[0] for t in self.searchable_object_types()]

      # limit number of documents to score, per object type
      search_args['groupedby'] = 'object_type'
      search_args['collapse'] = 'object_type'
      search_args['collapse_limit'] = 5
      search_args['limit'] = search_args['collapse_limit'] * len(object_types)

    with index.searcher(closereader=False) as searcher:
      # 'closereader' is needed, else results cannot by used outside 'with'
      # statement
      results = searcher.search(query, **search_args)

      if facet_by_type:
        positions = { doc_id: pos
                      for pos, doc_id in enumerate(i[1] for i in results.top_n)}
        search_results = results
        results = {}
        for typename, doc_ids in search_results.groups('object_type').items():
          results[typename] = [search_results[positions[oid]] for oid in doc_ids]

      return results

  def search_for_class(self, query, cls, index='default', **search_args):
    return self.search(query, Models=(fqcn(cls),), index=index, **search_args)

  def register_classes(self):
    state = self.app_state
    classes = (cls for cls in db.Model._decl_class_registry.values()
               if isclass(cls) and issubclass(cls, Indexable))
    for cls in classes:
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
    if (not self.running
        or session.transaction.nested # inside a sub-transaction: not yet written in DB
        or session is not db.session()):
      # note: we have not tested too far if session is enclosed in a transaction
      # at connection level. For now it's not a standard use case, it would most
      # likely happens during tests (which don't do that for now)
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

    if items:
      index_update.apply_async(kwargs=dict(index='default', items=items))
    self.clear_update_queue()

  def get_document(self, obj, adapter=None):
    """
    """
    if adapter is None:
      class_name = fqcn(obj.__class__)
      adapter = self.adapted.get(class_name)

    if adapter is None or not adapter.indexable:
      return None

    document = adapter.get_document(obj)

    for k,v in document.items():
      if v is None:
        del document[k]
        continue
      if isinstance(v, (User, Group, Role)):
        document[k] = indexable_role(v)

    if not document.get('allowed_roles_and_users'):
      # no data for security: assume anybody can access the document
      document['allowed_roles_and_users'] = indexable_role(Anonymous)

    return document

  def index_objects(self, objects, index='default'):
    """
    Bulk index a list of objects.
    """
    if not objects:
      return

    index_name = index
    index = self.app_state.indexes[index_name]
    indexed = set()

    with index.writer() as writer:
      for obj in objects:
        document = self.get_document(obj)
        if document is None:
          continue

        object_key = document['object_key']
        if object_key in indexed:
          continue

        writer.delete_by_term('object_key', object_key)
        writer.add_document(**document)
        indexed.add(object_key)


service = WhooshIndexService()

@celery.task(ignore_result=True)
def index_update(index, items):
  """
  :param:index: index name
  :param:items: list of (operation, full class name, primary key, data) tuples.
  """
  index_name = index
  index = service.app_state.indexes[index_name]
  adapted = service.adapted

  session = Session(bind=db.session.get_bind(None, None), autocommit=True)

  if not getattr(session, '_model_changes', None):
    # Flask-Sqlalchemy up to 1.0 needs this
    setattr(session, '_model_changes', {})

  updated = set()
  with AsyncWriter(index) as writer:
    for op, cls_name, pk, data in items:
      if pk is None:
        continue

      # always delete. Whoosh manual says that 'update' is actually delete + add
      # operation
      object_key = u'{}:{}'.format(cls_name, pk)
      writer.delete_by_term('object_key', object_key)

      adapter = adapted.get(cls_name)
      if not adapter:
        # FIXME: log to sentry?
        continue

      if object_key in updated:
        # don't add twice the same document in same transaction. The writer will
        # not delete previous records, ending in duplicate records for same
        # document.
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

        document = service.get_document(obj, adapter)
        writer.add_document(**document)
        updated.add(object_key)

  session.close()
