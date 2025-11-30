"""Todo module definition."""

from assistant.core import Module, ModuleConfig
from .models import Todo
from .handlers import (
    handle_todo_add,
    handle_todo_list,
    handle_todo_complete,
    handle_todo_delete,
    handle_todo_focus,
)


class TodoModule(Module):
    """Personal todo management module."""

    def __init__(self, config: ModuleConfig):
        super().__init__(config)

        # Register models
        self._models = [Todo]

        # Register intents
        self._intents = [
            {
                "intent": "todo_add",
                "handler": "handle_todo_add",
                "description": "Add a new todo item",
                "examples": [
                    "add todo: buy groceries",
                    "create task: finish report by Friday",
                    "new task: call mom tomorrow",
                ],
            },
            {
                "intent": "todo_list",
                "handler": "handle_todo_list",
                "description": "List all todos or todos for a specific user",
                "examples": [
                    "show my todos",
                    "list tasks",
                    "what's on my todo list",
                    "show Sarah's todos",
                ],
            },
            {
                "intent": "todo_complete",
                "handler": "handle_todo_complete",
                "description": "Mark a todo as completed",
                "examples": [
                    "complete task 5",
                    "mark buy groceries as done",
                    "I finished the report",
                ],
            },
            {
                "intent": "todo_delete",
                "handler": "handle_todo_delete",
                "description": "Delete a todo",
                "examples": [
                    "delete task 3",
                    "remove buy groceries todo",
                ],
            },
            {
                "intent": "todo_focus",
                "handler": "handle_todo_focus",
                "description": "Focus on a specific todo (pin it)",
                "examples": [
                    "focus on task 5",
                    "focus 9",
                    "pin the report task",
                ],
            },
        ]

        # Register handlers
        self._handlers = {
            "handle_todo_add": handle_todo_add,
            "handle_todo_list": handle_todo_list,
            "handle_todo_complete": handle_todo_complete,
            "handle_todo_delete": handle_todo_delete,
            "handle_todo_focus": handle_todo_focus,
        }

    @property
    def name(self) -> str:
        return "todo"

    @property
    def display_name(self) -> str:
        return "Todo Management"

    @property
    def description(self) -> str:
        return "Personal todo list and task management"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_config_schema(self):
        return {
            "default_priority": {
                "type": "string",
                "default": "medium",
                "description": "Default priority for new todos",
                "options": ["low", "medium", "high", "urgent"],
            },
            "show_completed": {
                "type": "boolean",
                "default": False,
                "description": "Show completed todos in list by default",
            },
            "follow_up_enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable automatic follow-up reminders",
            },
        }
