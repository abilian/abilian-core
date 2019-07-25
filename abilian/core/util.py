"""Various tools that don't belong some place specific."""
import functools
import hashlib
import logging
import re
import time
import unicodedata
from datetime import datetime
from math import ceil
from typing import Any, Union

import pytz
from babel.dates import LOCALTZ
from flask import request
from werkzeug.local import LocalProxy


def unwrap(obj: Any):
    """Unwrap obj from werkzeug.local.LocalProxy if needed.

    This is required if one want to test `isinstance(obj, SomeClass)`.
    """
    if isinstance(obj, LocalProxy):
        obj = obj._get_current_object()
    return obj


# TODO: remove later
noproxy = unwrap


def fqcn(cls: type) -> str:
    """Fully Qualified Class Name."""
    return str(cls.__module__ + "." + cls.__name__)


def friendly_fqcn(cls_or_cls_name: Union[type, str]) -> str:
    """Friendly name of fully qualified class name.

    :param cls_or_cls_name: a string or a class
    """
    if isinstance(cls_or_cls_name, type):
        cls_name = fqcn(cls_or_cls_name)
    else:
        cls_name = cls_or_cls_name

    return cls_name.rsplit(".", 1)[-1]


def utcnow() -> datetime:
    """Return a new aware datetime with current date and time, in UTC TZ."""
    return datetime.now(pytz.utc)


def local_dt(dt: datetime) -> datetime:
    """Return an aware datetime in system timezone, from a naive or aware
    datetime.

    Naive datetime are assumed to be in UTC TZ.
    """
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)
    return LOCALTZ.normalize(dt.astimezone(LOCALTZ))


def utc_dt(dt: datetime) -> datetime:
    """Set UTC timezone on a datetime object.

    A naive datetime is assumed to be in UTC TZ.
    """
    if not dt.tzinfo:
        return pytz.utc.localize(dt)
    return dt.astimezone(pytz.utc)


def get_params(names):
    """Return a dictionary with params from request.

    TODO: I think we don't use it anymore and it should be removed
    before someone gets hurt.
    """
    params = {}
    for name in names:
        value = request.form.get(name) or request.files.get(name)
        if value is not None:
            params[name] = value
    return params


class timer:
    """Decorator that mesures the time it takes to run a function."""

    def __init__(self, f):
        self.__f = f
        self.log = logging.getLogger(f.__module__ + "." + f.__name__)

    def __call__(self, *args, **kwargs):
        self.__start = time.time()
        result = self.__f(*args, **kwargs)
        value = time.time() - self.__start
        self.log.info(f"elapsed time: {(value * 1000):.2f}ms")
        return result


# From http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
class memoized:
    """Decorator that caches a function's return value each time it is called.

    If called later with the same arguments, the cached value is
    returned (not reevaluated).
    """

    def __init__(self, func):
        self.func = func
        self.cache = {}
        functools.wraps(func)(self)

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

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return functools.partial(self.__call__, obj)


# From http://flask.pocoo.org/snippets/44/
class Pagination:
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

    # pylint: disable=W1653
    @property
    def next(self):
        return self.page + 1 if self.has_next else None

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current - 1 < num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


_NOT_WORD_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)


def slugify(value, separator="-"):
    """Slugify an Unicode string, to make it URL friendly."""
    if not isinstance(value, str):
        raise ValueError("value must be a Unicode string")
    value = _NOT_WORD_RE.sub(" ", value)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore")
    value = value.decode("ascii")
    value = value.strip().lower()
    value = re.sub(fr"[{separator}_\s]+", separator, value)
    return value


class BasePresenter:
    """A presenter wraps a model an adds specific (often, web-centric)
    accessors.

    Subclass to make it useful. Presenters are immutable.
    """

    def __init__(self, model):
        self._model = model

    def __getattr__(self, key):
        return getattr(self._model, key)

    def __setattr__(self, key, value):
        """Make presenter immutable."""
        if key == "_model":
            self.__dict__[key] = value
        else:
            raise AttributeError("Can't set attribute on a presenter.")

    @classmethod
    def wrap_collection(cls, models):
        return [cls(model) for model in models]


def encode_string(string_or_bytes: Union[str, bytes]) -> bytes:
    """Encode a string to bytes, if it isn't already.

    :param string_or_bytes: The string to encode.
        Does nothing if it's already bytes.
    """
    # from pysecurity

    if isinstance(string_or_bytes, str):
        return string_or_bytes.encode()
    else:
        return string_or_bytes


def md5(data: Union[str, bytes, None]):
    """md5 function, as in flask-security."""
    # flask-security is not needed anywhere else and as of 1.7.5 has
    # strong dependency requirements that prevent us from upgrading a
    # few packages (flask-login 0.4).
    return hashlib.md5(encode_string(data or "")).hexdigest()
