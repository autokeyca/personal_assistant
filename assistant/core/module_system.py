"""Module system for plugin-based architecture."""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ModuleConfig:
    """Configuration for a module."""
    enabled: bool = True
    priority: int = 100  # Lower = loads first
    dependencies: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


class Module(ABC):
    """Base class for all Jarvis modules."""

    def __init__(self, config: ModuleConfig):
        """
        Initialize the module.

        Args:
            config: Module configuration
        """
        self.config = config
        self.enabled = config.enabled
        self._handlers = {}
        self._jobs = []
        self._intents = []
        self._models = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Module name (unique identifier)."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable module name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Module description."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Module version."""
        pass

    @property
    def author(self) -> str:
        """Module author."""
        return "Jarvis Team"

    @property
    def owner_only(self) -> bool:
        """Whether this module is restricted to owner only."""
        return False

    def initialize(self) -> bool:
        """
        Initialize the module.
        Called when the module is loaded.

        Returns:
            True if initialization succeeded
        """
        logger.info(f"Initializing module: {self.display_name}")
        return True

    def shutdown(self):
        """Cleanup when module is unloaded."""
        logger.info(f"Shutting down module: {self.display_name}")

    def get_handlers(self) -> Dict[str, Callable]:
        """
        Get message handlers for this module.

        Returns:
            Dict mapping handler names to handler functions
        """
        return self._handlers

    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get scheduled jobs for this module.

        Returns:
            List of job definitions with:
            - name: Job name
            - function: Job function
            - interval: Interval in seconds
            - run_on_start: Whether to run immediately
        """
        return self._jobs

    def get_intents(self) -> List[Dict[str, str]]:
        """
        Get intent definitions for command parsing.

        Returns:
            List of intent definitions with:
            - intent: Intent name (e.g., 'todo_add')
            - handler: Handler function name
            - description: Intent description for LLM
            - examples: Example phrases
        """
        return self._intents

    def get_models(self) -> List[Any]:
        """
        Get database models for this module.

        Returns:
            List of SQLAlchemy model classes
        """
        return self._models

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this module.

        Returns:
            Dict describing configurable parameters
        """
        return {}

    def __repr__(self):
        return f"<Module: {self.display_name} v{self.version} (enabled={self.enabled})>"


class ModuleRegistry:
    """Registry for managing Jarvis modules."""

    def __init__(self):
        self._modules: Dict[str, Module] = {}
        self._initialized = False

    def register(self, module: Module):
        """
        Register a module.

        Args:
            module: Module instance to register
        """
        if module.name in self._modules:
            logger.warning(f"Module {module.name} already registered, replacing")

        self._modules[module.name] = module
        logger.info(f"Registered module: {module.display_name} v{module.version}")

    def unregister(self, module_name: str):
        """Unregister a module."""
        if module_name in self._modules:
            module = self._modules[module_name]
            module.shutdown()
            del self._modules[module_name]
            logger.info(f"Unregistered module: {module_name}")

    def get(self, module_name: str) -> Optional[Module]:
        """Get a module by name."""
        return self._modules.get(module_name)

    def get_all(self) -> List[Module]:
        """Get all registered modules."""
        return list(self._modules.values())

    def get_enabled(self) -> List[Module]:
        """Get all enabled modules."""
        return [m for m in self._modules.values() if m.enabled]

    def initialize_all(self) -> bool:
        """
        Initialize all enabled modules in dependency order.

        Returns:
            True if all modules initialized successfully
        """
        if self._initialized:
            logger.warning("Modules already initialized")
            return True

        # Sort by priority (lower = first)
        modules = sorted(self.get_enabled(), key=lambda m: m.config.priority)

        # Initialize in order
        for module in modules:
            try:
                if not module.initialize():
                    logger.error(f"Failed to initialize module: {module.name}")
                    return False
            except Exception as e:
                logger.error(f"Error initializing module {module.name}: {e}")
                return False

        self._initialized = True
        logger.info(f"Initialized {len(modules)} modules")
        return True

    def shutdown_all(self):
        """Shutdown all modules."""
        for module in self._modules.values():
            try:
                module.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down module {module.name}: {e}")

        self._initialized = False

    def get_all_handlers(self) -> Dict[str, Callable]:
        """Get all handlers from enabled modules."""
        handlers = {}
        for module in self.get_enabled():
            handlers.update(module.get_handlers())
        return handlers

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from enabled modules."""
        jobs = []
        for module in self.get_enabled():
            module_jobs = module.get_jobs()
            # Add module name to each job
            for job in module_jobs:
                job['module'] = module.name
            jobs.extend(module_jobs)
        return jobs

    def get_all_intents(self) -> List[Dict[str, str]]:
        """Get all intents from enabled modules."""
        intents = []
        for module in self.get_enabled():
            intents.extend(module.get_intents())
        return intents

    def get_all_models(self) -> List[Any]:
        """Get all database models from enabled modules."""
        models = []
        for module in self.get_enabled():
            models.extend(module.get_models())
        return models

    def get_module_info(self) -> List[Dict[str, Any]]:
        """Get information about all modules."""
        return [
            {
                "name": m.name,
                "display_name": m.display_name,
                "description": m.description,
                "version": m.version,
                "author": m.author,
                "enabled": m.enabled,
                "owner_only": m.owner_only,
            }
            for m in self._modules.values()
        ]


# Global module registry instance
registry = ModuleRegistry()
