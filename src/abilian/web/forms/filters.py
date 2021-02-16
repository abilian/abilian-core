"""Field filters for WTForm."""
from typing import Union

__all__ = ["strip", "uppercase", "lowercase"]


def strip(data: Union[None, int, str]) -> Union[int, str]:
    """Strip data if data is a string."""
    if data is None:
        return ""
    if not isinstance(data, str):
        return data
    return data.strip()


def uppercase(data: Union[None, int, str]) -> Union[None, int, str]:
    if not isinstance(data, str):
        return data
    return data.upper()


def lowercase(data: Union[None, int, str]) -> Union[None, int, str]:
    if not isinstance(data, str):
        return data
    return data.lower()
