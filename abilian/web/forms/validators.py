# coding=utf-8
from __future__ import absolute_import, division, print_function, \
    unicode_literals

# TODO: most of this is currently only stubs and needs to be implemented.
#
# Validators
#
# NOTE: the `rule` property is supposed to be useful for generating client-side
# validation code.
from wtforms.compat import string_types
from wtforms.validators import URL, UUID, AnyOf, DataRequired, Email, \
    EqualTo, IPAddress, MacAddress, NoneOf, NumberRange, Optional, Regexp, \
    StopValidation, ValidationError

from abilian.i18n import _, _n
from abilian.services import get_service


class Rule(object):

    @property
    def rule(self):
        return None


class Email(Email):

    def __call__(self, form, field):
        if self.message is None:
            self.message = field.gettext('Invalid email address.')

        if field.data:
            super(Email, self).__call__(form, field)

    @property
    def rule(self):
        return {"email": True}


class CorrectInputRequired(DataRequired):

    def __call__(self, form, field):
        if field.data is None or (isinstance(field.data, string_types) and
                                  not field.data.strip()) or (
                                      isinstance(field.data, (list, dict)) and
                                      not field.data):
            if self.message is None:
                message = field.gettext('This field is required.')
            else:
                message = self.message

            field.errors[:] = []
            raise StopValidation(message)


class Required(CorrectInputRequired):
    field_flags = ('required',)

    @property
    def rule(self):
        return {"required": True}


class EqualTo(EqualTo, Rule):
    pass


class Length(Rule):
    """Validates the length of a string.

    :param min: The minimum required length of the string. If not provided, minimum
    length will not be checked.

    :param max:  The maximum length of the string. If not provided, maximum length
    will not be checked.

    :param message: Error message to raise in case of a validation error. Can be
    interpolated using `%(min)d` and `%(max)d` if desired. Useful defaults are
    provided depending on the existence of min and max.
    """

    def __init__(self, min=-1, max=-1, message=None):
        assert min != -1 or max != -1, 'At least one of `min` or `max` must be specified.'
        assert max == -1 or min <= max, '`min` cannot be more than `max`.'
        self.min = min
        self.max = max
        self.message = message

    def __call__(self, form, field):
        l = field.data and len(field.data) or 0

        if l < self.min or self.max != -1 and l > self.max:
            message = self.message
            if message is None:
                if self.max == -1:
                    message = _n(
                        'Field must be at least %(min)d character long.',
                        'Field must be at least %(min)d characters long.',
                        self.min,
                        min=self.min)
                elif self.min == -1:
                    message = _n(
                        'Field cannot be longer than %(max)d character.',
                        'Field cannot be longer than %(max)d characters.',
                        self.max,
                        max=self.max)
                else:
                    message = _(
                        'Field must be between %(min)d and %(max)d characters long.',
                        min=self.min, max=self.max)
            raise ValidationError(message % dict(
                min=self.min, max=self.max, length=l))


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
    """Flag the field as hidden.
    """
    field_flags = ('hidden',)

    def __call__(self, form, field):
        pass


class AntiVirus(Rule):
    """Check content for viruses.
    """
    field_flags = ('antivirus',)

    def __call__(self, form, field):
        svc = get_service('antivirus')
        if not svc:
            return

        res = svc.scan(field.data)
        if res is False:
            raise ValidationError(_(u'Virus detected!'))


class RenderEmpty(object):
    """Force display.
    """
    field_flags = ('render_empty',)

    def __call__(self, form, field):
        pass


class SIRET(RenderEmpty):
    pass


def luhn(n):
    """
    Validate that a string made of numeric characters verify Luhn test. Used by
    siret validator.

    from http://rosettacode.org/wiki/Luhn_test_of_credit_card_numbers#Python
    https://en.wikipedia.org/wiki/Luhn_algorithm
    """
    r = [int(ch) for ch in str(n)][::-1]
    return (sum(r[0::2]) + sum(sum(divmod(d * 2, 10))
                               for d in r[1::2])) % 10 == 0


# specific SIRET like for MONACO, i.e MONACOCONFO001
# -  Principauté de Monaco "001"
# - la Guadeloupe "458"
# - la Martinique "462"
# - la Guyane "496"
# - la Réunion "372
SIRET_CODES = ('001', "458", "462", "496", "372")


def siret_validator():
    """Validate a SIRET: check its length (14), its final code, and
    pass it through the Luhn algorithm.

    """

    def _validate_siret(form, field, siret=""):
        """SIRET validator.  A WTForm validator wants a form and a field as
        parameters. We also want to give directly a siret, for a
        scripting use.

        """
        if field is not None:
            siret = (field.data or u'').strip()

        if len(siret) != 14:
            raise ValidationError(_(u'SIRET must have exactly 14 characters ({count})'
                                    ).format(count=len(siret)))

        if not all(('0' <= c <= '9') for c in siret):
            if not siret[-3:] in SIRET_CODES:
                raise ValidationError(
                    _('SIRET looks like special SIRET but geographical code seems invalid'
                      ' ({code})').format(code=siret[-3:]))

        elif not luhn(siret):
            raise ValidationError(
                _('SIRET number is invalid (length is ok: verify numbers)'))

    return _validate_siret


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
siret = SIRET
uuid = UUID
anyof = AnyOf
noneof = NoneOf
flaghidden = FlagHidden
renderempty = RenderEmpty

VALIDATORS = {
    'email': email,
    'url': url,
    'uuid': uuid,
    'renderempty': renderempty,
    'siret': siret,
    'required': required,
    'optional': optional,
}
