from assistant.core import Module, ModuleConfig

class CalendarModule(Module):
    @property
    def name(self) -> str:
        return "calendar"
    @property
    def display_name(self) -> str:
        return "Calendar Integration"
    @property
    def description(self) -> str:
        return "Google Calendar integration"
    @property
    def version(self) -> str:
        return "1.0.0"
    @property
    def owner_only(self) -> bool:
        return True
