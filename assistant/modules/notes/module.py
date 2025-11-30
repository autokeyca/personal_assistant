"""Notes module - demonstration of custom module creation."""

from assistant.core import Module, ModuleConfig


class NotesModule(Module):
    """Simple note-taking module."""

    def __init__(self, config: ModuleConfig):
        super().__init__(config)

        # Register intents
        self._intents = [
            {
                "intent": "note_add",
                "handler": "handle_note_add",
                "description": "Add a new note",
                "examples": ["note: buy milk", "remember: call Sarah"],
            },
            {
                "intent": "note_list",
                "handler": "handle_note_list",
                "description": "List all notes",
                "examples": ["show notes", "list my notes"],
            },
        ]

        # Register handlers
        from .handlers import handle_note_add, handle_note_list
        self._handlers = {
            "handle_note_add": handle_note_add,
            "handle_note_list": handle_note_list,
        }

    @property
    def name(self) -> str:
        return "notes"

    @property
    def display_name(self) -> str:
        return "Quick Notes"

    @property
    def description(self) -> str:
        return "Simple note-taking and quick memo storage"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self):
        return {
            "max_notes": {
                "type": "int",
                "default": 100,
                "description": "Maximum number of notes to store",
            },
            "auto_delete_days": {
                "type": "int",
                "default": 30,
                "description": "Auto-delete notes older than N days",
            },
        }
