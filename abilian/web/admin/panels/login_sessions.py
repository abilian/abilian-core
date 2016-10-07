# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import pygeoip
from flask import render_template

from abilian.i18n import _
from abilian.services.auth.models import LoginSession

from ..panel import AdminPanel

DATA_FILES = (
    '/usr/share/GeoIP/GeoIP.dat',
    '/usr/share/GeoIP/GeoIPv6.dat',)


class LoginSessionsPanel(AdminPanel):
    id = "login_sessions"
    label = "Session log"
    icon = 'log-in'

    def get(self):
        geoips = []
        for filename in DATA_FILES:
            try:
                geoips.append(pygeoip.GeoIP(filename))
            except (pygeoip.GeoIPError, IOError):
                pass

        sessions = LoginSession.query.order_by(LoginSession.id.desc()).limit(
            50).all()
        unknown_country = _(u'Country unknown')

        for session in sessions:
            country = unknown_country

            if geoips and session.ip_address:
                ip_address = session.ip_address
                multiple = ip_address.split(',')
                if multiple:
                    # only use last ip in the list, most likely the public address
                    ip_address = multiple[-1]
                for g in geoips:
                    try:
                        country = g.country_name_by_addr(ip_address)
                    except:  # noqa
                        continue

                    if country:
                        break
                    else:
                        country = unknown_country

                session.country = country

        return render_template("admin/login_sessions.html", **locals())
