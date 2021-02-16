""""""
from flask import Flask

from .extension import AttachmentExtension, AttachmentsManager
from .forms import AttachmentForm  # noqa


def register_plugin(app: Flask) -> None:
    AttachmentExtension(app)
