# coding=utf-8
"""
"""
from __future__ import absolute_import

import json
from abilian.testing import BaseTestCase
from abilian.core.models.subjects import User

class TestAuth(BaseTestCase):

  def test_login_post(self):
    kwargs = dict(email=u'user@domain.tld', password='azerty', can_login=True)
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
    kwargs = dict(email=u'user@domain.tld', password='azerty', can_login=True)
    u = User(**kwargs)
    self.session.add(u)
    self.session.commit()

    rv = self.client.post('/user/api/login', data=json.dumps(kwargs),
                          content_type='application/json')
    self.assertEquals(rv.status_code, 200, "expected 200, got:" + rv.status)
    self.assertEquals(rv.json, dict(email=u'user@domain.tld',
                                    username=u'user@domain.tld',
                                    fullname=u'Unknown',
                                    next_url=u''))


    rv = self.client.post('/user/api/logout')
    self.assertEquals(rv.status_code, 200, "expected 200, got:" + rv.status)
