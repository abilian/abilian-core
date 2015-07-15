# coding=utf-8
"""
"""
from __future__ import absolute_import

from wtforms.fields import StringField
from flask import current_app

from abilian.core.models.tag import Tag, TAGS_ATTR
from abilian.web.forms import Field, ModelForm
from abilian.web.forms.widgets import Select2
from abilian.web.forms.validators import required
from abilian.web.forms.filters import strip


class TagsField(Field):
  """
  Handle tags selection on for a given :attr:`tags namespace<.Tag.ns>`.

  Usage::

      __tags__ = TagsField(ns='tags namespace')

  """
  widget = Select2(js_init='tags-select', multiple=True)

  def __init__(self, ns, *args, **kwargs):
    super(TagsField, self).__init__(*args, **kwargs)
    self.ns = ns.strip()
    assert self.ns

  def iter_choices(self):
    choices = []
    choices.append(('', u'', False)) # tags are never required: first option is blank

    extension = current_app.extensions['tags']
    ns_tags = extension.get(ns=self.ns)

    for tag in ns_tags:
      choices.append((tag.label, tag.label, tag in self.data))

    # in case of error during form validation, don't forget new added tags
    for tag in self.data - set(ns_tags):
      choices.append((tag.label, tag.label, True))

    return sorted(choices)


  def default(self):
    return set()

  def process_formdata(self, valuelist):
    extension = current_app.extensions['tags']
    data = set()

    for label in set(valuelist):
      tag = extension.get(ns=self.ns, label=label)
      if tag is None:
        tag = Tag(ns=self.ns, label=label)
      data.add(tag)

    self.data = data

  def populate_obj(self, obj, name):
    extension = current_app.extensions['tags']
    all_tags = extension.entity_tags(obj)
    ns_existing = set(extension.get(ns=self.ns))
    to_remove = ns_existing - self.data

    for tag in to_remove:
      all_tags.remove(tag)

    for tag in self.data:
      all_tags.add(tag)


class TagForm(ModelForm):
  """
  Form for a single tag
  """
  ns = StringField(u'Namespace',
                   validators=[required()],
                   filters=(strip,),
  )

  label = StringField(u'Label', filters=(strip,), validators=[required(),])

  class Meta:
    model = Tag
    include_primary_keys = True
    assign_required = False # for 'id': allow None, for new records
