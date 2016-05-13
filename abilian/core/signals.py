"""
All signals used by Abilian Core.

Signals are the main tools used for decoupling applications components by
sending notifications. In short, signals allow certain senders to notify
subscribers that something happened.

Cf. http://flask.pocoo.org/docs/signals/ for detailed documentation.

The main signal is currently :obj:`activity`.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from blinker.base import Namespace

signals = Namespace()

#: Triggered at application initialization when all extensions and plugins have
#: been loaded
components_registered = signals.signal("app:components:registered")

#: Trigger when JS api must be registered. At this time :func:`flask.url_for` is
#: usable
register_js_api = signals.signal('app:register-js-api')

#: This signal is used by the activity streams service and its clients.
activity = signals.signal("activity")

#: This signal is sent when user object has been loaded. g.user and current_user
#: are available.
user_loaded = signals.signal('user_loaded')
