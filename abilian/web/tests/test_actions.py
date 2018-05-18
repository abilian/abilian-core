# coding=utf-8

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from flask import Flask
from jinja2 import Markup

from abilian.web.action import Action, Glyphicon, StaticIcon, actions

BASIC = Action("cat_1", "basic", "Basic Action", url="http://some.where", icon="ok")
CONDITIONAL = Action(
    "cat_1",
    "conditional",
    "Conditional Action",
    url="http://condition.al",
    condition=lambda ctx: ctx["show_all"],
    icon=Glyphicon("hand-right"),
    button="warning",
)

OTHER_CAT = Action(
    "cat_2:sub",
    "other",
    "Other Action",
    url=lambda ctx: "http://count?{}".format(len(ctx)),
    icon=StaticIcon("icons/other.png", size=14),
    css="custom-class",
)

ALL_ACTIONS = (BASIC, CONDITIONAL, OTHER_CAT)


def setup_actions(app):
    actions.init_app(app)
    for a in ALL_ACTIONS:
        a.enabled = True
    actions.register(*ALL_ACTIONS)
    actions._init_context(app)
    actions.context["show_all"] = True


def test_installed(app_context):
    assert actions.installed()  # test current_app (==self.app)
    assert actions.installed(app_context.app)
    assert not actions.installed(Flask("dummyapp"))


def test_actions(app_context):
    setup_actions(app_context.app)

    all_actions = actions.actions()
    assert "cat_1" in all_actions
    assert "cat_2:sub" in all_actions
    assert all_actions["cat_1"] == [BASIC, CONDITIONAL]
    assert all_actions["cat_2:sub"] == [OTHER_CAT]


def test_for_category(app_context):
    setup_actions(app_context.app)

    cat_1 = actions.for_category("cat_1")
    assert cat_1 == [BASIC, CONDITIONAL]

    cat_2 = actions.for_category("cat_2:sub")
    assert cat_2 == [OTHER_CAT]


def test_conditional(app_context):
    setup_actions(app_context.app)

    actions.context["show_all"] = False
    assert actions.for_category("cat_1") == [BASIC]


def test_enabled(app_context):
    setup_actions(app_context.app)

    assert CONDITIONAL.enabled
    assert actions.for_category("cat_1") == [BASIC, CONDITIONAL]

    CONDITIONAL.enabled = False
    assert not CONDITIONAL.enabled
    assert actions.for_category("cat_1") == [BASIC]


def test_action_url_from_context():
    url = OTHER_CAT.url({"for": "having", "2 keys": "in context"})
    assert url == "http://count?2"
    assert OTHER_CAT.url({}) == "http://count?0"


def test_render(app, test_request_context):
    setup_actions(app)

    assert BASIC.render() == Markup(
        '<a class="action action-cat_1 action-cat_1-basic" '
        'href="http://some.where">'
        '<i class="glyphicon glyphicon-ok"></i> Basic Action</a>'
    )

    assert CONDITIONAL.render() == Markup(
        '<a class="action action-cat_1 action-cat_1-conditional '
        'btn btn-warning" href="http://condition.al">'
        '<i class="glyphicon glyphicon-hand-right"></i> '
        "Conditional Action</a>"
    )

    assert OTHER_CAT.render() == Markup(
        '<a class="action action-cat_2-sub action-cat_2-sub-other '
        'custom-class" href="http://count?3">'
        '<img src="/static/icons/other.png" width="14" height="14" /> '
        "Other Action</a>"
    )
