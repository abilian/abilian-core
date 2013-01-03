# -*- coding: utf-8 -*-
import logging
from sqlalchemy import func
from sqlalchemy.sql.expression import or_

logger = logging.getLogger(__name__)

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

class TextSearchCriterion(BaseCriterion):
  """ Fulltext search on given attributes
  """

  def __init__(self, name, label=u'', attributes=None):
    self.name = name
    self.label = label
    self.attributes = attributes if attributes is not None else (name,)

  def filter(self, query, module, request, searched_text, *args, **kwargs):
    if not searched_text:
      return query

    cls = module.managed_class
    clauses = []
    has_joins = False

    for attr_name in self.attributes:
      if '.' in attr_name:
        rel_attr_name, attr = attr_name.split('.', 1)
        rel_attr = getattr(cls, rel_attr_name, None)

        if rel_attr is not None:
          model = rel_attr.property.mapper.class_
          attr = getattr(model, attr, None)
          if attr is not None:
            query = query.join(rel_attr_name)
            has_joins = True
      else:
        attr = getattr(cls, attr_name, None)

      if attr is not None:
        # TODO: gérer les accents
        clauses.append(func.lower(attr).like("%{}%".format(searched_text)))
      else:
        logger.error("could not find \"{}\"".format(attr_name))

    if clauses:
      query = query.filter(or_(*clauses))

    if has_joins:
      query = query.reset_joinpoint()

    return query

  @property
  def has_form_filter(self):
    return False
