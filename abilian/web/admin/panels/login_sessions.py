# coding=utf-8
"""
"""
from __future__ import absolute_import

import pygeoip
from flask import render_template
from abilian.services.auth.models import LoginSession

from ..panel import AdminPanel


class LoginSessionsPanel(AdminPanel):
  id = "login_sessions"
  label = "Session log"
  icon = 'log-in'

  def get(self):
    try:
      geoip = pygeoip.GeoIP('/usr/share/GeoIP/GeoIP.dat')
    except:
      geoip = None

    sessions = LoginSession.query.order_by(LoginSession.id.desc()).limit(50).all()

    for session in sessions:
      country = "Country unknown"
      if geoip and session.ip_address:
        country = geoip.country_name_by_addr(session.ip_address) or country
      session.country = country

    return render_template("admin/login_sessions.html", **locals())
