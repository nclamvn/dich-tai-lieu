"""
Mock LLM Client - For Testing Cinema Pipeline Without Real AI

Provides simulated AI responses for scene extraction, screenplay writing, etc.
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MockLLMClient:
    """
    Mock LLM client for testing the cinema pipeline.
    
    Simulates AI responses with realistic structure but placeholder content.
    Useful for testing the pipeline logic without consuming API credits.
    """
    
    def __init__(self, delay: float = 0.5, language: str = "vi"):
        """
        Initialize mock LLM.
        
        Args:
            delay: Simulated response delay in seconds
            language: Response language ("vi" or "en")
        """
        self.delay = delay
        self.language = language
        self._call_count = 0
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> str:
        """
        Simulate LLM completion.
        
        Detects what kind of prompt this is and returns appropriate mock response.
        """
        self._call_count += 1
        
        # Simulate delay
        await asyncio.sleep(self.delay)
        
        logger.debug(f"[MOCK LLM] Call #{self._call_count}, prompt length: {len(prompt)}")
        
        # Detect prompt type and return appropriate mock response
        if "scene" in prompt.lower() and "json" in prompt.lower():
            return self._mock_scene_extraction()
        elif "screenplay" in prompt.lower() or "kịch bản" in prompt.lower():
            return self._mock_screenplay_response()
        elif "boundary" in prompt.lower() or "ranh giới" in prompt.lower():
            return self._mock_boundary_detection()
        else:
            return self._mock_generic_response()
    
    def _mock_scene_extraction(self) -> str:
        """Return mock scene extraction JSON."""
        if self.language == "vi":
            return json.dumps({
                "setting": "Căn phòng ánh sáng mờ, bàn gỗ cũ kỹ bên cửa sổ",
                "time_of_day": "dusk",
                "characters": [
                    {
                        "name": "Nhân vật chính",
                        "description": "Người đàn ông trung niên, mặc áo sơ mi trắng",
                        "emotion": "trầm tư"
                    }
                ],
                "key_actions": [
                    "Nhân vật đứng nhìn ra cửa sổ",
                    "Ánh hoàng hôn chiếu vào phòng"
                ],
                "dialogue": [],
                "mood": "melancholic",
                "lighting_mood": "Ánh sáng vàng dịu từ hoàng hôn",
                "camera_suggestions": [
                    "Wide shot từ góc phòng",
                    "Slow push in về phía nhân vật"
                ]
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "setting": "Dimly lit room, old wooden desk by the window",
                "time_of_day": "dusk",
                "characters": [
                    {
                        "name": "Protagonist",
                        "description": "Middle-aged man in white shirt",
                        "emotion": "pensive"
                    }
                ],
                "key_actions": [
                    "Character stands looking out window",
                    "Sunset light fills the room"
                ],
                "dialogue": [],
                "mood": "melancholic",
                "lighting_mood": "Soft golden sunset light",
                "camera_suggestions": [
                    "Wide shot from room corner",
                    "Slow push in toward character"
                ]
            })
    
    def _mock_screenplay_response(self) -> str:
        """Return mock screenplay JSON."""
        if self.language == "vi":
            return json.dumps({
                "scene_heading": "NỘI. PHÒNG KHÁCH - HOÀNG HÔN",
                "action_lines": [
                    "Căn phòng chìm trong ánh sáng vàng cam của hoàng hôn.",
                    "NHÂN VẬT CHÍNH đứng bên cửa sổ, lưng quay về phía camera."
                ],
                "dialogue": [],
                "transition": "CUT TO:",
                "notes": "Nhấn mạnh sự cô đơn qua không gian rộng và ánh sáng yếu."
            }, ensure_ascii=False)
        else:
            return json.dumps({
                "scene_heading": "INT. LIVING ROOM - DUSK",
                "action_lines": [
                    "The room is bathed in warm orange sunset light.",
                    "PROTAGONIST stands by the window, back to camera."
                ],
                "dialogue": [],
                "transition": "CUT TO:",
                "notes": "Emphasize loneliness through wide space and dim lighting."
            })
    
    def _mock_boundary_detection(self) -> str:
        """Return mock scene boundary detection."""
        return json.dumps({
            "boundaries": [0, 500, 1200, 2000],
            "titles": ["Chapter 1", "Scene 2", "Scene 3", "Chapter 2"],
            "types": ["chapter", "scene", "scene", "chapter"]
        })
    
    def _mock_generic_response(self) -> str:
        """Return generic mock response."""
        if self.language == "vi":
            return "Đây là phản hồi giả lập từ Mock LLM. Trong môi trường production, đây sẽ là phản hồi thực từ AI."
        return "This is a mock response from Mock LLM. In production, this would be a real AI response."
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ):
        """
        Simulate chat completion (alternative interface used by ScreenplayWriter).
        
        Returns object with .content attribute.
        """
        # Extract user message
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break
        
        content = await self.complete(prompt, **kwargs)
        
        # Return object with content attribute
        class MockResponse:
            pass
        response = MockResponse()
        response.content = content
        return response
    
    def get_call_count(self) -> int:
        """Get number of completion calls made."""
        return self._call_count
    
    def reset(self):
        """Reset call counter."""
        self._call_count = 0


# Convenience function for testing
def create_mock_llm(language: str = "vi", delay: float = 0.1) -> MockLLMClient:
    """Create a pre-configured mock LLM client for testing."""
    return MockLLMClient(delay=delay, language=language)
