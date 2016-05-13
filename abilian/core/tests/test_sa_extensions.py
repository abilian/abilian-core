from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import uuid

from sqlalchemy import Column

from abilian.core.entities import Entity
from abilian.core.extensions import db
from abilian.core.sqlalchemy import UUID, JSONDict, JSONList
from abilian.testing import BaseTestCase


class DummyModel2(Entity):
    list_attr = Column(JSONList())
    dict_attr = Column(JSONDict())
    uuid = Column(UUID())


class SAExtensionTestCase(BaseTestCase):

    def test_list_attribute(self):
        model = DummyModel2(list_attr=[1, 2, 3])
        db.session.add(model)
        db.session.commit()
        model_id = model.id
        db.session.remove()
        model2 = DummyModel2.query.get(model_id)
        assert model2.list_attr == [1, 2, 3]

        model2.list_attr.append(4)
        assert model2.list_attr == [1, 2, 3, 4]

        del model2.list_attr[0]
        assert model2.list_attr == [2, 3, 4]

    def test_dict_attribute(self):
        model = DummyModel2(dict_attr=dict(a=3, b=4))
        db.session.add(model)
        db.session.commit()
        model_id = model.id
        db.session.remove()
        model2 = DummyModel2.query.get(model_id)
        assert model2.dict_attr == dict(a=3, b=4)

        model2.dict_attr['c'] = 5
        assert model2.dict_attr == dict(a=3, b=4, c=5)

    def test_uuid_attribute(self):
        # uuid from string
        model = DummyModel2(uuid='c5ad316a-2cd0-4f78-a49b-cff216c10713')
        db.session.add(model)
        db.session.commit()
        model_id = model.id
        db.session.remove()
        model2 = DummyModel2.query.get(model_id)

        assert isinstance(model2.uuid, uuid.UUID)

        # plain UUID object
        u = uuid.UUID('3eb7f164-bf15-4564-a058-31bdea0196e6')
        model = DummyModel2(uuid=u)
        db.session.add(model)
        db.session.commit()
        model_id = model.id
        db.session.remove()
        model2 = DummyModel2.query.get(model_id)

        assert isinstance(model2.uuid, uuid.UUID)
        assert model2.uuid == u
