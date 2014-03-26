# coding=utf-8
"""
"""
from __future__ import absolute_import

import pkg_resources
from flask.ext.assets import Bundle

from .filters import SubBundle

RESOURCES_DIR = pkg_resources.resource_filename('abilian.web', 'resources')

JQUERY = Bundle('jquery/js/jquery-1.10.2.min.js',
                'jquery/js/jquery-migrate-1.2.1.min.js')

JQUERY_DEBUG = Bundle('jquery/js/jquery-1.10.2.js',
                      'jquery/js/jquery-migrate-1.2.1.js')

BOOTBOX_JS = Bundle('bootbox/bootbox.min.js')
BOOTBOX_JS_DEBUG = Bundle('bootbox/bootbox.js')

BOOTSTRAP_JS = Bundle('bootstrap/js/bootstrap.min.js')
BOOTSTRAP_JS_DEBUG = Bundle('bootstrap/js/bootstrap.js')

BOOTSTRAP_LESS = 'bootstrap/less/bootstrap.less'
BOOTSTRAP_CSS = Bundle('bootstrap/css/bootstrap.min.css',
                       'bootstrap/css/bootstrap-theme.min.css')

BOOTSTRAP_CSS_DEBUG = Bundle('bootstrap/css/bootstrap.css',
                             'bootstrap/css/bootstrap-theme.css')

BOOTSTRAP_DATEPICKER_LESS = 'bootstrap-datepicker/less/datepicker.less'
BOOTSTRAP_DATEPICKER_CSS = Bundle('bootstrap-datepicker/css/datepicker.css')
BOOTSTRAP_DATEPICKER_JS = Bundle('bootstrap-datepicker/js/bootstrap-datepicker.js')

BOOTSTRAP_SWITCH_LESS = 'bootstrap-switch/less/bootstrap3/bootstrap-switch.less'
BOOTSTRAP_SWITCH_CSS = Bundle('bootstrap-switch/bootstrap-switch.css')
BOOTSTRAP_SWITCH_JS = Bundle('bootstrap-switch/bootstrap-switch.js')

BOOTSTRAP_TIMEPICKER_LESS = 'bootstrap-timepicker/less/timepicker.less'
BOOTSTRAP_TIMEPICKER_CSS = Bundle('bootstrap-timepicker/css/bootstrap-timepicker.css')
BOOTSTRAP_TIMEPICKER_JS = Bundle('bootstrap-timepicker/js/bootstrap-timepicker.js')

DATATABLE_LESS = ('datatables/css/jquery.dataTables.css',
                  'datatables/css/jquery.dataTables_themeroller.css')
DATATABLE_CSS = Bundle(*DATATABLE_LESS)
DATATABLE_JS = Bundle('datatables/js/jquery.dataTables.min.js')
DATATABLE_JS_DEBUG = Bundle('datatables/js/jquery.dataTables.js')

FILEAPI_JS = Bundle('fileapi/FileAPI.min.js',
                    'fileapi/plugins/jquery.fileapi.min.js')
FILEAPI_JS_DEBUG = Bundle('fileapi/FileAPI.js',
                          'fileapi/plugins/jquery.fileapi.js')

FONTAWESOME_LESS = 'font-awesome/less/font-awesome.less'
FONTAWESOME_CSS = Bundle('font-awesome/css/font-awesome.min.css')
FONTAWESOME_CSS_DEBUG = Bundle('font-awesome/css/font-awesome.css')

SELECT2_LESS = ('select2/select2.css',
                'select2/select2-bootstrap.css',)
SELECT2_CSS = Bundle(*SELECT2_LESS)
SELECT2_JS = Bundle('select2/select2.min.js')
SELECT2_JS_DEBUG = Bundle('select2/select2.js')

TYPEAHEAD_LESS = 'typeahead/typeahead.js-bootstrap.less'
TYPEAHEAD_CSS = Bundle('typeahead/typeahead.js-bootstrap.css')
TYPEAHEAD_JS = Bundle('typeahead/typeahead.min.js',
                      'typeahead/hogan-2.0.0.js',)
TYPEAHEAD_JS_DEBUG = Bundle('typeahead/typeahead.js',
                            'typeahead/hogan-2.0.0.js')

ABILIAN_LESS = 'css/abilian.css'
ABILIAN_CSS = Bundle('css/abilian.css')
ABILIAN_JS_NS = Bundle('js/abilian-namespace.js')
ABILIAN_JS = Bundle('js/abilian.js',
                    'js/datatables-setup.js',
                    'js/widgets/file.js',
                    'js/widgets/image.js')

LESS_FILES = (BOOTSTRAP_LESS,
              FONTAWESOME_LESS,
              SELECT2_LESS,
              TYPEAHEAD_LESS,
              BOOTSTRAP_DATEPICKER_LESS,
              BOOTSTRAP_SWITCH_LESS,
              BOOTSTRAP_TIMEPICKER_LESS,
              DATATABLE_LESS,
              ABILIAN_LESS,
)


LESS = []
for file_list in LESS_FILES:
  if isinstance(file_list, str):
    file_list = (file_list,)
  for f in file_list:
    filters=None
    # # for proper import in generated .less file, css files must be preprocessed
    # # to fix urls and @import statements
    # if f.endswith('.css'):
    #   filters='cssrewrite,cssimporter'
    LESS.append(Bundle(f, filters=filters))

LESS = SubBundle(*LESS, filters='less_import')

CSS = Bundle(BOOTSTRAP_CSS,
             FONTAWESOME_CSS,
             SELECT2_CSS,
             TYPEAHEAD_CSS,
             BOOTSTRAP_DATEPICKER_CSS,
             BOOTSTRAP_SWITCH_CSS,
             BOOTSTRAP_TIMEPICKER_CSS,
             DATATABLE_CSS,
             ABILIAN_CSS,)
CSS_DEBUG = Bundle(BOOTSTRAP_CSS_DEBUG,
                   FONTAWESOME_CSS_DEBUG,
                   SELECT2_CSS,
                   TYPEAHEAD_CSS,
                   BOOTSTRAP_DATEPICKER_CSS,
                   BOOTSTRAP_SWITCH_CSS,
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
            BOOTSTRAP_SWITCH_JS,
            BOOTSTRAP_TIMEPICKER_JS,
            DATATABLE_JS,
            FILEAPI_JS,
            ABILIAN_JS,)
JS_DEBUG = Bundle(BOOTSTRAP_JS_DEBUG,
                  TYPEAHEAD_JS_DEBUG,
                  SELECT2_JS_DEBUG,
                  BOOTBOX_JS_DEBUG,
                  BOOTSTRAP_DATEPICKER_JS,
                  BOOTSTRAP_SWITCH_JS,
                  BOOTSTRAP_TIMEPICKER_JS,
                  DATATABLE_JS_DEBUG,
                  FILEAPI_JS_DEBUG,
                  ABILIAN_JS,)
