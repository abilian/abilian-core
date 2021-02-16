""""""


class Taggable:
    """Mixin trait for taggable objects.

    Currently not used.
    """


class TagService:
    """The tag service."""

    def tag(self, obj, term, user=None):
        """Apply a tag on a taggable object.

        If user is None, uses the current logged in user.
        """

    def untag(self, obj, term, user=None):
        """Remove the given tag from the given object.

        See tag().
        """

    def get_objects_tagged_with(self, term):
        """Returns a list of objects tagged with a given term."""

    def get_tags_applied_on(self, obj):
        """Returns a list of tags applied on a given document."""
