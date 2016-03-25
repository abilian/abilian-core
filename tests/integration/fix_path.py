# Fix for when running from an IDE (ex: PyCharm under MacOS)
import os
# Hack around the fact that twill (a requirement for Flask-Testing) embeds
# an older version of subprocess.
import subprocess  # noqa

this_bin = os.path.dirname(__file__) + "/../bin"
os.environ['PATH'] = "/usr/local/bin:" + this_bin + ":" + os.environ['PATH']
