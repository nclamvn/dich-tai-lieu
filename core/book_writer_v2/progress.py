"""
Progress Tracking

Real-time progress updates via WebSocket and callbacks.
"""

import asyncio
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging


@dataclass
class ProgressUpdate:
    """A single progress update"""
    project_id: str
    agent: str
    message: str
    percentage: float
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "agent": self.agent,
            "message": self.message,
            "percentage": self.percentage,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class ProgressTracker:
    """
    Track and broadcast pipeline progress.

    Supports:
    - Callback functions
    - WebSocket broadcasting
    - Progress history
    """

    def __init__(self):
        self.logger = logging.getLogger("BookWriter.Progress")
        self.callbacks: Dict[str, Callable] = {}
        self.history: Dict[str, list] = {}
        self.websockets: Dict[str, list] = {}

    def register_callback(
        self,
        project_id: str,
        callback: Callable[[ProgressUpdate], None]
    ):
        """Register a callback for progress updates"""
        self.callbacks[project_id] = callback

    def unregister_callback(self, project_id: str):
        """Unregister a callback"""
        self.callbacks.pop(project_id, None)

    async def register_websocket(self, project_id: str, websocket):
        """Register a WebSocket connection"""
        if project_id not in self.websockets:
            self.websockets[project_id] = []
        self.websockets[project_id].append(websocket)

    async def unregister_websocket(self, project_id: str, websocket):
        """Unregister a WebSocket connection"""
        if project_id in self.websockets:
            self.websockets[project_id].remove(websocket)

    async def update(
        self,
        project_id: str,
        agent: str,
        message: str,
        percentage: float,
        details: Dict[str, Any] = None,
    ):
        """Send a progress update."""
        update = ProgressUpdate(
            project_id=project_id,
            agent=agent,
            message=message,
            percentage=percentage,
            details=details or {},
        )

        # Store in history
        if project_id not in self.history:
            self.history[project_id] = []
        self.history[project_id].append(update)

        # Call callback if registered
        if project_id in self.callbacks:
            try:
                callback = self.callbacks[project_id]
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                self.logger.warning(f"Callback error: {e}")

        # Broadcast to WebSockets
        if project_id in self.websockets:
            message_json = update.to_json()
            for ws in self.websockets[project_id]:
                try:
                    await ws.send_text(message_json)
                except Exception as e:
                    self.logger.warning(f"WebSocket send error: {e}")

    def get_history(self, project_id: str) -> list:
        """Get progress history for a project"""
        return [u.to_dict() for u in self.history.get(project_id, [])]

    def get_latest(self, project_id: str) -> Optional[dict]:
        """Get latest progress update"""
        history = self.history.get(project_id, [])
        if history:
            return history[-1].to_dict()
        return None

    def clear_history(self, project_id: str):
        """Clear history for a project"""
        self.history.pop(project_id, None)


# Global tracker instance
progress_tracker = ProgressTracker()
