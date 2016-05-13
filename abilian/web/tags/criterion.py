# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, unicode_literals

import sqlalchemy as sa

from abilian.core.models.tag import Tag, entity_tag_tbl
from abilian.i18n import _

from ..search.criterion import BaseCriterion
from .extension import ENTITY_DEFAULT_NS_ATTR


class TagCriterion(BaseCriterion):
    """
    Filter entities with selected tag(s).
    """
    form_default_value = u''

    def __init__(self, *args, **kwargs):
        if len(args) == 0:
            kwargs.setdefault('name', 'tags')

        if len(args) < 2:
            kwargs.setdefault('label', _(u'Tags'))

        super(TagCriterion, self).__init__(*args, **kwargs)

    @BaseCriterion.model.setter
    def model(self, model):
        BaseCriterion.model.fset(self, model)
        self.ns = getattr(model, ENTITY_DEFAULT_NS_ATTR)

    @property
    def valid_tags(self):
        join_clause = entity_tag_tbl.join(
            self.model,
            self.model.id == entity_tag_tbl.c.entity_id,)
        model_tags = sa.sql.select(
            [entity_tag_tbl.c.tag_id],
            from_obj=join_clause)
        return Tag.query.filter(Tag.ns == self.ns,
                                Tag.id.in_(model_tags))\
                        .all()

    def get_request_values(self, request):
        tag_ids = []

        for val in request.values.getlist(self.name):
            try:
                tag_ids.append(int(val))
            except ValueError:
                pass

        valid_tags = set(self.valid_tags)
        tags = []
        for tid in tag_ids:
            t = Tag.query.get(tid)
            if t in valid_tags:
                tags.append(t)

        return tags

    def filter(self, query, module, request, searched_text, *args, **kwargs):

        tags = self.get_request_values(request)
        if not tags:
            return query

        cond = sa.sql.exists(sa.sql.select(
            [1],
            sa.sql.and_(entity_tag_tbl.c.entity_id == self.model.id,
                        entity_tag_tbl.c.tag_id.in_(t.id for t in tags)),))
        return query.filter(cond)

    @property
    def form_filter_type(self):
        return "select"

    @property
    def form_unset_value(self):
        return []

    @property
    def form_filter_args(self):
        # expected value: [list of selectable items, is multiple?]
        return [[(unicode(t.id), t.label) for t in self.valid_tags], True,]
