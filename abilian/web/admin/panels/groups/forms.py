# coding=utf-8
"""
"""
from __future__ import absolute_import

from wtforms.fields import StringField, BooleanField, TextField

from abilian.i18n import _l
from abilian.services.security.models import Role
from abilian.web.forms import Form, fields, widgets
from abilian.web.forms.filters import strip
from abilian.web.forms.validators import required


class GroupAdminForm(Form):

  name = StringField(_l(u'Name'),
                     filters=(strip,),
                     validators=[required()])
  description = TextField(_l(u'Description'),
                          filters=(strip,))

  public = BooleanField(_l(u'Public'),
                        widget=widgets.BooleanWidget(on_off_mode=True))

  roles = fields.Select2MultipleField(
      _l(u'Roles'),
      choices=lambda: [(r.name, r.label) for r in Role.assignable_roles()],
  )
