from __future__ import annotations

import time
from dataclasses import dataclass

from alphascope.alerts.telegram_command_listener import TelegramCommandListener
from alphascope.config.settings import settings
from alphascope.storage.repositories import StorageRepository


@dataclass(slots=True)
class TelegramBotConfig:
    token: str
    allowed_chat_id: str | None = None
    poll_seconds: int = 1


class PlatformTelegramBot:
    def __init__(
        self,
        config: TelegramBotConfig | None = None,
        repository: StorageRepository | None = None,
    ) -> None:
        self.config = config or TelegramBotConfig(
            token=settings.telegram_bot_token or "",
            allowed_chat_id=settings.telegram_chat_id,
            poll_seconds=settings.telegram_poll_seconds,
        )
        self.repository = repository or StorageRepository()
        self.listener = TelegramCommandListener(repository=self.repository)

    def dispatch_once(self) -> int:
        return self.listener.poll_updates()

    def run_forever(self) -> None:
        self.listener.start()
        try:
            while True:
                time.sleep(self.config.poll_seconds)
        except KeyboardInterrupt:
            self.listener.stop()
