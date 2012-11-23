"""
Indexing service for Yaka.

Adds Whoosh indexing capabilities to SQLAlchemy models.

Based on Flask-whooshalchemy by Karl Gyllstrom.

:copyright: (c) 2012 by Stefane Fermigier
:copyright: (c) 2012 by Karl Gyllstrom
:license: BSD (see LICENSE.txt)
"""

# TODO: not sure that one index per class is the way to go.
# TODO: speed issue
# TODO: this is a singleton. makes tests hard (for instance, launching parallel tests).

import sqlalchemy
from sqlalchemy import event
from sqlalchemy.orm.session import Session

from logbook import Logger

import whoosh.index
from whoosh import sorting
from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import Schema

from yaka.core.entities import all_entity_classes

import os
from shutil import rmtree

log = Logger("Index service")


class WhooshIndexService(object):

  app = None

  def __init__(self, app=None):
    self.indexes = {}
    self.indexed_classes = set()
    self.running = False
    if app:
      self.init_app(app)

  def init_app(self, app):
    self.app = app
    self.whoosh_base = app.config.get("WHOOSH_BASE")
    if not self.whoosh_base:
      self.whoosh_base = "whoosh"  # Default value

    event.listen(Session, "before_commit", self.before_commit)
    event.listen(Session, "after_commit", self.after_commit)

  def start(self):
    assert self.app, "service not bound to an app"
    log.info("Starting index service")
    self.running = True
    self.register_classes()

  def stop(self):
    log.info("Stopping index service")
    self.running = False

  def clear(self):
    log.info("Resetting indexes")
    assert not self.running

    for cls in self.indexed_classes:
      index_path = os.path.join(self.whoosh_base, cls.__name__)
      try:
        rmtree(index_path)
      except OSError:
        pass

    self.indexes = {}
    self.indexed_classes = set()

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

    results = searcher.search(parser.parse(query), groupedby=facets, limit=limit, filter=filter)
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
        if type(field.type) in (sqlalchemy.types.Text, sqlalchemy.types.UnicodeText):
          schema[field.name] = whoosh.fields.TEXT(analyzer=StemmingAnalyzer())

    return Schema(**schema), primary

  def before_commit(self, session):
    if not self.running:
      return

    self.to_update = {}

    for model in session.new:
      model_class = model.__class__
      if hasattr(model_class, '__searchable__'):
        self.to_update.setdefault(model_class.__name__, []).append(("new", model))

    for model in session.deleted:
      model_class = model.__class__
      if hasattr(model_class, '__searchable__'):
        self.to_update.setdefault(model_class.__name__, []).append(("deleted", model))

    for model in session.dirty:
      model_class = model.__class__
      if hasattr(model_class, '__searchable__'):
        self.to_update.setdefault(model_class.__name__, []).append(("changed", model))

  #noinspection PyUnusedLocal
  def after_commit(self, session):
    """
    Any db updates go through here. We check if any of these models have
    ``__searchable__`` fields, indicating they need to be indexed. With these
    we update the whoosh index for the model. If no index exists, it will be
    created here; this could impose a penalty on the initial commit of a model.
    """

    if not self.running:
      return

    for typ, values in self.to_update.iteritems():
      model_class = values[0][1].__class__
      index = self.index_for_model_class(model_class)
      with index.writer() as writer:
        primary_field = model_class.search_query.primary
        indexed_fields = model_class.whoosh_schema.names()

        for change_type, model in values:
          # delete everything. stuff that's updated or inserted will get
          # added as a new doc. Could probably replace this with a whoosh
          # update.

          writer.delete_by_term(primary_field, unicode(getattr(model, primary_field)))

          if change_type in ("new", "changed"):
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
            writer.add_document(**attrs)

    self.to_update = {}


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
    self.parser = MultifieldParser(list(fields), index.schema)

  def __call__(self, query, limit=None):
    """API similar to SQLAlchemy's queries.
    """
    session = self.model_class.query.session

    results = self.index.searcher().search(self.parser.parse(query), limit=limit)
    keys = [x[self.primary] for x in results]
    if not keys:
      # Dummy request...
      return session.query(self.model_class).filter("id = -1")
    else:
      primary_column = getattr(self.model_class, self.primary)
      return session.query(self.model_class).filter(primary_column.in_(keys))

  def search(self, query, limit=None):
    """New API: returns both whoosh records and SA models."""
    # TODO: highly suboptimal

    session = self.model_class.query.session
    hits = self.index.searcher().search(self.parser.parse(query), limit=limit)
    for hit in hits:
      yield (hit, session.query(self.model_class).get(hit[self.primary]))

