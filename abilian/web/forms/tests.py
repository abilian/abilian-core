# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import datetime

import mock
import pytz
from wtforms.form import Form

from abilian.core.entities import Entity
from abilian.services.security import READ, WRITE, Anonymous, Owner, Role
from abilian.testing import BaseTestCase

from . import FormPermissions, fields, filters


def user_tz():
    # This one is GMT+8 and has no DST (tests should pass any time in year)
    return 'Asia/Hong_Kong'


USER_TZ = pytz.timezone(user_tz())


# test filters
def test_strip():
    assert filters.strip(None) == ''
    assert filters.strip(4) == 4
    assert filters.strip(' a string ') == 'a string'
    assert filters.strip(u' voilà ') == u'voilà'


def test_uppercase():
    assert filters.uppercase(None) is None
    assert filters.uppercase(4) == 4
    assert filters.uppercase(' a string ') == ' A STRING '
    assert filters.uppercase(u' Voilà ') == u' VOILÀ '


def test_lowercase():
    assert filters.lowercase(None) is None
    assert filters.lowercase(4) == 4
    assert filters.lowercase(' A STRING ') == ' a string '
    assert filters.lowercase(u' VOILÀ ') == u' voilà '


# FormPermissions
def test_form_permissions_controller():
    security_mock = mock.Mock()
    has_role = security_mock.has_role = mock.Mock()
    has_role.return_value = True
    current_app_mock = mock.Mock()
    current_app_mock.services = dict(security=security_mock)
    MarkRole = Role('tests:mark-role')
    _MARK = object()
    _ENTITY_MARK = Entity()

    with mock.patch('abilian.web.forms.current_app', current_app_mock):
        # default role
        fp = FormPermissions()
        assert fp.has_permission(READ) == True
        assert has_role.called is True
        assert has_role.call_args[-1]['role'] == [Anonymous]
        has_role.reset_mock()
        assert fp.has_permission(READ, obj=_MARK) == True
        assert has_role.called is False

        has_role.reset_mock()
        assert fp.has_permission(READ, obj=_ENTITY_MARK) == True
        assert has_role.called is True
        assert has_role.call_args[-1]['object'] is _ENTITY_MARK

        # change default
        has_role.reset_mock()
        fp = FormPermissions(default=MarkRole)
        fp.has_permission(READ)
        assert has_role.call_args[-1]['role'] == [MarkRole]
        has_role.reset_mock()
        fp.has_permission(READ, field='test')
        assert has_role.call_args[-1]['role'] == [MarkRole]

        has_role.reset_mock()
        fp = FormPermissions(default=MarkRole, read=Anonymous)
        fp.has_permission(READ)
        assert has_role.call_args[-1]['role'] == [Anonymous]
        has_role.reset_mock()
        fp.has_permission(READ, field='test')
        assert has_role.call_args[-1]['role'] == [MarkRole]
        has_role.reset_mock()
        fp.has_permission(WRITE)
        assert has_role.call_args[-1]['role'] == [MarkRole]

        # field roles
        has_role.reset_mock()
        fp = FormPermissions(
            default=MarkRole, read=Anonymous, fields_read={'test': Owner})
        fp.has_permission(READ)
        assert has_role.call_args[-1]['role'] == [Anonymous]

        has_role.reset_mock()
        fp.has_permission(READ, field='test')
        assert has_role.call_args[-1]['role'] == [Owner]

        has_role.reset_mock()
        fp.has_permission(READ, field='test')
        assert has_role.call_args[-1]['role'] == [Owner]

        # dynamic roles
        has_role.reset_mock()
        dyn_roles = mock.Mock()
        dyn_roles.return_value = [MarkRole]
        fp = FormPermissions(read=dyn_roles)
        fp.has_permission(READ)
        assert dyn_roles.call_args == [
            dict(
                permission=READ, field=None, obj=None)
        ]
        assert has_role.call_args[-1]['role'] == [MarkRole]

        has_role.reset_mock()
        dyn_roles.reset_mock()
        fp = FormPermissions(read=[Owner, dyn_roles])
        fp.has_permission(READ)
        assert dyn_roles.call_args == [
            dict(
                permission=READ, field=None, obj=None)
        ]
        assert has_role.call_args[-1]['role'] == [Owner, MarkRole]


class FieldsTestCase(BaseTestCase):

    def create_app(self):
        app = super(FieldsTestCase, self).create_app()
        app.extensions['babel'].timezone_selector_func = None
        app.extensions['babel'].timezoneselector(user_tz)
        return app

    def test_datetime_field(self):
        """
        Test fields supports date with year < 1900
        """
        obj = mock.Mock()

        with self.app.test_request_context(
                headers={'Accept-Language': 'fr-FR,fr;q=0.8'}):
            f = fields.DateTimeField(use_naive=False).bind(Form(), 'dt')
            f.process_formdata(['17/06/1789 | 10:42'])
            # 1789: applied offset for HongKong is equal to LMT+7:37:00,
            # thus we compare with tzinfo=user_tz
            assert f.data == datetime.datetime(
                1789, 6, 17, 10, 42, tzinfo=USER_TZ)
            # UTC stored
            assert f.data.tzinfo is pytz.UTC
            # displayed in user current timezone
            assert f._value() == '17/06/1789 10:42'

            # non-naive mode: test process_data change TZ to user's TZ
            f.process_data(f.data)
            assert f.data.tzinfo is USER_TZ
            assert f.data == datetime.datetime(
                1789, 6, 17, 10, 42, tzinfo=USER_TZ)

            f.populate_obj(obj, 'dt')
            assert obj.dt == datetime.datetime(
                1789, 6, 17, 10, 42, tzinfo=USER_TZ)

            # test more recent date: offset is GMT+8
            f.process_formdata(['23/01/2011 | 10:42'])
            assert f.data == datetime.datetime(
                2011, 1, 23, 2, 42, tzinfo=pytz.utc)

            # NAIVE mode: dates without timezone. Those are the problematic ones when
            # year < 1900: strptime will raise an Exception use naive dates; by
            # default
            f = fields.DateTimeField().bind(Form(), 'dt')
            f.process_formdata(['17/06/1789 | 10:42'])
            # UTC stored
            assert f.data.tzinfo is pytz.UTC
            assert f.data == datetime.datetime(
                1789, 6, 17, 10, 42, tzinfo=pytz.UTC)

            # naive stored
            f.populate_obj(obj, 'dt')
            assert obj.dt == datetime.datetime(1789, 6, 17, 10, 42)

    def test_datetimefield_force_4digit_year(self):
        # use 'en': short date pattern is u'M/d/yy'
        headers = {'Accept-Language': 'en'}
        with self.app.test_request_context(headers=headers):
            f = fields.DateTimeField().bind(Form(), 'dt')
            f.data = datetime.datetime(2011, 1, 23, 10, 42, tzinfo=pytz.utc)
            assert f._value() == u'1/23/2011, 6:42 PM'

    def test_date_field(self):
        """
        Test fields supports date with year < 1900
        """
        headers = {'Accept-Language': 'fr-FR,fr;q=0.8'}
        with self.app.test_request_context(headers=headers):
            f = fields.DateField().bind(Form(), 'dt')
            f.process_formdata(['17/06/1789'])
            assert f.data == datetime.date(1789, 6, 17)
            assert f._value() == u'17/06/1789'

    def test_datefield_force_4digit_year(self):
        # use 'en': short date pattern is u'M/d/yy'
        headers = {'Accept-Language': 'en'}
        with self.app.test_request_context(headers=headers):
            f = fields.DateField().bind(Form(), 'dt')
            f.data = datetime.date(2011, 1, 23)
            assert f._value() == u'1/23/2011'
