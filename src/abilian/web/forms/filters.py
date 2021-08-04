"""Field filters for WTForm."""
from __future__ import annotations

from typing import Union

__all__ = ["strip", "uppercase", "lowercase"]


def strip(data: None | int | str) -> int | str:
    """Strip data if data is a string."""
    if data is None:
        return ""
    if not isinstance(data, str):
        return data
    return data.strip()


def uppercase(data: None | int | str) -> None | int | str:
    if not isinstance(data, str):
        return data
    return data.upper()


def lowercase(data: None | int | str) -> None | int | str:
    if not isinstance(data, str):
        return data
    return data.lower()
