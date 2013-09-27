# coding=utf-8
"""
"""
from __future__ import absolute_import
import logging
import os
import re
import pkg_resources

from webassets.filter import Filter, register_filter
from flask.ext.assets import Bundle

RESOURCES_DIR = pkg_resources.resource_filename(__name__, 'resources')

JQUERY = Bundle('jquery/js/jquery-1.10.2.min.js',
                'jquery/js/jquery-migrate-1.2.1.min.js')

JQUERY_DEBUG = Bundle('jquery/js/jquery-1.10.2.js',
                      'jquery/js/jquery-migrate-1.2.1.js')

BOOTSTRAP_JS = Bundle('bootstrap/js/bootstrap.min.js')
BOOTSTRAP_JS_DEBUG = Bundle('bootstrap/js/bootstrap.js')

BOOTSTRAP_CSS = Bundle('bootstrap/css/bootstrap.min.css',
                       'bootstrap/css/bootstrap-theme.min.css')

BOOTSTRAP_CSS_DEBUG = Bundle('bootstrap/css/bootstrap.css',
                             'bootstrap/css/bootstrap-theme.css')

CSS = BOOTSTRAP_CSS
CSS_DEBUG = BOOTSTRAP_CSS_DEBUG
JS = BOOTSTRAP_JS
JS_DEBUG = BOOTSTRAP_JS_DEBUG


class ImportCSSFilter(Filter):
  """ This filter searches (recursively) '@import' rules and replaces them by
  content of target file.
  """
  name = 'cssimporter'

  logger = logging.getLogger(__name__ + '.ImportCssFilter')
  _IMPORT_RE = re.compile('''@import '(?P<filename>[a-zA-Z0-9_-]+\.css)';''')

  def input(self, _in, out, **kwargs):
    filepath = kwargs['source_path']
    base_dir = os.path.dirname(filepath)
    self.logger.debug('process "%s"', filepath)

    for line in _in.readlines():
      import_match = self._IMPORT_RE.search(line)
      if import_match is None:
        out.write(line)
        continue

      filename = import_match.group('filename')
      self.logger.debug('Import "%s" line: |%s|', filename, line.strip())
      abs_filename = os.path.join(base_dir, filename)
      start, end = import_match.span()
      if start > 0:
        out.write(line[:start])
        out.write('\n')

      with open(abs_filename, 'r') as included:
        self.input(included, out, source_path=abs_filename)

      if end < len(line):
        out.write(line[end:])
      else:
        out.write('\n')

register_filter(ImportCSSFilter)
