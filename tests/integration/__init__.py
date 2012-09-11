# Fix for when running from an IDE (ex: PyCharm under MacOS)
import os
os.environ['PATH'] = "/usr/local/bin:" + os.environ['PATH']

# Hack around the fact that twill (a requirement for Flask-Testing) embeds
# an older version of subprocess.
import subprocess