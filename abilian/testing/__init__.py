# coding=utf-8
"""
Elements to build test cases for an :class:`abilian.app.Application`
"""
from __future__ import absolute_import, print_function, division, unicode_literals

import getpass

from six import string_types

import os
from time import time
import subprocess
import requests
import tempfile
import shutil
import warnings
from pathlib import Path

from sqlalchemy.exc import SAWarning
from flask import url_for
from flask_testing import TestCase
from flask_login import login_user, logout_user
from flask_assets import Bundle

from abilian.app import Application
from abilian.core.models.subjects import User, ClearPasswordStrategy

assert 'twill' not in subprocess.__file__

__all__ = ['TestConfig', 'BaseTestCase']

_CLEAR_PWD = ClearPasswordStrategy()
_DEFAULT_PWD = User.__password_strategy__


class NullBundle(Bundle):
    """
    This bundle class emits no url, thus avoid any asset build. Saves a lot of
    time during tests.
    """

    def urls(self):
        return []


class TestConfig(object):
    """
    Base class config settings for test cases.

    The environment variable :envvar:`SQLALCHEMY_DATABASE_URI` can be set to easily
    test against different databases.
    """
    SITE_NAME = 'Abilian Test'
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SERVER_NAME = 'localhost'  # needed for url_for with '_external=True'
    SQLALCHEMY_ECHO = False
    TESTING = True
    SECRET_KEY = "SECRET"
    CSRF_ENABLED = False
    WTF_CSRF_ENABLED = False

    # during tests let httpexceptions be raised
    TRAP_HTTP_EXCEPTIONS = False
    TRAP_BAD_REQUEST_ERRORS = True

    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    MAIL_SENDER = 'test@testcase.app.tld'

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

    #: list services names that should be started during setUp. 'repository' and
    #: 'session_repository' services are always started, do not list them here.
    SERVICES = ()

    #: enable assets building during tests. False by default.
    TESTING_BUILD_ASSETS = False

    #: set to False to use cryptographic scheme (standard) for user password. By
    #: default the testcase switches to clear text to avoid longer running.
    CLEAR_PASSWORDS = True

    @classmethod
    def setUpClass(cls):
        TestCase.setUpClass()

        if not isinstance(cls.SERVICES, tuple):
            if isinstance(cls.SERVICES, string_types):
                cls.SERVICES = (cls.SERVICES,)
            else:
                cls.SERVICES = tuple(cls.SERVICES)

        tmp_dir = Path(
            tempfile.mkdtemp(
                prefix='tmp-py-unittest-',
                suffix='-' + cls.__name__,))
        cls.TEST_INSTANCE_PATH = str(tmp_dir)
        for p in (tmp_dir / 'tmp', tmp_dir / 'cache', tmp_dir / 'data'):
            p.mkdir()

        # sa_warn = 'error' if cls.SQLALCHEMY_WARNINGS_AS_ERROR else 'default'
        sa_warn = 'default'  # FIXME
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
            instance_path=self.TEST_INSTANCE_PATH,)
        return self.app

    def setUp(self):
        TestCase.setUp(self)

        User.__password_strategy__ = _CLEAR_PWD if self.CLEAR_PASSWORDS else _DEFAULT_PWD

        if not self.TESTING_BUILD_ASSETS:
            extensions = self.app.jinja_env.extensions
            assets_ext = extensions['webassets.ext.jinja2.AssetsExtension']
            assets_ext.BundleClass = NullBundle

        # session_repository must be started before session is created, as it must
        # receive all transactions events. It also requires 'repository'.
        self.app.services['repository'].start()
        self.app.services['session_repository'].start()
        self.session = self.db.session()

        if self.db.engine.name == 'postgresql':
            # ensure we are on a clean DB: let's use our own schema
            self.__pg_schema = 'test_{}'.format(str(time()).replace('.', '_'))
            username = self.db.engine.url.username or getpass.getuser()
            with self.db.engine.connect() as conn:
                with conn.begin():
                    conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(
                        self.__pg_schema))
                    conn.execute('CREATE SCHEMA {}'.format(self.__pg_schema))
                    conn.execute('SET search_path TO {}'.format(
                        self.__pg_schema))
                    conn.execute(
                        'ALTER ROLE {username} SET search_path TO {schema}'
                        ''.format(
                            username=username, schema=self.__pg_schema))
                conn.execute('COMMIT')

        self.app.create_db()

        for svc in self.SERVICES:
            svc = self.app.services[svc]
            if not svc.running:
                svc.start()

    def tearDown(self):
        for svc in self.SERVICES:
            svc = self.app.services[svc]
            if svc.running:
                svc.stop()

        self.db.session.remove()

        with self.db.engine.connect() as conn:
            if self.db.engine.name == 'postgresql':
                username = self.db.engine.url.username or getpass.getuser()
                with self.db.engine.connect() as conn:
                    with conn.begin():
                        conn.execute(
                            'ALTER ROLE {username} SET search_path TO public'
                            ''.format(username=username))
                        conn.execute('SET search_path TO public')
                        conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(
                            self.__pg_schema))
                    conn.execute('COMMIT')
                del self.__pg_schema
            else:
                if self.db.engine.name == 'sqlite':
                    # core.extension.sqlalchemy performs a 'PRAGMA foreign_keys=ON' on a
                    # connection listener.
                    #
                    # We must revert it to perform drop_all without ever encounting a
                    # foreign key error
                    conn.execute("PRAGMA foreign_keys=OFF;")

                self.db.metadata.drop_all(bind=conn)

        self.db.engine.dispose()
        self.app.services['session_repository'].stop()
        self.app.services['repository'].stop()

        User.__password_strategy__ = _DEFAULT_PWD

        # Resets babel extension
        babel = self.app.extensions['babel']
        babel.locale_selector_func = None
        babel.timezone_selector_func = None

        TestCase.tearDown(self)

    def _login_tests_sanity_check(self):
        """
        For login methods: perform checks to avoid using login methods whereas
        application will not perform auth or security checks.
        """
        if self.app.config.get('NO_LOGIN'):
            raise RuntimeError('login is useless when "NO_LOGIN" is set. '
                               'Fix testcase.')

        if not self.app.services['security'].running:
            raise RuntimeError(
                'trying to use login in test but security service is '
                'not running. Fix testcase.')

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
        self._login_tests_sanity_check()
        success = login_user(user, remember, force)
        if not success:
            raise ValueError(
                'User is not active, cannot login; or use force=True')

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
        self._login_tests_sanity_check()

        r = self.client.post(
            url_for('login.login_post'),
            data={'email': email,
                  'password': password})
        self.assertEqual(r.status_code, 302)

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
        response = requests.post(
            validator_url + '?out=json',
            content,
            headers={'Content-Type': content_type})

        body = response.json()

        for message in body['messages']:
            if message['type'] == 'error':
                detail = 'on line {0} [{1}]\n{2}'.format(
                    message['lastLine'], message['extract'], message['message'])
                self.fail('Got a validation error for %r:\n%s' % (url, detail))
