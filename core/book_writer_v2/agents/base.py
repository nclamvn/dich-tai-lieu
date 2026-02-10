"""
Base Agent Class

All agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, Optional, Callable
import logging
import asyncio
from dataclasses import dataclass

from ..config import BookWriterConfig
from ..exceptions import AgentError


T = TypeVar('T')  # Input type
R = TypeVar('R')  # Result type


@dataclass
class AgentContext:
    """Context passed to agents"""
    project_id: str
    config: BookWriterConfig
    progress_callback: Optional[Callable[[str, float], None]] = None

    def report_progress(self, message: str, percentage: float = 0):
        """Report progress to callback if available"""
        if self.progress_callback:
            self.progress_callback(message, percentage)


class BaseAgent(ABC, Generic[T, R]):
    """
    Base class for all Book Writer agents.

    Each agent:
    1. Has a specific role in the pipeline
    2. Takes typed input and produces typed output
    3. Uses AI for content generation
    4. Reports progress
    5. Handles errors gracefully
    """

    def __init__(self, config: BookWriterConfig, ai_client: Any):
        self.config = config
        self.ai = ai_client
        self.logger = logging.getLogger(f"BookWriter.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and progress"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of agent's role"""
        pass

    @abstractmethod
    async def execute(self, input_data: T, context: AgentContext) -> R:
        """Execute the agent's main task."""
        pass

    async def call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Call AI with automatic fallback."""
        try:
            response = await self.ai.generate(
                prompt=prompt,
                system=system_prompt or self.default_system_prompt,
                model=self.config.primary_model,
                max_tokens=max_tokens or self.config.max_tokens_per_call,
                temperature=temperature or self.config.temperature,
            )
            return response

        except Exception as e:
            self.logger.warning(f"Primary model failed: {e}, trying fallback")

            try:
                response = await self.ai.generate(
                    prompt=prompt,
                    system=system_prompt or self.default_system_prompt,
                    model=self.config.fallback_model,
                    max_tokens=max_tokens or self.config.max_tokens_per_call,
                    temperature=temperature or self.config.temperature,
                )
                return response

            except Exception as e2:
                raise AgentError(
                    self.name,
                    f"Both primary and fallback models failed: {e2}",
                    recoverable=False
                )

    @property
    def default_system_prompt(self) -> str:
        """Default system prompt for this agent"""
        return f"""You are the {self.name} agent in a professional book writing system.

Your role: {self.description}

Guidelines:
- Produce high-quality, publication-ready content
- Follow word count targets precisely
- Maintain consistent style and tone
- Be thorough and comprehensive
- Output in the requested format"""

    def count_words(self, text: str) -> int:
        """Count words in text"""
        if not text:
            return 0
        return len(text.split())

    async def retry_with_backoff(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
    ) -> Any:
        """Retry function with exponential backoff."""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)

        raise AgentError(
            self.name,
            f"Failed after {max_retries} attempts: {last_error}",
            recoverable=False
        )
