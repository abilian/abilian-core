# coding=utf-8
"""
Abilian script commands to be used in a project. See `Flask-Script documentation
<http://flask-script.readthedocs.org>`_ for full documentation.

Here is how a `manage.py` can include these commands::

     from flask_script import Manager
     from abilian.commands import setup_abilian_commands

     my_manager = Manager(app)
     setup_abilian_commands(my_manager)

You can also include abilian commands as sub commands::

     from abilian.commands import manager as abilian_manager
     my_manager.add_command('abilian', abilian_manager)

Extensions can add their own commands to :py:data:`~abilian.core.commands.manager`::

     from flask_script import Manager
     from abilian.commands import manager

     @manager.command
     def hello():
         print u"hello"

     # or install subcommands
     sub_manager = Manager(usage='Little extension')
     abilian_manager.add_command('special_commands', sub_manager)
"""
from __future__ import absolute_import, print_function, division

from flask_migrate import MigrateCommand
from flask_assets import ManageAssets

from .base import manager
from .config import manager as config_manager

# Additional commands
from . import indexing  # noqa

__all__ = ['manager', 'setup_abilian_commands']


def setup_abilian_commands(manager):
    """Register abilian commands on ``manager``.

    :param manager: ``flask_script.Manager`` instance to add commands onto

    Usage exemple::

      from flask_script import Manager
      from abilian.commands import setup_abilian_commands

      my_manager = Manager(app)
      setup_abilian_commands(my_manager)
    """
    abilian_manager = globals()['manager']
    manager._options.extend(abilian_manager._options)

    for name, command in abilian_manager._commands.items():
        manager.add_command(name, command)

    manager.add_command("assets", ManageAssets())  # flask-assets
    manager.add_command("config", config_manager)
    manager.add_command("migrate", MigrateCommand)
    return manager
