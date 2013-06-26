"""Base stuff for testing.
"""
import os

import subprocess
import requests


assert not 'twill' in subprocess.__file__

from flask.ext.testing import TestCase

from abilian.application import Application


__all__ = ['TestConfig', 'BaseTestCase']


class TestConfig(object):
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False
  TESTING = True
  SECRET_KEY = "SECRET"
  CSRF_ENABLED = False


class BaseTestCase(TestCase):
  config_class = TestConfig
  application_class = Application

  def create_app(self):
    config = self.config_class()
    self.app = self.application_class(config)
    return self.app

  def setUp(self):
    self.app.create_db()
    self.session = self.db.session

  def tearDown(self):
    self.db.session.remove()
    self.db.drop_all()
    self.db.engine.dispose()

  @property
  def db(self):
    return self.app.extensions['sqlalchemy'].db

  # Useful for debugging
  def dump_routes(self):
    rules = list(self.app.url_map.iter_rules())
    rules.sort(key=lambda x: x.rule)
    for rule in rules:
      print rule, rule.methods, rule.endpoint

  #
  # Validates HTML if asked by the config or the Unix environment
  #
  def get(self, url, validate=True):
    response = self.client.get(url)
    if not validate or response != 200:
      return response

    validator_url = self.app.config.get('VALIDATOR_URL') \
        or os.environ.get('VALIDATOR_URL')
    if not validator_url:
      return response

    content_type = response.headers['Content-Type']
    if content_type.split(';')[0].strip() != 'text/html':
      return response

    return self.validate(url, response.data, content_type, validator_url)

  # TODO: post(), put(), etc.

  def assert_valid(self, response):
    validator_url = self.app.config.get('VALIDATOR_URL') \
        or os.environ.get('VALIDATOR_URL')
    if validator_url:
      self.validate(None, response.data,
                    response.headers['Content-Type'], validator_url)

  def validate(self, url, content, content_type, validator_url):
    response = requests.post(validator_url + '?out=json', content,
                             headers={'Content-Type': content_type})

    body = response.json()

    for message in body['messages']:
      if message['type'] == 'error':
        detail = u'on line %s [%s]\n%s' % (
          message['lastLine'],
          message['extract'],
          message['message'])
        self.fail((u'Got a validation error for %r:\n%s' %
                   (url, detail)).encode('utf-8'))

