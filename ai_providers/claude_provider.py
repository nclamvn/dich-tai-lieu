"""
Claude AI Provider - Anthropic
AI Publisher Pro - Multi-Provider Support
"""

import base64
from typing import Optional, List, Dict, Any, AsyncIterator

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from .base import (
    BaseAIProvider, 
    AIProviderType, 
    AIMessage, 
    AIResponse, 
    AIConfig
)


class ClaudeProvider(BaseAIProvider):
    """
    Anthropic Claude AI Provider
    
    Supports:
    - Claude 3.5 Sonnet (recommended for translation)
    - Claude 3.5 Haiku (fast, cost-effective)
    - Claude 3 Opus (highest quality)
    - Vision capabilities
    - Streaming
    """
    
    MODELS = {
        "claude-sonnet-4-20250514": "Claude Sonnet 4 (Latest)",
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
        "claude-3-5-haiku-20241022": "Claude 3.5 Haiku",
        "claude-3-opus-20240229": "Claude 3 Opus",
    }
    
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.CLAUDE
    
    @property
    def supported_models(self) -> List[str]:
        return list(self.MODELS.keys())
    
    @property
    def supports_vision(self) -> bool:
        return True
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    async def initialize(self) -> None:
        """Initialize Anthropic client"""
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self._client = anthropic.AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    def _convert_messages(
        self, 
        messages: List[AIMessage]
    ) -> List[Dict[str, Any]]:
        """Convert AIMessage to Anthropic format"""
        converted = []
        
        for msg in messages:
            if msg.images:
                # Vision message with images
                content = []
                for img in msg.images:
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64.b64encode(img).decode()
                        }
                    })
                content.append({
                    "type": "text",
                    "text": msg.content
                })
                converted.append({"role": msg.role, "content": content})
            else:
                converted.append({"role": msg.role, "content": msg.content})
        
        return converted
    
    async def complete(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate completion using Claude"""
        if not self._client:
            await self.initialize()
        
        api_messages = self._convert_messages(messages)
        
        response = await self._client.messages.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_prompt or "",
            messages=api_messages
        )
        
        return AIResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.provider_type,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            finish_reason=response.stop_reason,
            raw_response=response
        )
    
    async def stream(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion using Claude"""
        if not self._client:
            await self.initialize()
        
        api_messages = self._convert_messages(messages)
        
        async with self._client.messages.stream(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            system=system_prompt or "",
            messages=api_messages
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def analyze_document(
        self,
        content: str,
        images: Optional[List[bytes]] = None,
        task: str = "analyze"
    ) -> AIResponse:
        """Analyze document using Claude's vision capabilities"""
        
        system_prompt = """You are an expert document analyst. 
Analyze the provided document and extract:
1. Document type and genre
2. Main language
3. Key structural elements (headers, paragraphs, lists, tables)
4. Special content (formulas, code blocks, citations)
5. Terminology and domain-specific terms
6. Writing style and tone

Respond in JSON format."""
        
        messages = [
            AIMessage(
                role="user",
                content=f"Analyze this document:\n\n{content}",
                images=images
            )
        ]
        
        return await self.complete(messages, system_prompt=system_prompt)
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        terminology: Optional[Dict[str, str]] = None
    ) -> AIResponse:
        """Translate text using Claude"""
        
        system_prompt = f"""You are an expert translator specializing in {source_lang} to {target_lang} translation.

Translation Guidelines:
- Preserve the original meaning, tone, and style
- Maintain formatting (paragraphs, lists, emphasis)
- Keep technical terms, proper nouns, and formulas intact
- Ensure natural, fluent output in the target language

{"Context: " + context if context else ""}

{"Terminology to use:" + str(terminology) if terminology else ""}

Output ONLY the translated text, no explanations."""
        
        messages = [
            AIMessage(role="user", content=text)
        ]
        
        return await self.complete(
            messages, 
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for translation
        )
