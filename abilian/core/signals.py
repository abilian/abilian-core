"""
All signals used by Abilian Core.

Signals are the main tools used for decoupling applications components by
sending notifications. In short, signals allow certain senders to notify
subscribers that something happened.

Cf. http://flask.pocoo.org/docs/signals/ for detailed documentation.

The main signal is currently :obj:`activity`.
"""

from __future__ import absolute_import

from blinker.base import Namespace

signals = Namespace()

#: Triggered at application initialization when all extensions and plugins have
#: been loaded
components_registered = signals.signal("app:components:registered")

#: This signal is used by the activity streams service and its clients.
activity = signals.signal("activity")

#: This signal is sent when user object has been loaded. g.user and current_user
#: are available.
user_loaded = signals.signal('user_loaded')

#: Currently not used and subject to change.
entity_created = signals.signal("entity:created")

#: Currently not used and subject to change.
entity_updated = signals.signal("entity:updated")

#: Currently not used and subject to change.
entity_deleted = signals.signal("entity:deleted")

#user_created = signals.signal("user:created")
#user_deleted = signals.signal("user:deleted")

# More signals ?
