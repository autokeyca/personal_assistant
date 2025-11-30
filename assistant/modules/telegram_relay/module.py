from assistant.core import Module, ModuleConfig

class TelegramRelayModule(Module):
    @property
    def name(self) -> str:
        return "telegram_relay"
    @property
    def display_name(self) -> str:
        return "Telegram Relay"
    @property
    def description(self) -> str:
        return "Send Telegram messages between users"
    @property
    def version(self) -> str:
        return "1.0.0"
