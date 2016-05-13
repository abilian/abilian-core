# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from babel import Locale
from flask import _app_ctx_stack, _request_ctx_stack
from flask_babel import get_locale
from jinja2 import DictLoader

from abilian import i18n
from abilian.testing import BaseTestCase


class I18NTestCase(BaseTestCase):

    def test_set_locale(self):
        en = Locale('en')
        fr = Locale('fr')
        with self.app.test_request_context('/'):
            assert get_locale() == en

            with i18n.set_locale('fr') as new_locale:
                assert get_locale() == fr
                assert isinstance(new_locale, Locale)
                assert new_locale == fr
            assert get_locale() == en

            with i18n.set_locale(fr):
                assert get_locale() == fr
                with i18n.set_locale(en):
                    assert get_locale() == en
                assert get_locale() == fr
            assert get_locale() == en

        # no request context: no locale set
        app_ctx = _app_ctx_stack.top
        self._ctx.pop()
        self._ctx = None
        app_ctx.push()
        with i18n.set_locale(fr):
            assert get_locale() is None

    def test_ensure_request_context(self):
        en = Locale('en')
        fr = Locale('fr')

        # by default, a request context is present is test case setup.  first let's
        # show no new request context is set up and that set_locale works as
        # advertised
        app_ctx = _app_ctx_stack.top
        current_ctx = _request_ctx_stack.top
        assert current_ctx is not None
        assert get_locale() == en

        with i18n.ensure_request_context():
            assert current_ctx == _request_ctx_stack.top

            with i18n.set_locale(fr):
                assert get_locale() == fr

        self._ctx.pop()
        self._ctx = None
        assert _app_ctx_stack.top is None
        assert _request_ctx_stack.top is None
        assert get_locale() is None

        app_ctx.push()
        # ensure set_locale() doesn't set up a request context
        with i18n.set_locale(fr):
            assert _request_ctx_stack.top is None
            assert get_locale() is None

        with i18n.ensure_request_context():
            assert _request_ctx_stack.top is not None
            assert current_ctx != _request_ctx_stack.top
            assert get_locale() == en

            with i18n.set_locale(fr):
                assert get_locale() == fr

        assert _request_ctx_stack.top is None
        assert get_locale() is None

        # test chaining
        with i18n.ensure_request_context(), i18n.set_locale(fr):
            assert get_locale() == fr

    def test_get_template_i18n(self):
        template_path = '/myfile.txt'
        en = Locale('en')
        result = i18n.get_template_i18n(template_path, locale=en)
        self.assertIn('/myfile.en.txt', result)
        self.assertIn('/myfile.txt', result)

        en = Locale('en_US')
        result = i18n.get_template_i18n(template_path, locale=en)
        self.assertIn('/myfile.en_US.txt', result)
        self.assertIn('/myfile.txt', result)

        with i18n.set_locale('fr'):
            result = i18n.get_template_i18n(template_path, get_locale())
            self.assertIn('/myfile.fr.txt', result)
            self.assertIn('/myfile.txt', result)

    def test_render_template_i18n(self):
        loader = DictLoader({u'tmpl.txt': u'default ({{ locale }})',
                             u'tmpl.en.txt': u'en locale ({{ locale }})',
                             u'tmpl.fr.txt': u'fr locale ({{ locale }})',})
        app_loader = self.app.jinja_loader
        self.app.jinja_loader = loader
        render = i18n.render_template_i18n
        try:
            assert render('tmpl.txt', locale='fr') == u'fr locale (fr)'
            assert render('tmpl.txt', locale='en') == u'en locale (en)'
            assert render('tmpl.txt', locale='de') == u'default (de)'
        finally:
            self.app.jinja_loader = app_loader

    def test_default_country(self):
        assert 'DEFAULT_COUNTRY' in self.app.config
        assert self.app.config['DEFAULT_COUNTRY'] is None
        assert i18n.default_country() is None
        assert i18n.country_choices()[0][0] == u'AF'

        self.app.config['DEFAULT_COUNTRY'] = u'FR'
        assert i18n.default_country() == u'FR'
        assert i18n.country_choices()[0][0] == u'FR'
        assert i18n.country_choices(default_country_first=False)[0][0] == u'AF'
