# coding=utf-8
""""""
from .extension import FileUploadsExtension


def register_plugin(app):
    FileUploadsExtension(app)
