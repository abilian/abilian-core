# coding=utf-8
""""""
from .extension import AttachmentExtension, AttachmentsManager
from .forms import AttachmentForm  # noqa


def register_plugin(app):
    AttachmentExtension(app=app)
