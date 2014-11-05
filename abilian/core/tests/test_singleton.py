# coding=utf-8
"""
"""
from __future__ import absolute_import

import unittest

from abilian.core.singleton import UniqueName


class UniqueNameTestCase(unittest.TestCase):

  def setUp(self):
    class NS1(UniqueName):
      pass

    class NS2(UniqueName):
      pass

    self.NS1 = NS1
    self.NS2 = NS2

  def test_singleton(self):
    val = self.NS1('val')
    other_val = self.NS1('val')
    self.assertIs(val, other_val)
    self.assertEquals(id(val), id(other_val))

  def test_equality(self):
    val = self.NS1('val')
    self.assertEquals(val, 'val')
    self.assertEquals(val, u'val')

  def test_namespaces(self):
    ns1_val = self.NS1('val')
    ns2_val = self.NS2('val')
    self.assertIsNot(ns1_val, ns2_val)
    # equality works because of string compat
    self.assertEquals(ns1_val, ns2_val)
