# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import url_for


def test_home(client):
    response = client.get(url_for("admin.dashboard"))
    assert response.status_code == 200


def test_sysinfo(client):
    response = client.get(url_for("admin.sysinfo"))
    assert response.status_code == 200


def test_login_session(client):
    response = client.get(url_for("admin.login_sessions"))
    assert response.status_code == 200


def test_audit(client):
    response = client.get(url_for("admin.audit"))
    assert response.status_code == 200


def test_settings(client):
    response = client.get(url_for("admin.settings"))
    assert response.status_code == 200
