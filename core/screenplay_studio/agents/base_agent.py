"""
Base Agent for Screenplay Studio

Abstract base class for all screenplay generation agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

from ai_providers.unified_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from an agent execution"""
    success: bool
    data: Any
    error: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0


class BaseAgent(ABC):
    """Abstract base class for screenplay agents"""

    name: str = "BaseAgent"
    description: str = "Base agent class"

    def __init__(self, ai_client: Optional[UnifiedLLMClient] = None):
        self.ai_client = ai_client or UnifiedLLMClient()
        self.logger = logging.getLogger(f"screenplay.{self.name}")

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """Execute the agent's main task"""
        pass

    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> tuple[str, int]:
        """Call LLM and return response with token count"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.ai_client.chat(
                messages=messages,
                max_tokens=max_tokens,
            )

            content = response.content if hasattr(response, "content") else str(response)
            tokens = 0
            if hasattr(response, "usage") and response.usage:
                tokens = getattr(response.usage, "total_tokens", 0)

            return content, tokens

        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            raise

    def log_start(self, input_summary: str = ""):
        """Log agent start"""
        self.logger.info(f"Starting {self.name}... {input_summary}")

    def log_complete(self, output_summary: str = ""):
        """Log agent completion"""
        self.logger.info(f"{self.name} complete. {output_summary}")

    def log_error(self, error: str):
        """Log agent error"""
        self.logger.error(f"{self.name} failed: {error}")
