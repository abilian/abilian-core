import logging
import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import Iterator, Optional, Union

logger = logging.getLogger(__name__)

# Hack for Mac OS + homebrew
os.environ["PATH"] += ":/usr/local/bin"

TMP_DIR = "tmp"
CACHE_DIR = "cache"


def get_tmp_dir() -> Path:
    from . import converter

    # pyre-fixme[16]: `Converter` has no attribute `tmp_dir`.
    return converter.tmp_dir


# Utils
@contextmanager
def make_temp_file(
    blob: Optional[bytes] = None,
    prefix: str = "tmp",
    suffix: str = "",
    tmp_dir: Optional[Path] = None,
) -> Iterator[Union[Iterator, Iterator[str]]]:
    if tmp_dir is None:
        tmp_dir = get_tmp_dir()

    fd, filename = mkstemp(dir=str(tmp_dir), prefix=prefix, suffix=suffix)
    if blob is not None:
        fd = os.fdopen(fd, "wb")
        fd.write(blob)
        fd.close()
    else:
        os.close(fd)

    # pyre-fixme[7]: Expected `Iterator[Union[Iterator[Any], Iterator[str]]]` but
    #  got `Generator[str, None, None]`.
    yield filename
    try:
        os.remove(filename)
    except OSError:
        pass
