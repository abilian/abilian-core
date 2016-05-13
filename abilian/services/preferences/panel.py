from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class PreferencePanel(object):
    """Base class for preference panels.

    Currently, this class does nothing. I may be useful in the future either
    as just a marker interface (for automatic plugin discovery / registration),
    or to add some common functionnalities. Otherwise, it will be removed.
    """

    def is_accessible(self):
        return True
