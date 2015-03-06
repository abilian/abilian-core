# coding=utf-8
"""
Class based views
"""
from __future__ import absolute_import

import logging

import sqlalchemy as sa
from flask import (
    g, request, render_template, redirect, url_for, current_app,
    flash,
)
from flask.ext.babel import gettext as _, lazy_gettext as _l
from werkzeug.exceptions import NotFound

from abilian.core.signals import activity
from abilian.core.entities import ValidationError

from .. import nav, csrf
from ..action import ButtonAction, Endpoint, actions
from .base import View

logger = logging.getLogger(__name__)


class BaseObjectView(View):
  """
  Base class common to all database objects views
  """
  #: form title
  title = None

  #: Model class
  Model = None

  #: primary key name to look for in url arguments
  pk = 'object_id'

  #: object instance for this view
  obj = None

  #: template to render
  template = None

  #: default templates inherit from "base_template". This allows to use generic
  #: templates with a custom base
  base_template = "base.html"

  def __init__(self, Model=None, pk=None, base_template=None, *args, **kwargs):
    View.__init__(self, *args, **kwargs)
    cls = self.__class__
    self.pk = pk if pk is not None else cls.pk
    self.Model = Model if Model is not None else cls.Model
    self.base_template = (base_template
                          if base_template is not None
                          else cls.base_template)

  def prepare_args(self, args, kwargs):
    args, kwargs = self.init_object(args, kwargs)

    if self.obj is None:
      raise NotFound()

    return args, kwargs

  def breadcrumb(self):
    """
    Return :class:`..nav.BreadcrumbItem` instance for this object.

    This method may return a list of BreadcrumbItem instances. Return
    `None` if nothing.
    """
    return None

  def init_object(self, args, kwargs):
    """
    This method is reponsible for setting :attr:`obj`. It is called during
    :meth:`prepare_args`.
    """
    object_id = kwargs.pop(self.pk, None)
    if object_id is not None:
      self.obj = self.Model.query.get(object_id)
      actions.context['object'] = self.obj

    return args, kwargs

  def get(self, *args, **kwargs):
    bc = self.breadcrumb()
    if bc is not None:
      bc = [bc] if isinstance(bc, nav.BreadcrumbItem) else list(bc)
      assert all(isinstance(b, nav.BreadcrumbItem) for b in bc)
      g.breadcrumb.extend(bc)

    kwargs = {'base_template': self.base_template}
    kwargs.update(self.template_kwargs)
    # forbid override "view" and "form"
    kwargs.update(dict(view=self, form=self.form))
    return render_template(self.template, **kwargs)

  @property
  def template_kwargs(self):
    """
    Template render arguments. You can override `base_template` for
    instance. Only `view` and `form` cannot be overriden.
    """
    return {}


class ObjectView(BaseObjectView):
  """
  View objects
  """

  #: FIXME: currently default template renders nothing, only Edit is implemented
  template = 'default/object_view.html'

  #: View form. Form object used to show objects fields
  Form = None

  #: form instance for this view
  form = None

  def __init__(self, Model=None, pk=None, Form=None, template=None, *args, **kwargs):
    BaseObjectView.__init__(self, Model, pk, *args, **kwargs)
    cls = self.__class__
    self.Form = Form if Form is not None else cls.Form
    self.template = template if template is not None else cls.template

  def prepare_args(self, args, kwargs):
    """
    :attr:`form` is initialized here. See also :meth:`View.prepare_args`.
    """
    args, kwargs = super(ObjectView, self).prepare_args(args, kwargs)
    self.form = self.Form(**self.get_form_kwargs())
    return args, kwargs

  def get_form_kwargs(self):
    return dict(obj=self.obj)

  def index_url(self):
    return url_for('.index')

  def redirect_to_index(self):
    return redirect(self.index_url())


CANCEL_BUTTON = ButtonAction(
  'form', 'cancel', title=_l(u'Cancel'),
    btn_class='default cancel' # .cancel: if jquery.validate is used it will
)                              # properly skip validation

EDIT_BUTTON = ButtonAction('form', 'edit', btn_class='primary',
                           title=_l(u'Save'))


class ObjectEdit(ObjectView):
  """
  Edit objects
  """
  template = 'default/object_edit.html'

  #: :class:ButtonAction instance to show on form
  _buttons = ()

  #: submitted form data
  data = None

  #: action name from form data
  action = None

  #: button clicked, corresponding to :attr:`action`.
  button = None

  #: verb used to describe activity
  activity_verb = 'update'

  #: UI flash message
  _message_success = _l(u"Entity successfully edited")

  def __init__(self, Model=None, pk=None, Form=None, template=None,
               view_endpoint=None, message_success=None, *args, **kwargs):
    ObjectView.__init__(self, Model, pk, Form, *args, **kwargs)
    self.view_endpoint = (view_endpoint
                          if view_endpoint is not None
                          else '.{}_view'.format(self.Model.__name__))
    if message_success:
      self._message_success = message_success

  @csrf.protect
  def post(self, *args, **kwargs):
    # conservative: no action submitted -> cancel
    action = self.data.get('__action', u'cancel')
    if action == u'cancel':
      return self.cancel()

    return self.handle_action(action)

  def put(self):
    return self.post()

  def prepare_args(self, args, kwargs):
    args, kwargs = super(ObjectEdit, self).prepare_args(args, kwargs)
    self._buttons = self.get_form_buttons(*args, **kwargs)
    self.data = request.form
    return args, kwargs

  def get_form_buttons(self, *args, **kwargs):
    return [EDIT_BUTTON, CANCEL_BUTTON]

  @property
  def buttons(self):
    return (button for button in self._buttons
            if button.available(actions.context))

  def view_url(self):
    kw = { self.pk: self.obj.id }
    return url_for(self.view_endpoint, **kw)

  def redirect_to_view(self):
    if self.button:
      url = self.button.url(actions.context)
      if url:
        return redirect(url)
    return redirect(self.view_url())

  def message_success(self):
    return unicode(self._message_success)

  # actions
  def handle_action(self, action):
    for button in self._buttons:
      if action == button.name:
        if not button.available(dict(view=self)):
          raise ValueError('Action "{}" not available'.format(action.encode('utf-8')))
        break
    else:
      raise ValueError('Unknown action: "{}"'.format(action.encode('utf-8')))

    self.action = action
    self.button = button
    return getattr(self, action)()

  def cancel(self):
    return self.redirect_to_view()

  def edit(self):
    if self.validate():
      return self.form_valid()
    else:
      resp = self.form_invalid()
      if resp:
        return resp

      flash(_(u"Please fix the error(s) below"), "error")

    # if we end here then something wrong has happened: show form with error
    # messages
    return self.get()

  def before_populate_obj(self):
    """
    This method is called after form has been validated and before calling
    `form.populate_obj()`. Sometimes one may want to remove a field from
    the form because it's non-sense to store it on edited object, and use it in
    a specific manner, for example::

        image = form.image
        del form.image
        store_image(image)
    """
    pass

  def after_populate_obj(self):
    """
    Called after `self.obj` values have been updated, and `self.obj`
    attached to an ORM session.
    """
    pass

  def handle_commit_exception(self, exc):
    """
    hook point to handle exception that may happen during commit.

    It is the responsability of this method to perform a rollback if it is
    required for handling `exc`. If the method does not handle `exc` if should
    do nothing and return None.

    :returns: * a valid :class:`Response` if exception is handled.
              * `None` if exception is not handled. Default handling happens.
    """
    return None

  def validate(self):
    return self.form.validate()

  def form_valid(self):
    """
    Save object.

    Called when form is validated.
    """
    session = current_app.db.session()
    self.before_populate_obj()
    self.form.populate_obj(self.obj)
    session.add(self.obj)
    self.after_populate_obj()

    try:
      session.flush()
      activity.send(self,
                    actor=g.user,
                    verb=self.activity_verb,
                    object=self.obj,
                    target=self.activity_target)
      session.commit()
    except ValidationError, e:
      rv = self.handle_commit_exception(e)
      if rv is not None:
        return rv
      session.rollback()
      flash(e.message, "error")
      return self.get()
    except sa.exc.IntegrityError, e:
      rv = self.handle_commit_exception(e)
      if rv is not None:
        return rv
      session.rollback()
      logger.error(e)
      flash(_(u"An entity with this name already exists in the database."),
            "error")
      return self.get()
    else:
      flash(self.message_success(), "success")
      return self.redirect_to_view()

  def form_invalid(self):
    """
    When a form doesn't validate this method is called.

    It may return a :class:`Flask.Response` instance, to handle specific
    errors in custom screens.

    Else the edit form screen is returned with error(s) highlighted.

    This method is useful for detecting edition conflict using hidden fields
    and show a specific screen to help resolve the conflict.
    """
    return None

  @property
  def activity_target(self):
    """
    Return `target` to use when creating activity.
    """
    return None


CREATE_BUTTON = ButtonAction('form', 'create', btn_class='primary', title=_l(u'Create'))
CHAIN_CREATE_BUTTON = ButtonAction(
    'form', 'chain_create', btn_class='primary',
    title=_l(u'Create and add new'),
    endpoint=lambda ctx: Endpoint(request.endpoint, **request.view_args),
    condition=lambda ctx: getattr(ctx['view'], 'chain_create_allowed', False)
)


class ObjectCreate(ObjectEdit):
  """
  Create a new object
  """
  activity_verb = 'post'
  _message_success = _l(u"Entity successfully added")

  #: set to `True` to show 'Save and add new' button
  chain_create_allowed = False

  def __init__(self, *args, **kwargs):
    chain_create_allowed = kwargs.pop('chain_create_allowed', None)
    if chain_create_allowed is not None:
      self.chain_create_allowed = bool(chain_create_allowed)

    ObjectEdit.__init__(self, *args, **kwargs)

  def init_object(self, args, kwargs):
    self.obj = self.Model()
    return args, kwargs

  def get_form_kwargs(self):
    kw = super(ObjectCreate, self).get_form_kwargs()
    if request.method == 'GET':
      # when GET allow form prefill instead of empty/current object data
      # FIXME: filter allowed parameters on given a field flags (could be
      # 'allow_from_get'?)
      kw['formdata'] = request.args

    return kw

  def get_form_buttons(self, *args, **kwargs):
    return [CREATE_BUTTON, CHAIN_CREATE_BUTTON, CANCEL_BUTTON]

  def breadcrumb(self):
    return nav.BreadcrumbItem(label=CREATE_BUTTON.title)

  # actions
  def create(self):
    return self.edit()

  chain_create = create

  def cancel(self):
    return self.redirect_to_index()


DELETE_BUTTON = ButtonAction('form', 'delete', title=_l(u'Delete'))


class ObjectDelete(ObjectEdit):
  """
  Delete object. Supports DELETE verb.
  """
  activity_verb = 'delete'
  _message_success = _l(u"Entity deleted")

  init_object = BaseObjectView.init_object

  def get_form_buttons(self, *args, **kwargs):
    return [DELETE_BUTTON, CANCEL_BUTTON]

  @csrf.protect
  def delete(self):
    session = current_app.db.session()
    session.delete(self.obj)
    activity.send(self, actor=g.user, verb="delete", object=self.obj)
    session.commit()
    flash(self.message_success(), 'success')
    # FIXME: for DELETE verb response in case of success should be 200, 202
    # (accepted) or 204 (no content)
    return self.redirect_to_index()
