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

  def test_basic(self):
    slug = slugify(u'a b c')
    assert slug == u'a-b-c'
    assert isinstance(slug, unicode)
    assert slugify(slug) == u'a-b-c' # idempotent

  def test_separator(self):
    slug = slugify(u"a-b++ c-+", u'+')
    assert slug == u'a+b+c'

  def test_non_unicode_input(self):
    slug = slugify(b"a b c")
    assert slug == u'a-b-c'
    assert isinstance(slug, unicode)

  def test_non_ascii(self):
    slug = slugify(u"C'est l'été !")
    assert slug == u'c-est-l-ete'

    # with a special space character
    slug = slugify(u"a_b\u205fc") # U+205F: MEDIUM MATHEMATICAL SPACE
    assert slug == u'a-b-c'

    # with non-ascii translatable chars, like EN DASH U+2013 (–) and EM DASH
    # U+2014 (—).
    # this test fails if regexp subst is done after unicode normalization
    assert slugify(u'a\u2013b\u2014c') == u'a-b-c'
