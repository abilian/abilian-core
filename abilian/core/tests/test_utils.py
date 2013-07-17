# coding=utf-8
from unittest import TestCase

from abilian.core.util import Pagination, slugify


class TestPagination(TestCase):

  def test1(self):
    p = Pagination(1, 10, 10)
    l = list(p.iter_pages())
    self.assertEquals([1], l)
    assert not p.has_prev
    assert not p.has_next
    assert p.prev is None
    assert p.next is None

  def test2(self):
    p = Pagination(1, 10, 20)
    l = list(p.iter_pages())
    self.assertEquals([1, 2], l)
    assert not p.has_prev
    assert p.has_next
    assert p.prev is None
    assert p.next == 2

  def test3(self):
    p = Pagination(1, 10, 100)
    l = list(p.iter_pages())
    self.assertEquals([1, 2, 3, 4, 5, None, 9, 10], l)
    assert not p.has_prev
    assert p.has_next
    assert p.prev is None
    assert p.next == 2

  def test4(self):
    p = Pagination(10, 10, 100)
    l = list(p.iter_pages())
    self.assertEquals([1, 2, None, 8, 9, 10], l)
    assert p.has_prev
    assert not p.has_next
    assert p.prev == 9
    assert p.next is None


class TestSlugify(TestCase):

  def test1(self):
    slug = slugify(u"a b c")
    assert slug == 'a-b-c'
    assert isinstance(slug, str)

  def test2(self):
    slug = slugify(u"C'est l'été")
    assert slug == 'c-est-l-ete'
    assert isinstance(slug, str)
