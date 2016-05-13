from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from sqlalchemy import Column, Text, UnicodeText

from abilian.core.entities import SEARCHABLE, Entity


class DummyContact(Entity):
    salutation = Column(UnicodeText, default=u"")
    first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
    last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
    email = Column(Text, default=u"")
