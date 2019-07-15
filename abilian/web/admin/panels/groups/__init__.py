""""""
from typing import Callable

from flask import render_template

from abilian.i18n import _, _l
from abilian.web.admin.panel import AdminPanel
from abilian.web.util import url_for

from . import views


class GroupsPanel(AdminPanel):
    """Group administration panel."""

    id = "groups"
    label = _l("Groups")
    icon = "grain"

    def install_additional_rules(self, add_url_rule: Callable) -> None:
        add_url_rule("/groups", view_func=views.JsonGroupsList.as_view("json_list"))
        add_url_rule("/new", view_func=views.GroupCreate.as_view("new"))
        add_url_rule("/<int:group_id>/", view_func=views.GroupView.as_view("group"))
        add_url_rule(
            "/<int:group_id>/edit",
            view_func=views.GroupEdit.as_view(
                "group_edit", view_endpoint=".groups_group"
            ),
        )

    def get(self):
        # FIXME: use widgets.AjaxMainTableView instead
        datatable_options = {
            "sDom": "lfFrtip",
            "aaSorting": [[0, "asc"]],
            "aoColumns": [
                {"asSorting": ["asc", "desc"]},
                {"bSortable": False},
                {"bSortable": False},
            ],
            "bFilter": True,
            "oLanguage": {
                "sSearch": _("Filter records:"),
                "sPrevious": _("Previous"),
                "sNext": _("Next"),
                "sInfo": _("Showing _START_ to _END_ of _TOTAL_ entries"),
                "sInfoFiltered": _("(filtered from _MAX_ total entries)"),
                "sAddAdvancedFilter": _("Add a filter"),
            },
            "bStateSave": False,
            "bPaginate": True,
            "sPaginationType": "bootstrap",
            "bLengthChange": False,
            "iDisplayLength": 30,
            "bProcessing": True,
            "bServerSide": True,
            "sAjaxSource": url_for(".groups_json_list"),
        }

        return render_template(
            "admin/groups.html", next=next, datatable_options=datatable_options
        )
