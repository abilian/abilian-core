"""
Various tools that don't belong some place specific.
"""

import functools
import logging
import time
from datetime import tzinfo, timedelta
import pytz
from math import ceil
import unicodedata
import re

from flask import request

class __system_tz(tzinfo):
  """ Host Timezone info. Useful for getting utc datetime in current
  timezone.
  This class is inspired by LocalTimeZone in python documentation:
  http://docs.python.org/2/library/datetime.html
  """
  __ZERO = timedelta(0)
  __UTCOFFSET = timedelta(seconds=-time.timezone)
  __ALTOFFSET = (timedelta(seconds=-time.altzone)
                 if time.daylight
                 else __UTCOFFSET)
  __DSTDIFF = __ALTOFFSET - __UTCOFFSET

  def tzname(self, dt):
    return time.tzname[int(self._isdst(dt))]

  def utcoffset(self, dt):
    return self.__ALTOFFSET if self._isdst(dt) else self.__UTCOFFSET

  def dst(self, dt):
    return self.__DSTDIFF if self._isdst(dt) else self.__ZERO

  def _isdst(self, dt):
    tt = (dt.year, dt.month, dt.day,
          dt.hour, dt.minute, dt.second,
          dt.weekday(), 0, 0)
    stamp = time.mktime(tt)
    tt = time.localtime(stamp)
    return tt.tm_isdst > 0

  # pytz specific, used by flask.ext.babel for example
  def normalize(self, dt):
    if dt.tzinfo is None:
      raise ValueError('Naive time - no tzinfo set')

    return dt.astimezone(self)

system_tz = __system_tz()

def local_dt(dt):
  """ Return an aware datetime in system timezone, from a naive or aware
  datetime. Naive datetime are assumed to be in UTC TZ.
  """
  if not dt.tzinfo:
    dt = dt.replace(tzinfo=pytz.utc)
  return dt.astimezone(system_tz)

def utc_dt(dt):
  """ set UTC timezone on a datetime object. A naive datetime is assumed to be
  in UTC TZ
  """
  if not dt.tzinfo:
    return dt.replace(tzinfo=pytz.utc)
  return dt.astimezone(pytz.utc)

def get_params(names):
  """
  Returns a dictionary with params from request.

  TODO: I think we don't use it anymore and it should be removed before
  someone gets hurt.
  """
  params = {}
  for name in names:
    value = request.form.get(name) or request.files.get(name)
    if value is not None:
      params[name] = value
  return params


class timer(object):
  """
  Decorator that mesures the time it takes to run a function.
  """

  __instances = {}

  def __init__(self, f):
    self.__f = f
    self.log = logging.getLogger("." + f.func_name)

  def __call__(self, *args, **kwargs):
    self.__start = time.time()
    result = self.__f(*args, **kwargs)
    value = time.time() - self.__start
    self.log.info('ellapsed time: {0:.2f}ms'.format(value * 1000))
    return result


# From http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
class memoized(object):
  """
  Decorator. Caches a function's return value each time it is called.
  If called later with the same arguments, the cached value is returned
  (not reevaluated).
  """

  def __init__(self, func):
    self.func = func
    self.cache = {}

  def __call__(self, *args):
    try:
      return self.cache[args]
    except KeyError:
      value = self.func(*args)
      self.cache[args] = value
      return value
    except TypeError:
      # uncachable -- for instance, passing a list as an argument.
      # Better to not cache than to blow up entirely.
      return self.func(*args)

  def __repr__(self):
    """Return the function's docstring."""
    return self.func.__doc__

  def __get__(self, obj, objtype):
    """Support instance methods."""
    return functools.partial(self.__call__, obj)


# From http://flask.pocoo.org/snippets/44/
class Pagination(object):

  def __init__(self, page, per_page, total_count):
    self.page = page
    self.per_page = per_page
    self.total_count = total_count

  @property
  def pages(self):
    return int(ceil(self.total_count / float(self.per_page)))

  @property
  def has_prev(self):
    return self.page > 1

  @property
  def has_next(self):
    return self.page < self.pages

  def iter_pages(self, left_edge=2, left_current=2,
                 right_current=5, right_edge=2):
    last = 0
    for num in xrange(1, self.pages + 1):
      if num <= left_edge or \
          (num > self.page - left_current - 1
              and num < self.page + right_current) or \
          num > self.pages - right_edge:
        if last + 1 != num:
          yield None
        yield num
        last = num


def slugify(value, separator="-"):
  """Slugify an unicode string, to make it URL friendly."""
  if not isinstance(value, unicode):
    value = unicode(value)
  value = unicodedata.normalize('NFKD', value)
  value = value.encode('ascii', 'ignore')
  value = value.decode('ascii')
  value = re.sub('[^\w\s-]', ' ', value)
  value = value.strip().lower()
  value = re.sub('[%s\s]+' % separator, separator, value)
  return str(value)
