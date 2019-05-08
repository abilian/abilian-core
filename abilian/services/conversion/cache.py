from pathlib import Path
from typing import Tuple

CacheKey = Tuple[str, str]


class Cache:

    cache_dir: Path

    def _path(self, key: CacheKey) -> Path:
        """File path for `key`:"""
        type = key[0]
        uuid = key[1]
        return self.cache_dir / type / f"{uuid}.blob"

    def __contains__(self, key: CacheKey):
        return self._path(key).exists()

    def get(self, key: CacheKey):
        if key in self:
            if key[0] == "txt":
                return self._path(key).read_text("utf8")
            else:
                return self._path(key).read_bytes()
        else:
            return None

    __getitem__ = get

    def set(self, key: CacheKey, value):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if key[0] == "txt":
            path.write_text(value, "utf8")
        else:
            path.write_bytes(value)

    __setitem__ = set

    def clear(self):
        pass
