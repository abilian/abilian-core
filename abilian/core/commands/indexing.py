# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import time
from collections import deque

import progressbar
import sqlalchemy as sa
import whoosh
from flask import current_app
from future.utils import string_types
from sqlalchemy.orm.session import Session
from whoosh.writing import CLEAR, AsyncWriter

from .base import manager

STOP = object()
COMMIT = object()


@manager.command
def reindex(clear=False, progressive=False, batch_size=None):
    """Reindex all content; optionally clear index before.

    All is done in asingle transaction by default.

    :param clear: clear index content.
    :param progressive: don't run in a single transaction.
    :param batch_size: number of documents to process before writing to the
                     index. Unused in single transaction mode. If `None` then
                     all documents of same content type are written at once.
    """
    svc = current_app.services['indexing']
    adapted = svc.adapted
    index = svc.app_state.indexes['default']
    session = Session(bind=current_app.db.session.get_bind(None, None),
                      autocommit=True)

    setattr(session, '_model_changes', {})  # please flask-sqlalchemy <= 1.0
    indexed = set()
    cleared = set()
    if batch_size is not None:
        batch_size = int(batch_size)
    strategy_kw = dict(clear=clear,
                       progressive=progressive,
                       batch_size=batch_size)
    strategy = progressive_mode if progressive else single_transaction
    strategy = strategy(index, **strategy_kw)
    next(strategy)  # starts generator
    count_indexed = 0

    for cls in sorted(svc.app_state.indexed_classes, key=lambda c: c.__name__):
        current_object_type = cls._object_type()

        if not clear and current_object_type not in cleared:
            strategy.send(current_object_type)
            cleared.add(current_object_type)

        adapter = adapted.get(current_object_type)

        if not adapter or not adapter.indexable:
            continue

        name = cls.__name__

        with session.begin():
            q = session.query(cls).options(sa.orm.lazyload('*'))
            count = q.count()

            if count == 0:
                print("{}: 0".format(name))
                continue

            widgets = [name, ': ', progressbar.Counter(), '/{}'.format(count),
                       ' ', progressbar.Timer(), ' ', progressbar.Percentage(),
                       ' ', progressbar.Bar(), ' ', progressbar.ETA()]
            progress = progressbar.ProgressBar(widgets=widgets, maxval=count)
            progress.start()
            count_current = 0

            for obj in q.yield_per(1000):
                if obj.object_type != current_object_type:
                    # may happen if obj is a subclass and its parent class is also
                    # indexable
                    continue

                object_key = obj.object_key

                if object_key in indexed:
                    continue
                document = svc.get_document(obj, adapter)
                strategy.send(document)
                indexed.add(object_key)
                count_indexed += 1
                count_current += 1
                try:
                    progress.update(count_current)
                except ValueError:
                    pass

                if batch_size is not None and (count_current % batch_size) == 0:
                    strategy.send(COMMIT)

            if batch_size is None:
                strategy.send(COMMIT)

            progress.finish()

        strategy.send(COMMIT)

    try:
        strategy.send(STOP)
    except StopIteration:
        pass

    try:
        strategy.close()
    except StopIteration:
        pass


# indexing strategies
def single_transaction(index, clear, **kwargs):
    with AsyncWriter(index) as writer:
        if clear:
            print("*" * 80)
            print("WILL CLEAR INDEX BEFORE REINDEXING")
            print("*" * 80)
            writer.writer.mergetype = CLEAR

        doc = yield True
        while doc is not STOP:
            if doc is COMMIT:
                doc = yield True
                continue
            if isinstance(doc, string_types):
                writer.delete_by_term('object_type', doc)
            else:
                writer.add_document(**doc)
            doc = yield True

        print("Writing Index...", end=' ')

    print("Done.")


def _get_writer(index):
    writer = None
    while writer is None:
        try:
            writer = index.writer()
        except whoosh.index.LockError:
            time.sleep(0.25)

    return writer


def progressive_mode(index, clear, batch_size, **kwargs):

    if clear:
        writer = _get_writer(index)
        print("*" * 80)
        print("CLEAR INDEX BEFORE REINDEXING")
        print("*" * 80)
        writer.writer.mergetype = CLEAR
        writer.commit()
        del writer

    queue = deque()
    doc = yield True
    while doc is not STOP:
        if doc is COMMIT:
            writer = _get_writer(index)
            while queue:
                doc = queue.pop()
                if isinstance(doc, string_types):
                    writer.delete_by_term('object_type', doc)
                else:
                    writer.add_document(**doc)
            writer.commit()
            del writer
        else:
            queue.append(doc)

        doc = yield True
