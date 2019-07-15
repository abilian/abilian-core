""""""
from abilian.app import Application

from .extension import FileUploadsExtension


def register_plugin(app: Application) -> None:
    FileUploadsExtension(app)
