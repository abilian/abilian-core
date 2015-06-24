# coding=utf-8
"""
"""
from __future__ import absolute_import

import sqlalchemy as sa
from werkzeug.exceptions import BadRequest

from abilian.i18n import _, _l
from abilian.core.entities import Entity
from abilian.core.models.attachment import Attachment, is_support_attachements
from abilian.web import url_for, nav
from abilian.web.blueprints import Blueprint
from abilian.web.action import actions, ButtonAction
from abilian.web.views import ObjectCreate
from .forms import AttachmentForm

bp = Blueprint('attachments', __name__, url_prefix='/attachments')

def _default_attachment_view(obj, obj_type, obj_id, **kwargs):
  entity = obj.entity
  return url_for(entity, _anchor='attachment-{}'.format(obj.id))


@bp.record_once
def register_default_view(state):
  state.app.default_view.register(Attachment, _default_attachment_view)

UPLOAD_BUTTON = ButtonAction('form', 'edit', btn_class='primary',
                              title=_l(u'Send'))


class AttachmentCreateView(ObjectCreate):
  """
  """
  Model = Attachment
  Form = AttachmentForm
  _message_success = _l(u"Attachment added")

  #: attachmented entity
  entity = None

  def __init__(self, *args, **kwargs):
    super(AttachmentCreateView, self).__init__(*args, **kwargs)

  def init_object(self, args, kwargs):
    args, kwargs = super(AttachmentCreateView, self).init_object(args, kwargs)
    entity_id = kwargs.pop('entity_id', None)
    if entity_id is not None:
      self.entity = Entity.query.get(entity_id)

    if self.entity is None:
      raise BadRequest('No entity to attachment')

      if not is_support_attachements(self.entity):
        raise BadRequest('This entity is not commentable')

    self.obj.entity = self.entity
    session = sa.orm.object_session(self.entity)

    if session:
      sa.orm.session.make_transient(self.obj)

    actions.context['object'] = self.entity
    return args, kwargs

  def breadcrumb(self):
    label = _(u'New attachment on "{title}"').format(title=self.entity.name)
    return nav.BreadcrumbItem(label=label)

  def get_form_buttons(self, *args, **kwargs):
    return [COMMENT_BUTTON]

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


create_view = AttachmentCreateView.as_view('create')
bp.route('/<int:entity_id>/create')(create_view)
