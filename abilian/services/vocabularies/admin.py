# coding=utf-8
"""
Admin panel for vocabularies
"""
from __future__ import absolute_import

from flask import g, current_app, render_template

from abilian.i18n import _l
from abilian.web.admin import AdminPanel
from abilian.web import views, url_for
from abilian.web.nav import BreadcrumbItem
from abilian.web.action import Glyphicon

from .forms import EditForm

class ViewBase(object):
  title = _l(u'Vocabulary entry')
  base_template = "admin/_base.html"
  Form = EditForm

  def prepare_args(self, args, kwargs):
    if self.Model is None:
      self.Model = kwargs.get('Model')
    return args, kwargs

  def index_url(self):
    return url_for('.vocabularies')


class Edit(ViewBase, views.ObjectEdit):
  def prepare_args(self, args, kwargs):
    args, kwargs = ViewBase.prepare_args(self, args, kwargs)
    return views.ObjectEdit.prepare_args(self, args, kwargs)

  def view_url(self):
    return self.index_url()

  def redirect_to_view(self):
    return self.redirect_to_index()


class Create(views.ObjectCreate, Edit):
  def init_object(self, args, kwargs):
    args, kwargs = super(Create, self).init_object(args, kwargs)
    self.obj.active = True # do this because default value seems ignored?
    return args, kwargs



class Delete(ViewBase, views.ObjectDelete):
  pass


class VocabularyPanel(AdminPanel):
  """
  Vocabularies administration
  """
  id = 'vocabularies'
  label = _l(u'Vocabularies')
  icon = 'list'

  @property
  def svc(self):
    return current_app.services['vocabularies']

  def voc_edit_url(self, item):
    return url_for('.' + self.id + '_edit',
                   group=item.Meta.group,
                   Model=item.Meta.name,
                   object_id=item.id)

  def get(self):
    svc = self.svc

    return render_template(
        'admin/vocabularies.html',
        service=svc,
        url_for_voc_edit=self.voc_edit_url,
        icon_checked=Glyphicon('check'),
        vocabularies=svc.grouped_vocabularies,
    )


  def install_additional_rules(self, add_url_rule):
    panel_endpoint = '.' + self.id
    base = '/<string:group>/<string:Model>'
    edit_view = Edit.as_view('edit', view_endpoint=panel_endpoint)
    add_url_rule(base + '/<int:object_id>', view_func=edit_view)
    add_url_rule(base + '/new',
                 view_func=Create.as_view('new', view_endpoint=panel_endpoint))

  def url_value_preprocess(self, endpoint, view_args):
    Model = view_args.pop('Model', None)
    group = view_args.pop('group', None)

    if Model is not None:
      svc = self.svc
      Model = svc.get_vocabulary(name=Model, group=group)
      g.breadcrumb.append(BreadcrumbItem(label=Model.Meta.group))
      g.breadcrumb.append(BreadcrumbItem(label=Model.Meta.label))
      view_args['Model'] = Model
