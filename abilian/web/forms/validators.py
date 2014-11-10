# TODO: most of this is currently only stubs and needs to be implemented.
#
# Validators
#
# NOTE: the `rule` property is supposed to be useful for generating client-side
# validation code.

from wtforms.validators import EqualTo, Length, NumberRange, Optional, Required,\
  Regexp, Email, IPAddress, MacAddress, URL, UUID, AnyOf, NoneOf


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
  field_flags = ('required',)

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
