# coding=utf-8

from flask import Flask
from flask.ext.testing import TestCase

from abilian.web.action import actions, Action
from abilian.testing import BaseTestCase


BASIC = Action('cat_1', 'basic', 'Basic Action', url='http://some.where')
CONDITIONAL = Action('cat_1', 'conditional', 'Conditional Action',
                     url='http://condition.al',
                     condition=lambda ctx: ctx['show_all'])
OTHER_CAT = Action('cat_2', 'other', 'Other Action',
                   url=lambda ctx: 'http://count?%d' % len(ctx))


class TestActions(BaseTestCase):
  """ Test Action and ActionRegistry.
  """
  def setUp(self):
    BaseTestCase.setUp(self)
    actions.init_app(self.app)
    actions.register(BASIC, CONDITIONAL, OTHER_CAT)
    actions._before_request()
    actions.context['show_all'] = True

  def test_installed(self):
    assert actions.installed() # test current_app (==self.app)
    assert actions.installed(self.app)
    assert not actions.installed(Flask('dummyapp'))

  def test_actions(self):
    all_actions = actions.actions()
    assert 'cat_1' in all_actions
    assert 'cat_2' in all_actions
    assert all_actions['cat_1'] == [BASIC, CONDITIONAL]
    assert all_actions['cat_2'] == [OTHER_CAT]

  def test_for_category(self):
    cat_1 = actions.for_category('cat_1')
    assert cat_1 == [BASIC, CONDITIONAL]
    cat_2 = actions.for_category('cat_2')
    assert cat_2 == [OTHER_CAT]

  def test_conditional(self):
    actions.context['show_all'] = False
    assert actions.for_category('cat_1') == [BASIC]

  def test_action_url_from_context(self):
    url = OTHER_CAT.url({'for': 'having', '2 keys': 'in context'})
    assert url == 'http://count?2'
    assert OTHER_CAT.url({}) == 'http://count?0'
