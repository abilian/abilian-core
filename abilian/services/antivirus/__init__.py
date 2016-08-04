# coding=utf-8
"""
"""
from __future__ import absolute_import, print_function, division

import io
import logging
import os

import pathlib
import six

from abilian.core.models.blob import Blob
from ..base import Service

logger = logging.getLogger(__name__)

try:
    import clamd
    cd = clamd.ClamdUnixSocket()
    CLAMD_AVAILABLE = True
except ImportError:
    CLAMD_AVAILABLE = False

CLAMD_CONF = {'StreamMaxLength': u'25M', 'MaxFileSize': u'25M'}
CLAMD_STREAMMAXLENGTH = 26214400
CLAMD_MAXFILESIZE = 26214400

if CLAMD_AVAILABLE:
    conf_path = pathlib.Path('/etc', 'clamav', 'clamd.conf')
    if conf_path.exists():
        conf_lines = [l.strip() for l in conf_path.open('rt').readlines()]
        CLAMD_CONF = dict(
            l.split(u' ', 1) for l in conf_lines if not l.startswith('#'))

        def _size_to_int(size_str):
            multiplier = 0
            if not size_str:
                return 0

            unit = size_str[-1].lower()
            if unit in ('k', 'm'):
                size_str = size_str[:-1]
                multiplier = 1024
                if unit == 'm':
                    multiplier *= 1024

            if not size_str:
                return 0

            size = int(size_str)
            if multiplier:
                size *= multiplier

            return size

        CLAMD_STREAMMAXLENGTH = _size_to_int(CLAMD_CONF['StreamMaxLength'])
        CLAMD_MAXFILESIZE = _size_to_int(CLAMD_CONF['MaxFileSize'])
        del conf_path, conf_lines, _size_to_int


class AntiVirusService(Service):
    """Antivirus service.
    """
    name = 'antivirus'

    def scan(self, file_or_stream):
        """
        :param file_or_stream: :class:`Blob` instance, filename or file object

        :returns: True if file is 'clean', False if a virus is detected, None if
        file could not be scanned.

        If `file_or_stream` is a Blob, scan result is stored in
        Blob.meta['antivirus'].
        """
        res = self._scan(file_or_stream)
        if isinstance(file_or_stream, Blob):
            file_or_stream.meta['antivirus'] = res
        return res

    def _scan(self, file_or_stream):
        if not CLAMD_AVAILABLE:
            return None

        content = file_or_stream
        if isinstance(file_or_stream, Blob):
            # py3 compat: bytes == py2 str(). Pathlib uses os.fsencode()
            file_or_stream = bytes(file_or_stream.file)
        elif isinstance(file_or_stream, six.text_type):
            file_or_stream = file_or_stream.encode(os.fsencode)

        if isinstance(file_or_stream, bytes):
            content = io.open(file_or_stream, 'rb')

        if content.seekable():
            pos = content.tell()
            content.seek(0, io.SEEK_END)
            size = content.tell()
            content.seek(pos)

            if size > CLAMD_STREAMMAXLENGTH:
                logger.error(
                    'Content size exceed antivirus size limit, size=%d, limit=%d (%s)',
                    size,
                    CLAMD_STREAMMAXLENGTH,
                    CLAMD_CONF['StreamMaxLength'].encode('utf-8'),
                    extra={'stack': True},)
                return None

        # use stream scan. When using scan by filename, clamd runnnig user must have
        # access to file, which we cannot guarantee
        scan = cd.instream
        res = None
        try:
            res = scan(content)
        except clamd.ClamdError as e:
            self.logger.warning('Error during content scan: %s', repr(e))
            return None

        if 'stream' not in res:
            # may happen if file doesn't exists
            return False

        res = res['stream']
        return res[0] == u'OK'


service = AntiVirusService()
