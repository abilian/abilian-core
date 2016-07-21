"""Social graph API.

May or may not be needed, since the followers / followees notions are already
implemented in the core model.
"""
from __future__ import absolute_import, division, print_function, \
    unicode_literals


class FollowService(object):

    def get_followers(self, user):
        pass

    def get_followees(self, user):
        pass
