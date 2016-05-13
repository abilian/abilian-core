# coding: utf-8
"""
Add a few specific filters to Jinja2.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime
import re
from calendar import timegm
from functools import wraps

import bleach
import dateutil.parser
import flask_babel as babel
from babel.dates import DateTimePattern, format_timedelta, parse_pattern
from flask import Flask
from jinja2 import Markup, escape, evalcontextfilter
from pytz import utc
from werkzeug.routing import BuildError

from abilian.web.decorators import deprecated

from ..core.util import local_dt, slugify, utc_dt
from .util import url_for


def autoescape(filter_func):
    """
    Decorator to autoescape result from filters.
    """

    @evalcontextfilter
    @wraps(filter_func)
    def _autoescape(eval_ctx, *args, **kwargs):
        result = filter_func(*args, **kwargs)
        if eval_ctx.autoescape:
            result = Markup(result)
        return result

    return _autoescape


@autoescape
def nl2br(value):
    """Replace newlines with <br />.
    """
    result = escape(value).replace(u'\n', Markup(u'<br />\n'))
    return result


_PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@autoescape
def paragraphs(value):
    """Blank lines delimitates paragraphs.
    """
    result = u'\n\n'.join((u'<p>{}</p>'.format(p.strip().replace('\n', Markup(
        '<br />\n'))) for p in _PARAGRAPH_RE.split(escape(value))))
    return result


def labelize(s):
    return u" ".join([w.capitalize() for w in s.split(u"_")])


def filesize(d):
    if not isinstance(d, int):
        d = int(d)

    if d < 1000:
        s = "%d&nbsp;B" % d

    elif d < 1e4:
        s = "%.1f&nbsp;kB" % (d / 1e3)
    elif d < 1e6:
        s = "%.0f&nbsp;kB" % (d / 1e3)

    elif d < 1e7:
        s = "%.1f&nbsp;MB" % (d / 1e6)
    elif d < 1e9:
        s = "%.0f&nbsp;MB" % (d / 1e6)

    elif d < 1e10:
        s = "%.1f&nbsp;GB" % (d / 1e9)

    else:
        s = "%.0f&nbsp;GB" % (d / 1e9)

    return Markup(s)


def roughsize(size, above=20, mod=10):
    """
    6 -> '6'
    15 -> '15'
    134 -> '130+'
    """
    if size < above:
        return unicode(size)

    return u'{:d}+'.format(size - size % mod)


def datetimeparse(s):
    """Parse a string date time to a datetime object.

    Suitable for dates serialized with .isoformat()

    :return: None, or an aware datetime instance, tz=UTC.
    """
    try:
        dt = dateutil.parser.parse(s)
    except:
        return None

    return utc_dt(dt)


def age(dt, now=None, add_direction=True, date_threshold=None):
    """
    :param dt: :class:`datetime<datetime.datetime>` instance to format

    :param now: :class:`datetime<datetime.datetime>` instance to compare to `dt`

    :param add_direction: if `True`, will add "in" or "ago" (example for `en`
       locale) to time difference `dt - now`, i.e "in 9 min." or " 9min. ago"

    :param date_threshold: above threshold, will use a formated date instead of
       elapsed time indication. Supported values: "day".
    """
    # Fail silently for now XXX
    if not dt:
        return ""

    if not now:
        now = datetime.datetime.utcnow()

    locale = babel.get_locale()
    dt = utc_dt(dt)
    now = utc_dt(now)
    delta = dt - now

    if date_threshold is not None:
        dy, dw, dd = dt_cal = dt.isocalendar()
        ny, nw, nd = now_cal = now.isocalendar()

        if dt_cal != now_cal:
            # not same day
            remove_year = (dy == ny)
            date_fmt = locale.date_formats['long'].pattern
            time_fmt = locale.time_formats['short'].pattern
            fmt = locale.datetime_formats['medium']

            if remove_year:
                date_fmt = date_fmt.replace('y', '').strip()
                # remove leading or trailing spaces, comma, etc...
                date_fmt = re.sub(u'^[^A-Za-z]*|[^A-Za-z]*$', u'', date_fmt)

            fmt = fmt.format(time_fmt, date_fmt)
            return babel.format_datetime(dt, format=fmt)

    # don't use (flask.ext.)babel.format_timedelta: as of Flask-Babel 0.9 it
    # doesn't support "threshold" arg.
    return format_timedelta(delta,
                            locale=locale,
                            granularity='minute',
                            threshold=0.9,
                            add_direction=add_direction)


def date_age(dt, now=None):
    # Fail silently for now XXX
    if not dt:
        return ""

    formatted_date = babel.format_datetime(dt, format='yyyy-MM-dd HH:mm')
    return u"{} ({})".format(formatted_date, age(dt, now))


@deprecated
def date(value, format="EE, d MMMM y"):
    """
    @deprecated: use flask_babel's dateformat filter instead.
    """
    if isinstance(value, datetime.date):
        return babel.format_date(value, format)
    else:
        return babel.format_date(local_dt(value), format)


def babel2datepicker(pattern):
    """Convert date format from babel
    (http://babel.pocoo.org/docs/dates/#date-fields)) to a format understood by
    bootstrap-datepicker.
    """
    if not isinstance(pattern, DateTimePattern):
        pattern = parse_pattern(pattern)

    map_fmt = {
        # days
        'd': 'dd',
        'dd': 'dd',
        'EEE': 'D',
        'EEEE': 'DD',
        'EEEEE': 'D',  # narrow name => short name
        # months
        'M': 'mm',
        'MM': 'mm',
        'MMM': 'M',
        'MMMM': 'MM',
        # years
        'y': 'yyyy',
        'yy': 'yyyy',
        'yyy': 'yyyy',
        'yyyy': 'yyyy',

        # time picker format
        # hours
        'h': '%I',
        'hh': '%I',
        'H': '%H',
        'HH': '%H',
        # minutes,
        'm': '%M',
        'mm': '%M',
        # seconds
        's': '%S',
        'ss': '%S',
        # am/pm
        'a': '%p',
    }

    return pattern.format % map_fmt


# Doesn't work yet. TZ issues.
def to_timestamp(dt):
    utc_datetime = dt.astimezone(utc)
    return timegm(utc_datetime.timetuple()) + utc_datetime.microsecond / 1e6


def abbrev(s, max_size):
    if len(s) <= max_size:
        return s
    else:
        h = max_size // 2 - 1
        return s[0:h] + "..." + s[-h:]


def bool2check(val, true=u'\u2713', false=u''):
    """Filter value as boolean and show check mark (✓) or nothing.
    """
    return true if val else false


@autoescape
def linkify(s):
    return Markup(bleach.linkify(s))


def obj_to_url(obj):
    """Find url for obj using :func:`url_for`, return empty string is not found.

    :func:`url_for` is also provided in jinja context, the filtering version is
    forgiving when `obj` has no default view set.
    """
    try:
        return url_for(obj)
    except BuildError:
        return u''


def init_filters(env):
    if isinstance(env, Flask):
        # old api for init_filters: we used to pass flask application
        env = env.jinja_env

    env.filters['nl2br'] = nl2br
    env.filters['paragraphs'] = paragraphs
    env.filters['date_age'] = date_age
    env.filters['datetimeparse'] = datetimeparse
    env.filters['age'] = age
    env.filters['date'] = date
    env.filters['babel2datepicker'] = babel2datepicker
    env.filters['to_timestamp'] = to_timestamp
    env.filters['url_for'] = obj_to_url
    env.filters['abbrev'] = abbrev
    env.filters['filesize'] = filesize
    env.filters['roughsize'] = roughsize
    env.filters['labelize'] = labelize
    env.filters['linkify'] = linkify
    env.filters['toslug'] = slugify
    env.filters['bool2check'] = bool2check
