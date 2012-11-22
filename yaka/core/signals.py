"""
All signals used by Abilian Core.

Cf. http://flask.pocoo.org/docs/signals/ for detailed documentation.

These signals are currently not used, and for this reason subject to change.
"""

from blinker.base import Namespace

signals = Namespace()

entity_created = signals.signal("entity:created")
entity_updated = signals.signal("entity:updated")
entity_deleted = signals.signal("entity:deleted")

#user_created = signals.signal("user:created")
#user_deleted = signals.signal("user:deleted")

activity = signals.signal("activity")
