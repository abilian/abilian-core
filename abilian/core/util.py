"""
Various tools that don't belong some place specific.
"""

import functools
import logging
import time
import pytz
from math import ceil
import unicodedata
import re

from babel.dates import LOCALTZ
from werkzeug.local import LocalProxy

from flask import request


def noproxy(obj):
  """
  Unwrap obj from werkzeug.local.LocalProxy if needed. This is required if
  one want to test `isinstance(obj, SomeClass)`.
  """
  if isinstance(obj, LocalProxy):
    obj = obj._get_current_object()
  return obj


def fqcn(cls):
  """
  Fully Qualified Class Name
  """
  return unicode(cls.__module__ + '.' + cls.__name__)


def friendly_fqcn(cls_name):
  """
  Friendly name of fully qualified class name.
  :param cls_name: a string or a class
  """
  if isinstance(cls_name, type):
    cls_name = fqcn(cls_name)

  return cls_name.rsplit('.', 1)[-1]


def local_dt(dt):
  """ Return an aware datetime in system timezone, from a naive or aware
  datetime. Naive datetime are assumed to be in UTC TZ.
  """
  if not dt.tzinfo:
    dt = dt.replace(tzinfo=pytz.utc)
  return dt.astimezone(LOCALTZ)


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
    self.log = logging.getLogger(f.__module__ + '.' + f.func_name)

  def __call__(self, *args, **kwargs):
    self.__start = time.time()
    result = self.__f(*args, **kwargs)
    value = time.time() - self.__start
    self.log.info('elapsed time: {0:.2f}ms'.format(value * 1000))
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
  def prev(self):
    return self.page - 1 if self.has_prev else None

  @property
  def has_next(self):
    return self.page < self.pages

  @property
  def next(self):
    return self.page + 1 if self.has_next else None

  def iter_pages(self, left_edge=2, left_current=2,
                 right_current=5, right_edge=2):
    last = 0
    for num in xrange(1, self.pages + 1):
      if (num <= left_edge or
          (self.page - left_current - 1 < num < self.page + right_current) or
          num > self.pages - right_edge):
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


class BasePresenter(object):
  """
  A presenter wraps a model an adds specific (often, web-centric) accessors.
  subclass to make it useful. Presenters are immutable.
  """
  def __init__(self, model):
    self._model = model

  def __getattr__(self, key):
    return getattr(self._model, key)

  def __setattr__(self, key, value):
    """Make presenter immutable.
    """
    if key == '_model':
      self.__dict__[key] = value
    else:
      raise AttributeError("Can't set attribute on a presenter.")

  @classmethod
  def wrap_collection(cls, models):
    return [cls(model) for model in models]
