"""Module loader for loading Jarvis modules from configuration."""

import logging
import yaml
import importlib
from pathlib import Path
from typing import Dict, List
from .module_system import ModuleRegistry, ModuleConfig, registry

logger = logging.getLogger(__name__)


class ModuleLoader:
    """Loads and initializes Jarvis modules from configuration."""

    def __init__(self, config_path: str = "modules_config.yaml"):
        """
        Initialize the module loader.

        Args:
            config_path: Path to modules configuration file
        """
        self.config_path = Path(config_path)
        self.registry = registry
        self.config = {}

    def load_config(self) -> Dict:
        """Load module configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Module config not found: {self.config_path}, using defaults")
            return {"modules": {}, "module_settings": {}}

        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f) or {}

        logger.info(f"Loaded module configuration from {self.config_path}")
        return self.config

    def get_available_modules(self) -> List[str]:
        """
        Discover available modules in the modules directory.

        Returns:
            List of module names
        """
        modules_dir = Path(__file__).parent.parent / "modules"
        if not modules_dir.exists():
            logger.warning(f"Modules directory not found: {modules_dir}")
            return []

        available = []
        for module_dir in modules_dir.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('_'):
                # Check if module.py exists
                if (module_dir / "module.py").exists():
                    available.append(module_dir.name)

        logger.info(f"Found {len(available)} available modules: {available}")
        return available

    def load_module(self, module_name: str, module_config: Dict) -> bool:
        """
        Load a single module.

        Args:
            module_name: Name of the module to load
            module_config: Module configuration dict

        Returns:
            True if module loaded successfully
        """
        try:
            # Import the module
            module_path = f"assistant.modules.{module_name}"
            module_package = importlib.import_module(module_path)

            # Get the module class (assumes it's named {ModuleName}Module)
            class_name = f"{module_name.replace('_', ' ').title().replace(' ', '')}Module"

            if not hasattr(module_package, class_name):
                logger.error(f"Module {module_name} does not export {class_name}")
                return False

            module_class = getattr(module_package, class_name)

            # Create module config
            config = ModuleConfig(
                enabled=module_config.get('enabled', True),
                priority=module_config.get('priority', 100),
                dependencies=module_config.get('dependencies', []),
                config=module_config.get('config', {})
            )

            # Instantiate and register
            module_instance = module_class(config)
            self.registry.register(module_instance)

            logger.info(f"Loaded module: {module_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
            return False

    def load_all_modules(self) -> bool:
        """
        Load all enabled modules from configuration.

        Returns:
            True if all modules loaded successfully
        """
        # Load configuration
        config = self.load_config()
        modules_config = config.get('modules', {})
        module_settings = config.get('module_settings', {})

        # Get available modules
        available = self.get_available_modules()

        # Load enabled modules
        loaded = 0
        failed = 0

        for module_name in available:
            module_config = modules_config.get(module_name, {})

            # Skip if explicitly disabled
            if not module_config.get('enabled', True):
                logger.info(f"Skipping disabled module: {module_name}")
                continue

            # Load module
            if self.load_module(module_name, module_config):
                loaded += 1
            else:
                failed += 1
                # Check if we should fail on error
                if module_settings.get('fail_on_error', False):
                    logger.error("Failing due to module load error (fail_on_error=true)")
                    return False

        logger.info(f"Module loading complete: {loaded} loaded, {failed} failed")

        # Initialize all loaded modules
        if not self.registry.initialize_all():
            logger.error("Failed to initialize modules")
            return False

        return True

    def reload_module(self, module_name: str) -> bool:
        """
        Reload a module (useful for development).

        Args:
            module_name: Name of module to reload

        Returns:
            True if reload successful
        """
        # Unregister existing module
        self.registry.unregister(module_name)

        # Load configuration
        config = self.load_config()
        module_config = config.get('modules', {}).get(module_name, {})

        # Reload module
        return self.load_module(module_name, module_config)

    def get_module_status(self) -> Dict:
        """
        Get status of all modules.

        Returns:
            Dict with module status information
        """
        return {
            "total_modules": len(self.registry.get_all()),
            "enabled_modules": len(self.registry.get_enabled()),
            "modules": self.registry.get_module_info(),
        }
