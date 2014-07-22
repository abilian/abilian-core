# coding=utf-8
"""
Preset loggers
"""
from __future__ import absolute_import

import logging

__all__ = ['patch_logger']

logging.basicConfig()

_mk_fmt = '[%(name)s] %(message)s at %(pathname)s:%(lineno)d'
_mk_format = logging.Formatter(fmt=_mk_fmt)

_patch_handler = logging.StreamHandler()
_patch_handler.setFormatter(_mk_format)
_patch_logger = logging.getLogger('PATCH')
_patch_logger.setLevel(logging.INFO)
_patch_logger.addHandler(_patch_handler)
_patch_logger.propagate = False

class PatchLoggerAdapter(logging.LoggerAdapter):

  def process(self, msg, kwargs):
    if isinstance(msg, basestring):
      return super(PatchLoggerAdapter, self).process(msg, kwargs)

    func = msg
    return '{}.{}'.format(func.__module__, func.__name__), kwargs

#: logger for monkey patchs. use like this:
#: patch_logger.info(<func>`patched_func`)
patch_logger = PatchLoggerAdapter(_patch_logger, None)
