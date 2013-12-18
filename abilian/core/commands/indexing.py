# coding=utf-8
"""
"""
from __future__ import absolute_import
import progressbar as pb
import sqlalchemy as sa
from sqlalchemy.orm.session import Session

from whoosh.writing import AsyncWriter, CLEAR
from flask import current_app

from .base import manager

@manager.command
def reindex(clear=False):
  """
  Reindex all content; optionally clear index before. All is done in a single transaction.
  """
  svc = current_app.services['indexing']
  adapted = svc.adapted
  index = svc.app_state.indexes['default']
  session = Session(bind=current_app.db.session.get_bind(None, None),
                    autocommit=True)

  indexed = set()
  cleared = set()

  with AsyncWriter(index) as writer:
    if clear:
      print "*" * 80
      print "WILL CLEAR INDEX BEFORE REINDEXING"
      print "*" * 80
      writer.writer.mergetype = CLEAR

    for cls in sorted(svc.app_state.indexed_classes, key=lambda c: c.__name__):
      current_object_type = cls._object_type()

      if not clear and  current_object_type not in cleared:
        writer.delete_by_term('object_type', current_object_type)
        cleared.add(current_object_type)

      adapter = adapted.get(current_object_type)

      if not adapter or not adapter.indexable:
        continue

      name = cls.__name__

      with session.begin():
        q = session.query(cls).options(sa.orm.lazyload('*'))
        count = q.count()

        if count == 0:
          print "{}: 0".format(name)
          continue

        widgets = [name,
                   ': ', pb.Counter(), '/{}'.format(count),
                   ' ', pb.Timer(),
                   ' ',pb.Percentage(),
                   ' ', pb.Bar(),
                   ' ', pb.ETA(),
                   ]
        progress = pb.ProgressBar(widgets=widgets, maxval=count)
        progress.start()
        count_current = 0

        with writer.group():
          for obj in q.yield_per(1000):
            if obj.object_type != current_object_type:
              # may happen if obj is a subclass and mother class is indexable
              continue

            object_key = obj.object_key

            if object_key in indexed:
              continue
            document = adapter.get_document(obj)
            writer.add_document(**document)
            indexed.add(object_key)
            count_current += 1
            try:
              progress.update(count_current)
            except ValueError:
              pass

        progress.finish()
