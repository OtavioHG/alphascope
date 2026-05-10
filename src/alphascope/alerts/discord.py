from __future__ import annotations

import requests


class DiscordNotifier:
    def __init__(self, webhook_url: str | None):
        self.webhook_url = webhook_url

    def send_message(self, message: str) -> bool:
        if not self.webhook_url:
            return False
        response = requests.post(self.webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        return True
