# coding=utf-8

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from six import text_type

from abilian.core.util import Pagination, slugify


def test_pagination_1():
    p = Pagination(1, 10, 10)
    l = list(p.iter_pages())
    assert l == [1]
    assert not p.has_prev
    assert not p.has_next
    assert p.prev is None
    assert p.next is None


def test_pagination_2():
    p = Pagination(1, 10, 20)
    l = list(p.iter_pages())
    assert l == [1, 2]
    assert not p.has_prev
    assert p.has_next
    assert p.prev is None
    assert p.next == 2


def test_pagination_3():
    p = Pagination(1, 10, 100)
    l = list(p.iter_pages())
    assert l == [1, 2, 3, 4, 5, None, 9, 10]
    assert not p.has_prev
    assert p.has_next
    assert p.prev is None
    assert p.next == 2


def test_pagination_4():
    p = Pagination(10, 10, 100)
    l = list(p.iter_pages())
    assert l == [1, 2, None, 8, 9, 10]
    assert p.has_prev
    assert not p.has_next
    assert p.prev == 9
    assert p.next is None


def test_slugify_basic():
    slug = slugify('a b c')
    assert slug == 'a-b-c'
    assert isinstance(slug, text_type)
    assert slugify(slug) == 'a-b-c'  # idempotent


def test_slugify_separator():
    slug = slugify("a-b++ c-+", '+')
    assert slug == 'a+b+c'


def test_slugify_non_ascii():
    slug = slugify("C'est l'été !")
    assert slug == 'c-est-l-ete'

    # with a special space character
    slug = slugify("a_b\u205fc")  # U+205F: MEDIUM MATHEMATICAL SPACE
    assert slug == 'a-b-c'

    # with non-ascii translatable chars, like EN DASH U+2013 (–) and EM DASH
    # U+2014 (—).
    # this test fails if regexp subst is done after unicode normalization
    assert slugify('a\u2013b\u2014c') == 'a-b-c'
