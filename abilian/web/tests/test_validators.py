# coding=utf-8

from __future__ import absolute_import, print_function, unicode_literals

import pytest
from wtforms import Form, StringField
from wtforms.validators import ValidationError

from abilian.web.forms.validators import siret_validator


class DummyForm(Form):
    name = StringField(u'foo')
    siret = StringField(u'Siret')


def test_siret_validator():
    # valid
    form = DummyForm(siret="54207855500514", name="foo")
    field = form.siret
    validator = siret_validator()
    assert validator(form, field) is None

    # invalid Luhn (changed the first digit)
    form = DummyForm(siret="64207855500514", name="foo")
    field = form.siret
    validator = siret_validator()
    with pytest.raises(ValidationError):
        validator(form, field)

    # invalid
    form = DummyForm(siret="WRONG542078555", name="foo")
    field = form.siret
    validator = siret_validator()
    with pytest.raises(ValidationError):
        validator(form, field)

    # too short
    form = DummyForm(siret="54207", name="foo")
    field = form.siret
    validator = siret_validator()
    with pytest.raises(ValidationError):
        validator(form, field)
