""""""
import logging
from pprint import pformat

from flask import current_app
from flask.cli import AppGroup

logging.basicConfig()
logger = logging.getLogger("")

config_commands = AppGroup("config")


@config_commands.command()
def show(only_path=False):
    """Show the current config."""
    logger.setLevel(logging.INFO)
    infos = ["\n", f'Instance path: "{current_app.instance_path}"']

    logger.info("\n  ".join(infos))

    if not only_path:
        log_config(current_app.config)


def log_config(config):
    original_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        return _log_config(config)
    finally:
        logger.setLevel(original_level)


def _log_config(config):
    lines = ["Application configuration:"]

    for k, v in sorted(config.items()):
        prefix = "    "
        indent = len(k) + 3
        width = 80 - indent
        v = pformat(v, width=width).replace("\n", "\n" + " " * indent)
        lines.append(f"{prefix}{k}: {v}")
    logger.info("\n".join(lines))
