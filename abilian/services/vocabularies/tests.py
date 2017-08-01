# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import sqlalchemy as sa

from abilian.testing import BaseTestCase
from abilian.web import url_for

from .models import BaseVocabulary, Vocabulary
from .service import vocabularies


class TestVocabularies(BaseTestCase):

    DefaultVoc = Vocabulary('defaultstates', label='States')

    def test_vocabulary_creator(self):
        PriorityVoc = Vocabulary('priorities', label='Priorities')
        assert PriorityVoc.__name__ == 'VocabularyPriorities'
        assert PriorityVoc.__tablename__ == 'vocabulary_priorities'
        assert PriorityVoc.Meta.name == u'priorities'
        assert PriorityVoc.Meta.label == u'Priorities'
        assert PriorityVoc.Meta.group is None
        assert issubclass(PriorityVoc, BaseVocabulary)

        StateVoc = self.DefaultVoc
        DocCatVoc = Vocabulary(
            'categories', group='documents', label='Categories')

        # test registered vocabularies
        assert vocabularies.vocabularies == {PriorityVoc, StateVoc, DocCatVoc}
        assert (vocabularies.grouped_vocabularies == {
            None: [StateVoc, PriorityVoc],
            'documents': [DocCatVoc]
        })
        assert vocabularies.get_vocabulary('priorities') is PriorityVoc
        assert vocabularies.get_vocabulary('priorities', 'nogroup') is None
        assert vocabularies.get_vocabulary('categories',
                                           'documents') is DocCatVoc

        self.app.db.create_all()

        IMMEDIATE = PriorityVoc(label='Immediate', position=0)
        NORMAL = PriorityVoc(label='Normal', position=3, default=True)
        URGENT = PriorityVoc(label='Urgent', position=1)
        HIGH = PriorityVoc(label='High', position=2)
        items = (IMMEDIATE, NORMAL, URGENT, HIGH)
        map(self.session.add, items)
        self.session.flush()

        # test position=4 set automatically; Label stripped
        low_item = PriorityVoc(label=' Low  ')
        self.session.add(low_item)
        self.session.flush()
        assert low_item.position == 4
        assert low_item.label == u'Low'

        # test strip label on update
        IMMEDIATE.label = u'  Immediate  '
        self.session.flush()
        assert IMMEDIATE.label == u'Immediate'

        # test default ordering
        assert ([i.label for i in PriorityVoc.query.active().all()] ==
                [u'Immediate', u'Urgent', u'High', u'Normal', u'Low'])

        # no default ordering when using .values(): explicit ordering required
        query = PriorityVoc.query.active().order_by(PriorityVoc.position.asc())
        assert ([i.label for i in query.values(PriorityVoc.label)] ==
                [u'Immediate', u'Urgent', u'High', u'Normal', u'Low'])

        # test db-side constraint for non-empty labels
        try:
            with self.session.begin_nested():
                v = PriorityVoc(label='   ', position=6)
                self.session.add(v)
                self.session.flush()
        except sa.exc.IntegrityError:
            pass
        else:
            self.fail("Could insert an item with empty label")

        # test unique labels constraint
        try:
            with self.session.begin_nested():
                v = PriorityVoc(label='Immediate')
                self.session.add(v)
                self.session.flush()
        except sa.exc.IntegrityError:
            pass
        else:
            self.fail("Could insert duplicate label")

        # test unique position constraint
        try:
            with self.session.begin_nested():
                v = PriorityVoc(label='New one', position=1)
                self.session.add(v)
                self.session.flush()
        except sa.exc.IntegrityError:
            pass
        else:
            self.fail("Could insert duplicate position")

        # test by_position without results
        item = PriorityVoc.query.by_position(42)
        assert item is None

        # test by_position() and active()
        item = PriorityVoc.query.by_position(URGENT.position)
        assert item is URGENT
        item.active = False
        assert ([i.label for i in PriorityVoc.query.active().all()] ==
                [u'Immediate', u'High', u'Normal', u'Low'])
        assert PriorityVoc.query.active().by_position(URGENT.position) is None

        # test by_label()
        item = PriorityVoc.query.by_label(NORMAL.label)
        assert item is NORMAL

    def test_admin_panel_reorder(self):
        Voc = self.DefaultVoc
        session = self.session
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
        r = self.client.post(url, data=data)
        assert r.status_code == 302
        assert r.headers['Location'] == u'http://localhost/admin/vocabularies'
        assert Voc.query.order_by(Voc.position).all() == [second, first, third]

        data = {'up': first.id, 'return_to': 'group'}
        data.update(base_data)
        r = self.client.post(url, data=data)
        assert r.status_code == 302
        assert r.headers[
            'Location'] == u'http://localhost/admin/vocabularies/_/'
        assert Voc.query.order_by(Voc.position).all() == [first, second, third]

        data = {'up': first.id, 'return_to': 'model'}
        data.update(base_data)
        r = self.client.post(url, data=data)
        assert r.status_code == 302
        assert (r.headers['Location'] ==
                u'http://localhost/admin/vocabularies/_/defaultstates/')
        assert Voc.query.order_by(Voc.position).all() == [first, second, third]

        data = {'down': third.id}
        data.update(base_data)
        r = self.client.post(url, data=data)
        assert r.status_code == 302
        assert r.headers['Location'] == u'http://localhost/admin/vocabularies'
        assert Voc.query.order_by(Voc.position).all() == [first, second, third]

        data = {'up': third.id}
        data.update(base_data)
        r = self.client.post(url, data=data)
        assert r.status_code == 302
        assert r.headers['Location'] == u'http://localhost/admin/vocabularies'
        assert Voc.query.order_by(Voc.position).all() == [first, third, second]
