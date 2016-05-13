from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime

import html5lib
import mock
from flask import Flask
from flask_babel import Babel
from flask_testing import TestCase as FlaskTestCase
from jinja2 import Environment
from pytz import timezone, utc

from .. import filters

env = Environment()
filters.init_filters(env)


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

    def test_labelize(self):
        labelize = filters.labelize
        self.assertEquals(u'Test Case', labelize(u'test_case'))

    def test_filesize(self):
        filesize = filters.filesize
        self.assertEquals("100&nbsp;B", str(filesize('100')))
        self.assertEquals("100&nbsp;B", str(filesize(100)))
        self.assertEquals("1.0&nbsp;kB", str(filesize(1000)))
        self.assertEquals("1.1&nbsp;kB", str(filesize(1100)))
        self.assertEquals("10&nbsp;kB", str(filesize(10000)))
        self.assertEquals("1.1&nbsp;MB", str(filesize(1100100)))
        self.assertEquals("10&nbsp;MB", str(filesize(10000000)))
        self.assertEquals("1.1&nbsp;GB", str(filesize(1100100000)))
        self.assertEquals("100&nbsp;GB", str(filesize(100000000000)))

    def test_roughsize(self):
        roughsize = filters.roughsize
        self.assertEquals(u'6', roughsize(6))
        self.assertEquals(u'15', roughsize(15))
        self.assertEquals(u'130+', roughsize(134))
        self.assertEquals(u'10+', roughsize(15, above=10))
        self.assertEquals(u'55+', roughsize(57, mod=5))

    def test_date_age(self):
        date_age = filters.date_age
        now = datetime.datetime(2012, 6, 10, 10, 10, 10, tzinfo=utc)

        self.assertEquals("", date_age(None))
        dt = datetime.datetime(2012, 6, 10, 10, 10, 0, tzinfo=utc)
        self.assertEquals("2012-06-10 18:10 (1 minute ago)", date_age(dt, now))

        dt = datetime.datetime(2012, 6, 10, 10, 8, 10, tzinfo=utc)
        self.assertEquals("2012-06-10 18:08 (2 minutes ago)", date_age(dt, now))

        dt = datetime.datetime(2012, 6, 10, 8, 30, 10, tzinfo=utc)
        self.assertEquals("2012-06-10 16:30 (2 hours ago)", date_age(dt, now))

        # for coverage: test when using default parameter now=None
        dt_patcher = mock.patch.object(filters.datetime,
                                       'datetime',
                                       mock.Mock(wraps=datetime.datetime))
        with dt_patcher as mocked:
            mocked.utcnow.return_value = now
            self.assertEquals("2012-06-10 16:30 (2 hours ago)", date_age(dt))

    def test_age(self):
        age = filters.age
        now = datetime.datetime(2012, 6, 10, 10, 10, 10, tzinfo=utc)
        d1m = datetime.datetime(2012, 6, 10, 10, 10, 0, tzinfo=utc)
        d3w = datetime.datetime(2012, 5, 18, 8, 0, 0, tzinfo=utc)
        d2011 = datetime.datetime(2011, 9, 4, 12, 12, 0, tzinfo=utc)

        # default parameters
        assert age(None) == u''
        assert age(d1m, now) == u'1 minute ago'
        assert age(d3w, now) == u'3 weeks ago'

        # with direction
        assert age(d1m, now, add_direction=False) == u'1 minute'
        assert age(d3w, now, add_direction=False) == u'3 weeks'

        # with date_threshold
        assert age(d1m, now, date_threshold='day') == u'1 minute ago'
        # same year: 2012 not shown
        assert age(d3w, now, date_threshold='day') == u'May 18, 4:00 PM'
        # different year: 2011 shown
        assert (age(d2011, now, date_threshold='day') ==
                u'September 4, 2011, 8:12 PM')

        # using default parameter now=None
        dt_patcher = mock.patch.object(filters.datetime,
                                       'datetime',
                                       mock.Mock(wraps=datetime.datetime))
        with dt_patcher as mocked:
            mocked.utcnow.return_value = now
            assert age(d1m) == u'1 minute ago'

    def test_abbrev(self):
        abbrev = filters.abbrev
        self.assertEquals(u'test', abbrev(u'test', 20))
        self.assertEquals(u'Longer test...e truncated',
                          abbrev(u'Longer test. it should be truncated', 25))

    def test_linkify(self):
        tmpl = env.from_string('{{ "http://test.example.com"|linkify}}')
        rendered = tmpl.render()
        el = html5lib.parseFragment(rendered)
        self.assertEquals(len(el.getchildren()), 1)
        el = el.getchildren()[0]
        self.assertEquals(el.tag, u'{http://www.w3.org/1999/xhtml}a')
        self.assertEquals(el.text, u'http://test.example.com')
        self.assertEquals(
            sorted(el.items()), [(u'href', u'http://test.example.com'),
                                 (u'rel', u'nofollow')])

    def test_nl2br(self):
        tmpl = env.from_string(
            '{{ "first line\nsecond line\n\n  third, indented" | nl2br }}')
        self.assertEquals(
            tmpl.render(),
            u'first line<br />\nsecond line<br />\n<br />\n  third, indented')

    def test_paragraphs(self):
        tmpl = env.from_string('''{{ "First paragraph
    some text
    with line return

    Second paragraph
    ... lorem

    Last one - a single line" | paragraphs }}
    ''')

        self.assertEquals(tmpl.render(), u'''<p>First paragraph<br />
    some text<br />
    with line return</p>

<p>Second paragraph<br />
    ... lorem</p>

<p>Last one - a single line</p>
    ''')
