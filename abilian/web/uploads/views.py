# coding=utf-8
"""
"""
from __future__ import absolute_import

from werkzeug import secure_filename
from werkzeug.exceptions import BadRequest, NotFound
from flask import current_app, send_file, jsonify
from flask.signals import request_tearing_down
from flask_login import current_user
from flask_wtf.file import FileField, file_required

from abilian.core.util import pdb_on_error

from abilian.web import csrf, url_for
from abilian.web.forms import Form
from abilian.web.blueprints import Blueprint
from abilian.web.views import View, JSONView

bp = Blueprint('uploads', __name__, url_prefix='/upload')

class UploadForm(Form):

  file = FileField(validators=(file_required(),))

  
class BaseUploadsView(object):

  def prepare_args(self, args, kwargs):
    args, kwargs = super(BaseUploadsView, self).prepare_args(args, kwargs)
    self.uploads = current_app.extensions['uploads']
    self.user = current_user._get_current_object()
    return args, kwargs

  
class NewUploadView(BaseUploadsView, JSONView):
  """
  Upload a new file
  """
  methods = ['POST', 'PUT']
  decorators = (csrf.support_graceful_failure,)

  #: file handle to be returned
  handle = None

  def data(self, *args, **kwargs):
    return {
      'handle': self.handle,
      'url': url_for('.handle', handle=self.handle),
    }
  
  def post(self, *args, **kwargs):
    form = UploadForm()

    if not form.validate():
      raise BadRequest('File is missing.')
    
    uploaded = form['file'].data
    filename = secure_filename(uploaded.filename)
    mimetype = uploaded.mimetype
    self.handle = self.uploads.add_file(self.user, uploaded,
                                        filename=filename,
                                        mimetype=mimetype)
    return self.get(*args, **kwargs)
    
  def put(self, *args, **kwargs):
    return self.post(*args, **kwargs)


bp.add_url_rule('/', view_func=NewUploadView.as_view('new_file',),)


class _StreamCloser(object):
  """
  Ensure file is closed after after response has been sent.
  """
  def __init__(self, stream):
    self.stream = stream
    request_tearing_down.connect(self, weak=False)

  def __call__(self, *args, **kwargs):
    try:
      self.stream.close()
      self.stream = None
    finally:
      request_tearing_down.disconnect(self)
      

class UploadView(BaseUploadsView, View):
  """
  Manage an uploaded file: download, delete
  """
  methods = ['GET', 'DELETE']
  decorators = (csrf.support_graceful_failure,)
  
  def get(self, handle, *args, **kwargs):
    file_obj = self.uploads.get_file(self.user, handle)

    if file_obj is None:
      raise NotFound()

    metadata = self.uploads.get_metadata(self.user, handle)
    filename = metadata.get('filename', handle)
    content_type = metadata.get('mimetype', None)
    stream = file_obj.open('rb')
    _StreamCloser(stream)
    
    return send_file(stream,
                     as_attachment=True,
                     attachment_filename=filename,
                     mimetype=content_type,
                     cache_timeout=0,
                     add_etags=False,
                     conditional=False)

  def delete(self, handle, *args, **kwargs):
    if self.uploads.get_file(self.user, handle) is None:
      raise NotFound()

    self.uploads.remove_file(self.user, handle)
    return jsonify({'success': True})

  
bp.add_url_rule('/<string:handle>', view_func=UploadView.as_view('handle',),)
