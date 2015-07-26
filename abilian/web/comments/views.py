# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

import sqlalchemy as sa
from werkzeug.exceptions import BadRequest

from abilian.i18n import _, _l
from abilian.core.entities import Entity
from abilian.core.models.comment import Comment, is_commentable
from abilian.web import url_for, nav
from abilian.web.blueprints import Blueprint
from abilian.web.action import actions, ButtonAction
from abilian.web.views import ObjectCreate
from .forms import CommentForm

bp = Blueprint('comments', __name__, url_prefix='/comments')

def _default_comment_view(obj, obj_type, obj_id, **kwargs):
  entity = obj.entity
  return url_for(entity, _anchor='comment-{}'.format(obj.id))


@bp.record_once
def register_default_view(state):
  state.app.default_view.register(Comment, _default_comment_view)

COMMENT_BUTTON = ButtonAction('form', 'edit', btn_class='primary',
                              title=_l(u'Send'))


class CommentCreateView(ObjectCreate):
  """
  """
  Model = Comment
  Form = CommentForm
  _message_success = _l(u"Comment added")

  #: commented entity
  entity = None

  def __init__(self, *args, **kwargs):
    super(CommentCreateView, self).__init__(*args, **kwargs)

  def init_object(self, args, kwargs):
    args, kwargs = super(CommentCreateView, self).init_object(args, kwargs)
    entity_id = kwargs.pop('entity_id', None)
    if entity_id is not None:
      self.entity = Entity.query.get(entity_id)

    if self.entity is None:
      raise BadRequest('No entity to comment')

    if not is_commentable(self.entity):
      raise BadRequest('This entity is not commentable')

    self.obj.entity = self.entity
    session = sa.orm.object_session(self.entity)

    if session:
      sa.orm.session.make_transient(self.obj)

    actions.context['object'] = self.entity
    return args, kwargs

  def breadcrumb(self):
    label = _(u'New comment on "{title}"').format(title=self.entity.name)
    return nav.BreadcrumbItem(label=label)

  def get_form_buttons(self, *args, **kwargs):
    return [COMMENT_BUTTON]

  def view_url(self):
    kw = {}
    if self.obj and self.obj.id:
      kw['_anchor'] = 'comment-{}'.format(self.obj.id)
    return url_for(self.entity, **kw)

  def index_url(self):
    return self.view_url()

  @property
  def activity_target(self):
    return self.entity


create_view = CommentCreateView.as_view('create')
bp.route('/<int:entity_id>/create')(create_view)
