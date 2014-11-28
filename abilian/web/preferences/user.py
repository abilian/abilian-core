# coding=utf-8
"""
"""
from __future__ import absolute_import

from cStringIO import StringIO
import imghdr
import PIL.Image

from flask import g, current_app, request, redirect, url_for, render_template, \
    flash
from flask.ext.wtf.file import FileField
from werkzeug.exceptions import InternalServerError
from wtforms.fields import StringField
from wtforms.validators import ValidationError

from abilian.services.preferences.panel import PreferencePanel
from abilian.web import csrf
from abilian.web.forms import Form, widgets
from abilian.i18n import _l, _


class UserPreferencesForm(Form):

  password = StringField(_l(u'New Password'),
                         widget=widgets.PasswordInput(autocomplete='off'))
  confirm_password= StringField(_l(u'Confirm new password'),
                                widget=widgets.PasswordInput(autocomplete='off'))

  photo = FileField(label=_l('Photo'),
                    widget=widgets.ImageInput(width=55, height=55))

  def validate_password(self, field):
    pwd = field.data
    confirmed = self['confirm_password'].data

    if pwd != confirmed:
      raise ValidationError(
        _(u'Passwords differ. Ensure you have typed same password in both'
          u' "password" field and "confirm password" field.'))

  def validate_photo(self, field):
    data = request.files.get(field.name)
    if not data:
      return

    filename = data.filename
    valid = any(filename.lower().endswith(ext)
                for ext in ('.png', '.jpg', '.jpeg'))

    if not valid:
      raise ValidationError(_(u'Only PNG or JPG image files are accepted'))

    img_type = imghdr.what('ignored', data.read())

    if not img_type in ('png', 'jpeg'):
      raise ValidationError(_(u'Only PNG or JPG image files are accepted'))

    data.stream.seek(0)
    try:
      # check this is actually an image file
      im = PIL.Image.open(data.stream)
      im.load()
    except:
      raise ValidationError(_(u'Could not decode image file'))

    # convert to jpeg
    #FIXME: better do this at model level?
    jpeg = StringIO()
    im.convert('RGBA').save(jpeg, 'JPEG')
    field.data = jpeg.getvalue()


class UserPreferencesPanel(PreferencePanel):
  id = 'user'
  label = _l(u'About me')

  def is_accessible(self):
    return True

  def get(self):
    # Manual security check, should be done by the framework instead.
    if not self.is_accessible():
      raise InternalServerError()

    data = {}
    photo = g.user.photo
    if photo:
      # subclass str/bytes to set additional 'url' attribute
      photo = type('Photo', (bytes,),
                   dict(object=photo,
                        url=url_for('users.photo', user_id=g.user.id)))
      data['photo'] = photo

    form = UserPreferencesForm(formdata=None, prefix=self.id, **data)
    return render_template('preferences/user.html', form=form, title=self.label)

  @csrf.protect
  def post(self):
    # Manual security check, should be done by the framework instead.
    if not self.is_accessible():
      raise InternalServerError()

    if request.form['_action'] == 'cancel':
      return redirect(url_for('.user'))

    form = UserPreferencesForm(request.form, prefix=self.id)

    if form.validate():
      del form.confirm_password
      if form.password.data:
        g.user.set_password(form.password.data)
      del form.password

      if not form.photo.data:
        del form.photo

      form.populate_obj(g.user)

      current_app.db.session.commit()
      flash(_(u"Preferences saved."), "info")
      return redirect(url_for(".user"))
    else:
      return render_template('preferences/user.html', form=form)
