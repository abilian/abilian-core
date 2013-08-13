"""
Indexing service for Abilian.

Adds Whoosh indexing capabilities to SQLAlchemy models.

Based on Flask-whooshalchemy by Karl Gyllstrom.

:copyright: (c) 2012 by Stefane Fermigier
:copyright: (c) 2012 by Karl Gyllstrom
:license: BSD (see LICENSE.txt)
"""

# TODO: not sure that one index per class is the way to go.
# TODO: speed issue
# TODO: this is a singleton. makes tests hard (for instance, launching parallel tests).
# TODO: make asynchonous.
import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm.session import Session

import whoosh.index
from whoosh import sorting
from whoosh.writing import AsyncWriter
from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer, CharsetFilter
from whoosh.fields import Schema
from whoosh.support.charset import accent_map

from abilian.core.entities import all_entity_classes
from abilian.core.extensions import celery, db

import os
from shutil import rmtree

_TEXT_ANALYZER = StemmingAnalyzer() | CharsetFilter(accent_map)

class WhooshIndexService(object):

  app = None
  to_update = None

  def __init__(self, app=None):
    self.indexes = {}
    self.indexed_classes = set()
    self.running = False
    self.listening = False
    self.to_update = {}
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    app.extensions['indexing'] = self
    app.services['indexing'] = self

    self.whoosh_base = app.config.get("WHOOSH_BASE")
    if not self.whoosh_base:
      self.whoosh_base = "data/whoosh"  # Default value

    if not os.path.isabs(self.whoosh_base):
      self.whoosh_base = os.path.join(app.instance_path, self.whoosh_base)

    self.whoosh_base = os.path.abspath(self.whoosh_base)

    if not self.listening:
      event.listen(Session, "after_flush", self.after_flush)
      event.listen(Session, "after_flush_postexec", self.after_flush_postexec)
      event.listen(Session, "after_commit", self.after_commit)
      self.listening = True

    app.before_request(self.clear_update_queue)

  def clear_update_queue(self):
    self.to_update = {}

  def start(self):
    assert self.app, "service not bound to an app"
    self.app.logger.info("Starting index service")
    self.running = True
    self.register_classes()
    self.to_update = {}

  def stop(self):
    self.app.logger.info("Stopping index service")
    self.running = False

  def clear(self):
    self.app.logger.info("Resetting indexes")
    assert not self.running

    for cls in self.indexed_classes:
      index_path = os.path.join(self.whoosh_base, cls.__name__)
      try:
        rmtree(index_path)
      except OSError:
        pass

    self.indexes = {}
    self.indexed_classes = set()
    self.clear_update_queue()

  def search(self, query, cls=None, limit=10, filter=None):
    if cls:
      return self.search_for_class(query, cls, limit, filter)

    else:
      res = []
      for indexed_class in self.indexed_classes:
        searcher = indexed_class.search_query
        res += searcher.search(query, limit)
      return res

  def search_for_class(self, query, cls, limit=50, filter=None):
    index = self.indexes[cls.__name__]
    searcher = index.searcher()
    fields = set(index.schema._fields.keys()) - set(['id'])
    parser = MultifieldParser(list(fields), index.schema)

    facets = sorting.Facets()
    facets.add_field("language")
    facets.add_field("mime_type")
    facets.add_field("creator")
    facets.add_field("owner")

    results = searcher.search(parser.parse(query),
                              groupedby=facets, limit=limit, filter=filter)
    return results

  def register_classes(self):
    for cls in all_entity_classes():
      if not cls in self.indexed_classes:
        self.register_class(cls)

  def register_class(self, cls):
    """
    Registers a model class, by creating the necessary Whoosh index if needed.
    """
    self.indexed_classes.add(cls)

    index_path = os.path.join(self.whoosh_base, cls.__name__)

    if hasattr(cls, 'whoosh_schema'):
      schema = cls.whoosh_schema
      primary = 'id'
    else:
      schema, primary = self._get_whoosh_schema_and_primary(cls)
      cls.whoosh_schema = schema

    if whoosh.index.exists_in(index_path):
      index = whoosh.index.open_dir(index_path)
    else:
      if not os.path.exists(index_path):
        os.makedirs(index_path)
      index = whoosh.index.create_in(index_path, schema)

    self.indexes[cls.__name__] = index
    cls.search_query = Searcher(cls, primary, index)
    return index

  def index_for_model_class(self, cls):
    """
    Gets the whoosh index for this model, creating one if it does not exist.
    in creating one, a schema is created based on the fields of the model.
    Currently we only support primary key -> whoosh.ID, and sqlalchemy.TEXT
    -> whoosh.TEXT, but can add more later. A dict of model -> whoosh index
    is added to the ``app`` variable.
    """
    index = self.indexes.get(cls.__name__)
    if index is None:
      index = self.register_class(cls)
    return index

  def _get_whoosh_schema_and_primary(self, cls):
    schema = {}
    primary = None

    for field in cls.__table__.columns:
      if field.primary_key:
        schema[field.name] = whoosh.fields.ID(stored=True, unique=True)
        primary = field.name
      if field.name in cls.__searchable__:
        if type(field.type) in (sa.types.Text, sa.types.UnicodeText):
          schema[field.name] = whoosh.fields.TEXT(analyzer=_TEXT_ANALYZER)

    return Schema(**schema), primary

  def after_flush(self, session, flush_context):
    if not self.running or session is not db.session():
      return

    get_queue_for = lambda cls_name: self.to_update.setdefault(cls_name, [])

    for model in session.new:
      model_class = model.__class__

      if hasattr(model_class, '__searchable__'):
        get_queue_for(model_class.__name__).append(("new", model))

    for model in session.deleted:
      model_class = model.__class__
      if hasattr(model_class, '__searchable__'):
        get_queue_for(model_class.__name__).append(("deleted", model))

    for model in session.dirty:
      model_class = model.__class__
      if hasattr(model_class, '__searchable__'):
        get_queue_for(model_class.__name__).append(("changed", model))

  def after_flush_postexec(self, session, flush_context):
    #self.after_commit(session)
    pass

  def after_commit(self, session):
    """
    Any db updates go through here. We check if any of these models have
    ``__searchable__`` fields, indicating they need to be indexed. With these
    we update the whoosh index for the model. If no index exists, it will be
    created here; this could impose a penalty on the initial commit of a model.
    """
    if not self.running or session is not db.session():
      return

    for cls_name, values in self.to_update.iteritems():
      model_class = values[0][1].__class__
      assert model_class.__name__ == cls_name

      if (model_class not in self.indexed_classes
          or not hasattr(model_class, '__searchable__')):
        # safeguard
        continue

      primary_field = model_class.search_query.primary
      values = [(op, getattr(model, primary_field))
                for op, model in values
                # safeguard against DetachedInstanceError
                if sa.orm.object_session(model) is not None]
      index_update.apply_async(kwargs=dict(class_name=cls_name, items=values))

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
      if isinstance(value, str):
        value = unicode(value)
      elif isinstance(value, int):
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

  def __call__(self, query, limit=None):
    """
    Original WhooshAlchemy API: allows chaining search queries with SQL
    filtering.

    Not used anymore for performance reasons, but may still be
    useful in some circumstances.
    """
    session = self.model_class.query.session

    results = self.index.searcher().search(self.parser.parse(query), limit=limit)
    keys = [x[self.primary] for x in results]
    primary_column = getattr(self.model_class, self.primary)
    if not keys:
      # Dummy request...
      return session.query(self.model_class).filter(primary_column == -1)
    else:
      return session.query(self.model_class).filter(primary_column.in_(keys))

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
def index_update(class_name, items):
  """ items: dict of model class name => list of (operation, primary key)
  """
  cls_registry = dict([(cls.__name__, cls) for cls in service.indexed_classes])
  model_class = cls_registry.get(class_name)

  if model_class is None:
    raise ValueError("Invalid class: {}".format(class_name))

  index = service.index_for_model_class(model_class)
  primary_field = model_class.search_query.primary
  indexed_fields = model_class.whoosh_schema.names()

  session = Session(bind=db.session.get_bind(None, None))
  query = session.query(model_class)

  with AsyncWriter(index) as writer:
    for change_type, model_pk in items:
      if model_pk is None:
        continue
      # delete everything. stuff that's updated or inserted will get
      # added as a new doc. Could probably replace this with a whoosh
      # update.
      writer.delete_by_term(primary_field, unicode(model_pk))

      if change_type in ("new", "changed"):
        model = query.get(model_pk)
        if model is None:
          # deleted after task queued, but before task run
          continue

        # Hack: Load lazy fields
        # This prevents a transaction error in make_document
        for key in indexed_fields:
          getattr(model, key)

        document = service.make_document(model, indexed_fields, primary_field)
        writer.add_document(**document)

  session.close()
