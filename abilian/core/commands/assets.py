# coding=utf-8
"""
"""
from __future__ import absolute_import
from flask.ext.assets import ManageAssets as BaseManageAssets

class ManageAssets(BaseManageAssets):

  def create_parser(self, prog, *args, **kwargs):
    """ As of Flask-Script 0.6.2, create_parser is called with additional kwarg
    `parents`. As of Flask-Assets 0.8 ManageAssets commands is not compatible
    """
    return super(BaseManageAssets, self).create_parser(prog, *args, **kwargs)
