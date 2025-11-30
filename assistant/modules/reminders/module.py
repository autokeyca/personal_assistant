from assistant.core import Module, ModuleConfig

class RemindersModule(Module):
    @property
    def name(self) -> str:
        return "reminders"
    @property
    def display_name(self) -> str:
        return "Reminders"
    @property
    def description(self) -> str:
        return "Scheduled reminders and notifications"
    @property
    def version(self) -> str:
        return "1.0.0"
