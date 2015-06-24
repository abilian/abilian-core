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

  name = StringField(
    _l(u'attachment_label'),
    description=_l(u'If empty, filename will be used'),
    filters=(strip,),
  )
  
  blob = FileField(
    _l(u'file'),
    validators=[required()],
    filters=(strip,),
    multiple=False)

  def process(self, *args, **kwargs):
    super(AttachmentForm, self).process(*args, **kwargs)

    if not self['name'].data and self['blob'].data:
      f = self['blob'].data
      if hasattr(f, 'filename'):
        self['name'].data = getattr(f, 'filename')
  
  class Meta:
    model = Attachment
    include_primary_keys = True
    assign_required = False # for 'id': allow None, for new records
    
