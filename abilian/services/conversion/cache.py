class Cache:

    cache_dir = None

    def _path(self, key: str):
        """File path for `key`:"""
        return self.cache_dir / f"{key}.blob"

    def __contains__(self, key: str):
        return self._path(key).exists()

    def get(self, key: str):
        if key in self:
            value = self._path(key).open("rb").read()
            if key.startswith("txt:"):
                value = str(value, encoding="utf8")
            return value
        else:
            return None

    __getitem__ = get

    def set(self, key: str, value):
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
