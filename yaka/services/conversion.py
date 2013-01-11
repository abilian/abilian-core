"""
Conversion service.

Hardcoded to manage only conversion to PDF, to text and to image series.

Includes result caching (on filesystem).

Assumes poppler-utils and LibreOffice are installed.
"""

import glob
import hashlib
import shutil
import itertools
from tempfile import mktemp, mkstemp
import traceback
from abc import ABCMeta, abstractmethod
from magic import Magic
import os
import subprocess
import threading
from base64 import encodestring, decodestring
from xmlrpclib import ServerProxy
import mimetypes
from os.path import join
import re
import StringIO

from PIL import Image
from PIL.ExifTags import TAGS

from yaka.services.image import resize


# Hack for Mac OS + homebrew
os.environ['PATH'] += ":/usr/local/bin"


TMP_DIR = "tmp"
CACHE_DIR = "cache"

mime_sniffer = Magic(mime=True)
encoding_sniffer = Magic(mime_encoding=True)


class ConversionError(Exception):
  pass


class Cache(object):

  def get(self, key):
    if os.path.exists("cache/%s.blob" % key):
      value = open("cache/%s.blob" % key).read()
      if key.startswith("txt:"):
        value = unicode(value, encoding="utf8")
      return value
    else:
      return None

  def set(self, key, value):
    if not os.path.exists(CACHE_DIR):
      os.mkdir(CACHE_DIR)
    fd = open("cache/%s.blob" % key, "wbc")
    if key.startswith("txt:"):
      fd.write(value.encode("utf8"))
    else:
      fd.write(value)
    fd.close()

  __setitem__ = set

  def clear(self):
    pass


class Converter(object):
  def __init__(self):
    self.handlers = []
    self.cache = Cache()
    if not os.path.exists(TMP_DIR):
      os.mkdir(TMP_DIR)
    if not os.path.exists(CACHE_DIR):
      os.mkdir(CACHE_DIR)

  def clear(self):
    self.cache.clear()
    shutil.rmtree(TMP_DIR)
    shutil.rmtree(CACHE_DIR)

  def register_handler(self, handler):
    self.handlers.append(handler)

  # TODO: refactor, pass a "File" or "Document" or "Blob" object
  def to_pdf(self, digest, blob, mime_type):
    cache_key = "pdf:" + digest

    pdf = self.cache.get(cache_key)
    if pdf:
      return pdf

    for handler in self.handlers:
      if handler.accept(mime_type, "application/pdf"):
        pdf = handler.convert(blob)
        self.cache[cache_key] = pdf
        return pdf
    raise ConversionError("No handler found to convert from %s to PDF" % mime_type)

  def to_text(self, digest, blob, mime_type):
    """Converts a file to plain text.

    Useful for full-text indexing. Returns an unicode string.
    """
    # Special case, for now (XXX).
    if mime_type.startswith("image/"):
      return u""

    cache_key = "txt:" + digest

    text = self.cache.get(cache_key)
    if text:
      return text

    # Direct conversion possible
    for handler in self.handlers:
      if handler.accept(mime_type, "text/plain"):
        text = handler.convert(blob)
        self.cache[cache_key] = text
        return text

    # Use PDF as a pivot format
    pdf = self.to_pdf(digest, blob, mime_type)
    for handler in self.handlers:
      if handler.accept("application/pdf", "text/plain"):
        text = handler.convert(pdf)
        self.cache[cache_key] = text
        return text

    raise ConversionError()

  def to_image(self, digest, blob, mime_type, index, size=500):
    """
    Converts a file to a list of images. Returns image at the given index.
    """
    # Special case, for now (XXX).
    if mime_type.startswith("image/"):
      return ""

    cache_key = "img:%s:%s:%s" % (index, size, digest)
    converted = self.cache.get(cache_key)
    if converted:
      return converted

    # Direct conversion possible
    for handler in self.handlers:
      if handler.accept(mime_type, "image/jpeg"):
        converted_images = handler.convert(blob, size=size)
        for i in range(0, len(converted_images)):
          converted = converted_images[i]
          self.cache["img:%s:%s:%s" % (i, size, digest)] = converted
        return converted_images[index]

    # Use PDF as a pivot format
    pdf = self.to_pdf(digest, blob, mime_type)
    for handler in self.handlers:
      if handler.accept("application/pdf", "image/jpeg"):
        converted_images = handler.convert(pdf, size=size)
        for i in range(0, len(converted_images)):
          converted = converted_images[i]
          self.cache["img:%s:%s:%s" % (i, size, digest)] = converted
        return converted_images[index]

    raise ConversionError()

  def get_metadata(self, digest, file, mime_type):
    """Gets a dictionary representing the metadata embedded in the given file."""

    # XXX: ad-hoc for now, refactor later
    if mime_type.startswith("image/"):
      img = Image.open(StringIO.StringIO(file))
      ret = {}
      if not hasattr(img, '_getexif'):
        return {}
      info = img._getexif()
      if not info:
        return {}
      for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret["EXIF:" + str(decoded)] = value
      return ret

    if mime_type == "application/pdf":
      in_fn = make_temp_file(file)
      output = subprocess.check_output(['pdfinfo', in_fn])
      ret = {}
      for line in output.split("\n"):
        if ":" in line:
          key, value = line.strip().split(":", 1)
          ret["PDF:" + key] = unicode(value.strip(), errors="replace")

      os.remove(in_fn)
      return ret

    return {}

  @staticmethod
  def digest(blob):
    assert type(blob) in (str, unicode)
    if type(blob) == str:
      digest = hashlib.md5(blob).hexdigest()
    else:
      digest = hashlib.md5(blob.encode("utf8")).hexdigest()
    return digest


class Handler(object):
  __metaclass__ = ABCMeta

  accepts_mime_types = []
  produces_mime_types = []

  def accept(self, source_mime_type, target_mime_type):
    """Generic matcher based on patterns."""

    match_source = False
    match_target = False

    for pat in self.accepts_mime_types:
      if re.match("^%s$" % pat, source_mime_type):
        match_source = True
        break

    for pat in self.produces_mime_types:
      if re.match("^%s$" % pat, target_mime_type):
        match_target = True
        break

    return match_source and match_target

  @abstractmethod
  def convert(self, key, **kw):
    pass


class PdfToTextHandler(Handler):
  accepts_mime_types = ['application/pdf']
  produces_mime_types = ['text/plain']

  def convert(self, blob, **kw):
    in_fn = make_temp_file(blob)
    out_fn = mktemp(dir=TMP_DIR)

    try:
      try:
        subprocess.check_call(['pdftotext', in_fn, out_fn])
      except Exception, e:
        raise ConversionError(e)

      converted = open(out_fn).read()
      encoding = encoding_sniffer.from_file(out_fn)

      if encoding in ("binary", None):
        encoding = "ascii"
      try:
        converted_unicode = unicode(converted, encoding, errors="ignore")
      except:
        traceback.print_exc()
        converted_unicode = unicode(converted, errors="ignore")

      return converted_unicode
    finally:
      os.remove(in_fn)
      os.remove(out_fn)

class AbiwordTextHandler(Handler):
  accepts_mime_types = ['application/msword']
  produces_mime_types = ['text/plain']

  def convert(self, blob, **kw):
    in_fn = make_temp_file(blob, suffix=".doc")
    out_fn = mktemp(dir=TMP_DIR, suffix='.txt')

    cur_dir = os.getcwd()
    try:
      try:
        os.chdir(TMP_DIR)
        subprocess.check_call(
          ['abiword', '--to', os.path.basename(out_fn), os.path.basename(in_fn)])
      except Exception, e:
        raise ConversionError(e)
      finally:
        os.chdir(cur_dir)

      converted = open(out_fn).read()
      encoding = encoding_sniffer.from_file(out_fn)

      if encoding in ("binary", None):
        encoding = "ascii"
      try:
        converted_unicode = unicode(converted, encoding, errors="ignore")
      except:
        traceback.print_exc()
        converted_unicode = unicode(converted, errors="ignore")

      return converted_unicode
    finally:
      os.remove(in_fn)
      os.remove(out_fn)

class AbiwordPDFHandler(Handler):
  accepts_mime_types = ['application/msword',
                        'application/vnd.oasis.opendocument.text',
                        'text/rtf',]
  produces_mime_types = ['application/pdf']

  def convert(self, blob, **kw):
    in_fn = make_temp_file(blob, suffix=".doc")
    out_fn = mktemp(dir=TMP_DIR, suffix='.pdf')

    cur_dir = os.getcwd()
    try:
      try:
        os.chdir(TMP_DIR)
        subprocess.check_call(
          ['abiword', '--to', os.path.basename(out_fn), os.path.basename(in_fn)])
      except Exception, e:
        raise ConversionError(e)
      finally:
        os.chdir(cur_dir)

      converted = open(out_fn).read()
      return converted
    finally:
      os.remove(in_fn)
      if os.path.exists(out_fn):
        os.remove(out_fn)


class ImageMagickHandler(Handler):
  accepts_mime_types = ['image/.*']
  produces_mime_types = ['application/pdf']

  def convert(self, blob, **kw):
    in_fn = make_temp_file(blob)
    out_fn = mktemp(dir=TMP_DIR)

    try:
      subprocess.check_call(['convert', in_fn, "pdf:" + out_fn])

      converted = open(out_fn).read()
      return converted
    except Exception, e:
      raise ConversionError(e)
    finally:
      os.remove(in_fn)
      os.remove(out_fn)


class PdfToPpmHandler(Handler):
  accepts_mime_types = ['application/pdf']
  produces_mime_types = ['image/jpeg']

  def convert(self, blob, size=500):
    """Size is the maximum horizontal size."""

    in_fn = make_temp_file(blob)
    out_fn = mktemp(dir=TMP_DIR)
    l = []

    try:
      subprocess.check_call(['pdftoppm', '-jpeg', in_fn, out_fn])

      l = glob.glob("%s-*.jpg" % out_fn)
      l.sort()
      converted_images = []
      for fn in l:
        converted = resize(open(fn).read(), size)
        converted_images.append(converted)

      return converted_images
    except Exception, e:
      raise ConversionError(e)
    finally:
      for fn in itertools.chain([in_fn, out_fn], l):
        try:
          os.remove(fn)
        except OSError:
            pass


class UnoconvPdfHandler(Handler):
  """Handles conversion from office documents (MS-Office, OOo) to PDF.

  Uses unoconv.
  """

  # TODO: add more if needed.
  accepts_mime_types = ['application/vnd.oasis.*',
                        'application/msword',
                        'application/mspowerpoint',
                        'application/vnd.ms-excel',
                        'application/vnd.openxmlformats-officedocument.*',
                        'text/rtf']
  produces_mime_types = ['application/pdf']
  run_timeout = 60
  _process = None

  def convert(self, blob, **kw):
    "Unoconv converter called"
    in_fn = make_temp_file(blob)
    out_fd, out_fn = mkstemp(prefix='tmp-unoconv-', suffix=".pdf", dir=TMP_DIR)
    os.close(out_fd)

    # Hack for my Mac, FIXME later
    if os.path.exists("/Applications/LibreOffice.app/Contents/program/python"):
      cmd = ['/Applications/LibreOffice.app/Contents/program/python',
             '/usr/local/bin/unoconv', '-f', 'pdf', '-o', out_fn, in_fn]
    else:
      cmd = ['unoconv', '-f', 'pdf', '-o', out_fn, in_fn]

    def run_uno():
      self._process = subprocess.Popen(cmd, close_fds=True, cwd=TMP_DIR)
      try:
        self._process.communicate()
      except Exception, e:
        raise ConversionError(e)

    run_thread = threading.Thread(target=run_uno)
    run_thread.start()
    run_thread.join(self.run_timeout)

    try:
      if run_thread.is_alive():
        # timeout reached
        self._process.terminate()
        if not self._process.poll() is None:
          self._process.kill()

        self._process = None
        raise ConversionError("Conversion timeout ({})".format(self.run_timeout))

      converted = open(out_fn).read()
      return converted

    finally:
      self._process = None
      os.remove(in_fn)
      os.remove(out_fn)


class CloudoooPdfHandler(Handler):
  """Handles conversion from OOo to PDF.

  Highly inefficient since file are serialized in base64 over HTTP.

  Deactivated because it's so hard to set up.
  """

  accepts_mime_types = [r'application/.*']
  produces_mime_types = ['application/pdf']

  # Hardcoded for now
  SERVER_URL = "http://localhost:8011"

  pivot_format_map = {
    "doc": "odt",
    "docx": "odt",
    "xls": "ods",
    "xlsx": "ods",
    "ppt": "odp",
    "pptx": "odp",
    }

  def convert(self, key):
    in_fn = "data/%s.blob" % key
    in_mime_type = open("data/%s.mime" % key).read()
    file_extension = mimetypes.guess_extension(in_mime_type).strip(".")

    data = encodestring(open(in_fn).read())
    proxy = ServerProxy(self.SERVER_URL, allow_none=True)

    if in_mime_type.startswith("application/vnd.oasis.opendocument"):
      data = proxy.convertFile(data, file_extension, 'pdf')
    else:
      pivot_format = self.pivot_format_map[file_extension]
      data = proxy.convertFile(data, file_extension, pivot_format)
      data = proxy.convertFile(data, pivot_format, 'pdf')

    converted = decodestring(data)
    new_key = hashlib.md5(converted).hexdigest()
    fd = open("data/%s.blob" % new_key, "wcb")
    fd.write(converted)
    fd.close()
    return new_key


class WvwareTextHandler(Handler):
  accepts_mime_types = ['application/msword']
  produces_mime_types = ['text/plain']

  def convert(self, blob, **kw):
    in_fn = make_temp_file(blob)
    out_fn = mktemp(dir=TMP_DIR)

    try:
      try:
        subprocess.check_call(['wvText', in_fn, out_fn])
      except Exception, e:
        raise ConversionError(e)

      converted = open(out_fn).read()

      encoding = encoding_sniffer.from_file(out_fn)
      if encoding in ("binary", None):
        encoding = "ascii"
      try:
        converted_unicode = unicode(converted, encoding, errors="ignore")
      except:
        traceback.print_exc()
        converted_unicode = unicode(converted, errors="ignore")

      return converted_unicode
    finally:
      os.remove(in_fn)
      os.remove(out_fn)

# Utils
def make_temp_file(blob, prefix='tmp', suffix=""):
  if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR)
  fd, in_fn = mkstemp(dir=TMP_DIR, prefix=prefix, suffix=suffix)
  fd = os.fdopen(fd, 'wb')
  fd.write(blob)
  fd.close()
  return in_fn

# Singleton, yuck!
converter = Converter()
converter.register_handler(PdfToTextHandler())
converter.register_handler(PdfToPpmHandler())
converter.register_handler(ImageMagickHandler())

#converter.register_handler(UnoconvPdfHandler())

converter.register_handler(AbiwordPDFHandler())
converter.register_handler(AbiwordTextHandler())


# Needs to be rewriten
#converter.register_handler(CloudoooPdfHandler())
