from typing import Any, Dict, Optional, Tuple, Type

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import String, TypeDecorator


class ValueSingletonMeta(type):
    def __new__(
        mcs: Type["ValueSingletonMeta"],
        name: str,
        bases: Tuple[Type],
        dct: Dict[str, Any],
    ) -> Type:
        dct["__instances__"] = {}
        dct.setdefault("__slots__", ())
        new_type = type.__new__(mcs, name, bases, dct)
        return new_type

    def __call__(cls, value: Any, *args, **kwargs) -> Any:
        if isinstance(value, cls):
            return value

        if value not in cls.__instances__:
            value_instance = type.__call__(cls, value, *args, **kwargs)
            cls.__instances__[getattr(value_instance, cls.attr)] = value_instance
        return cls.__instances__[value.lower()]


class UniqueName(metaclass=ValueSingletonMeta):
    """Base class to create singletons from strings.

    A subclass of :class:`UniqueName` defines a namespace.
    """

    __slots__ = ("_hash", "__name")
    attr = "name"

    def __init__(self, name: str) -> None:
        self.__name = str(name).strip().lower()
        self._hash = hash(self.__name)

    @property
    def name(self) -> str:
        return self.__name

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.name)})"

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return self._hash == other._hash
        return self.__name == str(other)

    def __hash__(self) -> int:
        return self._hash


class UniqueNameType(TypeDecorator):
    """Sqlalchemy type that stores a subclass of :class:`UniqueName`

    Usage::
    class MySingleton(UniqueName):
        pass

    class MySingletonType(UniqueNameType):
        Type = MySingleton
    """

    impl = String
    Type: type
    default_max_length = 100

    def __init__(self, *args, **kwargs) -> None:
        assert self.Type is not None
        kwargs.setdefault("length", self.default_max_length)
        TypeDecorator.__init__(self, *args, **kwargs)

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        if value is not None:
            value = str(value)
        return value

    def process_result_value(self, value: Optional[str], dialect: Dialect) -> Any:
        if value is not None:
            value = self.Type(value)
        return value
