import logging
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional

from flask import current_app

from abilian.core.util import fqcn

if TYPE_CHECKING:
    from abilian.app import Application


class ServiceNotRegistered(Exception):
    pass


class ServiceState:
    """Service state stored in Application.extensions."""

    #: reference to :class:`Service` instance
    service: "Service"

    running = False

    def __init__(self, service: "Service", running: bool = False) -> None:
        self.service = service
        self.running = running
        self.logger = logging.getLogger(fqcn(self.__class__))


class Service:
    """Base class for services."""

    #: State class to use for this Service
    AppStateClass = ServiceState

    #: service name in Application.extensions / Application.services
    name = ""

    def __init__(self, app: Optional[Any] = None) -> None:
        if self.name is None:
            msg = f"Service must have a name ({fqcn(self.__class__)})"
            raise ValueError(msg)

        self.logger = logging.getLogger(fqcn(self.__class__))
        if app:
            self.init_app(app)

    def init_app(self, app: "Application") -> None:
        app.extensions[self.name] = self.AppStateClass(self)
        app.services[self.name] = self

    def start(self, ignore_state: bool = False) -> None:
        """Starts the service."""
        self.logger.debug("Start service")
        self._toggle_running(True, ignore_state)

    def stop(self, ignore_state: bool = False) -> None:
        """Stops the service."""
        self.logger.debug("Stop service")
        self._toggle_running(False, ignore_state)

    def _toggle_running(self, run_state: bool, ignore_state: bool = False) -> None:
        state = self.app_state
        run_state = bool(run_state)
        if not ignore_state:
            assert run_state ^ state.running
        state.running = run_state

    @property
    def app_state(self) -> Any:
        """Current service state in current application.

        :raise:RuntimeError if working outside application context.
        """
        try:
            return current_app.extensions[self.name]
        except KeyError:
            raise ServiceNotRegistered(self.name)

    @property
    def running(self) -> bool:
        """
        :returns: `False` if working outside application context, if service is
            not registered on current application, or if service is halted
            for current application.
        """
        try:
            return self.app_state.running
        except (RuntimeError, ServiceNotRegistered):
            # RuntimeError: happens when current_app is None: working outside
            # application context
            return False

    @staticmethod
    def if_running(meth: Callable) -> Callable:
        """Decorator for service methods that must be ran only if service is in
        running state."""

        @wraps(meth)
        def check_running(self: Any, *args: Any, **kwargs: Any) -> Optional[Any]:
            if not self.running:
                return
            return meth(self, *args, **kwargs)

        return check_running
