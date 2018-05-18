# coding=utf-8
"""Configuration and injectable fixtures for Pytest.

Supposed to replace the too-complex current UnitTest-based testing
framework.

DI and functions over complex inheritance hierarchies FTW!
"""

from __future__ import absolute_import, division, print_function, \
    unicode_literals

import os
import warnings

import pytest

pytest_plugins = ["abilian.testing.fixtures"]

if os.environ.get("FAIL_ON_WARNINGS"):
    # Don't remove !
    import pandas

    warnings.simplefilter("error")

if os.environ.get("COLLECT_ANNOTATIONS"):
    import pyannotate_runtime

    def pytest_collection_finish(session):
        """Handle the pytest collection finish hook: configure pyannotate.
        Explicitly delay importing `collect_types` until all tests have
        been collected.  This gives gevent a chance to monkey patch the
        world before importing pyannotate.
        """
        from pyannotate_runtime import collect_types

        collect_types.init_types_collection()

    @pytest.fixture(autouse=True)
    def collect_types_fixture():
        from pyannotate_runtime import collect_types

        collect_types.resume()
        yield
        collect_types.pause()

    def pytest_sessionfinish(session, exitstatus):
        from pyannotate_runtime import collect_types

        collect_types.dump_stats("type_info.json")
