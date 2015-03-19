# coding=utf-8
"""
"""
from __future__ import absolute_import

from babel import Locale
from flask.ext.babel import get_locale
from abilian.testing import BaseTestCase
from abilian import i18n


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
