"""Draft API for a like service.

Every entity (and even comments) should be likeable.
"""


class Like:
    pass


class LikeService:
    def like(self, object, user=None):
        """Given or current user likes the given likeable object."""

    def dislike(self, object, user=None):
        """Given or current user dislikes the given likeable object."""

    def get_likes_count_on(self, object):
        """Returns the number of likes on the given likeable object."""

    def get_dislikes_count_on(self, object):
        """Returns the number of dislikes on the given likeable object."""

    def get_likes_on(self, object):
        """Returns all the likes (and dislikes) on a given object."""
