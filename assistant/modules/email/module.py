"""Email module definition."""
from assistant.core import Module, ModuleConfig

class EmailModule(Module):
    @property
    def name(self) -> str:
        return "email"
    @property
    def display_name(self) -> str:
        return "Email Integration"
    @property
    def description(self) -> str:
        return "Gmail integration with notifications and email sending"
    @property
    def version(self) -> str:
        return "1.0.0"
    @property
    def owner_only(self) -> bool:
        return True
