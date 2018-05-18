# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, unicode_literals

import os

from demo.app import create_app
from flask_script import Manager

from abilian.core.commands import setup_abilian_commands

manager = Manager(create_app)

setup_abilian_commands(manager)


def main():
    manager.run()


def filter_filename(filename):
    if "abilian-core/abilian" in filename:
        return filename

    return None


def main_annotate():
    from pyannotate_runtime import collect_types

    collect_types.init_types_collection(filter_filename=filter_filename)
    collect_types.resume()
    try:
        manager.run()
    except BaseException:
        pass
    collect_types.dump_stats(b"type_info.json")


if __name__ == "__main__":
    if "ANNOTATE" in os.environ:
        main_annotate()
    else:
        main()
