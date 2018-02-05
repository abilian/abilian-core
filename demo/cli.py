# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, unicode_literals

from flask_script import Manager

from abilian.core.commands import setup_abilian_commands
from demo.app import create_app

manager = Manager(create_app)


setup_abilian_commands(manager)


def main():
    manager.run()


if __name__ == "__main__":
    main()
