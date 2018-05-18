# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import time
from collections import deque

import sqlalchemy as sa
import whoosh
import whoosh.index
from flask import current_app
from six import string_types
from sqlalchemy.orm.session import Session
from tqdm import tqdm
from whoosh.writing import CLEAR, AsyncWriter

from abilian.core.extensions import db
from abilian.services import get_service

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
    index_service = get_service("indexing")
    adapted = index_service.adapted
    index = index_service.app_state.indexes["default"]
    session = Session(bind=db.session.get_bind(None, None), autocommit=True)

    session._model_changes = {}  # please flask-sqlalchemy <= 1.0
    indexed = set()
    cleared = set()
    if batch_size is not None:
        batch_size = int(batch_size)

    strategy = progressive_mode if progressive else single_transaction
    strategy = strategy(
        index, clear=clear, progressive=progressive, batch_size=batch_size
    )
    next(strategy)  # starts generator

    for cls in sorted(
        index_service.app_state.indexed_classes, key=lambda c: c.__name__
    ):
        current_object_type = cls._object_type()

        if not clear and current_object_type not in cleared:
            strategy.send(current_object_type)
            cleared.add(current_object_type)

        adapter = adapted.get(current_object_type)

        if not adapter or not adapter.indexable:
            continue

        name = cls.__name__

        with session.begin():
            query = session.query(cls).options(sa.orm.lazyload("*"))
            try:
                count = query.count()
            except Exception as e:
                current_app.logger.error(
                    "Indexing error on class {}: {}".format(name, repr(e))
                )
                continue

            print("*" * 79)
            print("{}".format(name))
            if count == 0:
                print("*" * 79)
                print("{}".format(name))
                continue

            print("*" * 79)
            print("{}".format(name))
            count_current = 0
            with tqdm(total=count) as bar:
                for obj in query.yield_per(1000):
                    if obj.object_type != current_object_type:
                        # may happen if obj is a subclass and its parent class
                        # is also indexable
                        bar.update()
                        continue

                    object_key = obj.object_key

                    if object_key in indexed:
                        bar.update()
                        continue
                    document = index_service.get_document(obj, adapter)
                    strategy.send(document)
                    indexed.add(object_key)

                    if batch_size is not None and (count_current % batch_size) == 0:
                        bar.update()
                        strategy.send(COMMIT)

                    bar.update()

            if batch_size is None:
                strategy.send(COMMIT)

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
                writer.delete_by_term("object_type", doc)
            else:
                writer.add_document(**doc)
            doc = yield True

        print("Writing Index...", end=" ")

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
        writer.mergetype = CLEAR
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
                    writer.delete_by_term("object_type", doc)
                else:
                    writer.add_document(**doc)
            writer.commit()
            del writer
        else:
            queue.append(doc)

        doc = yield True
