from typing import Any


class PreferencePanel:
    """Base class for preference panels.

    Currently, this class does nothing. I may be useful in the future
    either as just a marker interface (for automatic plugin discovery /
    registration), or to add some common functionnalities. Otherwise, it
    will be removed.
    """

    id: str
    label: Any

    def is_accessible(self):
        return True

    def get(self):
        raise NotImplementedError

    def post(self):
        raise NotImplementedError
