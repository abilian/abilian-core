# coding=utf-8
"""Conversion service.

Hardcoded to manage only conversion to PDF, to text and to image series.

Includes result caching (on filesystem).

Assumes poppler-utils and LibreOffice are installed.

TODO: rename Converter into ConversionService ?
"""

from __future__ import absolute_import

from abilian.services.conversion.handlers import (
    PdfToTextHandler,
    PdfToPpmHandler,
    ImageMagickHandler,
    LibreOfficePdfHandler,
)
from .service import Converter, ConversionError, HandlerNotFound

# Singleton, yuck!
converter = Converter()
converter.register_handler(PdfToTextHandler())
converter.register_handler(PdfToPpmHandler())
converter.register_handler(ImageMagickHandler())
converter.register_handler(LibreOfficePdfHandler())

conversion_service = converter

__all__ = (
    "conversion_service",
    "converter",
    "Converter",
    "ConversionError",
    "HandlerNotFound",
)

# converter.register_handler(AbiwordPDFHandler())
# converter.register_handler(AbiwordTextHandler())

# Needs to be rewriten
# converter.register_handler(CloudoooPdfHandler())
