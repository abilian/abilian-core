# coding=utf-8
"""
"""
from __future__ import absolute_import

try:
  import clamd
  cd = clamd.ClamdUnixSocket()
  CLAMD_AVAILABLE = True
except ImportError:
  CLAMD_AVAILABLE = False

from abilian.core.models.blob import Blob
from ..base import Service


class AntiVirusService(Service):
  """
  Antivirus service
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
      scan = cd.scan
      # py3 compat: bytes == py2 str(). Pathlib uses os.fsencode()
      content = bytes(file_or_stream.file)
    elif isinstance(file_or_stream, (str, unicode)):
      scan = cd.scan
    else:
      scan = cd.instream

    res = None
    try:
      res = scan(content)
    except clamd.ClamdError as e:
      self.logger.warning('Error during content scan: %s', repr(e))
      return None

    if content not in res:
      # may happen if file doesn't exists
      return False

    res = res[content]
    return res[0] == u'OK'


service = AntiVirusService()
