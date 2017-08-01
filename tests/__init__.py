# coding=utf-8
import subprocess
assert 'twill' not in subprocess.__file__

# TODO: enable (currently this breaks the tests)
# from sqlalchemy.exc import SAWarning
# import warnings
# warnings.simplefilter('error', SAWarning)
