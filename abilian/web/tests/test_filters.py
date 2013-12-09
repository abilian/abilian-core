import datetime
from nose.tools import eq_
from jinja2 import Environment
from pytz import timezone, utc

from flask import Flask
from flask.ext.testing import TestCase as FlaskTestCase
from flask.ext.babel import Babel

from ..filters import init_filters, filesize, date_age

env = Environment()
init_filters(env)


def en_locale():
  return 'en'


def user_tz():
  # This one is GMT+8 and has no DST (tests should pass any time in year)
  return 'Asia/Hong_Kong'

USER_TZ = timezone(user_tz())


class TestFilters(FlaskTestCase):

  def create_app(self):
    app = Flask(__name__)
    babel = Babel(app, default_locale='fr', default_timezone=USER_TZ)
    babel.localeselector(en_locale)
    babel.timezoneselector(user_tz)
    return app

  def test_filesize(self):
    eq_("100&nbsp;B", str(filesize(100)))
    eq_("1.0&nbsp;kB", str(filesize(1000)))
    eq_("1.1&nbsp;kB", str(filesize(1100)))
    eq_("10&nbsp;kB", str(filesize(10000)))

  def test_date_age(self):
    now = datetime.datetime(2012, 6, 10, 10, 10, 10, tzinfo=utc)

    dt = datetime.datetime(2012, 6, 10, 10, 10, 0, tzinfo=utc)
    eq_("2012-06-10 18:10 (1 minute ago)", date_age(dt, now))

    dt = datetime.datetime(2012, 6, 10, 10, 8, 10, tzinfo=utc)
    eq_("2012-06-10 18:08 (2 minutes ago)", date_age(dt, now))

    dt = datetime.datetime(2012, 6, 10, 8, 30, 10, tzinfo=utc)
    eq_("2012-06-10 16:30 (2 hours ago)", date_age(dt, now))

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
