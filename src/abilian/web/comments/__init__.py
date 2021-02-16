""""""
from flask import Flask

from .extension import CommentExtension


def register_plugin(app: Flask) -> None:
    CommentExtension(app)
