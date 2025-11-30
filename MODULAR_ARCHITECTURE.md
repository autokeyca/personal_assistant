# Jarvis Modular Architecture

## Overview

Jarvis has been reorganized into a **modular, plugin-based architecture** for easier maintenance, customization, and commercial distribution.

## Architecture

```
assistant/
├── core/                          # Core system (required)
│   ├── module_system.py          # Base Module class & ModuleRegistry
│   ├── module_loader.py          # Module loader from config
│   ├── config.py                 # Configuration management
│   ├── database.py               # Database connection
│   ├── llm.py                    # LLM service
│   ├── auth.py                   # User authentication
│   ├── prompt.py                 # Prompt management
│   └── behavior_config.py        # Runtime configuration
│
├── modules/                       # Feature modules (plugins)
│   ├── todo/                     # Personal todo management
│   │   ├── module.py            # Module definition
│   │   ├── models.py            # Database models
│   │   ├── service.py           # Business logic
│   │   └── handlers.py          # Bot handlers
│   │
│   ├── employee_management/      # Team/employee todos
│   ├── email/                    # Email integration
│   ├── calendar/                 # Calendar integration
│   ├── telegram_relay/           # Telegram messaging
│   ├── reminders/                # Reminder system
│   └── meta_programming/         # Self-modification
│
└── bot/
    └── main.py                    # Bot initialization
```

## Module System

### What is a Module?

A module is a **self-contained feature** with:
- Database models
- Business logic (services)
- Bot handlers
- Scheduled jobs
- Intent definitions

### Module Structure

Each module must have:

```python
# module.py - Module definition
from assistant.core import Module, ModuleConfig

class MyModule(Module):
    @property
    def name(self) -> str:
        return "my_module"  # Unique identifier

    @property
    def display_name(self) -> str:
        return "My Feature"

    @property
    def description(self) -> str:
        return "What this module does"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def owner_only(self) -> bool:
        return False  # True if owner-only feature
```

## Configuration

### modules_config.yaml

Control which modules are enabled:

```yaml
modules:
  todo:
    enabled: true
    priority: 10  # Load order (lower = first)
    config:
      default_priority: medium
      show_completed: false

  email:
    enabled: false  # Disable this module
    priority: 40
    owner_only: true
```

### Priority System

- Lower priority loads first
- Use for dependencies (core features first)
- Range: 1-100

### Module-Specific Config

Each module can define its own configuration:

```yaml
modules:
  todo:
    config:
      default_priority: medium
      follow_up_enabled: true
      reminder_interval: 3600
```

## Module Development

### Creating a New Module

1. **Create directory structure:**

```bash
mkdir -p assistant/modules/my_feature
cd assistant/modules/my_feature
touch __init__.py module.py handlers.py service.py models.py
```

2. **Define the module (`module.py`):**

```python
from assistant.core import Module, ModuleConfig

class MyFeatureModule(Module):
    def __init__(self, config: ModuleConfig):
        super().__init__(config)

        # Register intents
        self._intents = [
            {
                "intent": "my_action",
                "handler": "handle_my_action",
                "description": "What this intent does",
                "examples": ["do something", "perform action"],
            }
        ]

        # Register handlers
        from .handlers import handle_my_action
        self._handlers = {
            "handle_my_action": handle_my_action,
        }

        # Register models
        from .models import MyModel
        self._models = [MyModel]

    @property
    def name(self) -> str:
        return "my_feature"

    @property
    def display_name(self) -> str:
        return "My Feature"

    @property
    def description(self) -> str:
        return "Description of what it does"

    @property
    def version(self) -> str:
        return "1.0.0"
```

3. **Create handlers (`handlers.py`):**

```python
async def handle_my_action(update, context, entities, original_message, existing_message=None, user=None):
    """Handle the my_action intent."""
    # Your handler logic here
    await update.message.reply_text("Action performed!")
```

4. **Create database models (`models.py`):**

```python
from sqlalchemy import Column, Integer, String
from assistant.db.models import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
```

5. **Export the module (`__init__.py`):**

```python
from .module import MyFeatureModule
__all__ = ["MyFeatureModule"]
```

6. **Enable in `modules_config.yaml`:**

```yaml
modules:
  my_feature:
    enabled: true
    priority: 50
    config:
      some_setting: value
```

## Module Capabilities

### Handlers

Handlers process user commands:

```python
self._handlers = {
    "handle_todo_add": handle_todo_add,
    "handle_todo_list": handle_todo_list,
}
```

### Intents

Intents define what the LLM should recognize:

```python
self._intents = [
    {
        "intent": "todo_add",
        "handler": "handle_todo_add",
        "description": "Add a new todo",
        "examples": ["add todo", "create task"],
    }
]
```

### Database Models

Models define data structure:

```python
from .models import Todo, TodoStatus
self._models = [Todo, TodoStatus]
```

### Scheduled Jobs

Jobs run periodically:

```python
self._jobs = [
    {
        "name": "check_reminders",
        "function": check_reminders_job,
        "interval": 60,  # seconds
        "run_on_start": True,
    }
]
```

## Commercial Packaging

### Selling Jarvis

The modular architecture enables:

1. **Feature Tiering:**
   - Basic: todo, reminders
   - Pro: email, calendar
   - Enterprise: employee_management

2. **Custom Builds:**
   - Enable only requested modules
   - White-label different configurations

3. **License Control:**
   ```yaml
   modules:
     premium_feature:
       enabled: false  # Requires license key
   ```

4. **Module Marketplace:**
   - Third-party modules
   - Plugin ecosystem

### Configuration Examples

**Starter Package:**
```yaml
modules:
  todo: {enabled: true}
  reminders: {enabled: true}
  telegram_relay: {enabled: true}
```

**Professional Package:**
```yaml
modules:
  todo: {enabled: true}
  reminders: {enabled: true}
  email: {enabled: true}
  calendar: {enabled: true}
  telegram_relay: {enabled: true}
```

**Enterprise Package:**
```yaml
modules:
  # All features enabled
  todo: {enabled: true}
  employee_management: {enabled: true}
  email: {enabled: true}
  calendar: {enabled: true}
  meta_programming: {enabled: true}
```

## Module Registry API

### Loading Modules

```python
from assistant.core.module_loader import ModuleLoader

loader = ModuleLoader("modules_config.yaml")
loader.load_all_modules()  # Loads enabled modules
```

### Accessing Modules

```python
from assistant.core.module_system import registry

# Get a specific module
todo_module = registry.get("todo")

# Get all enabled modules
enabled = registry.get_enabled()

# Get module info
info = registry.get_module_info()
```

### Runtime Control

```python
# Disable a module
registry.unregister("email")

# Reload a module (dev mode)
loader.reload_module("todo")

# Get module status
status = loader.get_module_status()
```

## Migration Guide

### Migrating Existing Code to Modules

Current code in `assistant/services/` and `assistant/bot/handlers/` needs to be moved into modules.

**Steps:**

1. Create module directory
2. Move service to `module/service.py`
3. Move handlers to `module/handlers.py`
4. Extract models to `module/models.py`
5. Create `module.py` with module definition
6. Register in `modules_config.yaml`

**Example: Email Module**

Before:
```
assistant/services/email.py
assistant/bot/handlers/email.py
```

After:
```
assistant/modules/email/
  ├── module.py       # Module definition
  ├── service.py      # From services/email.py
  ├── handlers.py     # From bot/handlers/email.py
  └── models.py       # Email-related models
```

## Benefits

✅ **Maintainability** - Isolated features, easier debugging
✅ **Customization** - Enable/disable features via config
✅ **Commercial** - Feature tiering, licensing
✅ **Testing** - Test modules independently
✅ **Documentation** - Each module self-documents
✅ **Collaboration** - Teams work on separate modules
✅ **Distribution** - Package only needed modules

## Next Steps

1. ✅ Module system foundation created
2. ✅ Todo module migrated
3. ⏳ Migrate remaining modules (email, calendar, etc.)
4. ⏳ Update bot/main.py to use module loader
5. ⏳ Add module management commands (/modules list, /modules enable)
6. ⏳ Create module marketplace infrastructure

## Support

For questions about module development, see:
- `assistant/core/module_system.py` - Module base class
- `assistant/modules/todo/` - Reference implementation
- `modules_config.yaml` - Configuration reference
