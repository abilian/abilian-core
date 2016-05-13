from __future__ import (absolute_import, division, print_function,
                        unicode_literals)


class PrivateMessage(object):
    # TODO
    pass


class PrivateMessageService(object):

    def messages(self, user=None, page=0, per_page=50, filter=None):
        """Return the list of messages received by the given user (or current
    user if user=None).
    """

    def send(self, dest_user, subject, body, url=None):
        """Send a message to the destination user.
    """


class MessageService(object):
    # TODO
    pass
