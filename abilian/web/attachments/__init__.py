# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from .forms import AttachmentForm  # noqa
from .extension import AttachmentExtension, AttachmentsManager


def register_plugin(app):
    AttachmentExtension(app=app)
