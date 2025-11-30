#!/usr/bin/env python3
"""Comprehensive test suite for Jarvis modular architecture."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from assistant.core.module_loader import ModuleLoader
from assistant.core.module_system import registry


def test_module_discovery():
    """Test 1: Module Discovery"""
    print("\n" + "="*60)
    print("TEST 1: Module Discovery")
    print("="*60)

    loader = ModuleLoader("modules_config.yaml")
    available = loader.get_available_modules()

    print(f"✓ Discovered {len(available)} modules")
    assert len(available) == 7, f"Expected 7 modules, found {len(available)}"

    expected_modules = [
        'todo', 'email', 'calendar', 'reminders',
        'telegram_relay', 'employee_management', 'meta_programming'
    ]

    for module in expected_modules:
        assert module in available, f"Missing module: {module}"
        print(f"  ✓ {module} found")

    print("\n✅ Module discovery test PASSED\n")
    return True


def test_configuration_loading():
    """Test 2: Configuration Loading"""
    print("="*60)
    print("TEST 2: Configuration Loading")
    print("="*60)

    loader = ModuleLoader("modules_config.yaml")
    config = loader.load_config()

    assert 'modules' in config, "Config missing 'modules' section"
    assert 'module_settings' in config, "Config missing 'module_settings' section"

    print(f"✓ Configuration loaded")
    print(f"  Modules configured: {len(config['modules'])}")

    # Check todo module config
    todo_config = config['modules'].get('todo', {})
    assert todo_config.get('enabled') == True, "Todo module should be enabled"
    assert todo_config.get('priority') == 10, "Todo priority should be 10"

    print(f"✓ Todo module configuration:")
    print(f"  Enabled: {todo_config.get('enabled')}")
    print(f"  Priority: {todo_config.get('priority')}")
    print(f"  Config: {todo_config.get('config')}")

    print("\n✅ Configuration loading test PASSED\n")
    return True


def test_module_loading():
    """Test 3: Module Loading"""
    print("="*60)
    print("TEST 3: Module Loading & Registration")
    print("="*60)

    loader = ModuleLoader("modules_config.yaml")
    success = loader.load_all_modules()

    assert success, "Module loading failed"
    print(f"✓ Modules loaded successfully")

    status = loader.get_module_status()
    print(f"  Total: {status['total_modules']}")
    print(f"  Enabled: {status['enabled_modules']}")

    assert status['total_modules'] >= 6, "Expected at least 6 modules loaded"

    print("\n✅ Module loading test PASSED\n")
    return loader


def test_module_registry(loader):
    """Test 4: Module Registry"""
    print("="*60)
    print("TEST 4: Module Registry API")
    print("="*60)

    # Test get specific module
    email_module = registry.get("email")
    assert email_module is not None, "Email module should be registered"
    assert email_module.name == "email", "Module name mismatch"
    assert email_module.owner_only == True, "Email should be owner-only"

    print(f"✓ registry.get('email') works:")
    print(f"  Name: {email_module.name}")
    print(f"  Display: {email_module.display_name}")
    print(f"  Version: {email_module.version}")
    print(f"  Owner-only: {email_module.owner_only}")

    # Test get all modules
    all_modules = registry.get_all()
    print(f"\n✓ registry.get_all() returns {len(all_modules)} modules")

    # Test get enabled modules
    enabled = registry.get_enabled()
    print(f"✓ registry.get_enabled() returns {len(enabled)} modules")

    # Test module info
    info = registry.get_module_info()
    print(f"✓ registry.get_module_info() returns {len(info)} module details")

    print("\n✅ Module registry test PASSED\n")
    return True


def test_module_properties():
    """Test 5: Module Properties"""
    print("="*60)
    print("TEST 5: Module Properties & Metadata")
    print("="*60)

    modules = registry.get_all()

    for module in modules:
        # Test required properties
        assert hasattr(module, 'name'), f"{module} missing name"
        assert hasattr(module, 'display_name'), f"{module} missing display_name"
        assert hasattr(module, 'description'), f"{module} missing description"
        assert hasattr(module, 'version'), f"{module} missing version"

        # Test property values
        assert module.name, "Module name cannot be empty"
        assert module.display_name, "Display name cannot be empty"
        assert module.version, "Version cannot be empty"

        print(f"✓ {module.display_name}")
        print(f"  ID: {module.name}")
        print(f"  Version: {module.version}")
        print(f"  Owner-only: {module.owner_only}")

    print("\n✅ Module properties test PASSED\n")
    return True


def test_owner_only_modules():
    """Test 6: Owner-Only Restrictions"""
    print("="*60)
    print("TEST 6: Owner-Only Module Restrictions")
    print("="*60)

    owner_only_modules = ['email', 'calendar', 'employee_management', 'meta_programming']
    public_modules = ['todo', 'reminders', 'telegram_relay']

    for module_name in owner_only_modules:
        module = registry.get(module_name)
        if module:
            assert module.owner_only == True, f"{module_name} should be owner-only"
            print(f"✓ {module.display_name} is owner-only")

    for module_name in public_modules:
        module = registry.get(module_name)
        if module:
            assert module.owner_only == False, f"{module_name} should be public"
            print(f"✓ {module.display_name} is public")

    print("\n✅ Owner-only restrictions test PASSED\n")
    return True


def test_module_config_schema():
    """Test 7: Module Configuration Schema"""
    print("="*60)
    print("TEST 7: Module Configuration Schema")
    print("="*60)

    # todo module should have a config schema
    # (Note: Only fully implemented modules will have schemas)

    modules_with_schema = []
    for module in registry.get_all():
        schema = module.get_config_schema()
        if schema:
            modules_with_schema.append(module.name)
            print(f"✓ {module.display_name} has config schema:")
            for key, config in schema.items():
                print(f"  - {key}: {config.get('description', 'No description')}")

    print(f"\n✓ {len(modules_with_schema)} modules have configuration schemas")

    print("\n✅ Config schema test PASSED\n")
    return True


def test_priority_ordering():
    """Test 8: Priority-Based Loading"""
    print("="*60)
    print("TEST 8: Priority-Based Module Loading")
    print("="*60)

    loader = ModuleLoader("modules_config.yaml")
    config = loader.load_config()

    # Get priorities
    priorities = {}
    for module_name, module_config in config['modules'].items():
        if module_config.get('enabled'):
            priorities[module_name] = module_config.get('priority', 100)

    # Sort by priority
    sorted_modules = sorted(priorities.items(), key=lambda x: x[1])

    print("✓ Modules sorted by priority (lower = loads first):")
    for module_name, priority in sorted_modules:
        print(f"  {priority:3d} - {module_name}")

    # Verify todo loads before email
    assert priorities.get('todo', 999) < priorities.get('email', 0), \
        "Todo should load before email"

    print("\n✅ Priority ordering test PASSED\n")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("  JARVIS MODULAR ARCHITECTURE TEST SUITE")
    print("="*60)

    tests = [
        ("Module Discovery", test_module_discovery),
        ("Configuration Loading", test_configuration_loading),
        ("Module Loading", test_module_loading),
    ]

    passed = 0
    failed = 0
    loader = None

    try:
        # Run initial tests
        for name, test_func in tests:
            try:
                result = test_func()
                if name == "Module Loading":
                    loader = result  # Save loader for subsequent tests
                passed += 1
            except AssertionError as e:
                print(f"\n❌ {name} FAILED: {e}\n")
                failed += 1
                return
            except Exception as e:
                print(f"\n❌ {name} ERROR: {e}\n")
                failed += 1
                return

        # Run registry tests (need loader first)
        if loader:
            registry_tests = [
                ("Module Registry", lambda: test_module_registry(loader)),
                ("Module Properties", test_module_properties),
                ("Owner-Only Restrictions", test_owner_only_modules),
                ("Config Schema", test_module_config_schema),
                ("Priority Ordering", test_priority_ordering),
            ]

            for name, test_func in registry_tests:
                try:
                    test_func()
                    passed += 1
                except AssertionError as e:
                    print(f"\n❌ {name} FAILED: {e}\n")
                    failed += 1
                except Exception as e:
                    print(f"\n❌ {name} ERROR: {e}\n")
                    failed += 1

        # Summary
        print("="*60)
        print("  TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total:  {passed + failed}")

        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!\n")
            return 0
        else:
            print("\n⚠️  SOME TESTS FAILED\n")
            return 1

    except Exception as e:
        print(f"\n❌ Test suite error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
