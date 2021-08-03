from __future__ import annotations


class ConversionError(Exception):
    pass


class HandlerNotFound(ConversionError):
    pass
