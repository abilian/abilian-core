# coding=utf-8
""""""
from .extension import CommentExtension


def register_plugin(app):
    CommentExtension(app=app)
