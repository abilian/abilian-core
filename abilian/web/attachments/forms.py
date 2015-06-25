# coding=utf-8
"""
"""
from __future__ import absolute_import

from wtforms.fields import StringField

from abilian.i18n import _l
from abilian.core.models.attachment import Attachment
from abilian.web.forms import Form
from abilian.web.forms.fields import FileField
from abilian.web.forms.validators import required
from abilian.web.forms.filters import strip


class AttachmentForm(Form):
  
  blob = FileField(
    _l(u'file'),
    validators=[required()],
    filters=(strip,),
    multiple=False)

  description = StringField(
    _l(u'description (optional)'),
    filters=(strip,),
  )
  
  class Meta:
    model = Attachment
    include_primary_keys = True
    assign_required = False # for 'id': allow None, for new records
    
