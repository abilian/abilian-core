# coding=utf-8
""""""
from .extension import FileUploadsExtension
from abilian.app import Application


def register_plugin(app: Application) -> None:
    FileUploadsExtension(app)
