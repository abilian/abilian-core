""""""

from __future__ import annotations

from flask import Flask

from .extension import CommentExtension


def register_plugin(app: Flask):
    CommentExtension(app)
