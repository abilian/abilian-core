# coding=utf-8
"""Login-related views (login / logout / password reminder / ...).

Notes:
- Uses code copy/pasted (and modified) from Flask-Security
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import random
import string
from datetime import datetime
from typing import Any, List, Text

from flask import current_app, flash, redirect, render_template, request, \
    url_for
from flask.globals import _request_ctx_stack
from flask.json import jsonify
from flask_login import login_user, logout_user, user_logged_in, \
    user_logged_out
from flask_mail import Message
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from six.moves.urllib.parse import urljoin, urlparse
from sqlalchemy import sql
from sqlalchemy.orm.exc import NoResultFound

from abilian.core.extensions import csrf, db
from abilian.core.models.subjects import User
from abilian.core.signals import auth_failed
from abilian.core.util import md5
from abilian.i18n import _, render_template_i18n
from abilian.services.security import Anonymous
from abilian.web.blueprints import Blueprint

from .models import LoginSession

__all__ = ()

login = Blueprint(
    "login",
    __name__,
    url_prefix="/user",
    allowed_roles=Anonymous,
    template_folder="templates",
)
route = login.route


#
# Login / Logout
#
@route("/login")
def login_form():
    """Display the login form."""
    next_url = get_redirect_target()
    return render_template("login/login.html", next_url=next_url)


def do_login(form):
    email = form.get("email", "").lower()
    password = form.get("password")
    next_url = form.get("next", "")
    res = dict(username=email, email=email, next_url=next_url)

    if not email or not password:
        res["error"] = _("You must provide your email and password.")
        res["code"] = 401
        return res

    try:
        user = User.query.filter(
            sql.func.lower(User.email) == email, User.can_login == True
        ).one()
    except NoResultFound:
        auth_failed.send(current_app._get_current_object(), email=email)
        res["error"] = _(
            "Sorry, we couldn't find an account for " "email '{email}'."
        ).format(email=email)
        res["code"] = 401
        return res

    if user and not user.authenticate(password):
        auth_failed.send(current_app._get_current_object(), email=email)
        res["error"] = _("Sorry, wrong password.")
        res["code"] = 401
        return res

    # Login successful
    login_user(user)
    res["user"] = user
    res["email"] = user.email
    return res


@csrf.exempt
@route("/login", methods=["POST"])
def login_post():
    res = do_login(request.form)
    if "error" in res:
        code = res.pop("code")
        flash(res["error"], "error")
        return (render_template("login/login.html", **res), code)

    return redirect_back(url=request.url_root)


@csrf.exempt
@route("/api/login", methods=["POST"])
def login_json():
    res = do_login(request.get_json())
    code = None

    if "error" in res:
        code = res.pop("code")
    else:
        user = res.pop("user")
        res["fullname"] = user.name

    response = jsonify(**res)
    if code:
        response.status_code = code
    return response


@csrf.exempt
@route("/logout", methods=["GET", "POST"])
def logout():
    logout_user()
    return redirect(request.url_root)


@csrf.exempt
@route("/api/logout", methods=["POST"])
def logout_json():
    logout_user()
    return "{}", 200, {"content-type": "application/json"}


#
# Code to deal with forgotten passwords or initial password generation
# Note: most of this code is stolen (copy/pasted) from Flask-Security, with a
# few modifications.
#
@route("/forgotten_pw")
def forgotten_pw_form():
    return render_template("login/forgotten_password.html")


@route("/forgotten_pw", methods=["POST"])
@csrf.exempt
def forgotten_pw(new_user=False):
    """Reset password for users who have already activated their accounts."""
    email = request.form.get("email", "").lower()

    action = request.form.get("action")
    if action == "cancel":
        return redirect(url_for("login.login_form"))

    if not email:
        flash(_("You must provide your email address."), "error")
        return render_template("login/forgotten_password.html")

    try:
        user = User.query.filter(
            sql.func.lower(User.email) == email, User.can_login == True
        ).one()
    except NoResultFound:
        flash(
            _("Sorry, we couldn't find an account for " "email '{email}'.").format(
                email=email
            ),
            "error",
        )
        return render_template("login/forgotten_password.html"), 401

    if user.can_login and not user.password:
        user.set_password(random_password())
        db.session.commit()

    send_reset_password_instructions(user)
    flash(
        _("Password reset instructions have been sent to your email address."), "info"
    )

    return redirect(url_for("login.login_form"))


@route("/reset_password/<token>")
def reset_password(token):
    expired, invalid, user = reset_password_token_status(token)
    if invalid:
        flash(_("Invalid reset password token."), "error")
    elif expired:
        flash(_("Password reset expired"), "error")
    if invalid or expired:
        return redirect(url_for("login.forgotten_pw"))

    return render_template_i18n("login/password_reset.html")


@route("/reset_password/<token>", methods=["POST"])
@csrf.exempt
def reset_password_post(token):
    action = request.form.get("action")
    if action == "cancel":
        return redirect(request.url_root)

    expired, invalid, user = reset_password_token_status(token)

    if invalid or not user:
        flash(_("Invalid reset password token."), "error")
    elif expired:
        flash(_("Password reset expired"), "error")
    if invalid or expired or not user:
        return redirect(url_for("login.forgotten_pw"))

    password = request.form.get("password")

    if not password:
        flash(_("You must provide a password."), "error")
        return redirect(url_for("login.reset_password_post", token=token))

    # TODO: check entropy
    if len(password) < 7:
        flash(_("Your new password must be at least 8 characters long"), "error")
        return redirect(url_for("login.reset_password_post", token=token))

    if password.lower() == password:
        flash(
            _("Your new password must contain upper case and lower case " "letters"),
            "error",
        )
        return redirect(url_for("login.reset_password_post", token=token))

    if not len([x for x in password if x.isdigit()]) > 0:
        flash(_("Your new password must contain at least one digit"), "error")
        return redirect(url_for("login.reset_password_post", token=token))

    user.set_password(password)
    db.session.commit()

    flash(
        _(
            "Your password has been changed. "
            "You can now login with your new password"
        ),
        "success",
    )

    return redirect(url_for("login.login_form", next_url=request.url_root))


def random_password():
    pw = []
    for _i in range(0, 10):
        pw.append(random.choice(string.ascii_letters + string.digits))
    return pw


def get_serializer(name):
    # type: (str) -> Any
    config = current_app.config
    secret_key = config.get("SECRET_KEY")
    salt = config.get("SECURITY_{}_SALT".format(name.upper()))
    return URLSafeTimedSerializer(secret_key=secret_key, salt=salt)


def send_reset_password_instructions(user):
    # type: (User) -> None
    """Send the reset password instructions email for the specified user.

    :param user: The user to send the instructions to
    """
    token = generate_reset_password_token(user)
    url = url_for("login.reset_password", token=token)
    reset_link = request.url_root[:-1] + url

    subject = _("Password reset instruction for {site_name}").format(
        site_name=current_app.config.get("SITE_NAME")
    )
    mail_template = "password_reset_instructions"
    send_mail(subject, user.email, mail_template, user=user, reset_link=reset_link)


def generate_reset_password_token(user):
    # type: (User) -> Any
    """Generate a unique reset password token for the specified user.

    :param user: The user to work with
    """
    data = [str(user.id), md5(user.password)]
    return get_serializer("reset").dumps(data)


def reset_password_token_status(token):
    # type: (str) -> Any
    """Return the expired status, invalid status, and user of a password reset
    token.

    For example::

        expired, invalid, user = reset_password_token_status('...')

    :param token: The password reset token
    """
    return get_token_status(token, "reset", "RESET_PASSWORD")


def get_token_status(token, serializer_name, max_age=None):
    serializer = get_serializer(serializer_name)
    # max_age = get_max_age(max_age)
    user, data = None, None
    expired, invalid = False, False

    try:
        data = serializer.loads(token, max_age=max_age)
    except SignatureExpired:
        d, data = serializer.loads_unsafe(token)
        expired = True
    except BadSignature:
        invalid = True

    if data:
        user = User.query.get(data[0])

    expired = expired and (user is not None)
    return expired, invalid, user


def send_mail(subject, recipient, template, **context):
    """Send an email using the Flask-Mail extension.

    :param subject: Email subject
    :param recipient: Email recipient
    :param template: The name of the email template
    :param context: The context to render the template with
    """

    config = current_app.config
    sender = config["MAIL_SENDER"]
    msg = Message(subject, sender=sender, recipients=[recipient])

    template_name = "login/email/{}.txt".format(template)
    msg.body = render_template_i18n(template_name, **context)
    # msg.html = render_template('%s/%s.html' % ctx, **context)

    mail = current_app.extensions.get("mail")
    current_app.logger.debug("Sending mail...")
    mail.send(msg)


#
# Logging
#
@user_logged_in.connect
def log_session_start(app, user):
    session = LoginSession.new()
    db.session.add(session)
    db.session.commit()


@user_logged_out.connect
def log_session_end(app, user):
    if user.is_anonymous:
        return

    session = LoginSession.query.get_active_for(user)
    if session:
        session.ended_at = datetime.utcnow()
        db.session.commit()


# login redirect utilities
#  from http://flask.pocoo.org/snippets/62/
def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.url_root, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def check_for_redirect(target):
    target = urljoin(request.url_root, target)
    url = urlparse(target)
    reqctx = _request_ctx_stack.top
    try:
        endpoint, ignored = reqctx.url_adapter.match(url.path, "GET")
        if "." in endpoint and endpoint.rsplit(".", 1)[0] == "login":
            # don't redirect to any login view after successful login
            return None
    except Exception:
        # exceptions may happen if route is not found for example
        pass

    return target


def get_redirect_target():
    for target in (request.values.get("next"), request.referrer):
        if not target:
            continue
        if is_safe_url(target):
            return check_for_redirect(target)


def redirect_back(endpoint=None, url=None, **values):
    target = request.form.get("next")
    if not target or not is_safe_url(target):
        if endpoint:
            target = url_for(endpoint, **values)
        else:
            target = url
    return redirect(check_for_redirect(target))
