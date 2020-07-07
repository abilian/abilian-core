""""""
import logging
import socket
from collections import OrderedDict, namedtuple
from pathlib import Path
from typing import Dict, Text

import redis
import sqlalchemy as sa
import sqlalchemy.dialects
import sqlalchemy.exc
from flask import current_app, flash, redirect, render_template, request, \
    session, url_for

from abilian.core.commands import config as cmd_config
from abilian.core.extensions import csrf, db
from abilian.core.models.subjects import User
from abilian.core.util import unwrap
from abilian.services import get_service
from abilian.services.security import Admin, Anonymous
from abilian.web.blueprints import Blueprint

logger = logging.getLogger(__name__)
setup = Blueprint(
    "setup", __name__, allowed_roles=Anonymous, template_folder="templates"
)

# list supported dialects and detect unavailable ones due to missing dbapi
# module ('psycopg2' missing for example)

_dialects = OrderedDict((("sqlite", "SQLite (for demo)"), ("postgresql", "PostgreSQL")))

_dialects_unavailable = OrderedDict()  # type: Dict[Text, Text]

for dialect, _label in _dialects.items():
    d = sa.dialects.registry.load(dialect)
    try:
        d.dbapi()
    except ImportError as e:
        _dialects_unavailable[dialect] = str(e)

# enumerate steps for left column progress
Step = namedtuple("SetupStep", ("name", "endpoint", "title", "description"))

_setup_steps = (
    Step("db", "step_db", "Setup Database", "Setup basic database connection"),
    Step("redis", "step_redis", "Setup Redis", "Redis connection"),
    Step(
        "site_info",
        "step_site_info",
        "Basic site informations",
        "Site name, admin email...",
    ),
    Step("admin_account", "step_admin_account", "Admin account", None),
    Step("finalize", "finalize", "Finalize", None),
)


@setup.before_request
def step_progress():
    session.permanent = False  # limit lifetime to browser session
    current_step = next_step = prev_step = None

    for step in _setup_steps:
        if current_step is not None:
            next_step = step
            break
        endpoint = f"{setup.name}.{step.endpoint}"
        if endpoint == request.endpoint:
            current_step = step
        else:
            prev_step = step

    request.setup_step_progress = {
        "current_step": current_step,
        "prev_step": prev_step,
        "next_step": next_step,
    }


@setup.context_processor
def common_context():
    ctx = {
        "setup_steps": _setup_steps,
        "dialects": _dialects,
        "dialects_unavailable": _dialects_unavailable,
        "validated_steps": session_get("validated", ()),
    }
    ctx.update(request.setup_step_progress)
    return ctx


# session helpers
def session_set(key, data):
    session.setdefault("abilian_setup", {})[key] = data


def session_get(key, default=None):
    return session.setdefault("abilian_setup", {}).get(key, default)


def session_clear():
    if "abilian_setup" in session:
        del session["abilian_setup"]


def step_validated(step_endpoint, valid=True):
    validated = set(session_get("validated", ()))
    if valid:
        validated.add(step_endpoint)
    else:
        if step_endpoint in validated:
            validated.remove(step_endpoint)

    session_set("validated", tuple(validated))


#
# DB Setup
#
@csrf.exempt
@setup.route("/", methods=["GET", "POST"])
def step_db():
    if request.method == "POST":
        return step_db_validate()
    return step_db_form()


def step_db_form():
    return render_template("setupwizard/step_db.html", data=session_get("db", {}))


def step_db_validate():
    form = request.form
    dialect = form["dialect"]
    username = form.get("username", "").strip()
    password = form.get("password", "").strip()
    host = form.get("host", "").strip()
    port = form.get("port", "").strip()
    database = form.get("database", "").strip()

    # build db_uri
    db_uri = f"{dialect}://"

    if dialect != "sqlite":
        if username:
            db_uri += username
            # check password only if we have a username
            if password:
                db_uri += ":" + password

        # FIXME: it is an error to have a username and no host,
        # SA will interpret username:password as host:port
        if host:
            db_uri += "@" + host
            if port:
                db_uri += ":" + port

    db_uri += "/"

    if dialect == "sqlite" and (not database or database == ":memory:"):
        database = str(Path(current_app.instance_path) / "data" / "sqlite.db")

    db_uri += database

    # store in session
    db_params = {
        "uri": db_uri,
        "dialect": dialect,
        "username": username,
        "password": password,
        "host": host,
        "port": port,
        "database": database,
    }
    session_set("db", db_params)

    # test connection
    engine = sa.create_engine(db_uri)
    error = None
    try:
        conn = engine.connect()
    except sa.exc.OperationalError as e:
        error = str(e)
    else:
        conn.close()
        del conn

    engine.dispose()

    # FIXME: at this point we have not tested the connection is valid, i.e, we
    # have CREATE, SELECT, UPDATE, DELETE rights on the database

    if error:
        flash(error, "error")
        return step_db_form()

    step_validated("db")
    next_step = request.setup_step_progress["next_step"]
    endpoint = f"{setup.name}.{next_step.endpoint}"
    return redirect(url_for(endpoint))


#
# Redis
#
@csrf.exempt
@setup.route("/redis", methods=["GET", "POST"])
def step_redis():
    if request.method == "POST":
        return step_redis_validate()
    return step_redis_form()


def step_redis_form():
    return render_template("setupwizard/step_redis.html", data=session_get("redis", {}))


def step_redis_validate():
    form = request.form
    data = {
        "host": form.get("host", "localhost").strip(),
        "port": form.get("port", "").strip() or "6379",
        "db": form.get("db", "").strip() or "1",
    }

    for k in ("port", "db"):
        try:
            data[k] = int(data[k])
        except ValueError:
            pass

    data["uri"] = "redis://{host}:{port}/{db}".format(**data)
    session_set("redis", data)
    error = None

    try:
        r = redis.StrictRedis(host=data["host"], port=data["port"], db=data["db"])
    except Exception as e:
        error = "Connection error, check parameters"
        raise e

    try:
        r.info()
    except redis.exceptions.InvalidResponse:
        error = (
            "Connection error: doesn't look like it's a redis server. "
            "Verify host and port are those of your redis server."
        )
    except redis.exceptions.ResponseError as e:
        error = f"Redis server response: {e}"
    except redis.exceptions.RedisError as e:
        error = f"Unknown redis error ({e})"

    if error:
        flash(error, "error")
        return step_redis_form()

    step_validated("redis")
    next_step = request.setup_step_progress["next_step"]
    endpoint = f"{setup.name}.{next_step.endpoint}"
    return redirect(url_for(endpoint))


#
# Site info
#
@csrf.exempt
@setup.route("/site_info", methods=["GET", "POST"])
def step_site_info():
    if request.method == "POST":
        return step_site_info_validate()
    return step_site_info_form()


def get_possible_hostnames():
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    names = {"localhost": ["127.0.0.1"]}

    for name in (hostname, fqdn):
        try:
            name, aliases, ips = socket.gethostbyname_ex(name)
        except OSError:
            continue
        names.setdefault(name, []).extend(ips)
        for a in aliases:
            names.setdefault(a, []).extend(ips)

    return sorted(
        f"{name} ({', '.join(sorted(set(ips)))})" for name, ips in names.items()
    )


def step_site_info_form():
    cfg = current_app.config
    default_data = {
        "sitename": cfg.get("SITE_NAME", "") or "",
        "mailsender": cfg.get("MAIL_SENDER", "") or "",
    }
    return render_template(
        "setupwizard/step_site_info.html",
        data=session_get("site_info", default_data),
        suggested_hosts=get_possible_hostnames(),
    )


def step_site_info_validate():
    form = request.form
    data = {
        "sitename": form.get("sitename", "").strip(),
        "mailsender": form.get("mailsender", "").strip(),
        "server_mode": form.get("server_mode", "").strip(),
    }

    session_set("site_info", data)
    step_validated("site_info")
    next_step = request.setup_step_progress["next_step"]
    endpoint = f"{setup.name}.{next_step.endpoint}"
    return redirect(url_for(endpoint))


#
# Admin account creation
#
@csrf.exempt
@setup.route("/admin_account", methods=["GET", "POST"])
def step_admin_account():
    if request.method == "POST":
        return step_admin_account_validate()
    return step_admin_account_form()


def step_admin_account_form():
    return render_template(
        "setupwizard/step_admin_account.html", data=session_get("admin_account", {})
    )


def step_admin_account_validate():
    form = request.form
    password = form.get("password", "").strip()
    confirm_password = form.get("confirm_password", "").strip()
    admin_user = {
        "email": form.get("email", "").strip(),
        "name": form.get("name", "").strip(),
        "firstname": form.get("firstname", "").strip(),
        "password": password,
        "confirm_password": confirm_password,
    }
    session_set("admin_account", admin_user)

    if password != confirm_password:
        flash("Password fields don't match", "error")
        return step_admin_account_form()

    step_validated("admin_account")
    next_step = request.setup_step_progress["next_step"]
    endpoint = f"{setup.name}.{next_step.endpoint}"
    return redirect(url_for(endpoint))


#
# Finalize
#
@csrf.exempt
@setup.route("/finalize", methods=["GET", "POST"])
def finalize():
    validated = session_get("validated")
    assert all(s.name in validated for s in _setup_steps[:-1])

    if request.method == "POST":
        return finalize_validate()
    return finalize_form()


def finalize_form():
    file_location = Path(current_app.instance_path) / "config.py"
    return render_template("setupwizard/finalize.html", file_location=file_location)


def finalize_validate():
    config_file = Path(current_app.instance_path) / "config.py"
    logging_file = Path(current_app.instance_path) / "logging.yml"

    assert not config_file.exists()
    config = cmd_config.DefaultConfig(logging_file="logging.yml")
    config.SQLALCHEMY_DATABASE_URI = session_get("db")["uri"]

    redis_uri = session_get("redis")["uri"]
    config.REDIS_URI = redis_uri
    config.BROKER_URL = redis_uri
    config.CELERY_RESULT_BACKEND = redis_uri

    d = session_get("site_info")
    config.SITE_NAME = d["sitename"]
    config.MAIL_SENDER = d["mailsender"]

    is_production = d["server_mode"] == "production"
    config.PRODUCTION = is_production
    config.DEBUG = not is_production
    config.DEBUG_TB_ENABLED = config.DEBUG
    config.CELERY_ALWAYS_EAGER = not is_production

    cmd_config.write_config(config_file, config)
    cmd_config.maybe_write_logging(logging_file)

    admin_account = session_get("admin_account")
    # create a new app that will be configured with new config,
    # to create database and admin_user
    setup_app = unwrap(current_app)
    app = setup_app.__class__(
        setup_app.import_name,
        static_url_path=setup_app.static_url_path,
        static_folder=setup_app.static_folder,
        template_folder=setup_app.template_folder,
        instance_path=setup_app.instance_path,
    )
    with app.test_request_context("/setup/finalize"):
        app.create_db()
        db_session = db.session()
        admin = User(
            email=admin_account["email"],
            password=admin_account["password"],
            last_name=admin_account["name"],
            first_name=admin_account["firstname"],
            can_login=True,
        )
        db_session.add(admin)
        security = get_service("security")
        security.grant_role(admin, Admin)
        db_session.commit()

    session_clear()

    return render_template(
        "setupwizard/done.html", config_file=config_file, logging_file=logging_file
    )
