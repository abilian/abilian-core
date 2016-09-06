# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import pytest
from babel import Locale
from flask import _app_ctx_stack, _request_ctx_stack
from flask_babel import force_locale, get_locale
from jinja2 import DictLoader

from abilian import i18n
from abilian.testing import BaseTestCase

skip = pytest.mark.skip


class I18NTestCase(BaseTestCase):

    @skip
    def test_ensure_request_context(self):
        en = Locale(b'en')
        fr = Locale(b'fr')

        # by default, a request context is present is test case setup.  first let's
        # show no new request context is set up and that set_locale works as
        # advertised
        app_ctx = _app_ctx_stack.top
        current_ctx = _request_ctx_stack.top
        assert current_ctx is not None
        assert get_locale() == en

        with i18n.ensure_request_context():
            assert current_ctx == _request_ctx_stack.top

            with force_locale(fr):
                assert get_locale() == fr

        self._ctx.pop()
        self._ctx = None
        assert _app_ctx_stack.top is None
        assert _request_ctx_stack.top is None
        assert get_locale() is None

        app_ctx.push()

        # # ensure set_locale() doesn't set up a request context
        # with force_locale(fr):
        #     assert _request_ctx_stack.top is None
        #     assert get_locale() is None

        with i18n.ensure_request_context():
            assert _request_ctx_stack.top is not None
            assert current_ctx != _request_ctx_stack.top
            assert get_locale() == en

            with force_locale(fr):
                assert get_locale() == fr

        assert _request_ctx_stack.top is None
        assert get_locale() is None

        # test chaining
        with i18n.ensure_request_context(), force_locale(fr):
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

        with force_locale('fr'):
            result = i18n.get_template_i18n(template_path, get_locale())
            self.assertIn('/myfile.fr.txt', result)
            self.assertIn('/myfile.txt', result)

    def test_render_template_i18n(self):
        loader = DictLoader({
            'tmpl.txt': 'default ({{ locale }})',
            'tmpl.en.txt': 'en locale ({{ locale }})',
            'tmpl.fr.txt': 'fr locale ({{ locale }})',
        })
        app_loader = self.app.jinja_loader
        self.app.jinja_loader = loader
        render = i18n.render_template_i18n
        try:
            assert render('tmpl.txt', locale='fr') == 'fr locale (fr)'
            assert render('tmpl.txt', locale='en') == 'en locale (en)'
            assert render('tmpl.txt', locale='de') == 'default (de)'
        finally:
            self.app.jinja_loader = app_loader

    def test_default_country(self):
        assert 'DEFAULT_COUNTRY' in self.app.config
        assert self.app.config['DEFAULT_COUNTRY'] is None
        assert i18n.default_country() is None
        assert i18n.country_choices()[0][0] == 'AF'

        self.app.config['DEFAULT_COUNTRY'] = 'FR'
        assert i18n.default_country() == 'FR'
        assert i18n.country_choices()[0][0] == 'FR'
        assert i18n.country_choices(default_country_first=False)[0][0] == 'AF'
