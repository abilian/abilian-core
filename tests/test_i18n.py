# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from babel import Locale
from flask_babel import force_locale, get_locale
from jinja2 import DictLoader

from abilian import i18n


def test_get_template_i18n_en(app, test_request_context):
    template_path = '/myfile.txt'
    en = Locale('en')

    result = i18n.get_template_i18n(template_path, locale=en)

    assert '/myfile.en.txt' in result
    assert '/myfile.txt' in result


def test_get_template_i18n_en_us(app, test_request_context):
    template_path = '/myfile.txt'
    en = Locale('en_US')

    result = i18n.get_template_i18n(template_path, locale=en)

    assert '/myfile.en_US.txt' in result
    assert '/myfile.txt' in result


def test_get_template_i18n_fr(app, test_request_context):
    template_path = '/myfile.txt'
    with force_locale('fr'):
        result = i18n.get_template_i18n(template_path, get_locale())
        assert '/myfile.fr.txt' in result
        assert '/myfile.txt' in result


def test_render_template_i18n(app, test_request_context):
    loader = DictLoader({
        'tmpl.txt': 'default ({{ locale }})',
        'tmpl.en.txt': 'en locale ({{ locale }})',
        'tmpl.fr.txt': 'fr locale ({{ locale }})',
    })
    app_loader = app.jinja_loader
    app.jinja_loader = loader
    render = i18n.render_template_i18n
    try:
        assert render('tmpl.txt', locale='fr') == 'fr locale (fr)'
        assert render('tmpl.txt', locale='en') == 'en locale (en)'
        assert render('tmpl.txt', locale='de') == 'default (de)'
    finally:
        app.jinja_loader = app_loader


def test_default_country(app, test_request_context):
    assert 'DEFAULT_COUNTRY' in app.config
    assert app.config['DEFAULT_COUNTRY'] is None
    assert i18n.default_country() is None
    assert i18n.country_choices()[0][0] == 'AF'

    app.config['DEFAULT_COUNTRY'] = 'FR'
    assert i18n.default_country() == 'FR'
    assert i18n.country_choices()[0][0] == 'FR'
    assert i18n.country_choices(default_country_first=False)[0][0] == 'AF'


# No idea what this test was supposed to do...
# @skip
# def test_ensure_request_context(app, ctx):
#     en = Locale(b'en')
#     fr = Locale(b'fr')
#
#     # By default, a request context is present is test case setup.
#     # First let's show no new request context is set up and that
#     # set_locale works as advertised.
#     app_ctx = _app_ctx_stack.top
#     current_ctx = _request_ctx_stack.top
#     assert current_ctx is not None
#     assert get_locale() == en
#
#     with i18n.ensure_request_context():
#         assert current_ctx == _request_ctx_stack.top
#
#         with force_locale(fr):
#             assert get_locale() == fr
#
#     self._ctx.pop()
#     self._ctx = None
#     assert _app_ctx_stack.top is None
#     assert _request_ctx_stack.top is None
#     assert get_locale() is None
#
#     app_ctx.push()
#
#     # # ensure set_locale() doesn't set up a request context
#     # with force_locale(fr):
#     #     assert _request_ctx_stack.top is None
#     #     assert get_locale() is None
#
#     with i18n.ensure_request_context():
#         assert _request_ctx_stack.top is not None
#         assert current_ctx != _request_ctx_stack.top
#         assert get_locale() == en
#
#         with force_locale(fr):
#             assert get_locale() == fr
#
#     assert _request_ctx_stack.top is None
#     assert get_locale() is None
#
#     # test chaining
#     with i18n.ensure_request_context(), force_locale(fr):
#         assert get_locale() == fr
