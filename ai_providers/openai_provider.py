"""
OpenAI Provider - GPT-4, GPT-4o, etc.
AI Publisher Pro - Multi-Provider Support
"""

import base64
from typing import Optional, List, Dict, Any, AsyncIterator

try:
    from openai import AsyncOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .base import (
    BaseAIProvider,
    AIProviderType,
    AIMessage,
    AIResponse,
    AIConfig
)


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI GPT Provider
    
    Supports:
    - GPT-4o (recommended, multimodal)
    - GPT-4o-mini (fast, cost-effective)
    - GPT-4-turbo
    - o1-preview (reasoning)
    - Vision capabilities
    - Streaming
    """
    
    MODELS = {
        "gpt-4o": "GPT-4o (Latest, Multimodal)",
        "gpt-4o-mini": "GPT-4o Mini (Fast)",
        "gpt-4-turbo": "GPT-4 Turbo",
        "gpt-4": "GPT-4",
        "o1-preview": "O1 Preview (Reasoning)",
        "o1-mini": "O1 Mini",
    }
    
    DEFAULT_MODEL = "gpt-4o"
    
    # Models that support vision
    VISION_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4-turbo"}
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OPENAI
    
    @property
    def supported_models(self) -> List[str]:
        return list(self.MODELS.keys())
    
    @property
    def supports_vision(self) -> bool:
        return self.config.model in self.VISION_MODELS
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    async def initialize(self) -> None:
        """Initialize OpenAI client"""
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self._client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url
        )
    
    def _convert_messages(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convert AIMessage to OpenAI format"""
        converted = []
        
        # Add system message if provided
        if system_prompt:
            converted.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            if msg.images and self.supports_vision:
                # Vision message with images
                content = []
                content.append({"type": "text", "text": msg.content})
                for img in msg.images:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64.b64encode(img).decode()}"
                        }
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
        """Generate completion using OpenAI"""
        if not self._client:
            await self.initialize()
        
        api_messages = self._convert_messages(messages, system_prompt)
        
        response = await self._client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=api_messages
        )
        
        choice = response.choices[0]
        
        return AIResponse(
            content=choice.message.content,
            model=response.model,
            provider=self.provider_type,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            } if response.usage else None,
            finish_reason=choice.finish_reason,
            raw_response=response
        )
    
    async def stream(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion using OpenAI"""
        if not self._client:
            await self.initialize()
        
        api_messages = self._convert_messages(messages, system_prompt)
        
        stream = await self._client.chat.completions.create(
            model=kwargs.get("model", self.config.model),
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
            messages=api_messages,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def analyze_document(
        self,
        content: str,
        images: Optional[List[bytes]] = None,
        task: str = "analyze"
    ) -> AIResponse:
        """Analyze document using GPT-4 Vision"""
        
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
        """Translate text using OpenAI"""
        
        system_prompt = f"""You are an expert translator specializing in {source_lang} to {target_lang} translation.

Translation Guidelines:
- Preserve the original meaning, tone, and style
- Maintain formatting (paragraphs, lists, emphasis)
- Keep technical terms, proper nouns, and formulas intact
- Ensure natural, fluent output in the target language

{"Context: " + context if context else ""}

{"Terminology to use: " + str(terminology) if terminology else ""}

Output ONLY the translated text, no explanations."""
        
        messages = [
            AIMessage(role="user", content=text)
        ]
        
        return await self.complete(
            messages,
            system_prompt=system_prompt,
            temperature=0.3
        )
