# coding=utf-8
"""
"""
from __future__ import absolute_import

from abilian.testing import BaseTestCase
from abilian.core.subjects import User

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

