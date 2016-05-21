"""
Conversion service.

Hardcoded to manage only conversion to PDF, to text and to image series.

Includes result caching (on filesystem).

Assumes poppler-utils and LibreOffice are installed.

TODO: rename Converter into ConversionService ?
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import cStringIO as StringIO
import glob
import hashlib
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import traceback
from abc import ABCMeta, abstractmethod
from base64 import decodestring, encodestring
from contextlib import contextmanager
from tempfile import mkstemp
from xmlrpclib import ServerProxy

from future.utils import raise_from, string_types
from magic import Magic
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

from abilian.services.image import FIT, resize

logger = logging.getLogger(__name__)

# For some reason, twill includes a broken version of subprocess.
assert 'twill' not in subprocess.__file__

# Hack for Mac OS + homebrew
os.environ['PATH'] += ":/usr/local/bin"

TMP_DIR = "tmp"
CACHE_DIR = "cache"


def get_tmp_dir():
    return converter.TMP_DIR


class ConversionError(Exception):
    pass


class Cache(object):

    CACHE_DIR = None

    def _path(self, key):
        """ file path for `key`"""
        return self.CACHE_DIR / "{}.blob".format(key)

    def __contains__(self, key):
        return self._path(key).exists()

    def get(self, key):
        if key in self:
            value = self._path(key).open('rb').read()
            if key.startswith("txt:"):
                value = unicode(value, encoding="utf8")
            return value
        else:
            return None

    __getitem__ = get

    def set(self, key, value):
        # if not os.path.exists(self.CACHE_DIR):
        #   os.mkdir(CACHE_DIR)
        fd = self._path(key).open("wb")
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

    def init_app(self, app):
        self.init_work_dirs(cache_dir=Path(app.instance_path, CACHE_DIR),
                            tmp_dir=Path(app.instance_path, TMP_DIR),)

        app.extensions['conversion'] = self

        for handler in self.handlers:
            handler.init_app(app)

    def init_work_dirs(self, cache_dir, tmp_dir):
        self.TMP_DIR = Path(tmp_dir)
        self.CACHE_DIR = Path(cache_dir)
        self.cache.CACHE_DIR = self.CACHE_DIR

        if not self.TMP_DIR.exists():
            self.TMP_DIR.mkdir()
        if not self.CACHE_DIR.exists():
            self.CACHE_DIR.mkdir()

    def clear(self):
        self.cache.clear()
        for d in (self.TMP_DIR, self.CACHE_DIR):
            shutil.rmtree(bytes(d))
            d.mkdir()

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
        raise ConversionError("No handler found to convert from %s to PDF" %
                              mime_type)

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

    def has_image(self, digest, mime_type, index, size=500):
        """ Tell if there is a preview image
        """
        cache_key = "img:%s:%s:%s" % (index, size, digest)
        return mime_type.startswith("image/") or cache_key in self.cache

    def get_image(self, digest, blob, mime_type, index, size=500):
        """ Return an image for the given content, only if it already exists in the
        image cache
        """
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

        cache_key = "img:%s:%s:%s" % (index, size, digest)
        return self.cache.get(cache_key)

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

    def get_metadata(self, digest, content, mime_type):
        """Gets a dictionary representing the metadata embedded in the given content."""

        # XXX: ad-hoc for now, refactor later
        if mime_type.startswith("image/"):
            img = Image.open(StringIO.StringIO(content))
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
        else:
            if mime_type != "application/pdf":
                content = self.to_pdf(digest, content, mime_type)

            with make_temp_file(content) as in_fn:
                output = subprocess.check_output(['pdfinfo', in_fn])

            ret = {}
            for line in output.split(b"\n"):
                if b":" in line:
                    key, value = line.strip().split(b":", 1)
                    ret["PDF:" + key] = unicode(value.strip(), errors="replace")

            return ret

    @staticmethod
    def digest(blob):
        assert isinstance(blob, string_types)
        if isinstance(blob, str):
            digest = hashlib.md5(blob).hexdigest()
        else:
            digest = hashlib.md5(blob.encode("utf8")).hexdigest()
        return digest


class Handler(object):
    __metaclass__ = ABCMeta

    accepts_mime_types = []
    produces_mime_types = []

    def __init__(self, *args, **kwargs):
        self.log = logger.getChild(self.__class__.__name__)

    def init_app(self, app):
        pass

    @property
    def TMP_DIR(self):
        return get_tmp_dir()

    @property
    def mime_sniffer(self):
        return Magic(mime=True)

    @property
    def encoding_sniffer(self):
        return Magic(mime_encoding=True)

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
    accepts_mime_types = ['application/pdf', 'application/x-pdf']
    produces_mime_types = ['text/plain']

    def convert(self, blob, **kw):
        with make_temp_file(blob) as in_fn, make_temp_file() as out_fn:
            try:
                subprocess.check_call(['pdftotext', in_fn, out_fn])
            except Exception as e:
                raise raise_from(ConversionError('pdftotext'), e)

            converted = open(out_fn).read()
            encoding = self.encoding_sniffer.from_file(out_fn)

        if encoding in ("binary", None):
            encoding = "ascii"
        try:
            converted_unicode = unicode(converted, encoding, errors="ignore")
        except:
            traceback.print_exc()
            converted_unicode = unicode(converted, errors="ignore")

        return converted_unicode


class AbiwordTextHandler(Handler):
    accepts_mime_types = ['application/msword']
    produces_mime_types = ['text/plain']

    def convert(self, blob, **kw):
        tmp_dir = self.TMP_DIR
        cur_dir = os.getcwd()
        with make_temp_file(blob, suffix=".doc") as in_fn,\
             make_temp_file(suffix='.txt') as out_fn:
            try:
                os.chdir(str(tmp_dir))
                subprocess.check_call(['abiword', '--to', os.path.basename(
                    out_fn), os.path.basename(in_fn)])
            except Exception as e:
                raise_from(ConversionError('abiword'), e)
            finally:
                os.chdir(cur_dir)

            converted = open(out_fn).read()
            encoding = self.encoding_sniffer.from_file(out_fn)

        if encoding in ("binary", None):
            encoding = "ascii"
        try:
            converted_unicode = unicode(converted, encoding, errors="ignore")
        except:
            traceback.print_exc()
            converted_unicode = unicode(converted, errors="ignore")

        return converted_unicode


class AbiwordPDFHandler(Handler):
    accepts_mime_types = ['application/msword',
                          'application/vnd.oasis.opendocument.text',
                          'text/rtf',]
    produces_mime_types = ['application/pdf']

    def convert(self, blob, **kw):
        cur_dir = os.getcwd()
        with make_temp_file(blob, suffix=".doc") as in_fn,\
             make_temp_file(suffix='.pdf') as out_fn:
            try:
                os.chdir(bytes(self.TMP_DIR))
                subprocess.check_call(['abiword', '--to', os.path.basename(
                    out_fn), os.path.basename(in_fn)])
            except Exception as e:
                raise_from(ConversionError('abiword'), e)
            finally:
                os.chdir(cur_dir)

            converted = open(out_fn).read()
            return converted


class ImageMagickHandler(Handler):
    accepts_mime_types = ['image/.*']
    produces_mime_types = ['application/pdf']

    def convert(self, blob, **kw):
        with make_temp_file(blob) as in_fn, make_temp_file() as out_fn:
            try:
                subprocess.check_call(['convert', in_fn, "pdf:" + out_fn])
                converted = open(out_fn).read()
                return converted
            except Exception as e:
                raise_from(ConversionError('convert'), e)


class PdfToPpmHandler(Handler):
    accepts_mime_types = ['application/pdf', 'application/x-pdf']
    produces_mime_types = ['image/jpeg']

    def convert(self, blob, size=500):
        """Size is the maximum horizontal size."""
        l = []
        with make_temp_file(blob) as in_fn, make_temp_file() as out_fn:
            try:
                subprocess.check_call(['pdftoppm', '-jpeg', in_fn, out_fn])
                l = glob.glob("%s-*.jpg" % out_fn)
                l.sort()

                converted_images = []
                for fn in l:
                    converted = resize(open(fn).read(), size, size, mode=FIT)
                    converted_images.append(converted)

                return converted_images
            except Exception as e:
                raise_from(ConversionError('pdftoppm'), e)
            finally:
                for fn in l:
                    try:
                        os.remove(fn)
                    except OSError:
                        pass


class UnoconvPdfHandler(Handler):
    """Handles conversion from office documents (MS-Office, OOo) to PDF.

    Uses unoconv.
    """

    # TODO: add more if needed.
    accepts_mime_types = ['application/vnd.oasis.*', 'application/msword',
                          'application/mspowerpoint',
                          'application/vnd.ms-powerpoint',
                          'application/vnd.ms-excel', 'application/ms-excel',
                          'application/vnd.openxmlformats-officedocument.*',
                          'text/rtf']
    produces_mime_types = ['application/pdf']
    run_timeout = 60
    _process = None
    unoconv = 'unoconv'

    def init_app(self, app):
        unoconv = app.config.get('UNOCONV_LOCATION')
        found = False
        execute_ok = False

        if unoconv:
            found = os.path.isfile(unoconv)
            if found:
                # make absolute path: avoid errors when running with different CWD
                unoconv = os.path.abspath(unoconv)
                execute_ok = os.access(unoconv, os.X_OK)
                if not execute_ok:
                    self.log.warning('Not allowed to execute "{}", fallback to '
                                     '"unoconv"'.format(unoconv))
            else:
                self.log.warning('Cannot find "{}", fallback to "unoconv"'
                                 ''.format(unoconv))
        if (not unoconv or not found or not execute_ok):
            unoconv = 'unoconv'

        self.unoconv = unoconv

    @property
    def unoconv_version(self):
        # Hack for my Mac, FIXME later
        if os.path.exists(
                "/Applications/LibreOffice.app/Contents/program/python"):
            cmd = ['/Applications/LibreOffice.app/Contents/program/python',
                   '/usr/local/bin/unoconv', '--version']
        else:
            cmd = [self.unoconv, '--version']

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        out, err = process.communicate()
        return out

    def convert(self, blob, **kw):
        """
        Unoconv converter called.
        """
        timeout = self.run_timeout
        with make_temp_file(blob) as in_fn, \
                make_temp_file(prefix='tmp-unoconv-', suffix=".pdf") as out_fn:

            # Hack for my Mac, FIXME later
            if os.path.exists(
                    "/Applications/LibreOffice.app/Contents/program/python"):
                cmd = ['/Applications/LibreOffice.app/Contents/program/python',
                       '/usr/local/bin/unoconv', '-f', 'pdf', '-o', out_fn,
                       in_fn]
            else:
                cmd = [self.unoconv, '-f', 'pdf', '-o', out_fn, in_fn]

            def run_uno():
                try:
                    self._process = subprocess.Popen(cmd,
                                                     close_fds=True,
                                                     cwd=bytes(self.TMP_DIR))
                    self._process.communicate()
                except Exception as e:
                    logger.error('run_uno error: %s', bytes(e), exc_info=True)
                    raise_from(ConversionError('unoconv'), e)

            run_thread = threading.Thread(target=run_uno)
            run_thread.start()
            run_thread.join(timeout)

            try:
                if run_thread.is_alive():
                    # timeout reached
                    self._process.terminate()
                    if self._process.poll() is not None:
                        try:
                            self._process.kill()
                        except OSError:
                            logger.warning("Failed to kill process {}".format(
                                self._process))

                    self._process = None
                    raise ConversionError("Conversion timeout ({})".format(
                        timeout))

                converted = open(out_fn).read()
                return converted
            finally:
                self._process = None


class CloudoooPdfHandler(Handler):
    """Handles conversion from OOo to PDF.

    Highly inefficient since file are serialized in base64 over HTTP.

    Deactivated because it's so hard to set up.

    FIXME: needs cleanup, or removal.
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
        with open("data/%s.blob" % new_key, "wb") as fd:
            fd.write(converted)
        return new_key


class WvwareTextHandler(Handler):
    accepts_mime_types = ['application/msword']
    produces_mime_types = ['text/plain']

    def convert(self, blob, **kw):

        with make_temp_file(blob) as in_fn, make_temp_file() as out_fn:
            try:
                subprocess.check_call(['wvText', in_fn, out_fn])
            except Exception as e:
                raise_from(ConversionError('wxText'), e)

            converted = open(out_fn).read()

            encoding = self.encoding_sniffer.from_file(out_fn)
            if encoding in ("binary", None):
                encoding = "ascii"
            try:
                converted_unicode = unicode(
                    converted, encoding, errors="ignore")
            except:
                traceback.print_exc()
                converted_unicode = unicode(converted, errors="ignore")

            return converted_unicode


# Utils
@contextmanager
def make_temp_file(blob=None, prefix='tmp', suffix="", tmp_dir=None):
    if tmp_dir is None:
        tmp_dir = get_tmp_dir()

    fd, filename = mkstemp(dir=str(tmp_dir), prefix=prefix, suffix=suffix)
    if blob is not None:
        fd = os.fdopen(fd, 'wb')
        fd.write(blob)
        fd.close()
    else:
        os.close(fd)

    yield filename
    try:
        os.remove(filename)
    except OSError:
        pass

# Singleton, yuck!
converter = Converter()
converter.register_handler(PdfToTextHandler())
converter.register_handler(PdfToPpmHandler())
converter.register_handler(ImageMagickHandler())

_unoconv_handler = UnoconvPdfHandler()
converter.register_handler(_unoconv_handler)

#converter.register_handler(AbiwordPDFHandler())
#converter.register_handler(AbiwordTextHandler())

# Needs to be rewriten
#converter.register_handler(CloudoooPdfHandler())
