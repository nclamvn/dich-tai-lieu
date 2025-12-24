"""
Google Gemini Provider
AI Publisher Pro - Multi-Provider Support
"""

import base64
from typing import Optional, List, Dict, Any, AsyncIterator

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from .base import (
    BaseAIProvider,
    AIProviderType,
    AIMessage,
    AIResponse,
    AIConfig
)


class GeminiProvider(BaseAIProvider):
    """
    Google Gemini AI Provider
    
    Supports:
    - Gemini 2.0 Flash (latest, multimodal)
    - Gemini 1.5 Pro (high capability)
    - Gemini 1.5 Flash (fast)
    - Vision capabilities
    - Streaming
    """
    
    MODELS = {
        "gemini-2.0-flash-exp": "Gemini 2.0 Flash (Latest)",
        "gemini-1.5-pro": "Gemini 1.5 Pro",
        "gemini-1.5-flash": "Gemini 1.5 Flash",
        "gemini-1.5-flash-8b": "Gemini 1.5 Flash 8B (Fast)",
    }
    
    DEFAULT_MODEL = "gemini-2.0-flash-exp"
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.GEMINI
    
    @property
    def supported_models(self) -> List[str]:
        return list(self.MODELS.keys())
    
    @property
    def supports_vision(self) -> bool:
        return True  # All Gemini models support vision
    
    @property
    def supports_streaming(self) -> bool:
        return True
    
    async def initialize(self) -> None:
        """Initialize Gemini client"""
        if not HAS_GEMINI:
            raise ImportError(
                "google-generativeai package not installed. "
                "Run: pip install google-generativeai"
            )
        
        genai.configure(api_key=self.config.api_key)
        
        # Configure safety settings to be less restrictive for translation
        self._safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        self._client = genai.GenerativeModel(
            model_name=self.config.model,
            safety_settings=self._safety_settings,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
        )
    
    def _convert_messages(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Convert AIMessage to Gemini format"""
        contents = []
        
        # Gemini handles system prompt differently - prepend to first message
        system_text = system_prompt + "\n\n" if system_prompt else ""
        
        for i, msg in enumerate(messages):
            role = "user" if msg.role == "user" else "model"
            
            if msg.images:
                # Vision message with images
                parts = []
                
                # Add system prompt to first message
                text_content = msg.content
                if i == 0 and system_text:
                    text_content = system_text + text_content
                
                parts.append(text_content)
                
                for img in msg.images:
                    parts.append({
                        "mime_type": "image/png",
                        "data": base64.b64encode(img).decode()
                    })
                
                contents.append({"role": role, "parts": parts})
            else:
                text_content = msg.content
                if i == 0 and system_text:
                    text_content = system_text + text_content
                    
                contents.append({"role": role, "parts": [text_content]})
        
        return contents
    
    async def complete(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate completion using Gemini"""
        if not self._client:
            await self.initialize()
        
        contents = self._convert_messages(messages, system_prompt)
        
        # Use async generation
        response = await self._client.generate_content_async(
            contents,
            generation_config={
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
        )
        
        # Extract usage if available
        usage = None
        if hasattr(response, 'usage_metadata'):
            usage = {
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count
            }
        
        return AIResponse(
            content=response.text,
            model=self.config.model,
            provider=self.provider_type,
            usage=usage,
            finish_reason=response.candidates[0].finish_reason.name if response.candidates else None,
            raw_response=response
        )
    
    async def stream(
        self,
        messages: List[AIMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream completion using Gemini"""
        if not self._client:
            await self.initialize()
        
        contents = self._convert_messages(messages, system_prompt)
        
        response = await self._client.generate_content_async(
            contents,
            generation_config={
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_output_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            },
            stream=True
        )
        
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    
    async def analyze_document(
        self,
        content: str,
        images: Optional[List[bytes]] = None,
        task: str = "analyze"
    ) -> AIResponse:
        """Analyze document using Gemini Vision"""
        
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
        """Translate text using Gemini"""
        
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
