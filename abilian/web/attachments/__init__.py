# coding=utf-8
""""""
from __future__ import absolute_import, division, print_function

from .extension import AttachmentExtension, AttachmentsManager
from .forms import AttachmentForm  # noqa


def register_plugin(app):
    AttachmentExtension(app=app)
