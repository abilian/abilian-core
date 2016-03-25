# coding=utf-8
import subprocess
assert not 'twill' in subprocess.__file__

from sqlalchemy.exc import SAWarning
import warnings

#warnings.simplefilter('error', SAWarning)
