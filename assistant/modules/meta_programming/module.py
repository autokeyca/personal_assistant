from assistant.core import Module, ModuleConfig

class MetaProgrammingModule(Module):
    @property
    def name(self) -> str:
        return "meta_programming"
    @property
    def display_name(self) -> str:
        return "Meta-Programming"
    @property
    def description(self) -> str:
        return "Runtime self-modification and code generation"
    @property
    def version(self) -> str:
        return "1.0.0"
    @property
    def owner_only(self) -> bool:
        return True
