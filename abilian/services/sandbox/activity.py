"""Another try at an activity service.

See: ActivityStreams, OpenSocial

Note: ICOM also a notion of activity, but it's very different.
"""


class Activity:
    """Persistent object that represents an activity entry."""


class ActivityService:
    def post(self, activity):
        """Post an activity to the service."""

    # Now we need some methods to query the stream
