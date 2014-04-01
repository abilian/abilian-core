# coding=utf-8
"""
"""
from __future__ import absolute_import

import pkg_resources
from flask.ext.assets import Bundle

from . import filters

RESOURCES_DIR = pkg_resources.resource_filename('abilian.web', 'resources')

JQUERY = Bundle('jquery/js/jquery-1.10.2.js',
                'jquery/js/jquery-migrate-1.2.1.js')

BOOTBOX_JS = Bundle('bootbox/bootbox.js')

BOOTSTRAP_LESS = Bundle('bootstrap/less/bootstrap.less')
BOOTSTRAP_JS = Bundle('bootstrap/js/bootstrap.js')

BOOTSTRAP_DATEPICKER_LESS = 'bootstrap-datepicker/less/datepicker.less'
BOOTSTRAP_DATEPICKER_JS = Bundle('bootstrap-datepicker/js/bootstrap-datepicker.js')

BOOTSTRAP_SWITCH_LESS = Bundle('bootstrap-switch/less/bootstrap3/bootstrap-switch.less')
BOOTSTRAP_SWITCH_JS = Bundle('bootstrap-switch/bootstrap-switch.js')

BOOTSTRAP_TIMEPICKER_LESS = Bundle('bootstrap-timepicker/less/timepicker.less')
BOOTSTRAP_TIMEPICKER_JS = Bundle('bootstrap-timepicker/js/bootstrap-timepicker.js')

DATATABLE_LESS = Bundle('datatables/css/jquery.dataTables.css',
                        'datatables/css/jquery.dataTables_themeroller.css')
DATATABLE_JS = Bundle('datatables/js/jquery.dataTables.js')

FILEAPI_JS = Bundle('fileapi/FileAPI.js',
                    'fileapi/plugins/jquery.fileapi.js')

FONTAWESOME_LESS = Bundle('font-awesome/less/font-awesome.less')

SELECT2_LESS = Bundle('select2/select2.css',
                      'select2/select2-bootstrap.css',)
SELECT2_JS = Bundle('select2/select2.js')

TYPEAHEAD_LESS = Bundle('typeahead/typeahead.js-bootstrap.less')
TYPEAHEAD_JS = Bundle('typeahead/typeahead.js',
                      'typeahead/hogan-2.0.0.js')

ABILIAN_LESS = Bundle('less/abilian.less')
ABILIAN_JS_NS = Bundle('js/abilian-namespace.js')
ABILIAN_JS = Bundle('js/abilian.js',
                    'js/datatables-setup.js',
                    'js/widgets/file.js',
                    'js/widgets/image.js')

LESS = Bundle(BOOTSTRAP_LESS,
              FONTAWESOME_LESS,
              SELECT2_LESS,
              TYPEAHEAD_LESS,
              BOOTSTRAP_DATEPICKER_LESS,
              BOOTSTRAP_SWITCH_LESS,
              BOOTSTRAP_TIMEPICKER_LESS,
              DATATABLE_LESS,
              ABILIAN_LESS,
              )

TOP_JS = Bundle(JQUERY,
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
