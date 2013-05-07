# coding=utf-8
"""
Extensions to WTForms fields, widgets and validators.
"""
import logging
from cgi import escape

from wtforms import fields
from wtforms.fields.core import Field, SelectField, FormField
from wtforms.validators import EqualTo, Length, NumberRange, Optional, Required,\
  Regexp, Email, IPAddress, MacAddress, URL, UUID, AnyOf, NoneOf
from wtforms.widgets.core import html_params, Select, HTMLString, Input
from wtforms_alchemy import ModelFieldList as BaseModelFieldList
from .widgets import DefaultViewWidget

logger = logging.getLogger(__name__)

### PATCH wtforms.field.core.Field ####################
_PATCHED = False

if not _PATCHED:
  logger.info('PATCH %s: add methods for "view" mode on fields', repr(Field))
  Field.view_template = None

  _wtforms_Field_init = Field.__init__
  def _core_field_init(self, *args, **kwargs):
    view_widget = None
    if 'view_widget' in kwargs:
      view_widget = kwargs.pop('view_widget')

    _wtforms_Field_init(self, *args, **kwargs)
    if view_widget is None:
      view_widget = self.widget

    self.view_widget = view_widget

  Field.__init__ = _core_field_init
  del _core_field_init

  def render_view(self, **kwargs):
    """ render data
    """
    if hasattr(self.view_widget, 'render_view'):
      return self.view_widget.render_view(self, **kwargs)

    return DefaultViewWidget().render_view(self, **kwargs)

  Field.render_view = render_view
  del render_view

  def is_hidden(self):
    """ WTForms is not consistent with hidden fields, since flags.hidden is not
    set on HiddenField :-(
    """
    return (self.flags.hidden
            or isinstance(self, fields.HiddenField))

  Field.is_hidden = property(is_hidden)
  del is_hidden

  _PATCHED = True
### END PATCH wtforms.field.core.Field #################


class Chosen(Select):
  """
  Extends the Select widget using the Chosen jQuery plugin.
  """

  def __call__(self, field, **kwargs):
    kwargs.setdefault('id', field.id)
    html = [u'<select %s class="chzn-select">' % html_params(name=field.name, **kwargs)]
    for val, label, selected in field.iter_choices():
      html.append(self.render_option(val, label, selected))
    html.append(u'</select>')
    return HTMLString(u''.join(html))

  @classmethod
  def render_option(cls, value, label, selected, **kwargs):
    options = dict(kwargs, value=value)
    if selected:
      options['selected'] = True
    return HTMLString(u'<option %s>%s</option>' % (html_params(**options), escape(unicode(label))))


class TagInput(Input):
  """
  Extends the Select widget using the Chosen jQuery plugin.
  """

  def __call__(self, field, **kwargs):
    kwargs.setdefault('id', field.id)
    kwargs['class'] = "tagbox"
    if 'value' not in kwargs:
      kwargs['value'] = field._value()

    return HTMLString(u'<input %s>' % self.html_params(name=field.name, **kwargs))


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


class RelationSelectField(SelectField):
  # TODO: Later...
  pass


def strip(data):
    """
    Strip data if data is a string
    """
    if not isinstance(data, basestring):
        return data
    return data.strip()


# TODO: most of this is currently only stubs and needs to be implemented.
#
# Validators
#
# NOTE: the `rule` property is supposed to be useful for generating client-side
# validation code.
class Email(Email):
  def __call__(self, form, field):
    if self.message is None:
      self.message = field.gettext(u'Invalid email address.')

    if field.data:
      super(Email, self).__call__(form, field)

  @property
  def rule(self):
    return {"email": True}


class Required(Required):
  @property
  def rule(self):
    return {"required": True}


class EqualTo(EqualTo):
  @property
  def rule(self):
    return None


class Length(Length):
  @property
  def rule(self):
    return None


class NumberRange(NumberRange):
  @property
  def rule(self):
    return None


class Optional(Optional):
  @property
  def rule(self):
    return None


class Regexp(Regexp):
  @property
  def rule(self):
    return None


class IPAddress(IPAddress):
  @property
  def rule(self):
    return None


class MacAddress(MacAddress):
  @property
  def rule(self):
    return None


class URL(URL):
  @property
  def rule(self):
    return {"url": True}


class UUID(UUID):
  @property
  def rule(self):
    return None


class AnyOf(AnyOf):
  @property
  def rule(self):
    return None


class NoneOf(NoneOf):
  @property
  def rule(self):
    return None


class FlagHidden(object):
  """ Flag the field as hidden
  """
  field_flags = ('hidden',)

  def __call__(self, form, field):
    pass

  @property
  def rule(self):
    return None


# These are the canonical names that should be used.
equalto = EqualTo
length = Length
numberrange = NumberRange
optional = Optional
required = Required
regexp = Regexp
email = Email
ipaddress = IPAddress
macaddress = MacAddress
url = URL
uuid = UUID
anyof = AnyOf
noneof = NoneOf
flaghidden = FlagHidden
