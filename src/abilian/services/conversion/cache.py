from pathlib import Path
from typing import Optional, Tuple, Union

CacheKey = Tuple[str, str]


class Cache:

    cache_dir: Path

    def _path(self, key: CacheKey) -> Path:
        """File path for `key`:"""
        type = key[0]
        uuid = key[1]
        return self.cache_dir / type / f"{uuid}.blob"

    def __contains__(self, key: CacheKey) -> bool:
        return self._path(key).exists()

    def get(self, key: CacheKey) -> Union[str, bytes, None]:
        if key[0] == "txt":
            return self.get_text(key)
        else:
            return self.get_bytes(key)

    __getitem__ = get

    def get_bytes(self, key: CacheKey) -> Optional[bytes]:
        if key in self:
            path = self._path(key)
            return path.read_bytes()
        else:
            return None

    def get_text(self, key: CacheKey) -> Optional[str]:
        if key in self:
            path = self._path(key)
            return path.read_text("utf8")
        else:
            return None

    def set(self, key: CacheKey, value: Union[str, bytes]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if key[0] == "txt":
            assert isinstance(value, str)
            path.write_text(value, "utf8")
        else:
            assert isinstance(value, bytes)
            path.write_bytes(value)

    __setitem__ = set

    def clear(self) -> None:
        pass
