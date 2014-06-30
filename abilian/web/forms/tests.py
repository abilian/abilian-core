# coding=utf-8
"""
"""
from __future__ import absolute_import

import datetime
from unittest import TestCase
from wtforms.form import Form

from . import fields

class FieldsTestCase(TestCase):

  def test_datetime_field(self):
    """
    Test fields supports date with year < 1900
    """
    f = fields.DateTimeField().bind(Form(), 'dt')
    f.process_formdata(['17/06/1789 10:42'])
    self.assertEquals(f.data, datetime.datetime(1789, 06, 17, 10, 42))
    self.assertEquals(f._value(), '17/06/1789 10:42')

  def test_date_field(self):
    """
    Test fields supports date with year < 1900
    """
    f = fields.DateField().bind(Form(), 'dt')
    f.process_formdata(['17/06/1789'])
    self.assertEquals(f.data, datetime.date(1789, 06, 17))
    self.assertEquals(f._value(), '17/06/1789')
