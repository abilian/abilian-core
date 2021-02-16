from functools import wraps
from typing import Callable

from flask import Blueprint, current_app, request
from flask_wtf import Form as FlaskForm
from werkzeug.exceptions import Forbidden
from wtforms.ext.csrf.fields import CSRFTokenField

blueprint = Blueprint("csrf", __name__, url_prefix="/csrf")


@blueprint.route("/token", endpoint="json_token")
def json_token_view():
    return {"token": token()}


def field() -> CSRFTokenField:
    """Return an instance of `wtforms.ext.csrf.fields.CSRFTokenField`, suitable
    for rendering.

    Renders an empty string if `config.WTF_CSRF_ENABLED` is not set.
    """
    return FlaskForm().csrf_token


def time_limit():
    """Return current time limit for CSRF token."""
    return current_app.config.get("WTF_CSRF_TIME_LIMIT", 3600)


def name() -> str:
    """Field name expected to have CSRF token.

    Useful for passing it to JavaScript for instance.
    """
    return "csrf_token"


def token() -> str:
    """Value of current csrf token.

    Useful for passing it to JavaScript for instance.
    """
    return field().current_token or ""


def support_graceful_failure(view: Callable) -> Callable:
    """Decorator to indicate that the view will handle itself the csrf failure.

    View can be a view function or a class based view
    """
    view.csrf_support_graceful_failure = True
    return view


def has_failed():
    return getattr(request, "csrf_failed", False)


def protect(view: Callable) -> Callable:
    """Protects a view agains CSRF attacks by checking `csrf_token` value in
    submitted values. Do nothing if `config.WTF_CSRF_ENABLED` is not set.

    Raises `werkzeug.exceptions.Forbidden` if validation fails.
    """

    @wraps(view)
    def csrf_check(*args, **kwargs):
        # an empty form is used to validate current csrf token and only that!
        if not FlaskForm().validate():
            raise Forbidden("CSRF validation failed.")

        return view(*args, **kwargs)

    return csrf_check
