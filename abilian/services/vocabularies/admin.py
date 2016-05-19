# coding=utf-8
"""
Admin panel for vocabularies
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from flask import current_app, g, redirect, render_template, request

from abilian.i18n import _, _l
from abilian.web import url_for, views
from abilian.web.action import Glyphicon
from abilian.web.admin import AdminPanel
from abilian.web.nav import BreadcrumbItem

from .forms import EditForm

_MARKER = object()


class ViewBase(object):
    title = _l(u'Vocabulary entry')
    base_template = "admin/_base.html"
    Form = EditForm
    Model = None

    def prepare_args(self, args, kwargs):
        if self.Model is None:
            self.Model = kwargs.get('Model')
            if hasattr(self.Model, '__form__'):
                self.Form = getattr(self.Model, '__form__')
        return args, kwargs

    def index_url(self):
        return url_for('.vocabularies')


class Edit(ViewBase, views.ObjectEdit):

    def prepare_args(self, args, kwargs):
        args, kwargs = ViewBase.prepare_args(self, args, kwargs)
        return views.ObjectEdit.prepare_args(self, args, kwargs)

    def view_url(self):
        return url_for('.vocabularies_model',
                       group=self.Model.Meta.group or '_',
                       Model=self.Model.Meta.name,)


class Create(views.ObjectCreate, Edit):

    def init_object(self, args, kwargs):
        args, kwargs = super(Create, self).init_object(args, kwargs)
        self.obj.active = True  # do this because default value seems ignored?
        return args, kwargs


class Delete(ViewBase, views.ObjectDelete):
    pass


class VocabularyPanel(AdminPanel):
    """
    Vocabularies administration
    """
    id = 'vocabularies'
    label = _l(u'Vocabularies')
    icon = 'list'

    @property
    def svc(self):
        return current_app.services['vocabularies']

    def voc_edit_url(self, item):
        return url_for('.' + self.id + '_edit',
                       group=item.Meta.group or u'_',
                       Model=item.Meta.name,
                       object_id=item.id)

    def get(self):
        svc = self.svc
        return render_template('admin/vocabularies.html',
                               service=svc,
                               url_for_voc_edit=self.voc_edit_url,
                               icon_checked=Glyphicon('check'),
                               vocabularies=svc.grouped_vocabularies,)

    def post(self):
        data = request.form
        group = data.get('group', u'').strip()
        Model = data.get('Model', u'').strip()
        return_to = data.get('return_to')
        return_endpoint = '.vocabularies'
        return_args = {}

        if return_to not in (None, 'group', 'model'):
            return_to = None

        def do_return():
            return redirect(url_for(return_endpoint, **return_args))

        if not Model:
            return do_return()

        if not group or group == u'_':
            # default group
            group = None

        svc = self.svc
        Model = svc.get_vocabulary(name=Model, group=group)
        if not Model:
            return do_return()

        if return_to is not None:
            return_endpoint += '_' + return_to

        if return_to == 'group':
            return_args['group'] = group or '_'
        elif return_to == 'model':
            return_args['group'] = Model.Meta.group or '_'
            return_args['Model'] = Model.Meta.name

        if 'up' in data:
            cmp_op = Model.position.__lt__
            cmp_order = Model.position.desc()
            object_id = int(data.get('up'))
        elif 'down' in data:
            cmp_op = Model.position.__gt__
            cmp_order = Model.position.asc()
            object_id = int(data.get('down'))
        else:
            return do_return()

        session = current_app.db.session()
        query = Model.query.with_lockmode('update')
        item = query.get(object_id)
        other = query \
            .filter(cmp_op(item.position)) \
            .order_by(cmp_order) \
            .first()

        if other is not None:
            # switch positions
            # we have to work around unique constraint on 'position', since we cannot
            # write new positions simultaneously
            # "-1" is added to avoid breaking when one position==0
            pos = other.position
            other.position = -item.position - 1
            item.position = -pos - 1
            session.flush()
            item.position = pos
            other.position = -other.position - 1
            session.commit()

        return do_return()

    def group_view(self, group):
        groups = self.svc.grouped_vocabularies
        vocabularies = groups.get(group)

        return render_template('admin/vocabularies.html',
                               service=self.svc,
                               url_for_voc_edit=self.voc_edit_url,
                               icon_checked=Glyphicon('check'),
                               vocabularies={group: vocabularies},
                               edit_return_to='group')

    def model_view(self, Model, group=None):
        return render_template('admin/vocabularies.html',
                               service=self.svc,
                               url_for_voc_edit=self.voc_edit_url,
                               icon_checked=Glyphicon('check'),
                               vocabularies={Model.Meta.group: [Model]},
                               edit_return_to='model')

    def install_additional_rules(self, add_url_rule):
        panel_endpoint = '.' + self.id
        group_base = '/<string:group>/'
        add_url_rule(group_base, endpoint='group', view_func=self.group_view)
        # models
        base = group_base + '<string:Model>/'
        add_url_rule(base, endpoint='model', view_func=self.model_view)

        edit_view = Edit.as_view(b'edit', view_endpoint=panel_endpoint)
        add_url_rule(base + '<int:object_id>', view_func=edit_view)
        add_url_rule(base + 'new',
                     view_func=Create.as_view(b'new',
                                              view_endpoint=panel_endpoint))

    def url_value_preprocess(self, endpoint, view_args):
        Model = view_args.pop('Model', None)
        group = view_args.pop('group', _MARKER)

        if group == u'_':
            # "General" group
            group = None

        if group is not _MARKER:
            view_args['group'] = group

        if Model is not None:
            svc = self.svc
            Model = svc.get_vocabulary(name=Model, group=group)
            g.breadcrumb.append(BreadcrumbItem(
                label=Model.Meta.group if group else _('Global'),
                url=url_for('.vocabularies_group', group=group or u'_'),
            ))
            g.breadcrumb.append(
                BreadcrumbItem(label=Model.Meta.label,
                               url=url_for('.vocabularies_model',
                                           group=group or u'_',
                                           Model=Model.Meta.name),))
            view_args['Model'] = Model
