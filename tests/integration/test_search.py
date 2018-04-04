# coding=utf-8
"""Test the index service."""
from __future__ import absolute_import, print_function, unicode_literals

from flask_login import login_user
from sqlalchemy import Column, Text, UnicodeText
from sqlalchemy.orm import column_property

from abilian.core.entities import SEARCHABLE, Entity
from abilian.services import index_service


def gen_name(ctx):
    params = ctx.current_parameters
    return '{} {}'.format(
        params.get('first_name', ""),
        params.get('last_name', ""),
    ).strip()


class DummyContact1(Entity):
    name = column_property(
        Column(
            'name',
            UnicodeText(),
            info=SEARCHABLE,
            default=gen_name,
            onupdate=gen_name,
        ),
        Entity.name,
    )

    salutation = Column(UnicodeText, default="")
    first_name = Column(UnicodeText, default="", info=SEARCHABLE)
    last_name = Column(UnicodeText, default="", info=SEARCHABLE)
    email = Column(Text, default="")


def test_contacts_are_indexed(app, db_session):
    index_service.start()

    with app.test_request_context():
        root_user = app.create_root_user()
        login_user(root_user)

        contact = DummyContact1(
            first_name="John",
            last_name="Test User",
            email="test@example.com",
        )
        db_session.add(contact)
        # commit is needed here to trigger change in index
        db_session.commit()

        search_result = index_service.search('john')
        assert len(search_result) == 1

        found = search_result[0]
        assert contact.id == found['id']
        assert contact.name == found['name']

        search_result = index_service.search("john")
        assert len(search_result) == 1
        assert contact.id == int(search_result[0]['id'])
