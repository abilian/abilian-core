# coding=utf-8
"""
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import sqlalchemy as sa
from flask import Blueprint, Flask
from flask_testing import TestCase as FlaskTestCase

from abilian.core.entities import Entity
# needed if running only this test, else SA won't have registered this mapping
# required by Entity.owner_id, etc
from abilian.core.models.subjects import User  # noqa
from abilian.web.views import Registry, default_view


class RegEntity(Entity):
    name = sa.Column(sa.Unicode, default='')


class NonEntity(object):
    pass


class TestRegistry(FlaskTestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config.update({
            'TESTING': True,
            'CSRF_ENABLED': False,
            'WTF_CSRF_ENABLED': False,
        })

        app.default_view = Registry()
        return app

    def test_register_class_or_instance(self):
        obj = RegEntity()
        registry = self.app.default_view

        registry.register(RegEntity, lambda ignored: '')
        assert RegEntity.entity_type in registry._map
        registry._map = {}
        registry.register(obj, lambda ignored: '')
        assert RegEntity.entity_type in registry._map

    def test_custom_url_func(self):
        name = u'obj'
        obj = RegEntity(id=1, name=name)
        registry = self.app.default_view

        def custom_url(obj, obj_type, obj_id):
            return obj.name

        registry.register(obj, custom_url)
        self.assertEqual(registry.url_for(obj), name)

        def url_from_type_and_id(obj, obj_type, obj_id):
            return u'{}:{}'.format(obj_type, obj_id)

        registry.register(obj, url_from_type_and_id)
        self.assertEqual(registry.url_for(obj), u'test_registry.RegEntity:1')

    def test_default_url_func(self):
        obj = RegEntity(id=1)

        @self.app.route(
            '/regentities_path/<int:object_id>/view', endpoint='regentity.view')
        def dummy_default_view(object_id):
            pass

        self.assertEqual(
            self.app.default_view.url_for(obj), '/regentities_path/1/view')

        self.assertEqual(
            self.app.default_view.url_for(
                obj, _external=True),
            'http://localhost/regentities_path/1/view')

    def test_default_view_decorator(self):
        bp = Blueprint('registry', __name__, url_prefix='/blueprint')

        @default_view(bp, RegEntity)
        @bp.route('/<int:object_id>')
        def view(object_id):
            pass

        obj = RegEntity(id=1)
        # blueprint not registered: no rule set
        self.assertRaises(KeyError, self.app.default_view.url_for, obj)

        # blueprint registered: default view is set
        self.app.register_blueprint(bp)
        self.assertEqual(self.app.default_view.url_for(obj), '/blueprint/1')
        self.assertEqual(
            self.app.default_view.url_for(
                obj, _external=True),
            'http://localhost/blueprint/1')
