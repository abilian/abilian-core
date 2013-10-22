# coding=utf-8
"""
"""
from __future__ import absolute_import

from flask import Blueprint, abort

base = Blueprint('web', __name__,
                 template_folder='templates',
                 static_url_path='/static/base',
                 static_folder='static')

http_error_pages = Blueprint('http_error_pages', __name__)


@http_error_pages.route('/<int:code>')
def error_page(code):
  """ Helper for development to show 403, 404, 500..."""
  abort(code)
