"""Conversion service.

Hardcoded to manage only conversion to PDF, to text and to image series.

Includes result caching (on filesystem).

Assumes poppler-utils and LibreOffice are installed.

TODO: rename Converter into ConversionService ?
"""
import logging
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from typing import List

from flask import Flask
from PIL import Image
from PIL.ExifTags import TAGS

from .cache import Cache
from .exceptions import HandlerNotFound
from .handlers import Handler
from .util import make_temp_file

logger = logging.getLogger(__name__)

TMP_DIR = "tmp"
CACHE_DIR = "cache"


class Converter:
    tmp_dir: Path
    cache_dir: Path
    handlers: List[Handler]

    def __init__(self) -> None:
        self.handlers = []
        self.cache = Cache()

    def init_app(self, app: Flask) -> None:
        self.init_work_dirs(
            cache_dir=Path(app.instance_path, CACHE_DIR),
            tmp_dir=Path(app.instance_path, TMP_DIR),
        )

        app.extensions["conversion"] = self

        for handler in self.handlers:
            handler.init_app(app)

    def init_work_dirs(self, cache_dir: Path, tmp_dir: Path) -> None:
        self.tmp_dir = tmp_dir
        self.cache_dir = cache_dir
        self.cache.cache_dir = self.cache_dir

        if not self.tmp_dir.exists():
            self.tmp_dir.mkdir()
        if not self.cache_dir.exists():
            self.cache_dir.mkdir()

    def clear(self) -> None:
        self.cache.clear()
        for d in (self.tmp_dir, self.cache_dir):
            shutil.rmtree(bytes(d))
            d.mkdir()

    def register_handler(self, handler: Handler) -> None:
        self.handlers.append(handler)

    # TODO: refactor, pass a "File" or "Document" or "Blob" object
    def to_pdf(self, digest: str, blob: bytes, mime_type: str) -> bytes:
        cache_key = ("pdf", digest)
        pdf = self.cache.get_bytes(cache_key)
        if pdf:
            return pdf

        for handler in self.handlers:
            if handler.accept(mime_type, "application/pdf"):
                pdf = handler.convert(blob)
                self.cache[cache_key] = pdf
                return pdf
        raise HandlerNotFound(f"No handler found to convert from {mime_type} to PDF")

    def to_text(self, digest: str, blob: bytes, mime_type: str) -> str:
        """Convert a file to plain text.

        Useful for full-text indexing. Returns a Unicode string.
        """
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

        cache_key = ("txt", digest)

        text = self.cache.get_text(cache_key)
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

        raise HandlerNotFound(f"No handler found to convert from {mime_type} to text")

    def has_image(self, digest, mime_type, index, size=500):
        """Tell if there is a preview image."""
        cache_key = (f"img:{index}:{size}", digest)
        return mime_type.startswith("image/") or cache_key in self.cache

    def get_image(self, digest, blob, mime_type, index, size=500):
        """Return an image for the given content, only if it already exists in
        the image cache."""
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return ""

        cache_key = (f"img:{index}:{size}", digest)
        return self.cache.get(cache_key)

    def to_image(
        self, digest: str, blob: bytes, mime_type: str, index: int, size: int = 500
    ) -> bytes:
        """Convert a file to a list of images.

        Returns image at the given index.
        """
        # Special case, for now (XXX).
        if mime_type.startswith("image/"):
            return b""

        cache_key = (f"img:{index}:{size}", digest)
        converted = self.cache.get_bytes(cache_key)
        if converted:
            return converted

        # Direct conversion possible
        for handler in self.handlers:
            if handler.accept(mime_type, "image/jpeg"):
                converted_images = handler.convert(blob, size=size)
                for i in range(0, len(converted_images)):
                    converted = converted_images[i]
                    cache_key = (f"img:{i}:{size}", digest)
                    self.cache[cache_key] = converted
                return converted_images[index]

        # Use PDF as a pivot format
        pdf = self.to_pdf(digest, blob, mime_type)
        for handler in self.handlers:
            if handler.accept("application/pdf", "image/jpeg"):
                converted_images = handler.convert(pdf, size=size)
                for i in range(0, len(converted_images)):
                    converted = converted_images[i]
                    cache_key = (f"img:{i}:{size}", digest)
                    self.cache[cache_key] = converted
                return converted_images[index]

        raise HandlerNotFound(f"No handler found to convert from {mime_type} to image")

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
                    key = str(key)
                    ret["PDF:" + key] = str(value.strip(), errors="replace")

            return ret
