# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app
from werkzeug.exceptions import BadRequest

from abilian.core.entities import Entity
from abilian.core.models.tag import Tag
from abilian.i18n import _l
from abilian.web import url_for
from abilian.web.blueprints import Blueprint
from abilian.web.views import (BaseObjectView, JSONView, ObjectCreate,
                               ObjectDelete, ObjectEdit)

from .forms import TagForm

bp = Blueprint('tags',
               __name__,
               url_prefix='/tags',
               template_folder='templates')


class BaseTagView(object):
    """
    Mixin for tag views
    """
    Model = Tag
    Form = TagForm

    def __init__(self, *args, **kwargs):
        super(BaseTagView, self).__init__(*args, **kwargs)
        self.extension = current_app.extensions['tags']

    def view_url(self):
        return url_for()


class TagEdit(BaseTagView, ObjectEdit):
    _message_success = _l(u'Tag edited')


edit_view = TagEdit.as_view(b'edit')
bp.route('/manage/<int:object_id>/edit')(edit_view)


class TagCreate(BaseTagView, ObjectCreate):
    _message_success = _l(u'Tag created')


create_view = TagCreate.as_view(b'create')
bp.route('/manage/new')(create_view)


class TagDelete(BaseTagView, ObjectDelete):
    _message_success = _l(u'Tag deleted')


delete_view = TagDelete.as_view(b'delete')
bp.route('/manage/<int:object_id>/delete')(delete_view)

# Tags on entities
entity_bp = Blueprint('entity_tags', __name__, url_prefix='/tags/entity')


class BaseEntityTagView(BaseTagView):

    def init_object(self, args, kwargs):
        args, kwargs = super(BaseEntityTagView, self).init_object(args, kwargs)
        entity_id = kwargs.pop('entity_id', None)

        if entity_id is not None:
            self.entity = Entity.query.get(entity_id)

        if self.entity is None:
            raise BadRequest('No entity provided')

        return args, kwargs

    def view_url(self):
        return url_for(self.entity)

    def index_url(self):
        return self.view_url()


class EntityTagList(BaseEntityTagView, BaseObjectView, JSONView):

    def get(self, *args, **kwargs):
        return JSONView.get(self, *args, **kwargs)

    def data(self, *args, **kwargs):
        tags = sorted(self.extension.entity_tags(self.entity))
        return dict(result=tags)


entity_bp.route('/<int:object_id>/list')(EntityTagList.as_view(b'list'))


class EntityTagManage(BaseEntityTagView, ObjectEdit):
    methods = ['POST']

    # operation: add or remove
    mode = None

    def __init__(self, mode, *args, **kwargs):
        super(EntityTagManage, *args, **kwargs)
        assert mode in ('add', 'remove')
        self.mode = mode

    def form_valid(self):
        ns = self.form.ns.data
        label = self.form.label.data
        op = getattr(self.extension, self.mode)
        op(self.entity, ns=ns, label=label)


entity_bp.route('/<int:object_id>/add')(EntityTagManage.as_view(b'add',
                                                                mode='add'))
entity_bp.route('/<int:object_id>/remove')(EntityTagManage.as_view(
    b'remove', mode='remove'))


class EntityTagEdit(ObjectEdit):
    Model = Entity

    def init_object(self, args, kwargs):
        args, kwargs = super(EntityTagEdit, self).init_object(args, kwargs)
        extension = current_app.extensions['tags']
        self.Form = extension.entity_tags_form(self.obj)
        return args, kwargs

    def view_url(self):
        return url_for(self.obj)

    def index_url(self):
        return self.view_url()


entity_bp.route('/<int:object_id>/edit')(EntityTagEdit.as_view(b'edit'))
