from unittest import TestCase

from yaka.core.entities import SEARCHABLE, NOT_SEARCHABLE, AUDITABLE


class InfoTestCase(TestCase):

  def test(self):
    info = SEARCHABLE
    assert info['searchable']

    info = NOT_SEARCHABLE
    assert not info['searchable']

    info = SEARCHABLE + AUDITABLE
    assert info['searchable']
    assert info['auditable']
