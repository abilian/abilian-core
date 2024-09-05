""""""

from __future__ import annotations

from abilian.app import Application

from .extension import FileUploadsExtension


def register_plugin(app: Application):
    FileUploadsExtension(app)
