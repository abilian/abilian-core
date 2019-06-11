from pkgutil import extend_path

# pyre-fixme[18]: Global name `__path__` is undefined.
__path__ = extend_path(__path__, __name__)
