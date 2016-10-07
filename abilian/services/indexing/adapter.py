# coding=utf-8
"""
Objects to schema adapters
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging
from abc import ABCMeta, abstractmethod
from operator import attrgetter

import sqlalchemy as sa
from flask import current_app
from six import string_types
from whoosh.fields import TEXT

from abilian.core.extensions import db

from .schema import accent_folder

__all__ = ['SchemaAdapter', 'SAAdapter']

logger = logging.getLogger(__name__)


class SchemaAdapter(object):
    """
    Abstract base class for objects to schema adapter. The purpose of adapters is
    that given an object they return kwargs for document.
    """
    __metaclass__ = ABCMeta

    def __init__(self, Model, schema):
        """
        :param:Model: class of objects instances to be adapted
        :param:schema: :class:`whoosh.fields.Schema` instance
        """
        pass

    @staticmethod
    def can_adapt(obj_cls):
        """Return True if this class can adapt objects of class `obj_cls`.
        """
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, pk, **data):
        """Returns an object instance given its identifier and optional data
        kwargs.

        :returns:None if not object instance can be returned
        """
        raise NotImplementedError

    @abstractmethod
    def get_document(self, obj):
        raise NotImplementedError


class SAAdapter(SchemaAdapter):
    """Adapts an sqlalchemy model.

    A column on the model is indexed if `"searchable"` is set to `True` in
    its `info` field (see :meth:`sqlalchemy.schema.Column.__init__`)

    Additionnaly info can also contains `index_to`. It's expected to be an
    iterable of field names or tuple of (field name, whoosh field
    instance). The default the whoosh field is a
    :class:`whoosh.fields.TEXT` instance.

    When `index_to` is used the column name will *not* be indexed on the same
    field name unless specified in `index_to`.

    If multiple field names are passed to `index_to` the values will be
    concatenated with a space.

    `index_to` is useful for::

    * index many attributes to on field names, for exemple index `title`
    and `description` to a `_full_text` field
    * define new fields on schema
    """

    @staticmethod
    def can_adapt(obj_cls):
        return issubclass(obj_cls, db.Model)

    def __init__(self, Model, schema):
        """
        :param:Model: a sqlalchemy model class
        :param:schema: :class:`whoosh.fields.Schema` instance
        """
        assert issubclass(Model, db.Model)
        self.Model = Model
        self.indexable = getattr(Model, '__indexable__', False)
        self.index_args = getattr(Model, '__indexation_args__', {})
        self.doc_attrs = {}
        if self.indexable:
            self._build_doc_attrs(Model, schema)

    def _build_doc_attrs(self, Model, schema):
        mapper = sa.inspect(Model)

        args = self.doc_attrs
        # any field not in schema will be stored here. After all field have been
        # discovered we add missing ones
        field_definitions = dict()

        def setup_field(attr_name, field_name):
            field_def = False
            if not isinstance(field_name, string_types):
                field_name, field_def = field_name

            if field_name not in schema:
                if (field_name not in field_definitions or
                        field_definitions[field_name] is False):
                    field_definitions[field_name] = field_def

            # attrgetter offers dotted name support. Useful for attributes on related
            # objects.
            args.setdefault(field_name, {})[name] = attrgetter(name)

        # model level definitions
        for name, field_names in self.index_args.get('index_to', ()):
            if isinstance(field_names, string_types):
                field_names = (field_names,)
            for field_name in field_names:
                setup_field(name, field_name)

        # per column definitions
        for col in mapper.columns:
            name = col.name
            info = col.info

            if not info.get('searchable'):
                continue

            index_to = info.get('index_to', (name,))
            if isinstance(index_to, string_types):
                index_to = (index_to,)

            for field_name in index_to:
                setup_field(name, field_name)

        # add missing fields to schema
        for field_name, field_def in field_definitions.items():
            if field_name in schema:
                continue

            if field_def is False:
                field_def = TEXT(stored=True, analyzer=accent_folder)

            logger.debug('Adding field to schema:\n'
                         '  Model: %s\n'
                         '  Field: "%s" %s',
                         Model._object_type(), field_name, field_def)
            schema.add(field_name, field_def)

    def retrieve(self, pk, _session=None, **data):
        if _session is None:
            _session = current_app.db.session()
        return _session.query(self.Model).get(pk)

    def get_document(self, obj):
        kwargs = {}
        if not self.indexable:
            return kwargs

        # cache because the same attribute may be needed by many fields, i.e
        # "title" on "title" field and "full_text" field for example
        cached = {}
        missed = set(
        )  # negative cache. Might be used especially with dotted names

        for field, attrs in self.doc_attrs.items():
            values = []

            for a, getter in attrs.items():
                if a in missed:
                    continue

                if a not in cached:
                    try:
                        val = getter(obj)
                    except AttributeError:
                        missed.add(a)
                        continue
                    else:
                        cached[a] = val

                val = cached[a]
                if val is not None:
                    if isinstance(val, (list, tuple)):
                        val = u' '.join(val).strip()
                    values.append(val)

            values = [v for v in values if v]

            if values:
                if len(values) == 1:
                    kwargs[field] = values[0]
                else:
                    kwargs[field] = u' '.join(values)

        return kwargs
