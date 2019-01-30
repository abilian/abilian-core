# coding=utf-8
""""""
import redis


class Extension:
    """Redis extension for flask."""

    client = None

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions["redis"] = self
        uri = app.config.get("REDIS_URI")
        if uri:
            self.client = redis.from_url(uri)
        elif not app.testing:
            raise ValueError(
                "Redis extension: REDIS_URI is not defined in "
                "application configuration"
            )
