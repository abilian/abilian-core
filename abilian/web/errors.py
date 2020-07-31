"""Base Flask application class, used by tests or to be extended in real
applications."""
import logging
import logging.config
from functools import partial
from pathlib import Path

import sqlalchemy as sa
import yaml
from flask import Flask, _request_ctx_stack, g, render_template
from pkg_resources import resource_filename
from sqlalchemy.orm.attributes import NEVER_SET

from abilian.core import extensions

logger = logging.getLogger(__name__)
db = extensions.db


class ErrorManagerMixin(Flask):
    def setup_logging(self) -> None:
        # Force flask to create application logger before logging
        # configuration; else, flask will overwrite our settings
        self.logger  # noqa

        log_level = self.config.get("LOG_LEVEL")
        if log_level:
            self.logger.setLevel(log_level)

        logging_file = self.config.get("LOGGING_CONFIG_FILE")
        if logging_file:
            logging_file = (Path(self.instance_path) / logging_file).resolve()
        else:
            logging_file = Path(
                resource_filename("abilian.core", "default_logging.yml")
            )

        if logging_file.suffix == ".ini":
            # old standard 'ini' file config
            logging.config.fileConfig(str(logging_file), disable_existing_loggers=False)
        elif logging_file.suffix == ".yml":
            # yaml config file
            logging_cfg = yaml.safe_load(logging_file.open())
            logging_cfg.setdefault("version", 1)
            logging_cfg.setdefault("disable_existing_loggers", False)
            logging.config.dictConfig(logging_cfg)

    def handle_user_exception(self, e):
        # If session.transaction._parent is None, then exception has occured in
        # after_commit(): doing a rollback() raises an error and would hide
        # actual error.
        session = db.session()
        if session.is_active and session.transaction._parent is not None:
            # Inconditionally forget all DB changes, and ensure clean session
            # during exception handling.
            session.rollback()
        else:
            self._remove_session_save_objects()

        return Flask.handle_user_exception(self, e)

    def handle_exception(self, e):
        session = db.session()
        if not session.is_active:
            # Something happened in error handlers and session is not usable
            # anymore.
            self._remove_session_save_objects()

        return Flask.handle_exception(self, e)

    def _remove_session_save_objects(self):
        """Used during exception handling in case we need to remove() session:

        keep instances and merge them in the new session.
        """
        if self.testing:
            return
        # Before destroying the session, get all instances to be attached to the
        # new session. Without this, we get DetachedInstance errors, like when
        # tryin to get user's attribute in the error page...
        old_session = db.session()
        g_objs = []
        for key in iter(g):
            obj = getattr(g, key)
            if isinstance(obj, db.Model) and sa.orm.object_session(obj) in (
                None,
                old_session,
            ):
                g_objs.append((key, obj, obj in old_session.dirty))

        db.session.remove()
        session = db.session()

        for key, obj, load in g_objs:
            # replace obj instance in bad session by new instance in fresh
            # session
            setattr(g, key, session.merge(obj, load=load))

        # refresh `current_user`
        user = getattr(_request_ctx_stack.top, "user", None)
        if user is not None and isinstance(user, db.Model):
            _request_ctx_stack.top.user = session.merge(user, load=load)

    def log_exception(self, exc_info):
        """Log exception only if Sentry is not used (this avoids getting error
        twice in Sentry)."""
        dsn = self.config.get("SENTRY_DSN")
        if not dsn:
            super().log_exception(exc_info)

    def init_sentry(self):
        """Install Sentry handler if config defines 'SENTRY_DSN'."""
        dsn = self.config.get("SENTRY_DSN")
        if not dsn:
            return

        try:
            import sentry_sdk
        except ImportError:
            logger.error(
                'SENTRY_DSN is defined in config but package "sentry-sdk"'
                " is not installed."
            )
            return

        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(dsn=dsn, integrations=[FlaskIntegration(), CeleryIntegration()])

    def install_default_handlers(self) -> None:
        for http_error_code in (403, 404, 500):
            self.install_default_handler(http_error_code)

    def install_default_handler(self, http_error_code: int) -> None:
        """Install a default error handler for `http_error_code`.

        The default error handler renders a template named error404.html
        for http_error_code 404.
        """
        logger.debug(
            "Set Default HTTP error handler for status code %d", http_error_code
        )
        handler = partial(self.handle_http_error, http_error_code)
        self.errorhandler(http_error_code)(handler)

    def handle_http_error(self, code, error):
        """Helper that renders `error{code}.html`.

        Convenient way to use it::

           from functools import partial
           handler = partial(app.handle_http_error, code)
           app.errorhandler(code)(handler)
        """
        # 5xx code: error on server side
        if (code // 100) == 5:
            # ensure rollback if needed, else error page may
            # have an error, too, resulting in raw 500 page :-(
            db.session.rollback()

        template = f"error{code:d}.html"
        return render_template(template, error=error), code
