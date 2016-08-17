# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

from flask import render_template

from abilian.i18n import _, _l
from abilian.web.util import url_for
from abilian.web.admin.panel import AdminPanel

from . import views


class UsersPanel(AdminPanel):
    """
    User administration panel.
    """
    id = 'users'
    label = _l(u'Users')
    icon = 'user'

    def install_additional_rules(self, add_url_rule):
        add_url_rule(
            '/users', view_func=views.JsonUsersList.as_view('json_list'))
        add_url_rule('/new', view_func=views.UserCreate.as_view('new'))
        add_url_rule('/<int:user_id>', view_func=views.UserEdit.as_view('user'))

    def get(self):
        # FIXME: use widgets.AjaxMainTableView instead
        datatable_options = {
            'sDom': 'lfFritip',
            'aaSorting': [
                [1, u'asc'],
            ],
            'aoColumns': [
                dict(bSortable=False),
                dict(asSorting=['asc', 'desc']),
                dict(asSorting=['asc', 'desc']),
                dict(bSortable=False),
                dict(bSortable=False),
                dict(bSortable=False),
                dict(asSorting=['asc', 'desc']),
            ],
            'bFilter': True,
            'oLanguage': {
                'sSearch': _("Filter records:"),
                'sPrevious': _("Previous"),
                'sNext': _("Next"),
                'sInfo': _("Showing _START_ to _END_ of _TOTAL_ entries"),
                'sInfoFiltered': _("(filtered from _MAX_ total entries)"),
                'sAddAdvancedFilter': _("Add a filter"),
            },
            'bStateSave': False,
            'bPaginate': True,
            'sPaginationType': "bootstrap",
            'bLengthChange': False,
            'iDisplayLength': 30,
            'bProcessing': True,
            'bServerSide': True,
            'sAjaxSource': url_for('.users_json_list'),
        }

        return render_template(
            'admin/users.html', next=next, datatable_options=datatable_options)
