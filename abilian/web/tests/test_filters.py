import unittest
import datetime
from nose.tools import eq_
from jinja2 import Environment

from abilian.core.util import system_tz

from ..filters import init_filters, filesize, date_age


class FakeApp(object):
  def __init__(self, env):
    self.jinja_env = env


env = Environment()
init_filters(FakeApp(env))


class TestFilters(unittest.TestCase):

  def test_filesize(self):
    eq_("100&nbsp;B", str(filesize(100)))
    eq_("1.0&nbsp;kB", str(filesize(1000)))
    eq_("1.1&nbsp;kB", str(filesize(1100)))
    eq_("10&nbsp;kB", str(filesize(10000)))

  def test_date_age(self):
    now = datetime.datetime(2012, 6, 10, 10, 10, 10).replace(tzinfo=system_tz)

    dt = datetime.datetime(2012, 6, 10, 10, 10, 0).replace(tzinfo=system_tz)
    eq_("2012-06-10 10:10 (a minute ago)", date_age(dt, now))

    dt = datetime.datetime(2012, 6, 10, 10, 8, 10).replace(tzinfo=system_tz)
    eq_("2012-06-10 10:08 (2 minutes ago)", date_age(dt, now))

    dt = datetime.datetime(2012, 6, 10, 8, 10, 10).replace(tzinfo=system_tz)
    eq_("2012-06-10 08:10 (2 hours ago)", date_age(dt, now))

  def test_nl2br(self):
    tmpl = env.from_string(
      '{{ "first line\nsecond line\n\n  third, indented" | nl2br }}')
    eq_(tmpl.render(),
        u'first line<br />\nsecond line<br />\n<br />\n  third, indented')

  def test_paragraphs(self):
    tmpl = env.from_string(
    '''{{ "First paragraph
    some text
    with line return

    Second paragraph
    ... lorem

    Last one - a single line" | paragraphs }}
    ''')

    eq_(tmpl.render(),
        u'''<p>First paragraph<br />
    some text<br />
    with line return</p>

<p>Second paragraph<br />
    ... lorem</p>

<p>Last one - a single line</p>
    '''
        )
