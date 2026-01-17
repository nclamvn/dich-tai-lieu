from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime

class BaseAgent(ABC):
    """
    Abstract Base Agent for the AI Newsroom.
    All specialized agents (Ghostwriter, Translator, Editor) should inherit from this.
    """

    def __init__(self, agent_id: str, role: str, llm_client: Any):
        self.agent_id = agent_id
        self.role = role  # e.g., "ghostwriter", "editor"
        self.llm_client = llm_client
        self.created_at = datetime.now()

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method.
        Every agent must implement this to handle its specific task.
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return agent status."""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": "ready",
            "uptime": (datetime.now() - self.created_at).total_seconds()
        }
