"""Another try at an activity service.

See: ActivityStreams, OpenSocial

Note: ICOM also a notion of activity, but it's very different.
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class Activity(object):
    """
  Persistent object that represents an activity entry.
  """


class ActivityService(object):

    def post(self, activity):
        """Post an activity to the service.
    """

    # Now we need some methods to query the stream
