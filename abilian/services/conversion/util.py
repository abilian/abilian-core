# coding=utf-8

from __future__ import absolute_import, division, print_function, \
    unicode_literals

import logging
import os
import subprocess
from contextlib import contextmanager
from tempfile import mkstemp

try:
    from six.moves.xmlrpc_client import ServerProxy
except ImportError:
    ServerProxy = None

logger = logging.getLogger(__name__)

# For some reason, twill includes a broken version of subprocess.
assert "twill" not in subprocess.__file__

# Hack for Mac OS + homebrew
os.environ["PATH"] += ":/usr/local/bin"

TMP_DIR = "tmp"
CACHE_DIR = "cache"


def get_tmp_dir():
    from . import converter

    return converter.TMP_DIR


# Utils
@contextmanager
def make_temp_file(blob=None, prefix="tmp", suffix="", tmp_dir=None):
    if tmp_dir is None:
        tmp_dir = get_tmp_dir()

    fd, filename = mkstemp(dir=str(tmp_dir), prefix=prefix, suffix=suffix)
    if blob is not None:
        fd = os.fdopen(fd, "wb")
        fd.write(blob)
        fd.close()
    else:
        os.close(fd)

    yield filename
    try:
        os.remove(filename)
    except OSError:
        pass
