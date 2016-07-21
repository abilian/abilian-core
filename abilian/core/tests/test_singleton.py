# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from abilian.core.singleton import UniqueName


class NS1(UniqueName):
    pass


class NS2(UniqueName):
    pass


def test_singleton():
    val = NS1('val')
    other_val = NS1('val')
    assert val is other_val
    assert id(val) == id(other_val)


def test_equality():
    val = NS1('val')
    assert val == 'val'
    assert val == u'val'


def test_namespaces():
    ns1_val = NS1('val')
    ns2_val = NS2('val')
    assert ns1_val is not ns2_val
    # equality works because of string compat
    assert ns1_val == ns2_val
