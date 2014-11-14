# coding=utf-8
"""
Vocabularies service.
"""
from __future__ import absolute_import

from inspect import isclass

from abilian.services.base import Service

from .models import BaseVocabulary


class VocabularyService(Service):
  """
  """
  name = 'vocabularies'

  @property
  def vocabularies(self):
    return {cls for cls in BaseVocabulary._decl_class_registry.values()
            if isclass(cls) and issubclass(cls, BaseVocabulary)}

  @property
  def grouped_vocabularies(self):
    by_group = {}
    for voc in sorted(self.vocabularies, key=lambda v: v.Meta.name):
      by_group.setdefault(voc.Meta.group, []).append(voc)
    return by_group


  def get_vocabulary(self, name, group=None):
    vocs = self.grouped_vocabularies
    for voc in vocs.get(group, ()):
      if voc.Meta.name == name:
        return voc

    return None


vocabularies = VocabularyService()
