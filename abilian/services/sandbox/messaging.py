class PrivateMessage:
    # TODO
    pass


class PrivateMessageService:
    def messages(self, user=None, page=0, per_page=50, filter=None):
        """Return the list of messages received by the given user (or current
        user if user=None)."""

    def send(self, dest_user, subject, body, url=None):
        """Send a message to the destination user."""


class MessageService:
    # TODO
    pass
