""""""
import os
import sys

import pkg_resources
from flask import current_app, render_template

from abilian.web.admin import AdminPanel


class SysinfoPanel(AdminPanel):
    id = "sysinfo"
    label = "System information"
    icon = "hdd"

    def get(self) -> str:
        uname = os.popen("uname -a").read()
        python_version = sys.version.strip()

        packages = []

        for dist in pkg_resources.working_set:
            package = {
                "name": dist.project_name,
                "key": dist.key,
                "version": dist.version if dist.has_version() else "Unknown version",
                "vcs": None,
            }

            # FIXME: broken by pip 10
            # location = text_type(Path(dist.location).resolve())
            # vcs_name = get_backend_name(location)
            #
            # if vcs_name:
            #     vc = vcs.get_backend(vcs_name)()
            #     try:
            #         url = vc.get_url(location)
            #     except pip.exceptions.InstallationError:
            #         url = 'None'
            #     try:
            #         revision = vc.get_revision(location)
            #     except pip.exceptions.InstallationError:
            #         revision = 'None'
            #     package['vcs'] = dict(
            #         name=vcs_name,
            #         url=url,
            #         revision=revision,
            #     )

            packages.append(package)
            packages.sort(key=lambda d: d.get("key"))

        config_values = [(k, repr(v)) for k, v in sorted(current_app.config.items())]

        ctx = {
            "python_version": python_version,
            "packages": packages,
            "uname": uname,
            "config_values": config_values,
        }
        return render_template("admin/sysinfo.html", **ctx)
