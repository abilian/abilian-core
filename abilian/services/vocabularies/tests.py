# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import sqlalchemy as sa
import sqlalchemy.exc
from pytest import mark, raises

from abilian.web import url_for

from .models import BaseVocabulary, Vocabulary
from .service import vocabularies

# DefaultVoc = Vocabulary('defaultstates', group='', label='States')

# XXX: we need to use globals for now.
# Classes are global state in Python.
Voc = Vocabulary('voc', label='Voc', group='')
PriorityVoc = Vocabulary('priorities', label='Priorities', group='')
StateVoc = Vocabulary('defaultstates', group='', label='States')
DocCatVoc = Vocabulary('categories', group='documents', label='Categories')


def test_vocabulary_factory(session):
    assert Voc.__name__ == 'VocabularyVoc'
    assert Voc.__tablename__ == 'vocabulary_voc'
    assert Voc.Meta.name == 'voc'
    assert Voc.Meta.label == 'Voc'
    assert Voc.Meta.group is ""
    assert issubclass(Voc, BaseVocabulary)


def test_vocabularies(session):
    # test registered vocabularies
    assert vocabularies.vocabularies == {Voc, PriorityVoc, StateVoc, DocCatVoc}

    grouped = vocabularies.grouped_vocabularies
    assert set(grouped['']) == {Voc, StateVoc, PriorityVoc}
    assert grouped['documents'] == [DocCatVoc]

    assert vocabularies.get_vocabulary('priorities') is PriorityVoc
    assert vocabularies.get_vocabulary('priorities', 'nogroup') is None
    assert vocabularies.get_vocabulary('categories', 'documents') is DocCatVoc


def test_items(db, session):
    db.create_all()

    IMMEDIATE = PriorityVoc(label='Immediate', position=0)
    NORMAL = PriorityVoc(label='Normal', position=3, default=True)
    URGENT = PriorityVoc(label='Urgent', position=1)
    HIGH = PriorityVoc(label='High', position=2)
    items = (IMMEDIATE, NORMAL, URGENT, HIGH)
    for item in items:
        session.add(item)
    session.flush()

    # test position=4 set automatically; Label stripped
    low_item = PriorityVoc(label=' Low  ')
    session.add(low_item)
    session.flush()
    assert low_item.position == 4
    assert low_item.label == 'Low'

    # test strip label on update
    IMMEDIATE.label = '  Immediate  '
    session.flush()
    assert IMMEDIATE.label == 'Immediate'

    # test default ordering
    default_ordering = ['Immediate', 'Urgent', 'High', 'Normal', 'Low']
    query = PriorityVoc.query
    assert [i.label for i in query.active().all()] == default_ordering

    # no default ordering when using .values(): explicit ordering required
    query = PriorityVoc.query \
        .active() \
        .order_by(PriorityVoc.position.asc())
    assert (
        [
            i.label for i in query.values(PriorityVoc.label)
        ] == default_ordering
    )

    # test db-side constraint for non-empty labels
    with raises(
            sa.exc.IntegrityError,
            message="Could insert an item with empty label",
    ):
        with session.begin_nested():
            v = PriorityVoc(label='   ', position=6)
            session.add(v)
            session.flush()

    # test unique labels constraint
    with raises(sa.exc.IntegrityError, message="Could insert duplicate label"):
        with session.begin_nested():
            v = PriorityVoc(label='Immediate')
            session.add(v)
            session.flush()

    # test unique position constraint
    with raises(
            sa.exc.IntegrityError,
            message="Could insert duplicate position",
    ):
        with session.begin_nested():
            v = PriorityVoc(label='New one', position=1)
            session.add(v)
            session.flush()

    # test by_position without results
    item = PriorityVoc.query.by_position(42)
    assert item is None

    # test by_position() and active()
    item = PriorityVoc.query.by_position(URGENT.position)
    assert item is URGENT

    item.active = False
    expected = [
        'Immediate',
        'High',
        'Normal',
        'Low',
    ]
    assert ([i.label for i in PriorityVoc.query.active().all()] == expected)
    assert PriorityVoc.query.active().by_position(URGENT.position) is None

    # test by_label()
    item = PriorityVoc.query.by_label(NORMAL.label)
    assert item is NORMAL


@mark.skip
def test_admin_panel_reorder(app, db, session, client, test_request_context):
    db.create_all()
    items = [
        Voc(label='First', position=0),
        Voc(label='Second', position=2),
        Voc(label='Third', position=3),
    ]

    for i in items:
        session.add(i)
    session.commit()

    first, second, third = items
    url = url_for('admin.vocabularies')
    base_data = {'Model': Voc.Meta.name}
    data = {'down': first.id}
    data.update(base_data)
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert r.headers['Location'] == 'http://localhost/admin/vocabularies'
    assert Voc.query.order_by(Voc.position).all() == [second, first, third]

    data = {'up': first.id, 'return_to': 'group'}
    data.update(base_data)
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert r.headers['Location'] \
        == 'http://localhost/admin/vocabularies/_/'
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'up': first.id, 'return_to': 'model'}
    data.update(base_data)
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert r.headers['Location'] \
        == 'http://localhost/admin/vocabularies/_/defaultstates/'
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'down': third.id}
    data.update(base_data)
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert r.headers['Location'] == 'http://localhost/admin/vocabularies'
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'up': third.id}
    data.update(base_data)
    r = client.post(url, data=data)
    assert r.status_code == 302
    assert r.headers['Location'] == 'http://localhost/admin/vocabularies'
    assert Voc.query.order_by(Voc.position).all() == [first, third, second]
