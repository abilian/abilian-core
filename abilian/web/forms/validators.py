# TODO: most of this is currently only stubs and needs to be implemented.
#
# Validators
#
# NOTE: the `rule` property is supposed to be useful for generating client-side
# validation code.

from wtforms.validators import (
  ValidationError,
  EqualTo, Length, NumberRange, Optional, Required,\
  Regexp, Email, IPAddress, MacAddress, URL, UUID, AnyOf, NoneOf
)

from abilian.i18n import _
from abilian.services import get_service


class Rule(object):
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


class Required(Required):
  field_flags = ('required',)

  @property
  def rule(self):
    return {"required": True}


class EqualTo(EqualTo, Rule):
  pass


class Length(Length, Rule):
  pass


class NumberRange(NumberRange, Rule):
  pass


class Optional(Optional, Rule):
  pass


class Regexp(Regexp, Rule):
  pass


class IPAddress(IPAddress, Rule):
  pass


class MacAddress(MacAddress, Rule):
  pass


class URL(URL):
  @property
  def rule(self):
    return {"url": True}


class UUID(UUID, Rule):
  pass


class AnyOf(AnyOf, Rule):
  pass

class NoneOf(NoneOf, Rule):
  pass


class FlagHidden(Rule):
  """ Flag the field as hidden
  """
  field_flags = ('hidden',)

  def __call__(self, form, field):
    pass

class AntiVirus(Rule):
  """
  check content for viruses
  """
  field_flags = ('antivirus',)

  def __call__(self, form, field):
    svc = get_service('antivirus')
    if not svc:
      return

    res = svc.scan(field.data)
    if res is False:
      raise ValidationError(_(u'Virus detected!'))


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
