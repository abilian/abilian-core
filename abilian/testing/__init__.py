""" Elements to build test cases of an :class:`abilian.app.Application`
"""
import os
from time import time

import subprocess
import requests
import tempfile
import shutil
import warnings

from sqlalchemy.exc import SAWarning
from flask.ext.testing import TestCase
from abilian.app import Application

assert not 'twill' in subprocess.__file__


__all__ = ['TestConfig', 'BaseTestCase']


class TestConfig(object):
  """ Base class config settings for test cases.

    Environment variable :envvar:`SQLALCHEMY_DATABASE_URI` can be set to easily
    test against different databases.
  """
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False
  TESTING = True
  SECRET_KEY = "SECRET"
  CSRF_ENABLED = False

  def __init__(self):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
      self.SQLALCHEMY_DATABASE_URI = db_uri


class BaseTestCase(TestCase):
  """ Base test case to test an :class:`abilian.app.Application`.

  It will create an instance path that will be used and shared for all tests
  defined in this test case.

  The test case creates a clean database before running each test by calling
  :meth:`abilian.app.Application.create_db` et destroys it after test.

  Additionaly if the database is postgresql a schema is created for each test
  and the connection role is altered to use this DB schema. This is done to
  ensure harder test isolation.
  """

  #: config class to use for :attr:`application_class` configuration
  config_class = TestConfig

  #: Application class to instantiate
  application_class = Application

  TEST_INSTANCE_PATH = None
  """ Path to instance folder.  Mostly set for internal use, since you should
  access the value on the application (see `Flask instance folders
  <http://flask.pocoo.org/docs/config/#instance-folders>`_)

  This parameter is set by :meth:`setUpClass`
  """

  SQLALCHEMY_WARNINGS_AS_ERROR = True
  """ By default sqlalchemy treats warnings as info. This settings makes
  sqlalchemy warnings treated as errors (and thus making test fail). The
  rationale is that it improves code quality (for example most frequent warnings
  are non-unicode string assigned on a Unicode column; this setting force you to
  be explicit and ensure unicode where appropriate)
  """

  @classmethod
  def setUpClass(cls):
    TestCase.setUpClass()
    join = os.path.join
    tmp_dir = cls.TEST_INSTANCE_PATH = tempfile.mkdtemp(
      prefix='tmp-py-unittest-',
      suffix='-' + cls.__name__,
    )
    os.mkdir(join(tmp_dir, 'tmp'))
    os.mkdir(join(tmp_dir, 'cache'))

    sa_warn = 'error' if cls.SQLALCHEMY_WARNINGS_AS_ERROR else 'default'
    warnings.simplefilter(sa_warn, SAWarning)

  @classmethod
  def tearDownClass(cls):
    tmp_dir = cls.TEST_INSTANCE_PATH
    if tmp_dir:
      is_dir = os.path.isdir(tmp_dir)
      basename = os.path.basename(tmp_dir)
      if is_dir and basename.startswith('tmp-py-unittest'):
        shutil.rmtree(tmp_dir)
        cls.TEST_INSTANCE_PATH = None

    TestCase.tearDownClass()

  def get_setup_config(self):
    """ Called by `create_app` Override this if you want to tweak the config
    before :attr:`application_class` is instanciated.

    :return: an instance of :attr:`config_class`, or anything that is valid
             config object for Flask.
    """
    return self.config_class()

  def create_app(self):
    config = self.get_setup_config()
    self.app = self.application_class(
      config=config,
      instance_path=self.TEST_INSTANCE_PATH,
    )
    return self.app

  def setUp(self):
    TestCase.setUp(self)
    self.session = self.db.session

    if self.db.engine.name == 'postgresql':
      # ensure we are on a clean DB: let's use our own schema
      self.__pg_schema = 'test_{}'.format(str(time()).replace('.', '_'))
      username = self.db.engine.url.username
      with self.db.engine.connect() as conn:
        with conn.begin():
          conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(self.__pg_schema))
          conn.execute('CREATE SCHEMA {}'.format(self.__pg_schema))
          conn.execute('SET search_path TO {}'.format(self.__pg_schema))
          conn.execute(
            'ALTER ROLE {username} SET search_path TO {schema}'
            ''.format(username=username, schema=self.__pg_schema))
        conn.execute('COMMIT')
    self.app.create_db()

  def tearDown(self):
    self.db.session.remove()
    self.db.drop_all()

    if self.db.engine.name == 'postgresql':
      username = self.db.engine.url.username
      with self.db.engine.connect() as conn:
        with conn.begin():
          conn.execute('ALTER ROLE {username} SET search_path TO public'
                       ''.format(username=username))
          conn.execute('SET search_path TO public')
          conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(self.__pg_schema))
        conn.execute('COMMIT')
      del self.__pg_schema

    self.db.engine.dispose()
    TestCase.tearDown(self)

  @property
  def db(self):
    """ Shortcut to application db object
    """
    return self.app.extensions['sqlalchemy'].db

  def assert_302(self, response):
    self.assert_status(response, 302)

  def get(self, url, validate=True):
    """ Validates HTML if asked by the config or the Unix environment.
    """
    response = self.client.get(url)
    if validate and response == 200:
      self.assert_valid(response)

    return response

  # TODO: post(), put(), etc.

  def assert_valid(self, response):
    """ Validate html with config.VALIDATOR_URL
    """
    # FIXME: put this and document in TestConfig class
    validator_url = self.app.config.get('VALIDATOR_URL') \
        or os.environ.get('VALIDATOR_URL')
    if not validator_url:
      return

    content_type = response.headers['Content-Type']
    if content_type.split(';')[0].strip() != 'text/html':
      return

    self.validate(None, response.data, content_type, validator_url)

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
