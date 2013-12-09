# coding=utf-8
"""
"""
from __future__ import absolute_import

import os
import re
import sys

from flask import render_template

from ..panel import AdminPanel


class SysinfoPanel(AdminPanel):
  id = 'sysinfo'
  label = 'System information'
  icon = 'hdd'

  def get(self):
    uname = os.popen("uname -a").read()

    python_version = sys.version.strip()

    lines = os.popen("pip freeze").readlines()
    packages = []
    for line in lines:
      line = line.strip()
      if not line:
        continue
      m = re.search(r"egg=(\S+)$", line)
      if m:
        package = dict(name=m.group(1), version="from git")
      else:
        m = re.match(r"(\S+)==(.*)", line)
        if m:
          package = dict(name=m.group(1), version=m.group(2))
        else:
          package = dict(name=line, version="Unknown version")
      packages.append(package)

    return render_template("admin/sysinfo.html",
                           python_version=python_version,
                           packages=packages,
                           uname=uname)
