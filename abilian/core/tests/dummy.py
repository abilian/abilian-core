# coding=utf-8
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from sqlalchemy import Column, Text, UnicodeText

from abilian.core.entities import SEARCHABLE, Entity


class DummyContact(Entity):
    salutation = Column(UnicodeText, default="")
    first_name = Column(UnicodeText, default="", info=SEARCHABLE)
    last_name = Column(UnicodeText, default="", info=SEARCHABLE)
    email = Column(Text, default="")
