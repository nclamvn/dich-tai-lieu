"""Webhook utilities for Integration Bridge"""
import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


async def send_webhook(
    url: str,
    payload: Dict[str, Any],
    max_retries: int = 3,
    timeout: float = 30.0
) -> bool:
    """Send webhook with retry logic"""
    # Add timestamp
    payload["timestamp"] = datetime.utcnow().isoformat()

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code in [200, 201, 202, 204]:
                    return True
                # Retry on server errors
                if response.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                # Don't retry on client errors (4xx)
                return False
        except (httpx.RequestError, httpx.TimeoutException):
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return False
    return False


class WebhookManager:
    """Manage webhook subscriptions"""

    def __init__(self):
        self._subscriptions: Dict[str, set] = {}

    def subscribe(self, event: str, url: str):
        """Subscribe URL to an event"""
        if event not in self._subscriptions:
            self._subscriptions[event] = set()
        self._subscriptions[event].add(url)

    def unsubscribe(self, event: str, url: str):
        """Unsubscribe URL from an event"""
        if event in self._subscriptions:
            self._subscriptions[event].discard(url)

    async def notify(self, event: str, payload: Dict[str, Any]):
        """Notify all subscribers of an event"""
        if event not in self._subscriptions:
            return

        tasks = []
        for url in self._subscriptions[event]:
            full_payload = {"event": event, **payload}
            tasks.append(send_webhook(url, full_payload))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global webhook manager
webhook_manager = WebhookManager()
