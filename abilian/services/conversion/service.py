# coding=utf-8
"""Conversion service.

Hardcoded to manage only conversion to PDF, to text and to image series.

Includes result caching (on filesystem).

Assumes poppler-utils and LibreOffice are installed.

TODO: rename Converter into ConversionService ?
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals

import hashlib
import logging
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS
from six import string_types, text_type

from abilian.services.conversion.util import make_temp_file

logger = logging.getLogger(__name__)

TMP_DIR = "tmp"
CACHE_DIR = "cache"


class ConversionError(Exception):
    pass


class HandlerNotFound(ConversionError):
    pass


class Cache(object):

    CACHE_DIR = None

    def _path(self, key):
        """File path for `key`:"""
        return self.CACHE_DIR / "{}.blob".format(key)

    def __contains__(self, key):
        return self._path(key).exists()

    def get(self, key):
        if key in self:
            value = self._path(key).open("rb").read()
            if key.startswith("txt:"):
                value = text_type(value, encoding="utf8")
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
        self.init_work_dirs(
            cache_dir=Path(app.instance_path, CACHE_DIR),
            tmp_dir=Path(app.instance_path, TMP_DIR),
        )

        app.extensions["conversion"] = self

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
        raise HandlerNotFound(
            "No handler found to convert from {} to PDF".format(mime_type)
        )

    def to_text(self, digest, blob, mime_type):
        """Convert a file to plain text.

        Useful for full-text indexing. Returns a Unicode string.
        """
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

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

        raise HandlerNotFound(
            "No handler found to convert from {} to text".format(mime_type)
        )

    def has_image(self, digest, mime_type, index, size=500):
        """Tell if there is a preview image."""
        cache_key = "img:{}:{}:{}".format(index, size, digest)
        return mime_type.startswith("image/") or cache_key in self.cache

    def get_image(self, digest, blob, mime_type, index, size=500):
        """Return an image for the given content, only if it already exists in
        the image cache."""
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

        cache_key = "img:{}:{}:{}".format(index, size, digest)
        return self.cache.get(cache_key)

    def to_image(self, digest, blob, mime_type, index, size=500):
        """Convert a file to a list of images.

        Returns image at the given index.
        """
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

        cache_key = "img:{}:{}:{}".format(index, size, digest)
        converted = self.cache.get(cache_key)
        if converted:
            return converted

        # Direct conversion possible
        for handler in self.handlers:
            if handler.accept(mime_type, "image/jpeg"):
                converted_images = handler.convert(blob, size=size)
                for i in range(0, len(converted_images)):
                    converted = converted_images[i]
                    cache_key = "img:{}:{}:{}".format(i, size, digest)
                    self.cache[cache_key] = converted
                return converted_images[index]

        # Use PDF as a pivot format
        pdf = self.to_pdf(digest, blob, mime_type)
        for handler in self.handlers:
            if handler.accept("application/pdf", "image/jpeg"):
                converted_images = handler.convert(pdf, size=size)
                for i in range(0, len(converted_images)):
                    converted = converted_images[i]
                    cache_key = "img:{}:{}:{}".format(i, size, digest)
                    self.cache[cache_key] = converted
                return converted_images[index]

        raise HandlerNotFound(
            "No handler found to convert from {} to image".format(mime_type)
        )

    def get_metadata(self, digest, content, mime_type):
        """Get a dictionary representing the metadata embedded in the given
        content."""

        # XXX: ad-hoc for now, refactor later
        if mime_type.startswith("image/"):
            img = Image.open(BytesIO(content))
            ret = {}
            if not hasattr(img, "_getexif"):
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
                try:
                    output = subprocess.check_output(["pdfinfo", in_fn])
                except OSError:
                    logger.error("Conversion failed, probably pdfinfo is not installed")
                    raise

            ret = {}
            for line in output.split(b"\n"):
                if b":" in line:
                    key, value = line.strip().split(b":", 1)
                    key = text_type(key)
                    ret["PDF:" + key] = text_type(value.strip(), errors="replace")

            return ret

    @staticmethod
    def digest(blob):
        assert isinstance(blob, string_types)
        if isinstance(blob, str):
            digest = hashlib.md5(blob).hexdigest()
        else:
            digest = hashlib.md5(blob.encode("utf8")).hexdigest()
        return digest
