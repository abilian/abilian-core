# coding=utf-8
"""
Reusable widgets to be included in views.

NOTE: code is currently quite messy. Needs to be refactored.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import base64
import cgi
import logging
import re
from collections import namedtuple
from datetime import datetime

import bleach
import sqlalchemy as sa
import wtforms
from flask import Markup, current_app, g, json, render_template, \
    render_template_string
from flask_babel import format_date, format_datetime, format_number, get_locale
from flask_login import current_user
from flask_wtf.file import FileField
from six import string_types, text_type
from six.moves import filter
from six.moves.urllib import parse
from wtforms.widgets import PasswordInput as BasePasswordInput
from wtforms.widgets import TextArea as BaseTextArea
from wtforms.widgets import HTMLString, Input, Select, html_params
from wtforms_alchemy import ModelFieldList

from abilian.core.entities import Entity
from abilian.core.models.blob import Blob
from abilian.i18n import _, _l
from abilian.services import image
from abilian.services.image import get_format
from abilian.web import csrf, url_for
from abilian.web.filters import babel2datepicker, labelize

from .util import babel2datetime

logger = logging.getLogger(__name__)

__all__ = [
    'linkify_url', 'text2html', 'Column', 'BaseTableView', 'MainTableView',
    'RelatedTableView', 'AjaxMainTableView', 'SingleView', 'Panel', 'Row',
    'Chosen', 'TagInput', 'DateInput', 'DefaultViewWidget', 'BooleanWidget',
    'FloatWidget', 'DateTimeWidget', 'DateWidget', 'MoneyWidget', 'EmailWidget',
    'URLWidget', 'ListWidget', 'TabularFieldListWidget', 'ModelListWidget',
    'Select2', 'Select2Ajax', 'RichTextWidget', 'FileInput', 'EntityWidget'
]


def linkify_url(value):
    """Tranform an URL pulled from the database to a safe HTML fragment."""

    value = value.strip()

    rjs = r'[\s]*(&#x.{1,7})?'.join(list('javascript:'))
    rvb = r'[\s]*(&#x.{1,7})?'.join(list('vbscript:'))
    re_scripts = re.compile('(%s)|(%s)' % (rjs, rvb), re.IGNORECASE)

    value = re_scripts.sub('', value)

    url = value
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "http://" + url

    url = parse.urlsplit(url).geturl()
    if '"' in url:
        url = url.split('"')[0]
    if '<' in url:
        url = url.split('<')[0]

    if value.startswith("http://"):
        value = value[len("http://"):]
    elif value.startswith("https://"):
        value = value[len("https://"):]

    if value.count("/") == 1 and value.endswith("/"):
        value = value[0:-1]

    return '<a href="%s">%s</a>&nbsp;<i class="fa fa-external-link"></i>' % (
        url, value)


def text2html(text):
    text = text.strip()
    if re.search('<(p|br)>', text.lower()):
        return text
    if '\n' not in text:
        return text

    lines = text.split("\n")
    lines = [line for line in lines if line]
    paragraphs = ['<p>%s</p>' % line for line in lines]
    return Markup(bleach.clean("\n".join(paragraphs), tags=['p']))


class Column(object):

    def __init__(self, **kw):
        for k, w in kw.items():
            setattr(self, k, w)


# TODO: rewrite
class BaseTableView(object):
    show_controls = False
    show_search = None
    paginate = False
    options = {}

    def __init__(self, columns, options=None):
        if self.show_search is None:
            self.show_search = self.show_controls

        self.init_columns(columns)
        self.name = u'{}-{:d}'.format(self.__class__.__name__.lower(),
                                      next(g.id_generator))
        if options is not None:
            self.options = options
            self.show_controls = self.options.get('show_controls',
                                                  self.show_controls)
            self.show_search = self.options.get('show_search',
                                                self.show_controls)
            self.paginate = self.options.get('paginate', self.paginate)

    def init_columns(self, columns):
        # TODO
        self.columns = []
        default_width = '{:2.0f}%'.format(0.99 / len(columns) * 100)
        for col in columns:
            if isinstance(col, string_types):
                col = dict(name=col, width=default_width)
            assert type(col) == dict
            col.setdefault('width', default_width)
            col.setdefault('sorting', ('asc', 'desc'))
            if 'label' not in col:
                col['label'] = labelize(col['name'])
            self.columns.append(col)

    def render(self, entities, **kwargs):
        aoColumns = []
        aaSorting = []
        offset = 0
        if self.show_controls:
            aoColumns.append({'asSorting': []})
            offset = 1

        for idx, c in enumerate(self.columns, offset):
            aoColumns.append({
                'asSorting': c['sorting'],
                'sWidth': str(c['width'])
            })
            aaSorting.append([idx, c['sorting'][0]])

        datatable_options = {
            'aaSorting': aaSorting,
            'aoColumns': aoColumns,
            'bFilter': self.show_search,
            'oLanguage': {
                'sSearch': self.options.get('search_label', _("Filter records:")),
            },
            'bStateSave': False,
            'bPaginate': self.paginate,
            'sPaginationType': "bootstrap",
            'bLengthChange': False,
            'iDisplayLength': self.options.get('paginate_length', 50)
        }
        js = render_template_string(
            '''
        require(
            ['jquery', 'jquery.dataTables'],
            function($) {
                $('#{{ table_id  }}').dataTable({{ options|tojson|safe }});
            });
        ''',
            table_id=self.name,
            options=datatable_options,)

        table = []
        for entity in entities:
            table.append(self.render_line(entity))

        template = filter(bool, (self.options.get('template'),
                                 'widgets/render_table.html'))
        return Markup(
            render_template(
                template, table=table, js=Markup(js), view=self, **kwargs))

    def render_line(self, entity):
        line = []
        make_link_on = self.options.get("make_link_on")

        for col in self.columns:
            if type(col) == str:
                column_name = col
                build_url = url_for
            else:
                column_name = col['name']
                build_url = col.get('url', url_for)

            value = entity
            attr = column_name.rsplit('.', 1)
            if len(attr) > 1:
                try:
                    value = getattr(value, attr[0], "")
                    value = value.display_value(attr[1])
                except AttributeError:
                    value = ""
            else:
                value = value.display_value(attr[0])

            format = col.get('format')
            if format:
                cell = format(value)
            elif column_name in (make_link_on, 'name') \
                    or col.get('linkable'):
                cell = Markup('<a href="%s">%s</a>' %
                              (build_url(entity), cgi.escape(text_type(value))))
            elif isinstance(value, Entity):
                cell = Markup('<a href="%s">%s</a>' %
                              (build_url(value), cgi.escape(value.name)))
            elif isinstance(value, string_types) \
                    and (value.startswith("http://") or value.startswith("www.")):
                cell = Markup(linkify_url(value))
            elif value in (True, False):
                cell = u'\u2713' if value else u''  # Unicode "Check mark"
            elif isinstance(value, list):
                cell = "; ".join(value)
            else:
                if not isinstance(value, (Markup,) + string_types):
                    if value is None:
                        value = u''
                    else:
                        value = text_type(value)
                cell = value

            line.append(cell)
        return line


class MainTableView(BaseTableView):
    """
    Table view for main objects list.
    """
    show_controls = True
    paginate = True


class RelatedTableView(BaseTableView):
    """
    Table view for related objects list.
    """
    show_controls = False
    paginate = False


class AjaxMainTableView(object):
    """
    Variant of the MainTableView that gets content from AJAX requests.

    TODO: refactor all of this (currently code is copy/pasted!).
    """
    show_controls = False
    paginate = True
    options = {}

    def __init__(self,
                 columns,
                 ajax_source,
                 search_criterions=(),
                 name=None,
                 options=None):
        self.init_columns(columns)
        self.ajax_source = ajax_source
        self.search_criterions = search_criterions
        self.name = name if name is not None else id(self)
        self.save_state = name is not None
        if options is not None:
            self.options = options

    def init_columns(self, columns):
        # TODO: compute the correct width for each column.
        self.columns = []
        default_width = 0.99 / len(columns)
        for col in columns:
            if type(col) == str:
                col = dict(name=col, width=default_width)
            assert type(col) == dict
            if 'label' not in col:
                col['label'] = labelize(col['name'])

            col.setdefault('sorting', ["asc", "desc"])

            if not col['sorting']:
                col.setdefault('sortable', False)
            else:
                col.setdefault('sortable', True)

            self.columns.append(col)

    def render(self):
        aoColumns = [{'asSorting': []}] if self.show_controls else []
        aoColumns += [{
            'asSorting': col['sorting'],
            'bSortable': col['sortable']
        } for col in self.columns]
        datatable_options = {
            'sDom': 'fFriltip',
            'aoColumns': aoColumns,
            'bFilter': True,
            'oLanguage': {
                'sSearch': self.options.get('search_label', _(u'Filter records:')),
                'oPaginate': {
                    'sPrevious': _(u'Previous'),
                    'sNext': _(u'Next'),
                },
                'sLengthMenu': _(u'Entries per page: _MENU_'),
                'sInfo': _(u'Showing _START_ to _END_ of _TOTAL_ entries'),
                'sInfoEmpty': _(u'Showing _START_ to _END_ of _TOTAL_ entries'),
                'sInfoFiltered': _(u'(filtered from _MAX_ total entries)'),
                'sAddAdvancedFilter': _(u'Add a filter'),
                'sZeroRecords': _(u'No matching records found'),
                'sEmptyTable': _(u'No matching records found'),
            },
            'bPaginate': self.paginate,
            'sPaginationType': "bootstrap",
            'bLengthChange': True,
            'iDisplayLength': 25,
            'bStateSave': self.save_state,
            'bProcessing': True,
            'bServerSide': True,
            'sAjaxSource': self.ajax_source,
        }
        if self.options.get('aaSorting', None):
            datatable_options['aaSorting'] = self.options.get('aaSorting')

        advanced_search_filters = []
        for c in self.search_criterions:
            if not c.has_form_filter:
                continue
            d = dict(
                name=c.name,
                label=text_type(c.label),
                type=c.form_filter_type,
                args=c.form_filter_args,
                unset=c.form_unset_value,)
            if c.has_form_default_value:
                d['defaultValue'] = c.form_default_value

            advanced_search_filters.append(d)

        if advanced_search_filters:
            datatable_options[
                'aoAdvancedSearchFilters'] = advanced_search_filters

        return Markup(
            render_template(
                'widgets/render_ajax_table.html',
                datatable_options=datatable_options,
                view=self))

    def render_line(self, entity):
        line = []
        for col in self.columns:
            if type(col) == str:
                column_name = col
            else:
                column_name = col['name']

            value = entity.display_value(column_name)
            cell = None
            has_custom_display = False
            # Manual massage.
            # 'display_fun' gets value *and* entity: useful to perform
            # specific markup based on other entity values.
            # 'display_fmt' is for simple value formatting (format_date from
            # babel for example)
            if value is None:
                value = ""
            elif 'display_fun' in col:
                has_custom_display = True
                value = col['display_fun'](entity, value)
            elif 'display_fmt' in col:
                value = col['display_fmt'](value)

            if has_custom_display:
                cell = value
            elif column_name == 'name':
                cell = Markup('<a href="%s">%s</a>' %
                              (url_for(entity), cgi.escape(value)))
            elif isinstance(value, Entity):
                cell = Markup('<a href="%s">%s</a>' %
                              (url_for(value), cgi.escape(value.name)))
            elif (isinstance(value, string_types) and
                  (value.startswith("http://") or value.startswith("www."))):
                cell = Markup(linkify_url(value))
            elif col.get('linkable'):
                cell = Markup('<a href="%s">%s</a>' %
                              (url_for(entity), cgi.escape(text_type(value))))
            else:
                cell = text_type(value)

            line.append(cell)
        return line


#
# Single object view
#
class SingleView(object):
    """View on a single object."""

    def __init__(self, form, *panels, **options):
        self.form = form
        self.panels = panels
        self.options = options

    def render(self, item, form, related_views=()):
        mapper = sa.orm.class_mapper(item.__class__)
        panels = []
        _to_skip = (None, False, 0, 0.0, '', u'-')

        for panel in self.panels:
            data = {}
            field_name_iter = (fn for row in panel.rows for fn in row)

            for name in field_name_iter:
                field = form._fields[name]
                if field.is_hidden:
                    continue

                value = field.data
                if not isinstance(field,
                                  FileField) and not field.flags.render_empty:
                    if value in _to_skip:
                        continue

                value = Markup(field.render_view(entity=item))
                if value == u'':
                    # related models may have [] as value, but we don't discard this type
                    # of value in order to let widget a chance to render something useful
                    # like an 'add model' button.
                    #
                    # if it renders an empty string, there's really no point in rendering
                    # a line for this empty field
                    continue

                label = self.label_for(field, mapper, name)
                data[name] = (label, value)

            if data:
                panels.append((panel, data))

        template = filter(bool, (self.options.get('view_template'),
                                 'widgets/render_single.html'))

        return Markup(
            render_template(
                template,
                view=self,
                related_views=related_views,
                csrf_token=csrf.field(),
                entity=item,
                panels=panels,
                form=form))

    def render_form(self, form, for_new=False, has_save_and_add_new=False):
        # Client-side rules for jQuery.validate
        # See: http://docs.jquery.com/Plugins/Validation/Methods#Validator
        rules = {}
        for field in form:
            rules_for_field = {}
            for validator in field.validators:
                rule_for_validator = getattr(validator, "rule", None)
                if rule_for_validator:
                    rules_for_field.update(rule_for_validator)
            if rules_for_field:
                rules[field.name] = rules_for_field
        if rules:
            rules = Markup(json.dumps(rules))
        else:
            rules = None

        template = filter(bool, (self.options.get('edit_template'),
                                 'widgets/render_for_edit.html'))

        return Markup(
            render_template(
                template,
                view=self,
                form=form,
                for_new=for_new,
                has_save_and_add_new=has_save_and_add_new,
                rules=rules))

    def label_for(self, field, mapper, name):
        label = field.label
        if label is None:
            try:
                info = mapper.c[name].info
                label = info['label']
            except (AttributeError, KeyError):
                pass

        if label is None:
            try:
                label = _(name)
            except KeyError:
                # i18n may be not initialized (in some unit tests for example)
                label = name

        return label


#
# Used to describe single entity views.
#
class Panel(object):
    """
    `Panel` and `Row` classes help implement a trivial internal DSL for
    specifying multi-column layouts in forms or object views.

    They are currently not really used, since we went with 1-column designs
    eventually.
    """

    def __init__(self, label=None, *rows):
        self.label = label
        self.rows = rows

    def __iter__(self):
        return iter(self.rows)

    def __getitem__(self, item):
        return self.rows[item]

    def __len__(self):
        return len(self.rows)


class Row(object):
    """
    `Panel` and `Row` classes help implement a trivial internal DSL for
    specifying multi-column layouts in forms or object views.

    They are currently not really used, since we went with 1-column designs
    eventually.
    """

    def __init__(self, *cols):
        self.cols = cols

    def __iter__(self):
        return iter(self.cols)

    def __getitem__(self, item):
        return self.cols[item]

    def __len__(self):
        return len(self.cols)


class ModelWidget(object):
    edit_template = 'widgets/model_widget_edit.html'
    view_template = 'widgets/model_widget_view.html'

    def __init__(self, edit_template=None, view_template=None):
        if edit_template is not None:
            self.edit_template = edit_template
        if view_template is not None:
            self.view_template = view_template

    def __call__(self, field, *args, **kwargs):
        return render_template(self.edit_template, form=field)

    def render_view(self, field, *args, **kwargs):
        _to_skip = (None, False, 0, 0.0, '', u'-')
        rows = []
        for f in field.form:
            if f.is_hidden:
                continue

            value = f.data
            if value in _to_skip and not f.flags.render_empty:
                continue

            value = Markup(f.render_view())
            if value == u'':
                # related models may have [] as value, but we don't discard this type
                # of value in order to let widget a chance to render something useful
                # like an 'add model' button.
                #
                # if it renders an empty string, there's really no point in rendering
                # a line for this empty field
                continue

            label = f.label
            rows.append((label, value))

        return render_template(self.view_template, field=field, rows=rows)


# Form field widgets ###########################################################
class TextInput(wtforms.widgets.TextInput):
    """Support pre and post icons.

    An Icon can be a plain string, or an instance of
    :class:`abilian.web.action.Icon`.
    """
    pre_icon = None
    post_icon = None

    def __init__(self,
                 input_type=None,
                 pre_icon=None,
                 post_icon=None,
                 *args,
                 **kwargs):
        super(TextInput, self).__init__(input_type, *args, **kwargs)

        if pre_icon is not None:
            self.pre_icon = pre_icon
        if post_icon is not None:
            self.post_icon = post_icon

    def __call__(self, field, *args, **kwargs):
        if not any((self.pre_icon, self.post_icon)):
            return super(TextInput, self).__call__(field, *args, **kwargs)

        kwargs.setdefault('type', self.input_type)
        if 'value' not in kwargs:
            kwargs['value'] = field._value()

        return Markup(
            render_template_string(
                u'''
            <div class="input-group input-group-type-{{ widget.typename }}">
            {%- if widget.pre_icon %}
              <div class="input-group-addon">{{ widget.pre_icon }}</div>
            {%- endif %}
              <input {{ params | safe}}>
            {%- if widget.post_icon %}
              <div class="input-group-addon">{{ widget.post_icon }}</div>
            {%- endif %}
            </div>
            ''',
                widget=self,
                params=self.html_params(
                    name=field.name, **kwargs)))

    @property
    def typename(self):
        return self.__class__.__name__.lower()


class TextArea(BaseTextArea):
    """
    Accepts "resizeable" parameter: "vertical", "horizontal", "both", None
    """
    _resizeable_valid = ("vertical", "horizontal", "both", None)
    resizeable = None
    rows = None

    def __init__(self, resizeable=None, rows=None, *args, **kwargs):
        BaseTextArea.__init__(self, *args, **kwargs)

        if resizeable not in self._resizeable_valid:
            raise ValueError(
                'Invalid value for resizeable: {}, valid values are: {!r}'
                ''.format(resizeable, self._resizeable_valid))
        if resizeable:
            self.resizeable = 'resizeable-' + resizeable
        else:
            self.resizeable = 'not-resizeable'

        if rows:
            self.rows = int(rows)

    def __call__(self, *args, **kwargs):
        if self.resizeable:
            css = kwargs.get('class_', '')
            kwargs['class_'] = css + ' ' + self.resizeable

        if self.rows and 'rows' not in kwargs:
            kwargs['rows'] = self.rows

        return super(TextArea, self).__call__(*args, **kwargs)


class FileInput(object):
    """
    Renders a file input.  Inspired from
    http://www.abeautifulsite.net/blog/2013/08/whipping-file-inputs-into-shape-with-bootstrap-3/
    """

    def __init__(self, template='widgets/file_input.html'):
        self.template = template

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs['name'] = field.name
        kwargs['type'] = 'file'
        kwargs['disabled'] = 'disabled'  # JS widget will activate it
        input_elem = u'<input {}>'.format(html_params(**kwargs))
        button_label = _(u'Add file') if 'multiple' in kwargs else _(u'Select file')

        existing = self.build_exisiting_files_list(field)
        uploads = self.build_uploads_list(field)

        if not field.multiple and uploads:
            # single file field: exising file replaced by new upload, don't show
            # existing
            existing = []
        else:
            for data in existing:
                # this might be a very big bytes object: in any case it will not be used
                # in widget's template, and during development it makes very large pages
                # due to debugtoolbar capturing template parameters
                del data['file']

        ctx = dict(
            id=field.id,
            field=field,
            widget=self,
            input=input_elem,
            button_label=button_label,
            existing=existing,
            uploaded=uploads)
        return Markup(render_template(self.template, **ctx))

    def build_exisiting_files_list(self, field):
        existing = []
        blob = None
        object_data = field.object_data

        if not object_data:
            return existing

        if not field.multiple:
            object_data = [object_data]
            blob = getattr(field, 'blob')

        for idx, data in enumerate(object_data):
            if data is not None:
                existing.append({
                    'file': data,
                    'size': len(bytes(data)),
                    'delete': idx in field.delete_files_index,
                })
                if hasattr(data, 'filename'):
                    existing[-1]['filename'] = data.filename
                elif blob and isinstance(blob, Blob):
                    existing[-1]['filename'] = blob.meta.get('filename', u'')

        return existing

    def build_uploads_list(self, field):
        uploads = current_app.extensions['uploads']
        uploaded = []

        for handle in field.upload_handles:
            file_ = uploads.get_file(current_user, handle)
            if file_ is None:
                continue
            meta = uploads.get_metadata(current_user, handle)
            uploaded.append({
                'file': file_,
                'handle': handle,
                'filename': meta.get('filename', handle),
                'size': file_.stat().st_size,
            })

        return uploaded


class ImageInput(FileInput):
    """
    An image widget with client-side preview. To show current image field
    data has to provide an attribute named `url`.
    """

    def __init__(
            self,
            template='widgets/image_input.html',
            width=120,
            height=120,
            resize_mode=image.CROP,
            valid_extensions=('jpg', 'jpeg', 'png'),):
        super(ImageInput, self).__init__(template=template)
        self.resize_mode = resize_mode
        self.valid_extensions = valid_extensions
        self.width, self.height = width, height

    def build_exisiting_files_list(self, field):
        existing = super(ImageInput, self).build_exisiting_files_list(field)
        for data in existing:
            value = data['file']
            if value:
                if hasattr(value, 'url'):
                    image_url = value.url
                else:
                    image_url = self.get_b64_thumb_url(
                        self.get_thumb(value, self.width, self.height))

                data['image_url'] = image_url

        return existing

    def build_uploads_list(self, field):
        uploaded = super(ImageInput, self).build_uploads_list(field)
        for data in uploaded:
            value = data['file']
            if value:
                if hasattr(value, 'url'):
                    image_url = value.url
                else:
                    with value.open('rb') as in_:
                        image_url = self.get_b64_thumb_url(
                            self.get_thumb(in_, self.width, self.height))

                data['image_url'] = image_url

        return uploaded

    def get_thumb(self, data, width, height):
        try:
            get_format(data)
        except IOError:
            return u''
        return image.resize(data, width, height, mode=self.resize_mode)

    def get_b64_thumb_url(self, img):
        try:
            fmt = image.get_format(img).lower()
        except IOError:
            return u''
        thumb = base64.b64encode(img)
        return u'data:image/{format};base64,{img}'.format(format=fmt, img=thumb)

    def render_view(self, field, **kwargs):
        data = field.data
        if not data:
            return u''
        try:
            get_format(data)
        except IOError:
            return u''

        width = kwargs.get('width', self.width)
        height = kwargs.get('heigth', self.height)

        thumb = self.get_thumb(data, width, height)
        width, height = image.get_size(thumb)

        tmpl = u'<img src="{{ url }}" width="{{ width }}" height="{{ height }}" />'
        return render_template_string(
            tmpl, url=self.get_b64_thumb_url(thumb), width=width, height=height)


class Chosen(Select):
    """
    Extends the Select widget using the Chosen jQuery plugin.
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        html = [
            u'<select %s class="chzn-select">' % html_params(
                name=field.name, **kwargs)
        ]
        for val, label, selected in field.iter_choices():
            html.append(self.render_option(val, label, selected))
        html.append(u'</select>')
        return HTMLString(u''.join(html))

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        options = dict(kwargs, value=value)
        if selected:
            options['selected'] = True
        return HTMLString(
            u'<option %s>%s</option>' %
            (html_params(**options), cgi.escape(text_type(label))))


class TagInput(Input):
    """
    Extends the Select widget using the Chosen jQuery plugin.
    """

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        kwargs['class_'] = "tagbox"
        if 'value' not in kwargs:
            kwargs['value'] = field._value()

        return HTMLString(u'<input %s>' % self.html_params(
            name=field.name, **kwargs))


class DateInput(Input):
    """
    Renders date inputs using the fancy Bootstrap Datepicker:
    https://github.com/eternicode/bootstrap-datepicker
    """
    input_type = 'date'

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        field_id = kwargs.pop('id')
        kwargs.setdefault('name', field.name)
        field_name = kwargs.pop('name')
        kwargs.pop('type', None)
        value = kwargs.pop('value', None)
        if value is None:
            value = field._value()
        if not value:
            value = ''

        date_fmt = kwargs.pop('format', None)
        if date_fmt is not None:
            date_fmt = date_fmt.replace("%", "") \
                .replace("d", "dd") \
                .replace("m", "mm") \
                .replace("Y", "yyyy")
        else:
            date_fmt = get_locale().date_formats['short'].pattern
            date_fmt = babel2datepicker(date_fmt)
            date_fmt = date_fmt.replace('M', 'm')  # force numerical months

        attributes = {
            'class': "input-group date",
            'data-provide': 'datepicker',
            'data-date': value,
            'data-date-format': date_fmt,
            'data-date-autoclose': 'true',
        }

        s = u'<div {}>\n'.format(html_params(**attributes))

        s += u'  <input size="13" type="text" class="form-control" {} />\n'.format(
            html_params(
                name=field_name, id=field_id, value=value, **kwargs))
        s += u'  <span class="input-group-addon"><i class="fa fa-calendar"></i></span>\n'
        s += u'</div>\n'
        return Markup(s)

    def render_view(self, field, **kwargs):
        return format_date(field.data) if field.data else u''


class TimeInput(Input):
    """
    Renders time inputs using boostrap timepicker:
    https://github.com/jdewit/bootstrap-timepicker
    """
    template = 'widgets/timepicker.html'

    def __init__(self,
                 template=None,
                 widget_mode='dropdown',
                 h24_mode=True,
                 minuteStep=1,
                 showSeconds=False,
                 secondStep=1,
                 showInputs=False,
                 disableFocus=False,
                 modalBackdrop=False):
        Input.__init__(self)

        if template is not None:
            self.template = template

        self.widget_mode = widget_mode
        self.h24_mode = h24_mode
        self.minuteStep = minuteStep
        self.showSeconds = showSeconds
        self.secondStep = secondStep
        self.showInputs = showInputs
        self.disableFocus = disableFocus
        self.modalBackdrop = modalBackdrop
        self.strptime = u'%H:%M' if self.h24_mode else u'%I:%M %p'

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        field_id = kwargs.pop('id')
        value = kwargs.pop('value', None)
        if value is None:
            value = field._value()
        if not value:
            value = ''

        time_fmt = get_locale().time_formats['short'].format
        is_h12 = ('%(h)s' in time_fmt or '%(K)s' in time_fmt)

        input_params = {
            'data-template': self.widget_mode,
            'data-show-meridian': is_h12,
            'data-minute-step': self.minuteStep,
            'data-show-seconds': self.showSeconds,
            'data-second-step': self.secondStep,
            'data-show-inputs': self.showInputs,
            'data-disable-focus': self.disableFocus,
            'data-modal-backdrop': self.modalBackdrop
        }

        input_params = {
            k: Markup(json.dumps(v))
            for k, v in input_params.items()
        }

        ctx = dict(
            id=field_id,
            value=value,
            field=field,
            required=False,
            timepicker_attributes=input_params)
        return Markup(render_template(self.template, **ctx))


class DateTimeInput(object):
    """
    if corresponding field.raw_data exist it is used
    to initialize default date & time (raw_data example: ["10/10/16 | 09:00"])
    """

    def __init__(self):
        self.date = DateInput()
        self.time = TimeInput()

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        field_id = kwargs.pop('id')
        kwargs.setdefault('name', field.name)
        field_name = kwargs.pop('name')

        locale = get_locale()
        date_fmt = locale.date_formats['short'].pattern
        date_fmt = babel2datetime(date_fmt)
        date_fmt = date_fmt.replace('%B', '%m').replace(
            '%b', '%m')  # force numerical months
        time_fmt = u'%H:%M'

        value = kwargs.pop('value', None)
        if value is None:
            if field.data:
                value = field.data
                date_value = value.strftime(date_fmt) if value else u''
                time_value = value.strftime(time_fmt) if value else u''
            elif field.raw_data:
                value = field.raw_data  # example "10/10/16 | 09:00"
                value = u''.join(value)
                value = value.split(u'|')

                try:
                    date_value = datetime.strptime(value[0].strip(), date_fmt)
                except (ValueError, IndexError):
                    date_value = u''

                try:
                    time_value = value[1].strip()  # example  "09:00"
                except IndexError:
                    time_value = u''

            else:
                date_value = u''
                time_value = u''

        return Markup(u'<div class="form-inline">\n'
                      u'<input class="datetimepicker" type="hidden" id="{id}" name="{name}" '
                      u'value="{date} | {time}" />\n'
                      u''.format(id=field_id,
                                 name=field_name,
                                 date=date_value,
                                 time=time_value)) \
               + self.date(field,
                           id=field_id + '-date',
                           name=field_name + '-date',
                           value=date_value) \
               + self.time(field,
                           id=field_id + '-time',
                           name=field_name + '-time',
                           value=time_value) \
               + Markup(u'</div>')


class DefaultViewWidget(object):

    def render_view(self, field, **kwargs):
        value = field.object_data
        if isinstance(value, string_types):
            return text2html(value)
        else:
            # [], None and other must be rendered using empty string
            return text_type(value or u'')


class BooleanWidget(wtforms.widgets.CheckboxInput):
    # valid data-* options when using boostrap-switch
    _ON_OFF_VALID_OPTIONS = frozenset(
        ('animate', 'indeterminate', 'inverse', 'radio-all-off', 'on-color',
         'off-color', 'on-text', 'off-text', 'label-text', 'handle-width',
         'label-width', 'base-class', 'wrapper-class'))

    def __init__(self, *args, **kwargs):
        self.on_off_mode = kwargs.pop('on_off_mode', False)
        self.on_off_options = {}
        on_off_options = kwargs.pop('on_off_options', {})
        for k, v in on_off_options.items():
            if k not in self._ON_OFF_VALID_OPTIONS:
                continue
            self.on_off_options['data-' + k] = v

        if self.on_off_mode:
            self.on_off_options['data-toggle'] = u'on-off'

        super(BooleanWidget, self).__init__(*args, **kwargs)

    def __call__(self, field, **kwargs):
        if self.on_off_mode:
            kwargs.update(self.on_off_options)

        return super(BooleanWidget, self).__call__(field, **kwargs)

    def render_view(self, field, **kwargs):
        return u'\u2713' if field.object_data else u''  # Text_type "Check mark"


class PasswordInput(BasePasswordInput):
    """
    Supports setting 'autocomplete' at instanciation time.
    """

    def __init__(self, *args, **kwargs):
        self.autocomplete = kwargs.pop('autocomplete', None)
        BasePasswordInput.__init__(self, *args, **kwargs)

    def __call__(self, field, **kwargs):
        kwargs.setdefault('autocomplete', self.autocomplete)
        return BasePasswordInput.__call__(self, field, **kwargs)

    def render_view(self, field, **kwargs):
        return u'*****'


class FloatWidget(wtforms.widgets.TextInput):
    """ In view mode, format float number to 'precision' decimal
    """

    def __init__(self, precision=None):
        self.precision = precision
        if precision is not None:
            self._fmt = '.{:d}f'.format(precision)

    def render_view(self, field, **kwargs):
        data = field.object_data
        if data is None:
            return u''

        return format(data, self._fmt)


class DateWidget(wtforms.widgets.TextInput):

    def render_view(self, field, **kwargs):
        return (format_date(field.object_data) if field.object_data else u'')


class DateTimeWidget(DateWidget):

    def render_view(self, field, **kwargs):
        return (format_datetime(field.object_data)
                if field.object_data else u'')


class EntityWidget(object):

    def render_view(self, field, **kwargs):
        objs = field.object_data
        if not field.multiple:
            objs = [objs]
        return u', '.join(u'<a href="{}">{}</a>'.format(
            url_for(o), cgi.escape(o.name)) for o in objs if o)


class HoursWidget(TextInput):
    """ Widget used to show / enter hours.
    Currently hardcoded to heure(s)
    """
    post_icon = _l(u'hour(s)')
    input_type = 'number'

    def render_view(self, field, **kwargs):
        val = field.object_data
        unit = u'h'

        if val is None:
            return u''

        # \u00A0: non-breakable whitespace
        return u'{value}\u00A0{unit}'.format(value=val, unit=unit)


class MoneyWidget(TextInput):
    """Widget used to show / enter money amount.

    Currently hardcoded to € / k€.
    """
    post_icon = u'€'
    input_type = 'number'

    def render_view(self, field, **kwargs):
        val = field.object_data
        unit = u'€'

        if val is None:
            return u''

        if val > 1000:
            unit = u'k€'
            val = int(round(val / 1000.0))

        # `format_currency()` is not used since it display numbers with cents
        # units, which we don't want
        #
        # \u00A0: non-breakable whitespace
        return u'{value}\u00A0{unit}'.format(
            value=format_number(val), unit=unit)


class EmailWidget(TextInput):
    pre_icon = u'@'

    def render_view(self, field, **kwargs):
        links = u''
        if isinstance(field, wtforms.fields.FieldList):
            for entry in field.entries:
                link = bleach.linkify(entry.data, parse_email=True)
                if link:
                    links = links + u' {}&nbsp;<i class="fa fa-envelope"></i><br>'.format(
                        link)
        else:
            link = bleach.linkify(field.object_data, parse_email=True)
            if link:
                links = u'{}&nbsp;<i class="fa fa-envelope"></i>'.format(link)
        return links


class URLWidget(object):

    def render_view(self, field, **kwargs):
        return (linkify_url(field.object_data) if field.object_data else u'')


class RichTextWidget(object):
    template = 'widgets/richtext.html'
    allowed_tags = {
        'a': {
            'href': True,
            'title': True
        },
        'abbr': {
            'title': True
        },
        'acronym': {
            'title': True
        },
        'b': True,
        'blockquote': True,
        'br': True,
        'code': True,
        'em': True,
        'h1': True,
        'h2': True,
        'h3': True,
        'h4': True,
        'h5': True,
        'h6': True,
        'i': True,
        'img': {
            'src': True
        },
        'li': True,
        'ol': True,
        'strong': True,
        'ul': True,
        'p': True,
        'u': True
    }

    def __init__(self, allowed_tags=None, template=None):
        if allowed_tags is not None:
            self.allowed_tags = allowed_tags
        if template is not None:
            self.template = template

    def __call__(self, field, **kwargs):
        value = kwargs.pop('value') if 'value' in kwargs else field._value()
        kwargs.setdefault('allowed_tags', self.allowed_tags)
        return render_template(
            self.template, field=field, value=value, kw=kwargs)


class ListWidget(wtforms.widgets.ListWidget):
    """ display field label is optionnal
    """

    def __init__(self, html_tag='ul', prefix_label=True, show_label=True):
        wtforms.widgets.ListWidget.__init__(self, html_tag, prefix_label)
        self.show_label = show_label

    def __call__(self, field, **kwargs):
        if self.show_label:
            return super(ListWidget, self).__call__(field, **kwargs)

        kwargs.setdefault('id', field.id)
        html = [
            u'<%s %s>' % (self.html_tag, wtforms.widgets.html_params(**kwargs))
        ]
        for subfield in field:
            html.append(u'<li>{}</li>'.format(subfield()))

        html.append(u'</%s>' % self.html_tag)
        return wtforms.widgets.HTMLString(''.join(html))

    def render_view(self, field, **kwargs):
        data = field.data
        is_empty = data == [] if field.multiple else data is None

        if not is_empty:
            data = ([
                label for v, label, checked in field.iter_choices() if checked
            ] if hasattr(field, 'iter_choices') and callable(field.iter_choices)
                    else field.object_data)
        else:
            data = []

        tpl = '''{%- for obj in data %}
              <span class="badge">{{ obj }}</span>
              {%- endfor %}'''
        return Markup(render_template_string(tpl, data=data))


class FieldListWidget(object):
    """For list of Fields (using <tr><td>)
    """
    view_template = 'widgets/fieldlist_view.html'
    template = 'widgets/fieldlist.html'

    def __init__(self, template=None, view_template=None):
        if template is not None:
            self.template = template
        if view_template is not None:
            self.view_template = view_template

    def __call__(self, field, **kwargs):
        assert isinstance(field, wtforms.fields.FieldList)
        return Markup(render_template(self.template, field=field))

    def render_view(self, field, **kwargs):
        assert isinstance(field, wtforms.fields.FieldList)
        value = field.object_data
        if not value:
            return ''
        return Markup(render_template(self.view_template, field=field))


class TabularFieldListWidget(object):
    """For list of formfields

    2 templates are available:

    * widgets/tabular_fieldlist_widget.html (default):
      Show sub-forms as a table, one row of inputs per model
    * widgets/model_fieldlist.html:
      Show sub-forms as a list of forms
    """

    def __init__(self, template='widgets/tabular_fieldlist_widget.html'):
        self.template = template

    def __call__(self, field, **kwargs):
        assert isinstance(field, wtforms.fields.FieldList)
        labels = None

        if len(field):
            assert isinstance(field[0], wtforms.fields.FormField)
            field_names = [f.short_name for f in field[0] if not f.is_hidden]
            data_type = field.entries[0].__class__.__name__ + 'Data'
            Data = namedtuple(data_type, field_names)
            labels = Data(*[f.label for f in field[0] if not f.is_hidden])

        return Markup(
            render_template(
                self.template, labels=labels, field=field))


class ModelListWidget(object):

    def __init__(self, template='widgets/horizontal_table.html'):
        self.template = template

    def render_view(self, field, **kwargs):
        assert isinstance(field, ModelFieldList)
        value = field.object_data
        if not value:
            return render_template(
                self.template, field=field, labels=(), rows=(), **kwargs)

        field_names = field._field_names
        labels = field._field_labels
        data_type = field.entries[0].object_data.__class__.__name__ + 'Data'
        Data = namedtuple(data_type, field_names)
        labels = Data(*labels)

        rows = []
        for entry in field.entries:
            row = []
            for f in filter(lambda f: not f.is_hidden, entry.form):
                row.append(Markup(f.render_view()))

            rows.append(Data(*row))

        rendered = render_template(
            self.template, field=field, labels=labels, rows=rows, **kwargs)
        return rendered


#
# Selection widget.
#
class Select2(Select):
    """
    Transforms a Select widget into a Select2 widget. Depends on global JS code.
    """
    unescape_html = False

    def __init__(self, unescape_html=False, js_init='select2', *args, **kwargs):
        super(Select2, self).__init__(*args, **kwargs)
        self.js_init = js_init

        if unescape_html:
            self.unescape_html = True

    def __call__(self, field, *args, **kwargs):
        # 'placeholder' option presence is required for 'allowClear'
        params = {'placeholder': u''}
        if self.unescape_html:
            params['makeHtml'] = True
        if not field.flags.required:
            params['allowClear'] = True

        css_class = kwargs.setdefault('class_', u'')
        if 'js-widget' not in css_class:
            css_class += u' js-widget'
            kwargs['class_'] = css_class

        kwargs.setdefault('data-init-with', self.js_init)
        kwargs['data-init-params'] = json.dumps(params)
        return Select.__call__(self, field, *args, **kwargs)

    def render_view(self, field, **kwargs):
        labels = [
            text_type(label) for v, label, checked in field.iter_choices()
            if checked
        ]
        return u'; '.join(labels)

    @classmethod
    def render_option(cls, value, label, selected, **kwargs):
        if value is None:
            return HTMLString('<option></option>')
        return Select.render_option(value, label, selected, **kwargs)


class Select2Ajax(object):
    """Ad-hoc select widget based on Select2.

    The code below is probably very fragile, since it depends on the internal
    structure of a Select2 widget.

    :param format_result: `formatResult` arg of Select2. Must be a valid
    javascript reference (like `Abilian.my_format_function`)

    :param format_selection: like `format_result`, but for Select2's
    `formatSelection`

    :param values_builder: an optional function, which given a data iterable of
    values, returns a list of dict items suitable for widget initial data;
    generally needed when using custom format_result/format_selection.
    """

    def __init__(self,
                 template='widgets/select2ajax.html',
                 multiple=False,
                 format_result=None,
                 format_selection=None,
                 values_builder=None):
        self.template = template
        self.multiple = multiple
        self.values_builder = (
            values_builder
            if callable(values_builder)
            else lambda data: [{'id': o.id, 'text': o.name} for o in data if o]
        )
        self.s2_params = dict(multiple=self.multiple)

        if format_result:
            self.s2_params['formatResult'] = format_result
        if format_selection:
            self.s2_params['formatSelection'] = format_selection

    def process_formdata(self, valuelist):
        """
        field helper: as of select2 3.x, multiple values are passed as a single
        string.
        """
        if self.multiple:
            valuelist = valuelist[0].split(u',')
        return valuelist

    def __call__(self, field, **kwargs):
        """
        Render widget
        """
        if self.multiple:
            kwargs['multiple'] = True

        css_class = kwargs.setdefault('class_', u'')
        if 'class' in kwargs:
            css_class += kwargs.pop('class', u'')
            kwargs['class_'] = css_class

        if 'js-widget' not in css_class:
            css_class += u' js-widget'
            kwargs['class_'] = css_class

        s2_params = {}
        s2_params.update(self.s2_params)

        if field.ajax_source:
            s2_params['ajax'] = {'url': text_type(field.ajax_source)}

        s2_params['placeholder'] = text_type(field.label.text)

        if not field.flags.required:
            s2_params['allowClear'] = True

        data = field.data
        if not self.multiple:
            data = [data]

        values = self.values_builder(data)
        input_value = u','.join(text_type(o.id) for o in data if o)
        data_node_id = None

        json_data = {}
        if values:
            json_data['values'] = values
            data_node_id = s2_params['dataNodeId'] = field.id + '-json'

        kwargs['data-init-with'] = 'select2ajax'
        kwargs['data-init-params'] = json.dumps(s2_params)

        extra_args = Markup(html_params(**kwargs))

        ctx = dict(
            field=field,
            name=field.name,
            id=field.id,
            input_value=input_value,
            json_data=json_data,
            required=not field.allow_blank,
            data_node_id=data_node_id,
            extra_args=extra_args)
        return Markup(render_template(self.template, **ctx))
