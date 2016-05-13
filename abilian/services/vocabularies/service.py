# coding=utf-8
"""
Vocabularies service.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from inspect import isclass

import jinja2

from abilian.services.base import Service

from .models import BaseVocabulary


def _vocabularies():
    return {cls
            for cls in BaseVocabulary._decl_class_registry.values()
            if isclass(cls) and issubclass(cls, BaseVocabulary)}


def _grouped_vocabularies():
    by_group = {}
    for voc in sorted(_vocabularies(), key=lambda v: v.Meta.name):
        by_group.setdefault(voc.Meta.group, []).append(voc)
    return by_group


def get_vocabulary(name, group=None):
    name = name.lower()
    vocs = _grouped_vocabularies()
    for voc in vocs.get(group, ()):
        if voc.Meta.name == name:
            return voc

    return None


class VocabularyService(Service):
    name = 'vocabularies'

    def init_app(self, app):
        Service.init_app(self, app)
        app.register_jinja_loaders(jinja2.PackageLoader(__name__, 'templates'))

    @property
    def vocabularies(self):
        return _vocabularies()

    @property
    def grouped_vocabularies(self):
        return _grouped_vocabularies()

    def get_vocabulary(self, name, group=None):
        return get_vocabulary(name, group=group)


vocabularies = VocabularyService()
