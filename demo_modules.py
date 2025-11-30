#!/usr/bin/env python3
"""
Demo script showing the Jarvis modular architecture in action.
Run this to see how modules are loaded and managed.
"""

import sys
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from assistant.core.module_loader import ModuleLoader
from assistant.core.module_system import registry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def print_separator(title=""):
    """Print a visual separator."""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    else:
        print(f"{'='*60}\n")


def demo_module_discovery():
    """Demo: Discover available modules."""
    print_separator("Module Discovery")

    loader = ModuleLoader("modules_config.yaml")
    available = loader.get_available_modules()

    print(f"📦 Found {len(available)} available modules:\n")
    for module_name in available:
        print(f"  ✓ {module_name}")


def demo_module_loading():
    """Demo: Load modules from configuration."""
    print_separator("Module Loading")

    loader = ModuleLoader("modules_config.yaml")

    print("Loading modules from configuration...\n")
    success = loader.load_all_modules()

    if success:
        print("✅ All modules loaded successfully!\n")
    else:
        print("❌ Some modules failed to load\n")

    return loader


def demo_module_info(loader):
    """Demo: Display module information."""
    print_separator("Module Information")

    status = loader.get_module_status()

    print(f"📊 Module Status:")
    print(f"  Total modules: {status['total_modules']}")
    print(f"  Enabled modules: {status['enabled_modules']}\n")

    print("📋 Loaded Modules:\n")

    for module_info in status['modules']:
        enabled_icon = "✅" if module_info['enabled'] else "❌"
        owner_badge = " [OWNER]" if module_info['owner_only'] else ""

        print(f"{enabled_icon} {module_info['display_name']}{owner_badge}")
        print(f"   ID: {module_info['name']}")
        print(f"   Version: {module_info['version']}")
        print(f"   {module_info['description']}")
        print()


def demo_module_intents():
    """Demo: Show all registered intents."""
    print_separator("Registered Intents")

    intents = registry.get_all_intents()

    print(f"🎯 {len(intents)} intents registered:\n")

    for intent_info in intents:
        intent = intent_info['intent']
        handler = intent_info['handler']
        desc = intent_info.get('description', 'No description')

        print(f"  • {intent}")
        print(f"    Handler: {handler}")
        print(f"    {desc}")

        if 'examples' in intent_info:
            examples = intent_info['examples'][:2]  # Show first 2 examples
            for example in examples:
                print(f"      Example: \"{example}\"")
        print()


def demo_module_handlers():
    """Demo: Show all registered handlers."""
    print_separator("Registered Handlers")

    handlers = registry.get_all_handlers()

    print(f"⚡ {len(handlers)} handlers registered:\n")

    for name, func in handlers.items():
        print(f"  • {name}")
        print(f"    Function: {func.__name__}")
        if func.__doc__:
            doc = func.__doc__.strip().split('\n')[0]
            print(f"    {doc}")
        print()


def demo_module_jobs():
    """Demo: Show all scheduled jobs."""
    print_separator("Scheduled Jobs")

    jobs = registry.get_all_jobs()

    print(f"⏰ {len(jobs)} scheduled jobs:\n")

    for job in jobs:
        print(f"  • {job['name']} (module: {job.get('module', 'unknown')})")
        print(f"    Interval: {job['interval']}s")
        print(f"    Run on start: {job.get('run_on_start', False)}")
        print()


def demo_runtime_control():
    """Demo: Runtime module control."""
    print_separator("Runtime Control")

    print("Module registry provides runtime control:\n")

    # Get a specific module
    todo_module = registry.get("todo")
    if todo_module:
        print(f"✓ Retrieved todo module: {todo_module.display_name}")
        print(f"  Enabled: {todo_module.enabled}")
        print(f"  Version: {todo_module.version}\n")

    # Get all enabled modules
    enabled = registry.get_enabled()
    print(f"✓ {len(enabled)} modules currently enabled\n")

    # Example: Disable a module (not actually doing it in demo)
    print("Example operations (not executed):")
    print("  - registry.unregister('email')  # Disable email module")
    print("  - loader.reload_module('todo')  # Reload todo module")
    print("  - registry.get_all_models()     # Get all database models")


def demo_commercial_packaging():
    """Demo: Show how modules enable commercial packaging."""
    print_separator("Commercial Packaging Example")

    print("The modular architecture enables flexible packaging:\n")

    packages = {
        "Starter": ["todo", "reminders"],
        "Professional": ["todo", "reminders", "email", "calendar"],
        "Enterprise": ["todo", "reminders", "email", "calendar",
                      "employee_management", "meta_programming"],
    }

    for package_name, modules in packages.items():
        print(f"📦 {package_name} Package:")
        for module in modules:
            print(f"  ✓ {module}")
        print()

    print("Simply configure modules_config.yaml to enable/disable features!")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("  JARVIS MODULAR ARCHITECTURE DEMO")
    print("="*60)

    try:
        # Run demos
        demo_module_discovery()
        loader = demo_module_loading()
        demo_module_info(loader)
        demo_module_intents()
        demo_module_handlers()
        demo_module_jobs()
        demo_runtime_control()
        demo_commercial_packaging()

        print_separator()
        print("✅ Demo completed successfully!")
        print("\nFor more information, see: MODULAR_ARCHITECTURE.md\n")

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n❌ Demo failed: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
