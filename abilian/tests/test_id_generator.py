# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import g

from abilian.testing import BaseTestCase


class TestIdGenerator(BaseTestCase):

    def test_id_generator(self):
        # inside app context: id_generator installed
        assert hasattr(g, 'id_generator')

        # test sucessives values
        assert next(g.id_generator) == 1
        assert next(g.id_generator) == 2
        assert next(g.id_generator) == 3

        gen = g.id_generator
        with self.app.app_context():
            # new app context: new id generator.
            # Note: if this behaviour is not desired and got changed, this test will
            # flag behaviour change.
            assert g.id_generator is not gen
            assert next(g.id_generator) == 1

        # app context popped: first id generator 'restored'
        assert g.id_generator is gen
        assert next(g.id_generator) == 4
