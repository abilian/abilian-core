from sqlalchemy import Column

from abilian.core.extensions import db
from abilian.core.entities import Entity
from abilian.core.sqlalchemy import JSONList, JSONDict
from abilian.testing import BaseTestCase


class DummyModel2(Entity):
  list_attr = Column(JSONList())
  dict_attr = Column(JSONDict())


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
