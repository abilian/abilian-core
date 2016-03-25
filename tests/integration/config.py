# -*- coding: utf-8 -*-

from abilian.testing import TestConfig as BaseConfig


class TestConfig(BaseConfig):

    CELERY_ALWAYS_EAGER = True  # run tasks locally, no async
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

    SALT = "retwis"
    WHOOSH_BASE = "whoosh"
