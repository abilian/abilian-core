"""
Elements to build test cases for an :class:`abilian.app.Application`
"""
import os
from time import time

import subprocess
import requests
import tempfile
import shutil
import warnings
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy.exc import SAWarning
from flask import url_for
from flask.ext.testing import TestCase
from flask.ext.login import login_user, logout_user
from abilian.core.models.subjects import User
from abilian.app import Application

assert not 'twill' in subprocess.__file__


__all__ = ['TestConfig', 'BaseTestCase']


class TestConfig(object):
  """
  Base class config settings for test cases.

  The environment variable :envvar:`SQLALCHEMY_DATABASE_URI` can be set to easily
  test against different databases.
  """
  SQLALCHEMY_DATABASE_URI = "sqlite://"
  SQLALCHEMY_ECHO = False
  TESTING = True
  SECRET_KEY = "SECRET"
  CSRF_ENABLED = False
  WTF_CSRF_ENABLED = False

  CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
  CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

  BABEL_DEFAULT_LOCALE = 'en'

  # It's a good idea to test with a timezone that's not your system timezone nor
  # UTC. It can reveal problem with date handling within app (rule is: all dates
  # are manipulated in UTC, and shown in user timezone).
  #
  # For example this one is GMT+8 and has no DST (tests should pass any time in
  # year)
  # BABEL_DEFAULT_TIMEZONE = 'Asia/Hong_Kong'
  BABEL_DEFAULT_TIMEZONE = 'UTC'  # this is flask-babel default

  def __init__(self):
    db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
      self.SQLALCHEMY_DATABASE_URI = db_uri


class BaseTestCase(TestCase):
  """
  Base test case to test an :class:`abilian.app.Application`.

  It will create an instance path that will be used and shared for all tests
  defined in this test case.

  The test case creates a clean database before running each test by calling
  :meth:`abilian.app.Application.create_db` et destroys it after test.

  Additionaly if the database is postgresql a schema is created for each test
  and the connection role is altered to use this DB schema. This is done to
  ensure harder test isolation.
  """

  #: Config class to use for :attr:`.application_class` configuration.
  config_class = TestConfig

  #: Application class to instantiate.
  application_class = Application

  #: Path to instance folder.  Mostly set for internal use, since you should
  #: access the value on the application (see `Flask instance folders
  #: <http://flask.pocoo.org/docs/config/#instance-folders>`_)
  #: This parameter is set by :meth:`setUpClass`
  TEST_INSTANCE_PATH = None

  #: By default sqlalchemy treats warnings as info. This settings makes
  #: sqlalchemy warnings treated as errors (and thus making test fail). The
  #: rationale is that it improves code quality (for example most frequent warnings
  #: are non-unicode string assigned on a Unicode column; this setting force you to
  #: be explicit and ensure unicode where appropriate)
  SQLALCHEMY_WARNINGS_AS_ERROR = True

  @classmethod
  def setUpClass(cls):
    TestCase.setUpClass()
    join = os.path.join
    tmp_dir = Path(tempfile.mkdtemp(prefix='tmp-py-unittest-',
                                    suffix='-' + cls.__name__,))
    cls.TEST_INSTANCE_PATH = str(tmp_dir)
    for p in  (tmp_dir/'tmp', tmp_dir/'cache', tmp_dir/'data'):
      p.mkdir()

    sa_warn = 'error' if cls.SQLALCHEMY_WARNINGS_AS_ERROR else 'default'
    warnings.simplefilter(sa_warn, SAWarning)

  @classmethod
  def tearDownClass(cls):
    if cls.TEST_INSTANCE_PATH:
      tmp_dir = Path(cls.TEST_INSTANCE_PATH)
      basename = tmp_dir.name
      if tmp_dir.is_dir() and basename.startswith('tmp-py-unittest'):
        shutil.rmtree(cls.TEST_INSTANCE_PATH)
        cls.TEST_INSTANCE_PATH = None

    TestCase.tearDownClass()

  def get_setup_config(self):
    """
    Called by :meth:`create_app` Override this if you want to tweak the config
    before :attr:`application_class` is instanciated.

    :return: an instance of :attr:`config_class`, or anything that is a valid
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
    # session_repository must be started before session is created, as it must
    # receive all transactions events. It also requires 'repository'.
    self.app.services['repository'].start()
    self.app.services['session_repository'].start()
    self.session = self.db.session()

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
    self.app.services['session_repository'].stop()
    TestCase.tearDown(self)

  def login(self, user, remember=False, force=False):
    """
    Perform user login for `user`, so that code needing a logged-in user can
    work.

    This method can also be used as a context manager, so that logout is
    performed automatically::

        with self.login(user):
            self.assertEquals(...)

    .. seealso:: :meth:`logout`
    """
    success = login_user(user, remember, force)
    if not success:
      raise ValueError(u'User is not active, cannot login; or use force=True')

    class LoginContext(object):
      def __init__(self, testcase):
        self.testcase = testcase

      def __enter__(self):
        return None

      def __exit__(self, type, value, traceback):
        self.testcase.logout()

    return LoginContext(self)

  def logout(self):
    """
    Perform user logout.

    .. seealso:: :meth:`login`
    """
    logout_user()

  def login_system(self):
    """
    Perform login with SYSTEM user. Can be used as a context manager.

    .. seealso:: :meth:`login`, :meth:`logout`
    """
    return self.login(User.query.get(0), force=True)

  def client_login(self, email, password):
    """
    Like :meth:`login` but with a web login request. Can be used as
    contextmanager.

    All subsequent request made with `self.client` will be authentifed until
    :meth:`client_logout` is called or exit of `with` block.
    """
    r = self.client.post(url_for('login.login_post'),
                         data={'email': email, 'password': password})
    self.assertEquals(r.status_code, 302)

    class LoginContext(object):
      def __init__(self, testcase):
        self.testcase = testcase

      def __enter__(self):
        return None

      def __exit__(self, type, value, traceback):
        self.testcase.client_logout()

    return LoginContext(self)


  def client_logout(self):
    """
    Like :meth:`logout` but with a web logout
    """
    self.client.post(url_for('login.logout'))

  @property
  def db(self):
    """
    Shortcut to the application db object.
    """
    return self.app.extensions['sqlalchemy'].db

  def assert_302(self, response):
    self.assert_status(response, 302)

  def get(self, url, validate=True):
    """
    Validates HTML if asked by the config or the Unix environment.
    """
    response = self.client.get(url)
    if validate and response == 200:
      self.assert_valid(response)

    return response

  # TODO: post(), put(), etc.

  def assert_valid(self, response):
    """
    Validate `response.data` as HTML using validator provided by
    `config.VALIDATOR_URL`.
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
