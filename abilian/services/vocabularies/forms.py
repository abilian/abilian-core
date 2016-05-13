# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import bleach
from wtforms.fields import BooleanField, IntegerField, StringField
from wtforms.widgets import HiddenInput

from abilian.i18n import _l
from abilian.web.forms import ModelForm
from abilian.web.forms.filters import strip
from abilian.web.forms.validators import required

ALLOWED_TAGS = ['b', 'i', 'del', 's', 'u', 'small', 'strong', 'em',]
ALLOWED_ATTRIBUTES = {}


class EditForm(ModelForm):
    label = StringField(
        _l(u'Label'),
        description=_l(u'allowed tags: %(tags)s',
                       tags=u', '.join(ALLOWED_TAGS)),
        filters=(strip,),
        validators=[required()])
    default = BooleanField(_l(u'Default'), default=False)
    active = BooleanField(_l(u'Active'), default=True)

    def validate_label(self, field):
        field.data = bleach.clean(field.data,
                                  tags=ALLOWED_TAGS,
                                  attributes=ALLOWED_ATTRIBUTES,
                                  strip=True)


class ListEditForm(EditForm):
    id = IntegerField(widget=HiddenInput())
    position = IntegerField(widget=HiddenInput())
