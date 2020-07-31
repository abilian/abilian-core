""""""
from multiprocessing.util import register_after_fork
from typing import Any, Dict, List, Optional

from celery import Celery
from celery import current_app as celery_current_app
from celery import current_task, task
from celery.app.task import Task
from celery.loaders.base import BaseLoader
from celery.task import PeriodicTask as CeleryPeriodicTask
from celery.utils.imports import symbol_by_name
from flask import Flask
from flask import current_app as flask_current_app
from flask import has_app_context
from flask.helpers import locked_cached_property
from sqlalchemy.orm.session import Session

from abilian.core.extensions import db
from abilian.core.util import unwrap


def default_app_factory():
    from abilian.app import Application

    return Application()


CELERY_CONF_KEY_PREFIXES = (
    "CELERY_",
    "CELERYD_",
    "BROKER_",
    "CELERYBEAT_",
    "CELERYMON_",
)


def is_celery_setting(key: str) -> bool:
    return any(key.startswith(prefix) for prefix in CELERY_CONF_KEY_PREFIXES)


def is_eager() -> bool:
    """True when tasks are run eagerly.

    As of celery 3.1.17 it seems that when CELERY_ALWAYS_EAGER is set in
    config, request.is_eager is *False*.
    """
    return (
        current_task and current_task.request.is_eager
    ) or celery_current_app.conf.CELERY_ALWAYS_EAGER


def safe_session() -> Session:
    """Return a sqlalchemy session that can be safely used in a task.

    During standard async task processing, there is generally no
    problem. When developping with task run in eager mode, the session
    is not usable when task is called during an `after_commit` event.
    """
    if not is_eager():
        return db.session()

    return Session(bind=db.session.get_bind(None, None))


class FlaskLoader(BaseLoader):
    #: override this in your project
    #: this can be a function or a class
    flask_app_factory = "abilian.core.celery.default_app_factory"
    app_context = None

    @locked_cached_property
    def flask_app(self) -> Flask:
        if has_app_context():
            return unwrap(flask_current_app)

        self.flask_app_factory = symbol_by_name(self.flask_app_factory)
        app = self.flask_app_factory()

        register_after_fork(app, self._setup_after_fork)
        return app

    def _setup_after_fork(self, app):
        binds = [None] + list(app.config.get("SQLALCHEMY_BINDS") or ())
        for bind in binds:
            engine = db.get_engine(app, bind)
            engine.dispose()

    def read_configuration(self, env: str = "") -> Dict[str, Any]:
        app = self.flask_app
        app.config.setdefault("CELERY_DEFAULT_EXCHANGE", app.name)
        app.config.setdefault("CELERY_DEFAULT_QUEUE", app.name)
        app.config.setdefault("CELERY_BROADCAST_EXCHANGE", app.name + "ctl")
        app.config.setdefault("CELERY_BROADCAST_QUEUE", app.name + "ctl")
        app.config.setdefault("CELERY_RESULT_EXCHANGE", app.name + "results")
        app.config.setdefault("CELERY_DEFAULT_ROUTING_KEY", app.name)
        cfg = {k: v for k, v in app.config.items() if is_celery_setting(k)}
        self.configured = True
        return cfg


class FlaskTask(Task):
    """Base Task class for :FlaskCelery: based applications."""

    abstract = True

    def __call__(self, *args: List, **kwargs: Dict[str, Any]) -> Optional[Any]:
        if is_eager():
            # this is here mainly because flask_sqlalchemy (as of 2.0) will
            # remove session on app context teardown.
            #
            # Unfortunatly when using eager tasks (during dev and tests,
            # mostly), calling apply_async() during after_commit() will
            # remove session because app_context would be pushed and popped.
            #
            # The TB looks like:
            #
            # sqlalchemy/orm/session.py: in transaction.commit:
            #     if self.session._enable_transaction_accounting:
            # AttributeError: 'NoneType' object has no attribute
            #                 '_enable_transaction_accounting'
            #
            # FIXME: also test has_app_context()?
            return super().__call__(*args, **kwargs)

        with self.app.loader.flask_app.app_context():
            return super().__call__(*args, **kwargs)


class PeriodicTask(FlaskTask, CeleryPeriodicTask):
    __doc__ = CeleryPeriodicTask.__doc__
    abstract = True


def periodic_task(*args, **options):
    """Deprecated decorator, please use :setting:`CELERYBEAT_SCHEDULE`."""
    # FIXME: 'task' below is not callable. Fix or remove.
    return task(**dict({"base": PeriodicTask}, **options))


class FlaskCelery(Celery):
    # can be overriden on command line with --loader
    loader_cls = FlaskLoader
    task_cls = FlaskTask
