# coding=utf-8
"""
"""
from __future__ import absolute_import

import pkg_resources
from flask_assets import Bundle

# register custom filters for webassets
from . import filters  # noqa

RESOURCES_DIR = pkg_resources.resource_filename('abilian.web', 'resources')

JQUERY = Bundle('jquery/js/jquery-1.11.3.js',
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

FILEAPI_JS = Bundle('fileapi/FileAPI.js')

FONTAWESOME_LESS = Bundle('font-awesome/less/font-awesome.less')

REQUIRE_JS = Bundle('requirejs/require.js',
                    'requirejs/domReady.js')


SCRIBE_JS = Bundle( # needs requirejs
    'scribe/scribe/scribe.js',
    ('scribe/scribe-plugin-formatter-plain-text-convert-new-lines-to-html/'
     'scribe-plugin-formatter-plain-text-convert-new-lines-to-html.js'),
    ('scribe/scribe-plugin-blockquote-command/'
     'scribe-plugin-blockquote-command.js'),
    ('scribe/scribe-plugin-link-prompt-command/'
     'scribe-plugin-link-prompt-command.js'),
    ('scribe/scribe-plugin-keyboard-shortcuts/'
     'scribe-plugin-keyboard-shortcuts.js'),
    'scribe/scribe-plugin-curly-quotes/scribe-plugin-curly-quotes.js',
    'scribe/scribe-plugin-heading-command/scribe-plugin-heading-command.js',
    #'scribe/scribe-plugin-toolbar/scribe-plugin-toolbar.js',
    'scribe/scribe-plugin-abilian-toolbar.js',
    ('scribe/scribe-plugin-intelligent-unlink-command/'
     'scribe-plugin-intelligent-unlink-command.js'),
    'scribe/scribe-plugin-smart-lists/scribe-plugin-smart-lists.js',
    'scribe/scribe-plugin-sanitizer/scribe-plugin-sanitizer.js',
    'scribe/widget.js',
)

SELECT2_LESS = Bundle('select2/select2.css',
                      'select2/select2-bootstrap.css',)
SELECT2_JS = Bundle('select2/select2.js')

TYPEAHEAD_LESS = Bundle('typeahead/typeahead.js-bootstrap.less')
TYPEAHEAD_JS = Bundle('typeahead/typeahead.js',
                      'typeahead/hogan-2.0.0.js')

ABILIAN_LESS = Bundle('less/abilian.less',
                      'less/print.less')

ABILIAN_JS_NS = Bundle('js/abilian-namespace.js')
ABILIAN_JS = Bundle('js/abilian.js',
                    'js/datatables-setup.js',
                    'js/datatables-advanced-search.js',
                    'js/widgets/base.js',
                    'js/widgets/delete.js',
                    'js/widgets/file.js',
                    'js/widgets/image.js',
                    'js/widgets/tags.js',
                    'js/widgets/dynamic-row.js',
            )

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

TOP_JS = Bundle(REQUIRE_JS,
                JQUERY,
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
            SCRIBE_JS,
            ABILIAN_JS,)

JS_I18N = (
  'select2/select2_locale_{lang}.js',
  'bootstrap-datepicker/js/locales/bootstrap-datepicker.{lang}.js',
  )
