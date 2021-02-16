""""""
from wtforms.fields import BooleanField, StringField

from abilian.i18n import _l
from abilian.services.security.models import Role
from abilian.web.forms import Form, fields, widgets
from abilian.web.forms.filters import strip
from abilian.web.forms.validators import required


class GroupAdminForm(Form):
    name = StringField(_l("Name"), filters=(strip,), validators=[required()])
    description = StringField(_l("Description"), filters=(strip,))

    public = BooleanField(_l("Public"), widget=widgets.BooleanWidget(on_off_mode=True))

    roles = fields.Select2MultipleField(
        _l("Roles"),
        choices=lambda: [(r.name, r.label) for r in Role.assignable_roles()],
    )
