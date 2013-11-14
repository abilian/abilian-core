# coding=utf-8
"""
"""
from __future__ import absolute_import

from collections import OrderedDict, namedtuple
import sqlalchemy as sa
import redis

from flask import (
  Blueprint, render_template, request, flash, session, redirect, url_for,
)

setup = Blueprint('setup', __name__, template_folder='templates')

# list supported dialects and detect unavailable ones due to missing dbapi
# module ('psycopg2' missing for example)

_dialects = OrderedDict((
    ('sqlite', u'SQLite (for demo)'),
    ('postgres', u'PostgreSQL'),
  ))

_dialects_unavailable = OrderedDict()

for dialect, label in _dialects.iteritems():
  d = sa.dialects.registry.load(dialect)
  try:
    d.dbapi()
  except ImportError as e:
    _dialects_unavailable[dialect] = e.message

# enumerate steps for left column progress
Step = namedtuple('SetupStep', ('endpoint', 'title', 'description'))

_setup_steps = (
  Step('step_db', 'Setup Database', 'Setup basic database connection'),
  Step('step_redis', 'Setup Redis', 'Redis connection'),
  Step('step_site_info', 'Basic site informations', 'Site name, admin email...'),
  )

@setup.before_request
def step_progress():
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
    }

  ctx.update(request.setup_step_progress)
  return ctx

# session helpers
def session_set(key, data):
  session.setdefault('abilian_setup', {})[key] = data

def session_get(key, default=None):
  return session.setdefault('abilian_setup', {}).get(key, default)

def step_validated(step_endpoint, valid=True):
  validated = set(session_get('validated', ()))
  if valid:
    validated.add(step_endpoint)
  else:
    if step_endpoint in validated:
      validated.remove(step_endpoint)

  session_set('validated', tuple(validated))

# DB Setup ####################
@setup.route('', methods=['GET', 'POST'])
def step_db():
  if request.method == 'POST':
    return step_db_validate()
  return step_db_form()

def step_db_form():
  return render_template('setupwizard/step_db.html',
                         data=session_get('db',  {}))

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

  if dialect == u'sqlite' and not database:
    database = u':memory:'

  db_uri += database

  # store in session
  db_params = dict(
    uri=db_uri,
    dialect=dialect,
    username=username, password=password,
    host=host, port=port,
    database=database,
  )
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

# Redis ####################
@setup.route('/redis', methods=['GET', 'POST'])
def step_redis():
  if request.method == 'POST':
    return step_redis_validate()
  return step_redis_form()

def step_redis_form():
  return render_template('setupwizard/step_redis.html',
                         data=session_get('redis', {}))

def step_redis_validate():
  form = request.form
  data = dict(
    host=form.get(u'host', u'localhost').strip(),
    port=form.get(u'port', u'').strip() or u'6379',
    db=form.get(u'db', u'').strip() or u'1',
  )

  for k in ('port', 'db'):
    try:
      data[k] = int(data[k])
    except ValueError:
      pass

  session_set('redis', data)
  error = None

  try:
    r = redis.StrictRedis(**data)
  except Exception as e:
    error = u'Connection error, check parameters'
    raise e

  try:
    r.client_list()
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


# Site info ####################
@setup.route('/site_info', methods=['GET', 'POST'])
def step_site_info():
  if request.method == 'POST':
    return step_db_validate()
  return step_site_info_form()

def step_site_info_form():
  return render_template('setupwizard/step_site_info.html',
                         data=session_get('site_info', {}))
