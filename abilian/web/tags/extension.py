# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from typing import Any

import six

from abilian.core.entities import Entity
from abilian.core.models.tag import TAGS_ATTR, Tag, supports_tagging
from abilian.i18n import _l
from abilian.web import url_for
from abilian.web.forms import Form
from abilian.web.views.object import EDIT_BUTTON

from .forms import TagsField
from .views import bp as tags_bp
from .views import entity_bp

ENTITY_DEFAULT_NS_ATTR = '__tags_default_ns__'


def ns(ns):
    """Class decorator that sets default tags namespace to use with its
    instances."""

    def setup_ns(cls):
        setattr(cls, ENTITY_DEFAULT_NS_ATTR, ns)
        return cls

    return setup_ns


class _TagsForm(Form):
    """Form to workaround a wtforms limitation: fields cannot start with an
    underscore, so '__tags__' is not accepted.

    This form help process tags (and only tags).

    .. seealso:: :py:meth:`~TagsExtension.entity_tags_form`
    """

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        tags = None
        if obj is not None:
            tags = getattr(obj, TAGS_ATTR, set())

        super(_TagsForm, self).process(
            formdata=formdata, obj=None, data=data, tags=tags, **kwargs
        )


class TagsExtension(object):
    """API for tags, installed as an application extension.

    It is also available in templates as `tags`.
    """

    def __init__(self, app):
        app.extensions['tags'] = self
        app.add_template_global(self, 'tags')
        app.register_blueprint(tags_bp)
        app.register_blueprint(entity_bp)

    def supports_tagging(self, entity):
        return supports_tagging(entity)

    # Deprecated: remove in 2019
    is_support_tagging = supports_tagging

    def entity_tags(self, entity):
        return getattr(entity, TAGS_ATTR)

    def tags_from_hit(self, tag_ids):
        """
        :param tag_ids: indexed ids of tags in hit result.
            Do not pass hit instances.

        :returns: an iterable of :class:`Tag` instances.
        """
        ids = []
        for t in tag_ids.split():
            t = t.strip()
            try:
                t = int(t)
            except ValueError:
                pass
            else:
                ids.append(t)

        if not ids:
            return []

        return Tag.query.filter(Tag.id.in_(ids)).all()

    def entity_default_ns(self, entity):
        return getattr(entity, ENTITY_DEFAULT_NS_ATTR, 'default')

    def entity_tags_form(self, entity, ns=None):
        """Construct a form class with a field for tags in namespace `ns`."""
        if ns is None:
            ns = self.entity_default_ns(entity)

        field = TagsField(label=_l('Tags'), ns=ns)
        if six.PY2:
            cls = type(b'EntityNSTagsForm', (_TagsForm,), {b'tags': field})
        else:
            cls = type('EntityNSTagsForm', (_TagsForm,), {'tags': field})
        return cls

    def get(self, ns, label=None):
        """Return :class:`tags instances<~Tag>` for the namespace `ns`, ordered
        by label.

        If `label` is not None the only one instance may be returned, or
        `None` if no tags exists for this label.
        """
        query = Tag.query.filter(Tag.ns == ns)

        if label is not None:
            return query.filter(Tag.label == label).first()

        return query.all()

    def add(self, entity, tag=None, ns=None, label=None):
        # type: (Entity, Tag, Any, Any) -> Tag
        if tag is None:
            assert None not in (ns, label)
            tag = self.get(ns, label)
            if tag is None:
                tag = Tag(ns=ns, label=label)

        tags = self.entity_tags(entity)
        tags.add(tag)
        return tag

    def remove(self, entity, tag=None, ns=None, label=None):
        if tag is None:
            assert None not in (ns, label)
            tag = self.get(ns, label)

        tags = self.entity_tags(entity)
        try:
            tags.remove(tag)
        except KeyError:
            pass

    def get_form_context(self, obj, ns=None):
        """Return a dict: form instance, action button, submit url...

        Used by macro m_tags_form(entity)
        """
        return {
            'url': url_for('entity_tags.edit', object_id=obj.id),
            'form': self.entity_tags_form(obj)(obj=obj, ns=ns),
            'buttons': [EDIT_BUTTON],
        }
