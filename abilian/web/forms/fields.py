from wtforms.fields.core import SelectField, FormField
from wtforms_alchemy import ModelFieldList as BaseModelFieldList
from flask.ext.wtf import FileField as BaseFileField


__all__ = ['ModelFieldList', 'FileField']

class ModelFieldList(BaseModelFieldList):
  """ Filter empty entries
  """

  def validate(self, form, extra_validators=tuple()):
    for field in self.entries:
      is_subform = isinstance(field, FormField)
      data = field.data.values() if is_subform else [field.data]

      if not any(data):
        # all inputs empty: discard row
        self.entries.remove(field)

    return super(ModelFieldList, self).validate(form, extra_validators)


class FileField(BaseFileField):
  """ support 'multiple' attribute, enabling html5 multiple file input in widget
  """
  multiple = False

  def __init__(self, *args, **kwargs):
    try:
      self.multiple = kwargs.pop('multiple')
    except KeyError:
      pass

    BaseFileField.__init__(self, *args, **kwargs)

  def __call__(self, **kwargs):
    if 'multiple' not in kwargs and self.multiple:
      kwargs['multiple'] = 'multiple'
    return BaseFileField.__call__(self, **kwargs)
