""""""
from flask import current_app
from flask_debugtoolbar.panels import DebugPanel

from abilian.core.util import fqcn
from abilian.i18n import _
from abilian.services import get_service
from abilian.web.action import actions


class IndexedTermsDebugPanel(DebugPanel):
    """A panel to display term values found in index for "current" object.

    FIXME: this notion of "current" object should formalized in
    abilian.app.Application
    """

    name = "IndexedTerms"

    @property
    def current_obj(self):
        return actions.context.get("object")

    @property
    def has_content(self):
        obj = self.current_obj
        return (
            obj is not None
            and hasattr(obj, "object_type")
            and hasattr(obj, "id")
            and obj.id is not None
        )

    def nav_title(self):
        return _("Indexed Terms")

    def nav_subtitle(self):
        """Subtitle showing until title in toolbar."""
        obj = self.current_obj
        if not obj:
            return _("No current object")

        try:
            return f"{obj.__class__.__name__}(id={obj.id})"
        except Exception:
            return ""

    def title(self):
        return _("Indexed Terms")

    def url(self):
        return ""

    def content(self):
        obj = self.current_obj

        index_service = get_service("indexing")
        index = index_service.app_state.indexes["default"]
        schema = index.schema
        context = self.context.copy()
        context["schema"] = schema
        context["sorted_fields"] = sorted(schema.names())

        adapter = index_service.adapted.get(fqcn(obj.__class__))
        if adapter and adapter.indexable:
            doc = context["current_document"] = index_service.get_document(obj, adapter)
            indexed = {}
            for name, field in schema.items():
                value = doc.get(name)
                indexed[name] = None
                if value and field.analyzer and field.format:
                    indexed[name] = list(field.process_text(value))
            context["current_indexed"] = indexed
            context["current_keys"] = sorted(set(doc) | set(indexed))

        with index.searcher() as search:
            document = search.document(object_key=obj.object_key)

        sorted_keys = sorted(document) if document is not None else None

        context.update({"document": document, "sorted_keys": sorted_keys})

        jinja_env = current_app.jinja_env
        jinja_env.filters.update(self.jinja_env.filters)
        template = jinja_env.get_or_select_template("debug_panels/indexing_panel.html")
        return template.render(context)
