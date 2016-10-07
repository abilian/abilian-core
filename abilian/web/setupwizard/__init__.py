# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

import os
import socket
import logging
from collections import OrderedDict, namedtuple
from pathlib import Path

import sqlalchemy as sa
import redis

from flask import (render_template, request, flash, session, redirect, url_for,
                   current_app, make_response)
import six
from six import text_type

from abilian.services import get_service
from abilian.services.security import Admin
from abilian.core.models.subjects import User
from abilian.core.commands import config as cmd_config
from abilian.core.extensions import csrf
from abilian.services.security import Anonymous
from abilian.web.blueprints import Blueprint

logger = logging.getLogger(__name__)
setup = Blueprint(
    'setup', __name__, allowed_roles=Anonymous, template_folder='templates')

# list supported dialects and detect unavailable ones due to missing dbapi
# module ('psycopg2' missing for example)

_dialects = OrderedDict((
    ('sqlite', u'SQLite (for demo)'),
    ('postgres', u'PostgreSQL'),))

_dialects_unavailable = OrderedDict()

for dialect, label in six.iteritems(_dialects):
    d = sa.dialects.registry.load(dialect)
    try:
        d.dbapi()
    except ImportError as e:
        _dialects_unavailable[dialect] = e.message

# enumerate steps for left column progress
Step = namedtuple('SetupStep', ('name', 'endpoint', 'title', 'description'))

_setup_steps = (
    Step('db', 'step_db', 'Setup Database', 'Setup basic database connection'),
    Step('redis', 'step_redis', 'Setup Redis', 'Redis connection'), Step(
        'site_info', 'step_site_info', 'Basic site informations',
        'Site name, admin email...'),
    Step('admin_account', 'step_admin_account', u'Admin account', None),
    Step('finalize', 'finalize', 'Finalize', None))


@setup.before_request
def step_progress():
    session.permanent = False  # limit lifetime to browser session
    current_step = next_step = prev_step = None

    for step in _setup_steps:
        if current_step is not None:
            next_step = step
            break
        endpoint = '{}.{}'.format(setup.name, step.endpoint)
        if endpoint == request.endpoint:
            current_step = step
        else:
            prev_step = step

    request.setup_step_progress = {
        'current_step': current_step,
        'prev_step': prev_step,
        'next_step': next_step,
    }


@setup.context_processor
def common_context():
    ctx = {
        'setup_steps': _setup_steps,
        'dialects': _dialects,
        'dialects_unavailable': _dialects_unavailable,
        'validated_steps': session_get('validated', ())
    }

    ctx.update(request.setup_step_progress)
    return ctx


# session helpers
def session_set(key, data):
    session.setdefault('abilian_setup', {})[key] = data


def session_get(key, default=None):
    return session.setdefault('abilian_setup', {}).get(key, default)


def session_clear():
    if 'abilian_setup' in session:
        del session['abilian_setup']


def step_validated(step_endpoint, valid=True):
    validated = set(session_get('validated', ()))
    if valid:
        validated.add(step_endpoint)
    else:
        if step_endpoint in validated:
            validated.remove(step_endpoint)

    session_set('validated', tuple(validated))


#
# DB Setup
#
@csrf.exempt
@setup.route('/', methods=['GET', 'POST'])
def step_db():
    if request.method == 'POST':
        return step_db_validate()
    return step_db_form()


def step_db_form():
    return render_template(
        'setupwizard/step_db.html', data=session_get('db', {}))


def step_db_validate():
    form = request.form
    dialect = form['dialect']
    username = form.get(u'username', u'').strip()
    password = form.get(u'password', u'').strip()
    host = form.get(u'host', u'').strip()
    port = form.get(u'port', u'').strip()
    database = form.get(u'database', u'').strip()

    # build db_uri
    db_uri = u'{}://'.format(dialect)

    if dialect != u'sqlite':
        if username:
            db_uri += username
            # check password only if we have a username
            if password:
                db_uri += u':' + password

        #FIXME: it is an error to have a username and no host, SA will interpret
        # username:password as host:port
        if host:
            db_uri += u'@' + host
            port = port
            if port:
                db_uri += u':' + port

    db_uri += u'/'

    if dialect == u'sqlite' and (not database or database == u':memory:'):
        database = text_type(
            Path(current_app.instance_path) / u'data' / u'sqlite.db')

    db_uri += database

    # store in session
    db_params = dict(
        uri=db_uri,
        dialect=dialect,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,)
    session_set('db', db_params)

    # test connection
    engine = sa.create_engine(db_uri)
    error = None
    try:
        conn = engine.connect()
    except sa.exc.OperationalError as e:
        error = e.message
    else:
        conn.close()
        del conn

    engine.dispose()

    # FIXME: at this point we have not tested the connection is valid, i.e, we
    # have CREATE, SELECT, UPDATE, DELETE rights on the database

    if error:
        flash(error, 'error')
        return step_db_form()

    step_validated('db')
    next_step = request.setup_step_progress['next_step']
    return redirect(url_for('{}.{}'.format(setup.name, next_step.endpoint)))


#
# Redis
#
@csrf.exempt
@setup.route('/redis', methods=['GET', 'POST'])
def step_redis():
    if request.method == 'POST':
        return step_redis_validate()
    return step_redis_form()


def step_redis_form():
    return render_template(
        'setupwizard/step_redis.html', data=session_get('redis', {}))


def step_redis_validate():
    form = request.form
    data = dict(
        host=form.get(u'host', u'localhost').strip(),
        port=form.get(u'port', u'').strip() or u'6379',
        db=form.get(u'db', u'').strip() or u'1',)

    for k in ('port', 'db'):
        try:
            data[k] = int(data[k])
        except ValueError:
            pass

    data['uri'] = u'redis://{host}:{port}/{db}'.format(**data)
    session_set('redis', data)
    error = None

    try:
        r = redis.StrictRedis(
            host=data['host'], port=data['port'], db=data['db'])
    except Exception as e:
        error = u'Connection error, check parameters'
        raise e

    try:
        r.info()
    except redis.exceptions.InvalidResponse:
        error = (u"Connection error: doesn't look like it's a redis server. "
                 u"Verify host and port are those of your redis server.")
    except redis.exceptions.ResponseError as e:
        error = u'Redis server response: {}'.format(e)
    except redis.exceptions.RedisError as e:
        error = u'Unknown redis error ({})'.format(e)

    if error:
        flash(error, 'error')
        return step_redis_form()

    step_validated('redis')
    next_step = request.setup_step_progress['next_step']
    return redirect(url_for('{}.{}'.format(setup.name, next_step.endpoint)))


#
# Site info
#
@csrf.exempt
@setup.route('/site_info', methods=['GET', 'POST'])
def step_site_info():
    if request.method == 'POST':
        return step_site_info_validate()
    return step_site_info_form()


def get_possible_hostnames():
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    names = {'localhost': ['127.0.0.1']}

    for name in (hostname, fqdn):
        try:
            name, aliases, ips = socket.gethostbyname_ex(name)
        except socket.error:
            continue
        names.setdefault(name, []).extend(ips)
        for a in aliases:
            names.setdefault(a, []).extend(ips)

    return sorted(u'{} ({})'.format(name, u', '.join(sorted(set(ips))))
                  for name, ips in six.iteritems(names))


def step_site_info_form():
    cfg = current_app.config
    default_data = {
        'sitename': cfg.get('SITE_NAME', u'') or u'',
        'mailsender': cfg.get('MAIL_SENDER', u'') or u'',
    }
    return render_template(
        'setupwizard/step_site_info.html',
        data=session_get('site_info', default_data),
        suggested_hosts=get_possible_hostnames())


def step_site_info_validate():
    form = request.form
    data = dict(
        sitename=form.get('sitename', u'').strip(),
        mailsender=form.get('mailsender', u'').strip(),
        server_mode=form.get('server_mode', u'').strip())

    session_set('site_info', data)
    step_validated('site_info')
    next_step = request.setup_step_progress['next_step']
    return redirect(url_for('{}.{}'.format(setup.name, next_step.endpoint)))


#
# Admin account creation
#
@csrf.exempt
@setup.route('/admin_account', methods=['GET', 'POST'])
def step_admin_account():
    if request.method == 'POST':
        return step_admin_account_validate()
    return step_admin_account_form()


def step_admin_account_form():
    return render_template(
        'setupwizard/step_admin_account.html',
        data=session_get('admin_account', {}))


def step_admin_account_validate():
    form = request.form
    password = form.get('password', u'').strip()
    confirm_password = form.get('confirm_password', u'').strip()
    admin_user = dict(
        email=form.get('email', u'').strip(),
        name=form.get('name', u'').strip(),
        firstname=form.get('firstname', u'').strip(),
        password=password,
        confirm_password=confirm_password)
    session_set('admin_account', admin_user)

    if password != confirm_password:
        flash('Password fields don\'t match', 'error')
        return step_admin_account_form()

    step_validated('admin_account')
    next_step = request.setup_step_progress['next_step']
    return redirect(url_for('{}.{}'.format(setup.name, next_step.endpoint)))


#
# Finalize
#
@csrf.exempt
@setup.route('/finalize', methods=['GET', 'POST'])
def finalize():
    validated = session_get('validated')
    assert all(s.name in validated for s in _setup_steps[:-1])

    if request.method == 'POST':
        return finalize_validate()
    return finalize_form()


def finalize_form():
    file_location = os.path.join(current_app.instance_path, 'config.py')
    return render_template(
        'setupwizard/finalize.html', file_location=file_location)


def finalize_validate():
    config_file = os.path.join(current_app.instance_path, 'config.py')
    logging_file = os.path.join(current_app.instance_path, 'logging.yml')

    assert not os.path.exists(config_file)
    config = cmd_config.DefaultConfig(logging_file='logging.yml')
    config.SQLALCHEMY_DATABASE_URI = session_get('db')['uri']

    redis_uri = session_get('redis')['uri']
    config.REDIS_URI = redis_uri
    config.BROKER_URL = redis_uri
    config.CELERY_RESULT_BACKEND = redis_uri

    d = session_get('site_info')
    config.SITE_NAME = d['sitename']
    config.MAIL_SENDER = d['mailsender']

    is_production = d['server_mode'] == u'production'
    config.PRODUCTION = is_production
    config.DEBUG = not is_production
    config.DEBUG_TB_ENABLED = config.DEBUG
    config.CELERY_ALWAYS_EAGER = not is_production

    cmd_config.write_config(config_file, config)
    cmd_config.maybe_write_logging(logging_file)

    admin_account = session_get('admin_account')
    # create a new app that will be configured with new config, to create database
    # and admin_user
    setup_app = current_app._get_current_object()
    app = setup_app.__class__(
        setup_app.import_name,
        static_url_path=setup_app.static_url_path,
        static_folder=setup_app.static_folder,
        template_folder=setup_app.template_folder,
        instance_path=setup_app.instance_path,)
    with app.test_request_context('/setup/finalize'):
        app.create_db()
        db_session = app.db.session()
        admin = User(
            email=admin_account['email'],
            password=admin_account['password'],
            last_name=admin_account['name'],
            first_name=admin_account['firstname'],
            can_login=True)
        db_session.add(admin)
        security = get_service('security')
        security.grant_role(admin, Admin)
        db_session.commit()

    session_clear()

    response = make_response(
        render_template(
            'setupwizard/done.html',
            config_file=config_file,
            logging_file=logging_file),
        200)
    return response
