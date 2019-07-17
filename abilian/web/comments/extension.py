""""""

from flask import Flask

from abilian.core.models import comment as comments
from abilian.web import url_for

from .forms import CommentForm
from .views import COMMENT_BUTTON
from .views import bp as blueprint


class CommentExtension:
    """API for comments, installed as an application extension.

    It is also available in templates as `comments`.
    """

    def __init__(self, app: Flask) -> None:
        app.extensions["comments"] = self
        app.add_template_global(self, "comments")
        app.register_blueprint(blueprint)

    def is_commentable(self, obj):
        return comments.is_commentable(obj)

    def for_entity(self, obj, check_commentable=False):
        return comments.for_entity(obj, check_commentable=check_commentable)

    def has_comments(self, obj):
        return bool(comments.for_entity(obj, check_commentable=True))

    def count(self, obj):
        return len(comments.for_entity(obj, check_commentable=True))

    def get_form_context(self, obj):
        """Return a dict: form instance, action button, submit url...

        Used by macro m_comment_form(entity)
        """
        return {
            "url": url_for("comments.create", entity_id=obj.id),
            "form": CommentForm(),
            "buttons": [COMMENT_BUTTON],
        }
