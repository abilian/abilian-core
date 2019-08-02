""""""
from typing import Iterator, Union

import sqlalchemy as sa
from pytest import fixture
from sqlalchemy.orm import Session

from abilian.app import Application
from abilian.core.entities import Entity
from abilian.services.indexing.service import WhooshIndexService


class IndexedContact(Entity):
    # default is 'test_service.IndexedContact'
    entity_type = "abilian.services.indexing.IndexedContact"
    name = sa.Column(sa.UnicodeText)


@fixture
def svc(app: Application) -> Iterator[Union[Iterator, Iterator[WhooshIndexService]]]:
    svc = app.services["indexing"]
    with app.app_context():
        svc.start()
        yield svc


def test_app_state(app: Application, svc: WhooshIndexService) -> None:
    state = svc.app_state
    assert IndexedContact in state.indexed_classes
    assert IndexedContact.entity_type in svc.adapted
    assert IndexedContact.entity_type in state.indexed_fqcn


def test_index_only_after_final_commit(
    app: Application, session: Session, svc: WhooshIndexService
) -> None:
    contact = IndexedContact(name="John Doe")

    state = svc.app_state

    session.begin(nested=True)
    assert state.to_update == []

    session.add(contact)
    # no commit: model is in wait queue
    session.flush()
    assert state.to_update == [("new", contact)]

    # commit but in a sub transaction: model still in wait queue
    session.commit()
    assert state.to_update == [("new", contact)]

    # 'final' commit: models sent for indexing update
    session.commit()
    assert state.to_update == []


def test_clear(app: Application, svc: WhooshIndexService) -> None:
    # just check no exception happens
    svc.clear()

    # check no double stop (would raise AssertionError from service base)
    svc.start()
    svc.stop()
    svc.clear()
