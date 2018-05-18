# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import current_app
from flask_login import current_user

from abilian.core.models import attachment as attachments
from abilian.services.security import READ, WRITE, security
from abilian.web import url_for

from .forms import AttachmentForm
from .views import UPLOAD_BUTTON
from .views import bp as blueprint

_MANAGER_ATTR = "__attachments_manager__"


class AttachmentExtension(object):
    """API for comments, installed as an application extension.

    It is also available in templates as `attachments`.
    """

    def __init__(self, app):
        app.extensions["attachments"] = self
        app.add_template_global(self, "attachments")
        app.register_blueprint(blueprint)

    def manager(self, obj):
        """Returns the :class:`AttachmentsManager` instance for this object."""
        manager = getattr(obj, _MANAGER_ATTR, None)
        if manager is None:
            manager = AttachmentsManager()
            setattr(obj.__class__, _MANAGER_ATTR, manager)

        return manager

    def supports_attachments(self, obj):
        return self.manager(obj).supports_attachments(obj)

    def for_entity(self, obj, check_support_attachments=False):
        return self.manager(obj).for_entity(
            obj, check_support_attachments=check_support_attachments
        )

    def has_attachments(self, obj):
        return self.manager(obj).has_attachments(obj)

    def count(self, obj):
        return self.manager(obj).count(obj)

    def get_form_context(self, obj):
        """Return a dict: form instance, action button, submit url...

        Used by macro m_attachment_form(entity)
        """
        return self.manager(obj).get_form_context(obj)


_DEFAULT_TEMPLATE = "macros/attachment_default.html"


class AttachmentsManager(object):
    """Allow customization of attachments form, display macros, etc.

    can be used as class decorator
    """
    Form = AttachmentForm
    macros_template = "macros/attachment.html"

    def __init__(
        self, Form=AttachmentForm, macros_template="macros/attachment_default.html"
    ):
        self.Form = Form
        self.macros_template = macros_template

    def __call__(self, Model):
        setattr(Model, _MANAGER_ATTR, self)
        return Model

    @property
    def macros(self):
        default_template = current_app.jinja_env.get_template(_DEFAULT_TEMPLATE)
        template = current_app.jinja_env.get_template(self.macros_template)
        default = default_template.module
        m = template.module
        return dict(
            m_attachments=getattr(m, "m_attachments", default.m_attachments),
            m_attachment=getattr(m, "m_attachment", default.m_attachment),
            m_attachment_form=getattr(
                m, "m_attachment_form", default.m_attachment_form
            ),
        )

    def supports_attachments(self, obj):
        return attachments.supports_attachments(obj)

    def for_entity(self, obj, check_support_attachments=False):
        return attachments.for_entity(
            obj, check_support_attachments=check_support_attachments
        )

    def has_attachments(self, obj):
        return bool(self.for_entity(obj, check_support_attachments=True))

    def count(self, obj):
        return len(self.for_entity(obj, check_support_attachments=True))

    def get_form_context(self, obj):
        """Return a dict: form instance, action button, submit url...

        Used by macro m_attachment_form(entity)
        """
        return {
            "url": url_for("attachments.create", entity_id=obj.id),
            "form": self.Form(),
            "buttons": [UPLOAD_BUTTON],
        }

    #
    # current user capabilities
    #
    def can_view(self, entity):
        """True if user can view attachments on entity."""
        return security.has_permission(current_user, READ, obj=entity)

    def can_edit(self, entity):
        """True if user can edit attachments on entity."""
        return security.has_permission(current_user, WRITE, obj=entity)

    def can_create(self, entity):
        """True if user can add attachments."""
        return security.has_permission(current_user, WRITE, obj=entity)

    def can_delete(self, entity):
        """True if user can delete attachments."""
        return security.has_permission(current_user, WRITE, obj=entity)
