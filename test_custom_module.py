#!/usr/bin/env python3
"""Test custom module creation - Notes module example."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assistant.core.module_loader import ModuleLoader
from assistant.core.module_system import registry


def test_custom_module():
    """Test creating and loading a custom Notes module."""

    print("\n" + "="*60)
    print("  CUSTOM MODULE CREATION TEST")
    print("  Testing: Notes Module")
    print("="*60)

    # Load modules
    print("\n1. Loading modules...")
    loader = ModuleLoader("modules_config.yaml")
    loader.load_all_modules()

    # Check if notes module discovered
    print("\n2. Checking module discovery...")
    available = loader.get_available_modules()
    print(f"   Available modules: {len(available)}")

    if 'notes' in available:
        print("   ✅ Notes module discovered")
    else:
        print("   ❌ Notes module NOT discovered")
        return False

    # Check if notes module loaded
    print("\n3. Checking module loading...")
    notes_module = registry.get("notes")

    if notes_module is None:
        print("   ❌ Notes module failed to load")
        return False

    print(f"   ✅ Notes module loaded successfully")
    print(f"      Name: {notes_module.name}")
    print(f"      Display: {notes_module.display_name}")
    print(f"      Version: {notes_module.version}")
    print(f"      Description: {notes_module.description}")

    # Check module properties
    print("\n4. Verifying module properties...")
    assert notes_module.name == "notes", "Name mismatch"
    assert notes_module.display_name == "Quick Notes", "Display name mismatch"
    assert notes_module.version == "1.0.0", "Version mismatch"
    print("   ✅ All properties correct")

    # Check intents
    print("\n5. Checking registered intents...")
    intents = notes_module.get_intents()
    print(f"   Registered intents: {len(intents)}")

    for intent in intents:
        print(f"   ✅ {intent['intent']}")
        print(f"      Handler: {intent['handler']}")
        print(f"      Description: {intent['description']}")
        print(f"      Examples: {intent.get('examples', [])}")

    assert len(intents) == 2, "Should have 2 intents"

    # Check handlers
    print("\n6. Checking registered handlers...")
    handlers = notes_module.get_handlers()
    print(f"   Registered handlers: {len(handlers)}")

    for name, func in handlers.items():
        print(f"   ✅ {name}")
        print(f"      Function: {func.__name__}")

    assert len(handlers) == 2, "Should have 2 handlers"
    assert 'handle_note_add' in handlers, "Missing handle_note_add"
    assert 'handle_note_list' in handlers, "Missing handle_note_list"

    # Check config schema
    print("\n7. Checking configuration schema...")
    schema = notes_module.get_config_schema()
    print(f"   Config parameters: {len(schema)}")

    for key, config in schema.items():
        print(f"   ✅ {key}")
        print(f"      Type: {config['type']}")
        print(f"      Default: {config['default']}")
        print(f"      Description: {config['description']}")

    assert 'max_notes' in schema, "Missing max_notes config"
    assert 'auto_delete_days' in schema, "Missing auto_delete_days config"

    # Check module config from YAML
    print("\n8. Checking loaded configuration...")
    config = notes_module.config.config
    print(f"   max_notes: {config.get('max_notes')}")
    print(f"   auto_delete_days: {config.get('auto_delete_days')}")

    assert config.get('max_notes') == 50, "max_notes should be 50"
    assert config.get('auto_delete_days') == 30, "auto_delete_days should be 30"
    print("   ✅ Configuration loaded correctly from YAML")

    # Check priority
    print("\n9. Checking priority...")
    priority = notes_module.config.priority
    print(f"   Priority: {priority}")
    assert priority == 15, "Priority should be 15"
    print("   ✅ Priority set correctly")

    # Summary
    print("\n" + "="*60)
    print("  ✅ ALL CUSTOM MODULE TESTS PASSED!")
    print("="*60)
    print("\n📝 Notes Module Successfully:")
    print("   • Discovered by module loader")
    print("   • Loaded and registered")
    print("   • Has correct metadata")
    print("   • Registered 2 intents")
    print("   • Registered 2 handlers")
    print("   • Defined config schema")
    print("   • Loaded config from YAML")
    print("   • Set correct priority")

    print("\n💡 This demonstrates how easy it is to create new modules!")
    print("\nSteps taken:")
    print("   1. Created assistant/modules/notes/ directory")
    print("   2. Created module.py with NotesModule class")
    print("   3. Created handlers.py with handler functions")
    print("   4. Added notes config to modules_config.yaml")
    print("   5. Module automatically discovered and loaded!")

    print("\n🎉 Custom module creation successful!\n")

    return True


if __name__ == "__main__":
    try:
        success = test_custom_module()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
