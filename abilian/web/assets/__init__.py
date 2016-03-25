# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

import pkg_resources

from flask import url_for, current_app
from flask_assets import Bundle

from abilian.services.security import Anonymous

# register custom filters for webassets
from . import filters  # noqa


def init_app(app):
    assets = app.extensions['webassets']
    assets.append_path(RESOURCES_DIR, '/static/abilian')
    app.add_static_url('abilian',
                       RESOURCES_DIR,
                       endpoint='abilian_static',
                       roles=Anonymous)

    app.before_first_request(requirejs_config)


def requirejs_config():
    assets = current_app.extensions['webassets']
    config = assets.requirejs_config

    # setup ckeditor
    ckeditor_lib = 'ckeditor/ckeditor'
    config['shim']['ckeditor'] = {'exports': 'CKEDITOR'}
    config['paths']['ckeditor'] = url_for('abilian_static',
                                          filename=ckeditor_lib)

    d3_lib = 'nvd3/d3.min'
    config['shim']['d3'] = {'exports': 'd3'}
    config['paths']['d3'] = url_for('abilian_static', filename=d3_lib)

    nvd3_lib = 'nvd3/nv.d3'
    config['shim']['nvd3'] = {'exports': 'nv', 'deps': ['d3']}
    config['paths']['nvd3'] = url_for('abilian_static', filename=nvd3_lib)


RESOURCES_DIR = pkg_resources.resource_filename('abilian.web', 'resources')

JQUERY = Bundle('jquery/js/jquery-1.11.3.js',
                'jquery/js/jquery-migrate-1.2.1.js')

BOOTBOX_JS = Bundle('bootbox/bootbox.js')

BOOTSTRAP_LESS = Bundle('bootstrap/less/bootstrap.less')
BOOTSTRAP_JS = Bundle('bootstrap/js/bootstrap.js')

BOOTSTRAP_DATEPICKER_LESS = 'bootstrap-datepicker/less/datepicker.less'
BOOTSTRAP_DATEPICKER_JS = Bundle(
    'bootstrap-datepicker/js/bootstrap-datepicker.js')

BOOTSTRAP_SWITCH_LESS = Bundle(
    'bootstrap-switch/less/bootstrap3/bootstrap-switch.less')
BOOTSTRAP_SWITCH_JS = Bundle('bootstrap-switch/bootstrap-switch.js')

BOOTSTRAP_TIMEPICKER_LESS = Bundle('bootstrap-timepicker/less/timepicker.less')
BOOTSTRAP_TIMEPICKER_JS = Bundle(
    'bootstrap-timepicker/js/bootstrap-timepicker.js')

DATATABLE_LESS = Bundle('datatables/css/jquery.dataTables.css',
                        'datatables/css/jquery.dataTables_themeroller.css')
DATATABLE_JS = Bundle('datatables/js/jquery.dataTables.js')

FILEAPI_JS = Bundle('fileapi/FileAPI.js')

FONTAWESOME_LESS = Bundle('font-awesome/less/font-awesome.less')

REQUIRE_JS = Bundle('requirejs/require.js', 'requirejs/domReady.js')

SELECT2_LESS = Bundle('select2/select2.css', 'select2/select2-bootstrap.css',)
SELECT2_JS = Bundle('select2/select2.js')

TYPEAHEAD_LESS = Bundle('typeahead/typeahead.js-bootstrap.less')
TYPEAHEAD_JS = Bundle('typeahead/typeahead.js', 'typeahead/hogan-2.0.0.js')

ABILIAN_LESS = Bundle('less/abilian.less', 'less/print.less')

ABILIAN_JS_NS = Bundle('js/abilian-namespace.js')
ABILIAN_JS = Bundle('js/abilian.js',
                    'js/datatables-setup.js',
                    'js/datatables-advanced-search.js',
                    'js/widgets/base.js',
                    'js/widgets/select2.js',
                    'js/widgets/richtext.js',
                    'js/widgets/delete.js',
                    'js/widgets/file.js',
                    'js/widgets/image.js',
                    'js/widgets/tags.js',
                    'js/widgets/dynamic-row.js',)

LESS = Bundle(BOOTSTRAP_LESS,
              FONTAWESOME_LESS,
              SELECT2_LESS,
              TYPEAHEAD_LESS,
              BOOTSTRAP_DATEPICKER_LESS,
              BOOTSTRAP_SWITCH_LESS,
              BOOTSTRAP_TIMEPICKER_LESS,
              DATATABLE_LESS,
              ABILIAN_LESS,)

TOP_JS = Bundle(REQUIRE_JS, JQUERY, ABILIAN_JS_NS)

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

JS_I18N = ('select2/select2_locale_{lang}.js',
           'bootstrap-datepicker/js/locales/bootstrap-datepicker.{lang}.js',)
