# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import sqlalchemy as sa
from flask import current_app, send_file
from werkzeug.exceptions import BadRequest
from werkzeug.utils import redirect

from abilian.core.entities import Entity
from abilian.core.models.attachment import Attachment, is_support_attachments
from abilian.i18n import _, _l
from abilian.web import nav, url_for
from abilian.web.action import ButtonAction, actions
from abilian.web.blueprints import Blueprint
from abilian.web.views import (BaseObjectView, ObjectCreate, ObjectDelete,
                               ObjectEdit)

from .forms import AttachmentForm

bp = Blueprint('attachments', __name__, url_prefix='/attachments')


def _default_attachment_view(obj, obj_type, obj_id, **kwargs):
    if not hasattr(obj, 'entity'):
        return url_for('attachments.entity', object_id=obj_id)
    entity = obj.entity
    return url_for(entity, _anchor='attachment-{}'.format(obj.id))


@bp.record_once
def register_default_view(state):
    state.app.default_view.register(Attachment, _default_attachment_view)


UPLOAD_BUTTON = ButtonAction(
    'form', 'edit', btn_class='primary',
    title=_l(u'Send'))


class BaseAttachmentView(object):
    """
    Mixin for attachment views
    """
    Model = Attachment
    Form = AttachmentForm

    #: owning entity
    entity = None

    def init_object(self, args, kwargs):
        args, kwargs = super(BaseAttachmentView, self).init_object(args, kwargs)
        entity_id = kwargs.pop('entity_id', None)

        if entity_id is not None:
            self.entity = Entity.query.get(entity_id)

        if self.entity is None:
            raise BadRequest('No entity provided')

        if not is_support_attachments(self.entity):
            raise BadRequest('This entity is doesn\'t support attachments')

        extension = current_app.extensions['attachments']
        self.Form = extension.manager(self.entity).Form
        actions.context['object'] = self.entity
        return args, kwargs

    def view_url(self):
        kw = {}
        if self.obj and self.obj.id:
            kw['_anchor'] = 'attachment-{}'.format(self.obj.id)
        return url_for(self.entity, **kw)

    def index_url(self):
        return self.view_url()

    @property
    def activity_target(self):
        return self.entity


class AttachmentDownload(BaseAttachmentView, BaseObjectView):

    def get(self):
        blob = self.obj.blob
        metadata = blob.meta
        filename = metadata.get('filename', self.obj.name)
        content_type = metadata.get('mimetype')
        stream = blob.file.open('rb')

        return send_file(stream,
                         as_attachment=True,
                         attachment_filename=filename,
                         mimetype=content_type,
                         cache_timeout=0,
                         add_etags=False,
                         conditional=False)


download_view = AttachmentDownload.as_view(b'download')
bp.route('/<int:entity_id>/<int:object_id>/download')(download_view)


class AttachmentEdit(BaseAttachmentView, ObjectEdit):
    _message_success = _l(u'Attachment edited')


edit_view = AttachmentEdit.as_view(b'edit')
bp.route('/<int:entity_id>/<int:object_id>/edit')(edit_view)


class AttachmentCreateView(BaseAttachmentView, ObjectCreate):

    _message_success = _l(u'Attachment added')

    def init_object(self, args, kwargs):
        args, kwargs = super(AttachmentCreateView, self).init_object(args,
                                                                     kwargs)

        self.obj.entity = self.entity
        session = sa.orm.object_session(self.entity)

        if session:
            sa.orm.session.make_transient(self.obj)

        return args, kwargs

    def breadcrumb(self):
        label = _(u'New attachment on "{title}"').format(title=self.entity.name)
        return nav.BreadcrumbItem(label=label)

    def get_form_buttons(self, *args, **kwargs):
        return [UPLOAD_BUTTON]


create_view = AttachmentCreateView.as_view(b'create')
bp.route('/<int:entity_id>/create')(create_view)


class AttachmentDelete(BaseAttachmentView, ObjectDelete):
    pass


delete_view = AttachmentDelete.as_view(b'delete')
bp.route('/<int:entity_id>/<int:object_id>/delete')(delete_view)


class AttachmentEntity(BaseObjectView):
    """Redirects to an attachment's entity view.
    """
    Model = Attachment

    def get(self):
        return redirect(url_for(self.obj))


entity_view = AttachmentEntity.as_view(b'entity')
bp.route('/<int:object_id>/entity')(entity_view)
