import importlib
import logging
import pkgutil
from typing import Callable, Generic, Optional, TypeVar

logger = logging.getLogger("agentauth.core.registry")

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry for component discovery and management.

    Supports manual registration via :meth:`register` and automatic discovery
    by scanning packages via :meth:`discover`.
    """

    def __init__(self, name: str):
        self.name = name
        self._registry: dict[str, type[T]] = {}

    def register(self, name: str) -> Callable[[type[T]], type[T]]:
        """Register a class under a specific name via decorator.

        Usage::

            @my_registry.register("my_component")
            class MyComponent:
                ...
        """

        def decorator(cls: type[T]) -> type[T]:
            if name in self._registry:
                logger.warning(
                    "[Registry:%s] Overwriting already registered item: %s", self.name, name
                )
            self._registry[name] = cls
            return cls

        return decorator

    def get(self, name: str) -> Optional[type[T]]:
        """Return the registered class for *name*, or ``None`` if not found."""
        return self._registry.get(name)

    def list_all(self) -> dict[str, type[T]]:
        """Return a copy of the internal registry map."""
        return self._registry.copy()

    def discover(self, package_name: str) -> None:
        """Automatically import all submodules in *package_name*.

        This triggers the execution of ``@registry.register`` decorators in
        those modules.
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as exc:
            logger.error(
                "[Registry:%s] Failed to import package '%s': %s", self.name, package_name, exc
            )
            return

        if not hasattr(package, "__path__"):
            # It's a single module, not a package. Just import it.
            return

        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            try:
                importlib.import_module(module_name)
                logger.debug("[Registry:%s] Discovered module: %s", self.name, module_name)
            except Exception as exc:
                logger.error(
                    "[Registry:%s] Failed to load module '%s': %s", self.name, module_name, exc
                )
