# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json
from functools import partial

from flask import request, url_for

from abilian.core.models.subjects import User
from abilian.services.auth import views
from abilian.testing import BaseTestCase, TestConfig


class AuthTestConfig(TestConfig):
    # Most views should not be protected by crsf. Let it fail if @csrf.exempt is
    # forgotten on a view.
    CSRF_ENABLED = True
    WTF_CSRF_ENABLED = True


class TestAuth(BaseTestCase):

    config_class = AuthTestConfig

    CLEAR_PASSWORDS = False

    def test_get_redirect_target(self):
        get_redirect_target = views.get_redirect_target
        form_url = partial(url_for, 'login.login_form')

        with self.app.test_request_context(form_url()):
            assert get_redirect_target() is None
            url_root = request.url_root[:-1]

        with self.app.test_request_context(form_url(next=u'/')):
            assert get_redirect_target() == url_root + u'/'

        # test "next" from referer
        referrer = url_root + u'/some/path'
        with self.app.test_request_context(form_url(),
                                           headers=[('Referer', referrer)]):
            assert get_redirect_target() == referrer

        # don't cycle if coming from 'login.*' page, like this kind of cycle:
        # forgot password form ->  login page -> success
        # -> redirect(next = forgot password form) -> ...
        referrer = url_root + url_for('login.forgotten_pw')
        with self.app.test_request_context(form_url(),
                                           headers=[('Referer', referrer)]):
            assert get_redirect_target() is None

        # test open redirect is forbidden
        with self.app.test_request_context(form_url(
                next=u'http://google.com/test')):
            assert get_redirect_target() is None

        # open redirect through malicious construct and browser not checking Location
        with self.app.test_request_context(form_url(next=u'/////google.com')):
            assert get_redirect_target() == url_root + u'///google.com'

    def test_login_post(self):
        kwargs = dict(email=u'User@domain.tld',
                      password='azerty',
                      can_login=True)
        u = User(**kwargs)
        self.session.add(u)
        self.session.commit()

        rv = self.client.post('/user/login', data=kwargs)
        self.assertEquals(rv.status_code, 302, "expected 302, got:" + rv.status)

        # wrong password
        d = dict(kwargs)
        d['password'] = 'wrong one'
        rv = self.client.post('/user/login', data=d)
        self.assertEquals(rv.status_code, 401, "expected 401, got:" + rv.status)

        # login disabled
        u.can_login = False
        self.session.commit()
        rv = self.client.post('/user/login', data=kwargs)
        self.assertEquals(rv.status_code, 401, "expected 401, got:" + rv.status)

    def test_api_post(self):
        kwargs = dict(email=u'User@domain.tld',
                      password='azerty',
                      can_login=True)
        u = User(**kwargs)
        self.session.add(u)
        self.session.commit()

        rv = self.client.post('/user/api/login',
                              data=json.dumps(kwargs),
                              content_type='application/json')
        self.assertEquals(rv.status_code, 200, "expected 200, got:" + rv.status)
        self.assertEquals(rv.json,
                          dict(email=u'User@domain.tld',
                               username=u'user@domain.tld',
                               fullname=u'Unknown',
                               next_url=u''))

        rv = self.client.post('/user/api/logout')
        self.assertEquals(rv.status_code, 200, "expected 200, got:" + rv.status)

    def test_forgotten_pw(self):
        mail = self.app.extensions['mail']
        kwargs = dict(email=u'User@domain.tld',
                      password='azerty',
                      can_login=True)
        u = User(**kwargs)
        self.session.add(u)
        self.session.commit()

        payload = dict()
        payload.update(kwargs)
        del payload['password']

        with mail.record_messages() as outbox:
            rv = self.client.post('/user/forgotten_pw', data=kwargs)
            self.assertEquals(rv.status_code, 302,
                              "expected 302, got:" + rv.status)
            self.assertEquals(len(outbox), 1)
            msg = outbox[0]
            self.assertEquals(msg.subject,
                              u'Password reset instruction for Abilian Test')
            self.assertEquals(msg.recipients, [u'User@domain.tld'])
            self.assertEquals(msg.cc, [])
