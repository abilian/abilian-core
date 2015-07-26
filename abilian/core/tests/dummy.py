from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from sqlalchemy import Column, UnicodeText, Text

from abilian.core.entities import Entity, SEARCHABLE


class DummyContact(Entity):
  salutation = Column(UnicodeText, default=u"")
  first_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  last_name = Column(UnicodeText, default=u"", info=SEARCHABLE)
  email = Column(Text, default=u"")
