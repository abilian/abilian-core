"""Configuration and injectable fixtures for Pytest.

Supposed to replace the too-complex current UnitTest-based testing
framework.

DI and functions over complex inheritance hierarchies FTW!
"""
import os
import warnings

pytest_plugins = ["abilian.testing.fixtures"]

if os.environ.get("FAIL_ON_WARNINGS"):
    # Don't remove !
    # noinspection PyUnresolvedReferences
    import pandas

    warnings.simplefilter("error")
