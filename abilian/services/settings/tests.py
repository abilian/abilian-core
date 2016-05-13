# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from unittest import TestCase

import pytest

from abilian.testing import BaseTestCase

from .models import EmptyValue, Setting


def test_type_set():
    s = Setting()
    # registered base type: no failure
    s.type = 'int'
    s.type = 'bool'
    s.type = 'json'
    s.type = 'string'

    with pytest.raises(ValueError):
        s.type = 'dummy type name'


def test_int():
    s = Setting(key='key', type='int')
    s.value = 42
    assert s._value == '42'

    s._value = '24'
    assert s.value == 24


def test_bool():
    s = Setting(key='key', type='bool')
    s.value = True
    assert s._value == 'true'

    s.value = False
    assert s._value == 'false'

    s._value = 'true'
    assert s.value is True

    s._value = 'false'
    assert s.value is False


def test_string():
    s = Setting(key='key', type='string')
    s.value = u'ascii'
    assert s._value == b'ascii'

    s.value = u'bel été'
    assert s._value == b'bel \xc3\xa9t\xc3\xa9'

    s._value = b'd\xc3\xa9code'
    assert s.value == u'décode'


def test_json():
    s = Setting(key='key', type='json')
    s.value = [1, 2, u'été', {1: '1', 2: '2'}]
    assert s._value == '[1, 2, "\\u00e9t\\u00e9", {"1": "1", "2": "2"}]'

    s.value = None
    assert s._value == 'null'


def test_empty_value():
    s = Setting(key='key', type='json')
    s._value = None
    assert s.value == EmptyValue


class SettingsServiceTestCase(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        self.service = self.app.services.get('settings')

    def test_service_facade(self):
        svc = self.service
        svc.set('key_1', 42, 'int')
        self.db.session.flush()
        self.assertEqual(svc.get('key_1'), 42)

        # new key with no type: raise error:
        with self.assertRaises(ValueError):
            svc.set('key_err', 42)

        # key already with type_, this should not raise an error
        svc.set('key_1', 24)
        self.db.session.flush()
        self.assertEqual(svc.get('key_1'), 24)

        svc.delete('key_1')
        self.db.session.flush()
        with self.assertRaises(KeyError):
            svc.get('key_1')

        # delete: silent by default
        svc.delete('non_existent')

        # delete: non-silent
        with self.assertRaises(KeyError):
            svc.delete('non_existent', silent=False)

        # tricky use case: ask key delete, set it later, then flush
        svc.set('key_1', 42, 'int')
        self.db.session.flush()
        svc.delete('key_1')
        svc.set('key_1', 1)
        self.db.session.flush()
        self.assertEqual(svc.get('key_1'), 1)

        # list keys
        svc.set('key_2', 2, 'int')
        svc.set('other', 'azerty', 'string')
        self.db.session.flush()
        self.assertEqual(sorted(svc.keys()), ['key_1', 'key_2', 'other'])
        self.assertEqual(sorted(svc.keys(prefix='key_')), ['key_1', 'key_2'])

        # as dict
        self.assertEqual(svc.as_dict(), {'other': u'azerty',
                                         'key_1': 1,
                                         'key_2': 2})
        self.assertEqual(svc.as_dict(prefix='key_'), {'key_1': 1, 'key_2': 2})

    def test_namespace(self):
        svc = self.service
        ns = svc.namespace('test')
        ns.set('1', 42, 'int')
        self.db.session.flush()
        self.assertEqual(ns.get('1'), 42)
        self.assertEqual(svc.get('test:1'), 42)

        ns.set('sub:2', 2, 'int')
        svc.set('other', 'not in NS', 'string')
        self.db.session.flush()
        self.assertEqual(sorted(ns.keys()), ['1', 'sub:2'])
        self.assertEqual(sorted(svc.keys()), ['other', 'test:1', 'test:sub:2'])

        # sub namespace test:sub:
        sub = ns.namespace('sub')
        self.assertEqual(sorted(sub.keys()), ['2'])
        self.assertEqual(sub.get('2'), 2)

        sub.set('1', 1, 'int')
        self.db.session.flush()
        self.assertEqual(sub.get('1'), 1)
        self.assertEqual(ns.get('1'), 42)
        self.assertEqual(
            sorted(svc.keys()), ['other', 'test:1', 'test:sub:1', 'test:sub:2'])

        # as dict
        self.assertEqual(sub.as_dict(), {'1': 1, '2': 2})
        self.assertEqual(ns.as_dict(prefix='sub:'), {'sub:1': 1, 'sub:2': 2})
        self.assertEqual(ns.as_dict(), {'1': 42, 'sub:1': 1, 'sub:2': 2})
        self.assertEqual(svc.as_dict(), {'other': u'not in NS',
                                         'test:1': 42,
                                         'test:sub:1': 1,
                                         'test:sub:2': 2})

        # deletion
        sub.delete('1')
        sub.delete('2')
        self.db.session.flush()
        self.assertEqual(sorted(sub.keys()), [])
        self.assertEqual(sorted(ns.keys()), ['1'])
        self.assertEqual(sorted(svc.keys()), ['other', 'test:1'])
