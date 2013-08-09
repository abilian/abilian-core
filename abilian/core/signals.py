"""
All signals used by Abilian Core.

Signals are the main tools used for decoupling applications components by
sending notifications. In short, signals allow certain senders to notify
subscribers that something happened.

Cf. http://flask.pocoo.org/docs/signals/ for detailed documentation.

The main signal is currently :ref:`activity`.
"""

from __future__ import absolute_import

from blinker.base import Namespace

signals = Namespace()

#: This signal is used by the activity streams service and its clients.
activity = signals.signal("activity")


#: Currently not used and subject to change.
entity_created = signals.signal("entity:created")

#: Currently not used and subject to change.
entity_updated = signals.signal("entity:updated")

#: Currently not used and subject to change.
entity_deleted = signals.signal("entity:deleted")

#user_created = signals.signal("user:created")
#user_deleted = signals.signal("user:deleted")

# More signals ?
