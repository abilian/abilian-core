# coding=utf-8
"""
"""
from __future__ import absolute_import

from wtforms.fields import StringField, BooleanField, TextField, HiddenField
from wtforms.validators import ValidationError

from abilian.i18n import _, _l
from abilian.services.security.models import Role

from abilian.web.forms import Form, widgets
from abilian.web.forms.fields import Select2MultipleField
from abilian.web.forms.filters import strip
from abilian.web.forms.validators import required

class UserAdminForm(Form):

  email = TextField(_l(u'Email'),
                      description=_l(u'Users log in with their email address.'),
                      view_widget=widgets.EmailWidget(),
                      filters=(strip,),
                      validators=[required()])
  first_name = StringField(_l(u'First Name'),
                           description=_l(u'ex: John'),
                           filters=(strip,),
                           validators=[required()])
  last_name = StringField(_l(u'Last Name'),
                          description=_l(u'ex: Smith'),
                          filters=(strip,),
                          validators=[required()])

  can_login = BooleanField(
      _l(u'Login enabled'),
      description=_l(u'If unchecked, user will not be able to connect.'),
      widget=widgets.BooleanWidget())

  roles = Select2MultipleField(
      _l(u'Roles'),
      choices=[(r.name, r.label) for r in Role.assignable_roles()],
  )

  password = StringField(
    _l(u'New Password'),
    description=_l(u'If empty the current password will not be changed.'),
    widget=widgets.PasswordInput(autocomplete='off')
  )
  confirm_password = StringField(_l(u'Confirm new password'),
                                 widget=widgets.PasswordInput(autocomplete='off'))

  def validate_password(self, field):
    pwd = field.data
    confirmed = self['confirm_password'].data

    if pwd != confirmed:
      raise ValidationError(
        _(u'Passwords differ. Ensure you have typed same password in both'
          u' "password" field and "confirm password" field.'))



class UserCreateForm(UserAdminForm):

  password = StringField(
    _l(u'Password'),
    description=_l(u'If empty a random password will be generated.'),
    widget=widgets.PasswordInput(autocomplete='off'))

  confirm_password = HiddenField()
