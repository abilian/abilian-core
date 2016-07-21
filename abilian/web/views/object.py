# coding=utf-8
"""
Class based views
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging

import sqlalchemy as sa
from flask import current_app, flash, g, redirect, render_template, request, \
    url_for
from six import text_type
from werkzeug.exceptions import BadRequest, NotFound

from abilian.core.entities import ValidationError
from abilian.core.signals import activity
from abilian.i18n import _, _l
from abilian.services.security import CREATE, DELETE, READ, WRITE

from .. import csrf, forms, nav
from ..action import ButtonAction, Endpoint, actions
from .base import JSONView, View

logger = logging.getLogger(__name__)


class BaseObjectView(View):
    """
    Base class common to all database objects views.
    """
    #: form title
    title = None

    #: Model class
    Model = None

    #: primary key name to look for in url arguments
    pk = 'object_id'

    #: object instance for this view
    obj = None

    #: object id
    object_id = None

    #: template to render
    template = None

    #: default templates inherit from "base_template". This allows to use generic
    #: templates with a custom base
    base_template = "base.html"

    def __init__(self, Model=None, pk=None, base_template=None, *args,
                 **kwargs):
        View.__init__(self, *args, **kwargs)
        cls = self.__class__
        self.pk = pk if pk is not None else cls.pk
        self.Model = Model if Model is not None else cls.Model
        self.base_template = (base_template if base_template is not None else
                              cls.base_template)

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
        self.object_id = kwargs.pop(self.pk, None)
        if self.object_id is not None:
            self.obj = self.Model.query.get(self.object_id)
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
        # forbid override "view"
        kwargs['view'] = self
        return render_template(self.template, **kwargs)

    @property
    def template_kwargs(self):
        """
        Template render arguments. You can override `base_template` for
        instance. Only `view` cannot be overriden.
        """
        return {}


class ObjectView(BaseObjectView):
    """View objects.
    """

    #: html template
    template = 'default/object_view.html'

    #: View form class. Form object used to show objects fields
    Form = None

    #: required permission. Must be an instance of
    #: :class:`abilian.services.security.Permission`
    permission = READ

    #: form instance for this view
    form = None

    def __init__(self,
                 Model=None,
                 pk=None,
                 Form=None,
                 template=None,
                 *args,
                 **kwargs):
        super(ObjectView, self).__init__(Model, pk, *args, **kwargs)
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
        kw = dict(obj=self.obj)
        if issubclass(self.Form, forms.Form) and self.permission:
            kw['permission'] = self.permission
        return kw

    def index_url(self):
        return url_for('.index')

    def redirect_to_index(self):
        return redirect(self.index_url())

    @property
    def template_kwargs(self):
        """Provides :attr:`form` to templates
        """
        kw = super(ObjectView, self).template_kwargs
        kw['form'] = self.form
        return kw


CANCEL_BUTTON = ButtonAction(
    'form',
    'cancel',
    title=_l(u'Cancel'),
    btn_class='default cancel'  # .cancel: if jquery.validate is used it will
)  # properly skip validation

EDIT_BUTTON = ButtonAction(
    'form', 'edit', btn_class='primary', title=_l(u'Save'))


class ObjectEdit(ObjectView):
    """Edit objects.
    """
    template = 'default/object_edit.html'
    decorators = (csrf.support_graceful_failure,)
    permission = WRITE

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

    view_endpoint = None

    def __init__(self,
                 Model=None,
                 pk=None,
                 Form=None,
                 template=None,
                 view_endpoint=None,
                 message_success=None,
                 *args,
                 **kwargs):
        ObjectView.__init__(
            self, Model, pk, Form, template=template, *args, **kwargs)
        if view_endpoint is not None:
            self.view_endpoint = view_endpoint

        if not self.view_endpoint:
            self.view_endpoint = '.{}_view'.format(self.Model.__name__)

        if message_success:
            self._message_success = message_success

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
        kw = {self.pk: self.obj.id}
        return url_for(self.view_endpoint, **kw)

    def redirect_to_view(self):
        if self.button:
            url = self.button.url(actions.context)
            if url:
                return redirect(url)
        return redirect(self.view_url())

    def message_success(self):
        return text_type(self._message_success)

    # actions
    def handle_action(self, action):
        for button in self._buttons:
            if action == button.name:
                if not button.available(dict(view=self)):
                    raise ValueError('Action "{}" not available'
                                     ''.format(action.encode('utf-8')))
                break
        else:
            raise ValueError('Unknown action: "{}"'.format(
                action.encode('utf-8')))

        self.action = action
        self.button = button
        return getattr(self, action)()

    def cancel(self):
        return self.redirect_to_view()

    def edit(self):
        if self.validate():
            return self.form_valid()
        else:
            if request.csrf_failed:
                errors = self.form.errors
                csrf_failed = errors.pop('csrf_token', False)
                if csrf_failed and not errors:
                    # failed only because of invalid/expired csrf, no error on form
                    return self.form_csrf_invalid()

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

    def commit_success(self):
        """
        Called after object has been successfully saved to database
        """

    def validate(self):
        return self.form.validate()

    def form_valid(self):
        """Save object.

        Called when form is validated.
        """
        session = current_app.db.session()

        with session.no_autoflush:
            self.before_populate_obj()
            self.form.populate_obj(self.obj)
            session.add(self.obj)
            self.after_populate_obj()

        try:
            session.flush()
            self.send_activity()
            session.commit()
        except ValidationError as e:
            rv = self.handle_commit_exception(e)
            if rv is not None:
                return rv
            session.rollback()
            flash(e.message, "error")
            return self.get()
        except sa.exc.IntegrityError as e:
            rv = self.handle_commit_exception(e)
            if rv is not None:
                return rv
            session.rollback()
            logger.error(e)
            flash(_(u"An entity with this name already exists in the system."),
                  "error")
            return self.get()
        else:
            self.commit_success()
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

    def form_csrf_invalid(self):
        """
        Called when a form doesn't validate *only* because of csrf token expiration.

        This works only if form is an instance of :class:`flask_wtf.form.SecureForm`.
        Else default CSRF protection (before request) will take place.

        It must return a valid :class:`Flask.Response` instance. By default it
        returns to edit form screen with an informative message.
        """
        current_app.extensions['csrf-handler'].flash_csrf_failed_message()
        return self.get()

    def send_activity(self):
        activity.send(
            self,
            actor=g.user,
            verb=self.activity_verb,
            object=self.obj,
            target=self.activity_target)

    @property
    def activity_target(self):
        """
        Return `target` to use when creating activity.
        """
        return None


CREATE_BUTTON = ButtonAction(
    'form', 'create', btn_class='primary', title=_l(u'Create'))
CHAIN_CREATE_BUTTON = ButtonAction(
    'form',
    'chain_create',
    btn_class='primary',
    title=_l(u'Create and add new'),
    endpoint=lambda ctx: Endpoint(request.endpoint, **request.view_args),
    condition=lambda ctx: getattr(ctx['view'], 'chain_create_allowed', False))


class ObjectCreate(ObjectEdit):
    """Create a new object.
    """
    permission = CREATE
    activity_verb = 'post'
    _message_success = _l(u"Entity successfully added")

    #: set to `True` to show 'Save and add new' button
    chain_create_allowed = False

    def __init__(self, *args, **kwargs):
        chain_create_allowed = kwargs.pop('chain_create_allowed', None)
        if chain_create_allowed is not None:
            self.chain_create_allowed = bool(chain_create_allowed)

        ObjectEdit.__init__(self, *args, **kwargs)

    def prepare_args(self, args, kwargs):
        # we must ensure that no flush() occurs and that obj is not registered in
        # session (to prevent accidental insert of an incomplete object)
        session = current_app.db.session()
        with session.no_autoflush:
            args, kwargs = super(ObjectCreate, self).prepare_args(args, kwargs)

        try:
            session.expunge(self.obj)
        except sa.exc.InvalidRequestError:
            # obj is not in session
            pass

        return args, kwargs

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
    """Delete object. Supports DELETE verb.
    """
    methods = ['POST']
    permission = DELETE
    activity_verb = 'delete'
    _message_success = _l(u"Entity deleted")

    init_object = BaseObjectView.init_object

    def get_form_buttons(self, *args, **kwargs):
        return [DELETE_BUTTON, CANCEL_BUTTON]

    def delete(self):
        session = current_app.db.session()
        session.delete(self.obj)
        activity.send(
            self,
            actor=g.user,
            verb="delete",
            object=self.obj,
            target=self.activity_target)
        try:
            session.commit()
        except sa.exc.IntegrityError as e:
            rv = self.handle_commit_exception(e)
            if rv is not None:
                return rv
            session.rollback()
            logger.error(e)
            flash(_("This entity is referenced by another object and cannot be deleted."),
                  "error")
            return self.redirect_to_view()
        else:
            flash(self.message_success(), 'success')
            # FIXME: for DELETE verb response in case of success should be 200, 202
            # (accepted) or 204 (no content)
            return self.redirect_to_index()


class JSONBaseSearch(JSONView):
    Model = None
    minimum_input_length = 2

    def __init__(self, *args, **kwargs):
        Model = kwargs.pop('Model', self.Model)
        minimum_input_length = kwargs.pop('minimum_input_length',
                                          self.minimum_input_length)
        super(JSONBaseSearch, self).__init__(*args, **kwargs)
        self.Model = Model
        self.minimum_input_length = minimum_input_length

    def prepare_args(self, args, kwargs):
        args, kwargs = JSONView.prepare_args(self, args, kwargs)
        kwargs['q'] = kwargs.get("q", u'').replace(u"%", u" ").lower()
        return args, kwargs

    def data(self, q, *args, **kwargs):
        if self.minimum_input_length and len(q) < self.minimum_input_length:
            raise BadRequest('Minimum query length is {:d}'.format(
                self.minimum_input_length),)

        results = []
        for obj in self.get_results(q, **kwargs):
            results.append(self.get_item(obj))

        return dict(results=results)

    def get_results(self, q, *args, **kwargs):
        raise NotImplementedError

    def get_item(self, obj):
        """
        Return a result item

        :param obj: Instance object
        :returns: a dictionnary with at least `id` and `text` values
        """
        raise NotImplementedError


class JSONModelSearch(JSONBaseSearch):
    """
    Base class for json sqlalchemy model search, as used by select2 widgets for
    example
    """

    def get_results(self, q, *args, **kwargs):
        query = self.Model.query

        query = self.options(query)
        query = self.filter(query, q, **kwargs)
        query = self.order_by(query)
        if not q and not self.minimum_input_length:
            query = query.limit(50)
        return query.all()

    def options(self, query):
        return query.options(sa.orm.noload('*'))

    def filter(self, query, q, **kwargs):
        if not q:
            return query
        return query.filter(sa.func.lower(self.Model.name).like(q + "%"))

    def order_by(self, query):
        return query.order_by(self.Model.name)

    def get_label(self, obj):
        return obj.name

    def get_item(self, obj):
        """
        Return a result item.

        :param obj: Instance object
        :returns: a dictionnary with at least `id` and `text` values
        """
        return dict(id=obj.id, text=self.get_label(obj), name=obj.name)


class JSONWhooshSearch(JSONBaseSearch):
    """
    Base class for JSON Whoosh search, as used by select2 widgets for example
    """

    def get_results(self, q, *args, **kwargs):
        svc = current_app.services['indexing']
        search_kwargs = {'limit': 30, 'Models': (self.Model,)}
        results = svc.search(q, **search_kwargs)
        return results

    def get_item(self, hit):
        """Return a result item.

        :param hit: Hit object from Whoosh
        :returns: a dictionnary with at least `id` and `text` values
        """
        return dict(id=hit['id'], text=hit['name'], name=hit['name'])
