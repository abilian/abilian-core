"""
Extensions to WTForms fields, widgets and validators.
"""

from cgi import escape

from wtforms.fields.core import SelectField
from wtforms.validators import EqualTo, Length, NumberRange, Optional, Required,\
  Regexp, Email, IPAddress, MacAddress, URL, UUID, AnyOf, NoneOf
from wtforms.widgets.core import html_params, Select, HTMLString, Input


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


class RelationSelectField(SelectField):
  # TODO: Later...
  pass


# TODO: all of this is currently only stubs and needs to be implemented.
#
# Validators
#
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


class Required(Required):
  @property
  def rule(self):
    return {"required": True}


class Regexp(Regexp):
  @property
  def rule(self):
    return None


class Email(Email):
  def __call__(self, form, field):
    if self.message is None:
      self.message = field.gettext(u'Invalid email address.')

    if field.data:
      super(Email, self).__call__(form, field)

  @property
  def rule(self):
    return {"email": True}


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
