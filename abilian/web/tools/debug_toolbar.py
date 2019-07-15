""""""
import sys
from typing import List

from blinker import Namespace, Signal
from flask import current_app, g
from flask_debugtoolbar.panels import DebugPanel

from abilian.web.action import actions


class ActionDebugPanel(DebugPanel):
    name = "Actions"

    user_enable = True
    has_content = True

    def nav_title(self):
        return "Actions"

    def title(self):
        return "Actions"

    def url(self):
        return ""

    def content(self) -> str:
        actions_for_template = []

        for category in actions.actions().keys():
            available_actions = actions.for_category(category)
            for action in available_actions:
                d = {
                    "category": action.category,
                    "title": action.title,
                    "class": action.__class__.__name__,
                }
                try:
                    d["endpoint"] = str(action.endpoint)
                except Exception:
                    d["endpoint"] = "<Exception>"
                try:
                    d["url"] = str(action.url(g.action_context))
                except Exception:
                    d["url"] = "<Exception>"
                actions_for_template.append(d)

        actions_for_template.sort(key=lambda x: (x["category"], x["title"]))

        ctx = {"actions": actions_for_template}

        jinja_env = current_app.jinja_env
        jinja_env.filters.update(self.jinja_env.filters)
        template = jinja_env.get_or_select_template("debug_panels/actions_panel.html")
        return template.render(ctx)


class SignalsDebugPanel(DebugPanel):
    name = "Signals"

    user_enable = True
    has_content = True

    events = []  # type: List[dict]

    def nav_title(self):
        return "Signals"

    def title(self):
        return "Signals"

    def url(self):
        return ""

    def content(self) -> str:
        module_names = sorted(sys.modules.keys())

        signals = []

        for module_name in module_names:
            module = sys.modules[module_name]
            if not module:
                continue
            module_vars = vars(module)
            for var_name, var in module_vars.items():
                if not isinstance(var, Namespace):
                    continue

                ns = var
                ns_name = var_name
                for signal_name, signal in ns.items():
                    receivers = [str(r) for r in signal.receivers.values()]
                    d = {
                        "module_name": module_name,
                        "ns_name": ns_name,
                        "signal_name": signal_name,
                        "signal": signal,
                        "receivers": receivers,
                    }
                    signals.append(d)

        signals.sort(key=lambda d: (d["module_name"], d["ns_name"], d["signal_name"]))

        ctx = {"signals": signals, "events": self.events}

        jinja_env = current_app.jinja_env
        jinja_env.filters.update(self.jinja_env.filters)
        template = jinja_env.get_or_select_template("debug_panels/signals_panel.html")
        return template.render(ctx)

    def process_request(self, request):
        self.events = []

        if getattr(Signal.send, "__wrapped", False):
            return

        orig_send = Signal.send
        events = self.events

        def wrapped_send(self, *sender, **kwargs):
            d = {"signal_name": self.name, "sender": str(sender[0]), "args": kwargs}
            events.append(d)
            return orig_send(self, *sender, **kwargs)

        wrapped_send.__wrapped = True
        Signal.send = wrapped_send
