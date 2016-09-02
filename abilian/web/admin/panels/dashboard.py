# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from datetime import datetime, timedelta

import pandas as pd
import six
import sqlalchemy as sa
from flask import current_app, render_template
from numpy import sum as numpysum

from abilian.core.models.subjects import User
from abilian.i18n import _, _l
from abilian.services.audit import CREATION, AuditEntry
from abilian.services.auth.models import LoginSession

from ..panel import AdminPanel


class DashboardPanel(AdminPanel):
    id = 'dashboard'
    path = ''
    label = _l('Dashboard')
    icon = 'eye-open'

    def get(self):
        login_entries = LoginSession.query \
            .order_by(LoginSession.started_at.asc()) \
            .all()
        # .options(sa.orm.joinedload(LoginSession.user))
        daily, weekly, monthly = uniquelogins(login_entries)
        new_logins, total_users = newlogins(login_entries)

        stats = {
            'today': stats_since(timedelta(days=1)),
            'this_week': stats_since(timedelta(days=7)),
            'this_month': stats_since(timedelta(days=30)),
        }

        # let's format the data into NVD3 datastructures
        connections = [
            {'key': _('Daily'), 'color': '#7777ff', 'values': daily},
            {'key': _('Weekly'), 'color': '#2ca02c', 'values': weekly, 'disabled': True},
            {'key': _('Monthly'), 'color': '#ff7f0e', 'values': monthly, 'disabled': True},
        ]
        new_logins = [
            {'key': _('New'), 'color': '#ff7f0e', "bar": True, 'values': new_logins},
            {'key': _('Total'), 'color': '#2ca02c', 'values': total_users}
        ]

        return render_template(
            "admin/dashboard.html",
            stats=stats,
            connections=connections,
            new_logins=new_logins)


def stats_since(dt):
    new_members = new_documents = new_messages = 0
    after_date = datetime.utcnow() - dt
    session = current_app.db.session()
    counts_per_type = session \
        .query(AuditEntry.entity_type.label('type'),
               sa.func.count(AuditEntry.entity_type).label('count')) \
        .group_by(AuditEntry.entity_type) \
        .filter(AuditEntry.happened_at > after_date) \
        .filter(AuditEntry.type == CREATION) \
        .all()

    for entity_type, count in counts_per_type:
        entity_class = entity_type.split('.')[-1]
        if entity_class == 'User':
            new_members = count
        elif entity_class == 'Document':
            new_documents = count
        elif entity_class == 'Message':
            new_messages = count

    active_users = session.query(sa.func.count(User.id))\
                          .filter(User.last_active > after_date).scalar()

    return {
        'new_members': new_members,
        'active_users': active_users,
        'new_documents': new_documents,
        'new_messages': new_messages,
    }


epoch = datetime.utcfromtimestamp(0)


def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0


def newlogins(sessions):
    """
    Brand new logins each day, and total of users each day.

    :return: data, total
      2 lists of dictionaries of the following format [{'x':epoch, 'y': value},]
    """
    if not sessions:
        return [], []
    users = {}
    dates = {}

    for session in sessions:
        user = session.user
        # time value is discarded to aggregate on days only
        date = session.started_at.strftime("%Y/%m/%d")
        # keep the info only it's the first time we encounter a user
        if user not in users:
            users[user] = date
            # build the list of users on a given day
            if date not in dates:
                dates[date] = [user]
            else:
                dates[date].append(user)

    data = []
    total = []
    previous = 0
    for date in sorted(dates.keys()):
        # print u"{} : {}".format(date, len(dates[date]))
        date_epoch = unix_time_millis(datetime.strptime(date, "%Y/%m/%d"))
        data.append({u'x': date_epoch, u'y': len(dates[date])})
        previous += len(dates[date])
        total.append({u'x': date_epoch, u'y': previous})

    return data, total


def uniquelogins(sessions):
    """Unique logins per days/weeks/months.

    :return: daily, weekly, monthly
    3 lists of dictionaries of the following format [{'x':epoch, 'y': value},]
    """
    # sessions = LoginSession.query.order_by(LoginSession.started_at.asc()).all()
    if not sessions:
        return [], [], []
    dates = {}
    for session in sessions:
        user = session.user
        # time value is discarded to aggregate on days only
        date = session.started_at.strftime("%Y/%m/%d")

        if date not in dates:
            dates[date] = set()  # we want unique users on a given day
            dates[date].add(user)
        else:
            dates[date].add(user)

    daily = []
    weekly = []
    monthly = []

    for date in sorted(dates.keys()):
        # print u"{} : {}".format(date, len(dates[date]))
        date_epoch = unix_time_millis(datetime.strptime(date, "%Y/%m/%d"))
        daily.append({'x': date_epoch, 'y': len(dates[date])})

    # first_day = data[0]['x']
    # last_day = data[-1]['x']

    daily_serie = pd.Series(dates)
    # convert the index to Datetime type
    daily_serie.index = pd.DatetimeIndex(daily_serie.index)
    # calculate the values instead of users lists
    daily_serie = daily_serie.apply(lambda x: len(x))

    # GroupBy Week/month, Thanks Panda
    weekly_serie = daily_serie \
        .groupby(pd.TimeGrouper(freq='W')) \
        .aggregate(numpysum)
    monthly_serie = daily_serie \
        .groupby(pd.TimeGrouper(freq='M')) \
        .aggregate(numpysum)

    for date, value in six.iteritems(weekly_serie):
        try:
            value = int(value)
        except ValueError:
            continue
        date_epoch = unix_time_millis(date)
        weekly.append({'x': date_epoch, 'y': value})

    for date, value in six.iteritems(monthly_serie):
        try:
            value = int(value)
        except ValueError:
            continue
        date_epoch = unix_time_millis(date)
        monthly.append({'x': date_epoch, 'y': value})

    return daily, weekly, monthly
