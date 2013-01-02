# -*- coding: utf-8 -*-
from sqlalchemy import func

class BaseCriterion(object):
  """
  """
  def __init__(self, name, label=u''):
    self.name = name
    self.label = label

  def filter(self, query, module, request, searched_text, *args, **kwargs):
    """
    """
    raise NotImplementedError

  @property
  def has_form_filter(self):
    return True

  @property
  def form_filter_type(self):
    raise NotImplementedError

  @property
  def form_filter_args(self):
    raise NotImplementedError

class NameCriterion(BaseCriterion):

  def filter(self, query, module, request, searched_text, *args, **kwargs):
    cls = module.managed_class
    attr = getattr(cls, "name", getattr(cls, "nom", None))

    if searched_text and attr is not None:
      # TODO: gérer les accents
      query = query.filter(func.lower(attr).like("%{}%".format(searched_text)))

    return query

  @property
  def has_form_filter(self):
    return False
