"""

"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class Taggable(object):
    """
    Mixin trait for taggable objects.

    Currently not used.
    """
    pass


class TagService(object):
    """
    The tag service.
    """

    def tag(self, object, term, user=None):
        """Apply a tag on a taggable object.

        If user is None, uses the current logged in user.
        """

    def untag(self, object, term, user=None):
        """Remove the given tag from the given object. See tag().
        """

    def get_objects_tagged_with(self, term):
        """Returns a list of objects tagged with a given term.
        """

    def get_tags_applied_on(self, object):
        """Returns a list of tags applied on a given document.
        """
