# coding=utf-8
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import g


def test_id_generator(app, app_context):
    # inside app context: id_generator installed
    assert hasattr(g, 'id_generator')

    # test sucessives values
    assert next(g.id_generator) == 1
    assert next(g.id_generator) == 2
    assert next(g.id_generator) == 3

    gen = g.id_generator
    with app.app_context():
        # new app context: new id generator.
        # Note: if this behavior is not desired and got changed,
        # this test will flag behavior change.
        assert g.id_generator is not gen
        assert next(g.id_generator) == 1

    # app context popped: first id generator 'restored'
    assert g.id_generator is gen
    assert next(g.id_generator) == 4
