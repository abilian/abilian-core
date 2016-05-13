# coding=utf-8
"""
Base classes for file download
"""
from __future__ import absolute_import, print_function, unicode_literals

from datetime import datetime, timedelta

from flask import request, send_file
from werkzeug.exceptions import BadRequest

from abilian.core.util import utc_dt

from .base import View


class BaseFileDownload(View):

    set_expire = False
    expire_offset = timedelta(days=365)
    as_attachment = False

    #: argument name that must be found in view kwargs. This is a safety measure
    #: to prevent setting far expire date on resources without a varying argument
    #: in url (path or query string), such as a timestamp, a serial, a hash...
    expire_vary_arg = None

    def __init__(self,
                 set_expire=None,
                 expire_offset=None,
                 expire_vary_arg=None,
                 as_attachment=None):
        # override class default value only if arg is specified in constructor. This
        # allows subclasses to easily override theses defaults.
        if set_expire is not None:
            self.set_expire = set_expire
        if expire_offset is not None:
            self.expire_offset = expire_offset
        if expire_vary_arg is not None:
            self.expire_vary_arg = expire_vary_arg
        if as_attachment is not None:
            self.as_attachment = bool(as_attachment)

        if self.set_expire:
            if not self.expire_offset:
                raise ValueError('expire_offset is not set')
            if not self.expire_vary_arg:
                raise ValueError('expire_vary_arg is not set')

    def prepare_args(self, args, kwargs):
        if self.set_expire:
            vary_arg = kwargs.get(self.expire_vary_arg,
                                  request.args.get(self.expire_vary_arg))
            if vary_arg is None:
                # argument for timestamp, serial etc is missing. We must refuse to serve
                # an image with expiry date set up to maybe 1 year from now.
                # Check the code that has generated this url!
                raise BadRequest('File version marker is missing ({}=?)'.format(
                    repr(self.expire_vary_arg)))

        args, kwargs = super(BaseFileDownload, self).prepare_args(args, kwargs)
        kwargs['attach'] = request.args.get('attach',
                                            self.as_attachment,
                                            type=bool)
        return args, kwargs

    def make_response(self, *args, **kwargs):
        # for example: return flask.make_response(...)
        # or: return flask.send_file(...)
        raise NotImplementedError()

    def get_filename(self, *args, **kwargs):
        raise NotImplementedError()

    def get_content_type(self, *args, **kwargs):
        raise NotImplementedError()

    def get(self, attach, *args, **kwargs):
        """
        :param image: image as bytes
        :param s: requested maximum width/height size
        """
        response = self.make_response(*args, **kwargs)
        response.headers['content-type'] = self.get_content_type(*args,
                                                                 **kwargs)

        if attach:
            filename = self.get_filename(*args, **kwargs)
            if not filename:
                filename = u'file.bin'
            response.headers.add('Content-Disposition',
                                 u'attachment',
                                 filename=filename)

        self.set_cache_headers(response)
        return response

    def set_cache_headers(self, response):
        if self.set_expire:
            response.cache_control.public = False
            response.cache_control.private = True
            response.cache_control.max_age = int(
                self.expire_offset.total_seconds())
            response.expires = utc_dt(datetime.utcnow() + self.expire_offset)


class BaseBlobDownload(BaseFileDownload):

    def get_blob(self, *args, **kwargs):
        raise NotImplementedError()

    def prepare_args(self, args, kwargs):
        args, kwargs = super(BaseBlobDownload, self).prepare_args(args, kwargs)
        self.blob = self.get_blob(*args, **kwargs)
        metadata = self.blob.meta
        self.filename = metadata.get('filename', self.obj.name)
        self.content_type = metadata.get('mimetype')
        return args, kwargs

    def get_filename(self, *args, **kwargs):
        return self.filename

    def get_content_type(self, *args, **kwargs):
        return self.content_type

    def make_response(self, *args, **kwargs):
        blob = self.blob
        stream = blob.file.open('rb')

        return send_file(stream,
                         as_attachment=False,
                         mimetype=self.content_type,
                         cache_timeout=0,
                         add_etags=False,
                         conditional=False)
