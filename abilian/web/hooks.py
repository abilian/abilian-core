import os

from flask import Flask

from abilian.core import signals


def init_hooks(app: Flask) -> None:
    @app.before_first_request
    def set_current_celery_app() -> None:
        """Listener for `before_first_request`.

        Set our celery app as current, so that task use the correct
        config. Without that tasks may use their default set app.
        """
        celery = app.extensions.get("celery")
        if celery:
            celery.set_current()

    @app.before_first_request
    def register_signals() -> None:
        signals.register_js_api.send(app)

    # def install_id_generator(sender, **kwargs):
    #     g.id_generator = count(start=1)
    #
    # appcontext_pushed.connect(install_id_generator)

    if os.environ.get("FLASK_VALIDATE_HTML"):
        # Workaround circular import
        from abilian.testing.validation import validate_response

        app.after_request(validate_response)
