# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa

from abilian.web import url_for
from abilian.testing import BaseTestCase

from .models import Vocabulary, BaseVocabulary
from .service import vocabularies


class TestVocabularies(BaseTestCase):

  DefaultVoc = Vocabulary('defaultstates', label=u'States')

  def test_vocabulary_creator(self):
    PriorityVoc = Vocabulary('priorities', label=u'Priorities')
    assert PriorityVoc.__name__ == 'VocabularyPriorities'
    assert PriorityVoc.__tablename__ == 'vocabulary_priorities'
    assert PriorityVoc.Meta.label == u'Priorities'
    assert PriorityVoc.Meta.group is None
    assert issubclass(PriorityVoc, BaseVocabulary)

    StateVoc = self.DefaultVoc
    DocCatVoc = Vocabulary('categories',
                           group='documents',
                           label=u'Categories')

    # test registered vocabularies
    assert vocabularies.vocabularies == {PriorityVoc, StateVoc, DocCatVoc}
    assert (vocabularies.grouped_vocabularies
            == {None: [StateVoc, PriorityVoc],
                'documents': [DocCatVoc]})
    assert vocabularies.get_vocabulary('priorities') is PriorityVoc
    assert vocabularies.get_vocabulary('priorities', 'nogroup') is None
    assert vocabularies.get_vocabulary('categories', 'documents') is DocCatVoc

    self.app.db.create_all()

    items = [PriorityVoc(label=u'Immediate', position=0),
             PriorityVoc(label=u'Normal', position=3, default=True),
             PriorityVoc(label=u'Urgent', position=1),
             PriorityVoc(label=u'High', position=2),
            ]
    map(self.session.add, items)
    self.session.flush()

    low_item = PriorityVoc(label=u'Low') # position=4 set automatically
    self.session.add(low_item)
    self.session.flush()
    assert low_item.position == 4

    # test default ordering
    assert ([i.label for i in PriorityVoc.query.active().all()]
            == [u'Immediate', u'Urgent', u'High', u'Normal', u'Low'])

    # no default ordering when using .values(): explicit ordering required
    query = PriorityVoc.query.active().order_by(PriorityVoc.position.asc())
    assert ([i.label for i in query.values(PriorityVoc.label)]
            == [u'Immediate', u'Urgent', u'High', u'Normal', u'Low'])

    # test db-side constraint for non-empty labels
    try:
      with self.session.begin_nested():
        v = PriorityVoc(label=u'   ', position=6)
        self.session.add(v)
        self.session.flush()
    except sa.exc.IntegrityError:
      pass
    else:
      self.fail("Could insert an item with empty label")

    item = PriorityVoc.query.by_position(1)
    item.active = False
    assert ([i.label for i in PriorityVoc.query.active().all()]
            == [u'Immediate', u'High', u'Normal', u'Low'])

    # test by_position with no results
    item = PriorityVoc.query.active().by_position(1)
    assert item is None

  def test_admin_panel_reorder(self):
    Voc = self.DefaultVoc
    session = self.session
    items = [
        Voc(label=u'First', position=0),
        Voc(label=u'Second', position=2),
        Voc(label=u'Third', position=3)
    ]

    for i in items:
      session.add(i)
    session.commit()

    first, second, third = items
    url = url_for('admin.vocabularies')
    base_data = {'group': '', 'Model': Voc.Meta.name}
    data = {'down': first.id}
    data.update(base_data)
    r = self.client.post(url, data=data)
    assert r.status_code == 200
    assert Voc.query.order_by(Voc.position).all() == [second, first, third]

    data = {'up': first.id}
    data.update(base_data)
    r = self.client.post(url, data=data)
    assert r.status_code == 200
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'up': first.id}
    data.update(base_data)
    r = self.client.post(url, data=data)
    assert r.status_code == 200
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'down': third.id}
    data.update(base_data)
    r = self.client.post(url, data=data)
    assert r.status_code == 200
    assert Voc.query.order_by(Voc.position).all() == [first, second, third]

    data = {'up': third.id}
    data.update(base_data)
    r = self.client.post(url, data=data)
    assert r.status_code == 200
    assert Voc.query.order_by(Voc.position).all() == [first, third, second]
