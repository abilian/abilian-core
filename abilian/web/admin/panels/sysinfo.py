# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

import os
import sys
import pkg_resources
from pip.vcs import vcs

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

    for dist in pkg_resources.working_set:
      package = dict(
          name=dist.project_name,
          key=dist.key,
          version=dist.version if dist.has_version() else u'Unknown version',
          vcs=None,
      )

      location = os.path.normcase(os.path.abspath(dist.location))
      vcs_name = vcs.get_backend_name(location)
      if vcs_name:
        vc = vcs.get_backend_from_location(location)()
        url, revision = vc.get_info(location)
        package['vcs'] = dict(name=vcs_name, url=url, revision=revision)

      packages.append(package)
      packages.sort(key=lambda d: d.get('key', None))

    return render_template("admin/sysinfo.html",
                           python_version=python_version,
                           packages=packages,
                           uname=uname)
