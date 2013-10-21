"""
Add a few specific filters to Jinja2.
"""

import re
from functools import wraps
import datetime
from pytz import utc
from calendar import timegm
from babel.dates import DateTimePattern
import bleach

from jinja2 import Markup, escape, evalcontextfilter
from flask import Flask
from flask.ext import babel
from flask.ext.babel import gettext as _

from ..core.util import local_dt, utc_dt


def autoescape(filter_func):
  """ Decorator to autoescape result from filters
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
  """ Replace newlines with <br />
  """
  result = escape(value).replace(u'\n', Markup(u'<br />\n'))
  return result

_PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@autoescape
def paragraphs(value):
  """ Blank lines delimitates paragraphs
  """
  result = u'\n\n'.join(
    (u'<p>{}</p>'.format(p.strip().replace('\n', Markup('<br />\n')))
     for p in _PARAGRAPH_RE.split(escape(value))))
  return result


def labelize(s):
  return " ".join([ w.capitalize() for w in s.split("_") ])


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


def age(dt, now=None):
  # Fail silently for now XXX
  if not dt:
    return ""

  if not now:
    now = datetime.datetime.utcnow()

  dt = utc_dt(dt)
  now = utc_dt(now)

  age = now - dt
  if age.days == 0:
    if age.seconds < 120:
      age_str = _("a minute ago")
    elif age.seconds < 3600:
      age_str = _("%(num)d minutes ago", num=age.seconds / 60)
    elif age.seconds < 7200:
      age_str = _("an hour ago")
    else:
      age_str = _("%(num)d hours ago", num=age.seconds / 3600)
  else:
    if age.days == 1:
      age_str = _("yesterday")
    elif age.days <= 31:
      age_str = _("%(num)d days ago", num=age.days)
    elif age.days <= 72:
      age_str = _("a month ago")
    elif age.days <= 365:
      age_str = _("%(num)d months ago", num=age.days / 30)
    elif age.days <= 2*365:
      age_str = _("last year")
    else:
      age_str = _("%(num)d years ago", num=age.days / 365)

  return age_str


def date_age(dt, now=None):
  # Fail silently for now XXX
  if not dt:
    return ""
  age_str = age(dt, now)
  return "%s (%s)" % (local_dt(dt).strftime("%Y-%m-%d %H:%M"), age_str)


def date(value):
  format = "EE, d MMMM y"
  if isinstance(value, datetime.date):
    return babel.format_date(value, format)
  else:
    return babel.format_date(local_dt(value), format)


def babel2datepicker(fmt):
  """ Convert date format from babel
  (http://babel.pocoo.org/docs/dates/#date-fields)) to a format understood by
  bootstrap-datepicker.
  """
  if isinstance(fmt, DateTimePattern):
    fmt = fmt.pattern

  # days
  replace = None
  if 'd' in fmt:
    replace = ('d', 'd')
  elif 'EEEEE' in fmt:
    replace = ('EEEEE', 'D') # narrow name => short name
  elif 'EEEE' in fmt:
    replace = ('EEEE', 'DD')
  else:
    replace = ('EEE', 'D')

  fmt = fmt.replace(*replace)
  replace = None

  # months
  if 'MMMM' in fmt:
    replace = ('MMMM', 'MM')
  elif 'MMM' in fmt:
    replace = ('MMM', 'M')
  elif 'M' in fmt:
    # numerical months, 1 or 2-digit format
    fmt.replace('M', 'm')

  if replace:
    fmt = fmt.replace(*replace)

  if 'yyyy' not in fmt:
    # by default change to 4-digit years
    fmt = fmt.replace('yy', 'yyyy')

  return fmt


# Doesn't work yet. TZ issues.
def to_timestamp(dt):
  utc_datetime = dt.astimezone(utc)
  return timegm(utc_datetime.timetuple()) + utc_datetime.microsecond / 1e6


def abbrev(s, max_size):
  if len(s) <= max_size:
    return s
  else:
    h = max_size / 2 - 1
    return s[0:h] + "..." + s[-h:]

@autoescape
def linkify(s):
  return Markup(bleach.linkify(s))

def init_filters(env):
  if isinstance(env, Flask):
    # old api for init_filters: we used to pass flask application
    env = env.jinja_env

  env.filters['nl2br'] = nl2br
  env.filters['paragraphs'] = paragraphs
  env.filters['date_age'] = date_age
  env.filters['age'] = age
  env.filters['date'] = date
  env.filters['babel2datepicker'] = babel2datepicker
  env.filters['to_timestamp'] = to_timestamp

  env.filters['abbrev'] = abbrev
  env.filters['filesize'] = filesize
  env.filters['labelize'] = labelize
  env.filters['linkify'] = linkify

