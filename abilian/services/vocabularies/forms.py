# coding=utf-8
"""
"""
from __future__ import absolute_import

from wtforms.fields import BooleanField, IntegerField, StringField
from wtforms.widgets import HiddenInput

from abilian.i18n import _l
from abilian.web.forms import ModelForm
from abilian.web.forms.validators import required
from abilian.web.forms.filters import strip


class EditForm(ModelForm):
  label = StringField(_l(u'Label'), filters=(strip,), validators=[required()])
  default = BooleanField(_l(u'Default'), default=False)
  active = BooleanField(_l(u'Active'), default=True)


class ListEditForm(EditForm):
  id = IntegerField(widget=HiddenInput())
  position = IntegerField(widget=HiddenInput())
