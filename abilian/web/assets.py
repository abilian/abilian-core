# coding=utf-8
"""
"""
from __future__ import absolute_import
import logging
import os
import re
import pkg_resources
from cStringIO import StringIO

from webassets.filter import Filter, register_filter, get_filter
from flask.ext.assets import Bundle

RESOURCES_DIR = pkg_resources.resource_filename(__name__, 'resources')

JQUERY = Bundle('jquery/js/jquery-1.10.2.min.js',
                'jquery/js/jquery-migrate-1.2.1.min.js')

JQUERY_DEBUG = Bundle('jquery/js/jquery-1.10.2.js',
                      'jquery/js/jquery-migrate-1.2.1.js')

BOOTBOX_JS = Bundle('bootbox/bootbox.min.js')
BOOTBOX_JS_DEBUG = Bundle('bootbox/bootbox.js')

BOOTSTRAP_JS = Bundle('bootstrap/js/bootstrap.min.js')
BOOTSTRAP_JS_DEBUG = Bundle('bootstrap/js/bootstrap.js')

BOOTSTRAP_CSS = Bundle('bootstrap/css/bootstrap.min.css',
                       'bootstrap/css/bootstrap-theme.min.css')

BOOTSTRAP_CSS_DEBUG = Bundle('bootstrap/css/bootstrap.css',
                             'bootstrap/css/bootstrap-theme.css')

BOOTSTRAP_DATEPICKER_CSS = Bundle('bootstrap-datepicker/css/datepicker.css')
BOOTSTRAP_DATEPICKER_JS = Bundle('bootstrap-datepicker/js/bootstrap-datepicker.js')

BOOTSTRAP_TIMEPICKER_CSS = Bundle('bootstrap-timepicker/css/bootstrap-timepicker.css')
BOOTSTRAP_TIMEPICKER_JS = Bundle('bootstrap-timepicker/js/bootstrap-timepicker.js')

DATATABLE_CSS = Bundle('datatables/css/jquery.dataTables.css',
                       'datatables/css/jquery.dataTables_themeroller.css')

DATATABLE_JS = Bundle('datatables/js/jquery.dataTables.min.js')
DATATABLE_JS_DEBUG = Bundle('datatables/js/jquery.dataTables.js')

FILEAPI_JS = Bundle('fileapi/FileAPI.min.js',
                    'fileapi/plugins/jquery.fileapi.min.js')
FILEAPI_JS_DEBUG = Bundle('fileapi/FileAPI.js',
                          'fileapi/plugins/jquery.fileapi.js')

FONTAWESOME_CSS = Bundle('font-awesome/css/font-awesome.min.css')
FONTAWESOME_CSS_DEBUG = Bundle('font-awesome/css/font-awesome.css')

SELECT2_CSS = Bundle('select2/select2.css',
                     'select2/select2-bootstrap.css',)
SELECT2_JS = Bundle('select2/select2.min.js')
SELECT2_JS_DEBUG = Bundle('select2/select2.js')

TYPEAHEAD_JS = Bundle('typeahead/typeahead.min.js',
                      'typeahead/hogan-2.0.0.js',)
TYPEAHEAD_JS_DEBUG = Bundle('typeahead/typeahead.js',
                            'typeahead/hogan-2.0.0.js')
TYPEAHEAD_CSS = Bundle('typeahead/typeahead.js-bootstrap.css')

ABILIAN_CSS = Bundle('css/abilian.css')
ABILIAN_JS_NS = Bundle('js/abilian-namespace.js')
ABILIAN_JS = Bundle('js/abilian.js',
                    'js/datatables-setup.js',
                    'js/widgets/file.js',
                    'js/widgets/image.js')

CSS = Bundle(BOOTSTRAP_CSS,
             FONTAWESOME_CSS,
             SELECT2_CSS,
             TYPEAHEAD_CSS,
             BOOTSTRAP_DATEPICKER_CSS,
             BOOTSTRAP_TIMEPICKER_CSS,
             DATATABLE_CSS,
             ABILIAN_CSS,)
CSS_DEBUG = Bundle(BOOTSTRAP_CSS_DEBUG,
                   FONTAWESOME_CSS_DEBUG,
                   SELECT2_CSS,
                   TYPEAHEAD_CSS,
                   BOOTSTRAP_DATEPICKER_CSS,
                   BOOTSTRAP_TIMEPICKER_CSS,
                   DATATABLE_CSS,
                   ABILIAN_CSS,)

TOP_JS = Bundle(JQUERY,
                ABILIAN_JS_NS)
TOP_JS_DEBUG = Bundle(JQUERY_DEBUG,
                      ABILIAN_JS_NS)

JS = Bundle(BOOTSTRAP_JS,
            TYPEAHEAD_JS,
            BOOTBOX_JS,
            SELECT2_JS,
            BOOTSTRAP_DATEPICKER_JS,
            BOOTSTRAP_TIMEPICKER_JS,
            DATATABLE_JS,
            FILEAPI_JS,
            ABILIAN_JS,)
JS_DEBUG = Bundle(BOOTSTRAP_JS_DEBUG,
                  TYPEAHEAD_JS_DEBUG,
                  SELECT2_JS_DEBUG,
                  BOOTBOX_JS_DEBUG,
                  BOOTSTRAP_DATEPICKER_JS,
                  BOOTSTRAP_TIMEPICKER_JS,
                  DATATABLE_JS_DEBUG,
                  FILEAPI_JS_DEBUG,
                  ABILIAN_JS,)


class ImportCSSFilter(Filter):
  """ This filter searches (recursively) '@import' rules and replaces them by
  content of target file.
  """
  name = 'cssimporter'

  logger = logging.getLogger(__name__ + '.ImportCssFilter')
  _IMPORT_RE = re.compile('''@import '(?P<filename>[a-zA-Z0-9_-]+\.css)';''')

  def input(self, _in, out, **kwargs):
    filepath = kwargs['source_path']
    source = kwargs['source']
    # output = kwargs['output']
    base_dir = os.path.dirname(filepath)
    rel_dir = os.path.dirname(source)

    self.logger.debug('process "%s"', filepath)

    for line in _in.readlines():
      import_match = self._IMPORT_RE.search(line)
      if import_match is None:
        out.write(line)
        continue

      filename = import_match.group('filename')
      self.logger.debug('Import "%s" line: |%s|', filename, line.strip())
      abs_filename = os.path.join(base_dir, filename)
      rel_filename= os.path.normpath(os.path.join(rel_dir, filename))

      start, end = import_match.span()
      if start > 0:
        out.write(line[:start])
        out.write('\n')

      with open(abs_filename, 'r') as included:
        # rewrite url() statements
        buf = StringIO()
        url_rewriter = get_filter('cssrewrite')
        url_rewriter.set_environment(self.env)
        url_rewriter.setup()
        url_rewriter.input(included, buf,
                           source=rel_filename,
                           source_path=abs_filename,
                           output=source,
                           output_path=filepath)
      buf.seek(0)
      # now process '@includes' directives in included file
      self.input(buf, out,
                 source=rel_filename,
                 source_path=abs_filename,
                 output=source,
                 output_path=filepath)

      if end < len(line):
        out.write(line[end:])
      else:
        out.write('\n')

register_filter(ImportCSSFilter)
