"""
AI Client Adapter for Book Writer v2.0

Adapts the existing AI client (UnifiedLLMClient) to work with Book Writer agents.
"""

from typing import Optional, Any
import logging


class AIClientAdapter:
    """
    Adapter to make existing AI clients work with Book Writer v2.0.

    The Book Writer agents expect an AI client with a `generate` method.
    This adapter wraps existing clients to provide that interface.
    """

    def __init__(self, unified_client: Any):
        self.client = unified_client
        self.logger = logging.getLogger("BookWriter.AIAdapter")

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using the AI client."""
        try:
            # Interface 1: UnifiedLLMClient.chat (primary path)
            if hasattr(self.client, 'chat'):
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = await self.client.chat(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                if isinstance(response, dict):
                    return response.get("content", response.get("text", str(response)))
                if hasattr(response, 'content'):
                    return response.content
                if hasattr(response, 'text'):
                    return response.text
                return str(response)

            # Interface 2: generate_text style
            if hasattr(self.client, 'generate_text'):
                return await self.client.generate_text(
                    prompt=prompt,
                    system_prompt=system,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

            # Interface 3: Anthropic messages API
            if hasattr(self.client, 'messages'):
                messages = [{"role": "user", "content": prompt}]
                response = await self.client.messages.create(
                    model=model or "claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,
                )
                return response.content[0].text

            # Interface 4: Direct callable
            if callable(self.client):
                return await self.client(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

            raise ValueError(f"Unknown AI client interface: {type(self.client)}")

        except Exception as e:
            self.logger.error(f"AI generation failed: {e}")
            raise


class MockAIClient:
    """
    Mock AI client for testing / when no real AI client is available.

    Generates placeholder content with approximate word counts.
    """

    def __init__(self):
        self.logger = logging.getLogger("BookWriter.MockAI")
        self.call_count = 0

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Generate mock content."""
        self.call_count += 1
        prompt_lower = prompt.lower()

        if "analyze" in prompt_lower and "book" in prompt_lower:
            return self._generate_analysis()
        if "structure" in prompt_lower or "blueprint" in prompt_lower:
            return self._generate_structure()
        if "outline" in prompt_lower:
            return self._generate_outline()
        if "write" in prompt_lower and "section" in prompt_lower:
            return self._generate_section_content()
        if "expand" in prompt_lower:
            return self._generate_expanded_content(prompt)
        if "edit" in prompt_lower:
            if "CONTENT TO EDIT:" in prompt:
                parts = prompt.split("CONTENT TO EDIT:")[1].split("---")
                if len(parts) > 1:
                    return parts[1].strip()
            return self._generate_section_content()

        return self._generate_generic_content()

    def _generate_analysis(self) -> str:
        return '''```json
{
    "topic_summary": "This book provides a comprehensive exploration of the subject matter.",
    "target_audience": "Professionals and enthusiasts seeking to deepen their understanding",
    "audience_profile": {
        "demographics": "Adults aged 25-55, college-educated professionals",
        "knowledge_level": "Intermediate",
        "pain_points": ["Lack of comprehensive resources"],
        "goals": ["Master the subject"]
    },
    "key_themes": ["Foundation concepts", "Practical applications", "Future trends", "Best practices", "Case studies"],
    "key_messages": ["Knowledge is power", "Practice leads to mastery", "Innovation drives success"],
    "unique_value": "Combines theoretical depth with practical applicability",
    "competitive_landscape": [
        {"title": "Similar Book A", "gap": "More practical examples"}
    ],
    "recommended_structure": {
        "num_parts": 3,
        "chapters_per_part": 4,
        "suggested_parts": ["Foundations", "Applications", "Advanced Topics"]
    },
    "tone_and_style": "Professional yet accessible, with real-world examples",
    "content_warnings": [],
    "research_notes": "Include current industry data and expert interviews"
}
```'''

    def _generate_structure(self) -> str:
        return '''```json
[
    {
        "title": "Part 1: Foundations",
        "chapters": [
            {
                "title": "Chapter 1: Introduction and Overview",
                "sections": [
                    {"title": "The Landscape Today"},
                    {"title": "Historical Context"},
                    {"title": "Key Concepts"},
                    {"title": "Why This Matters"}
                ]
            },
            {
                "title": "Chapter 2: Core Principles",
                "sections": [
                    {"title": "Fundamental Theories"},
                    {"title": "Building Blocks"},
                    {"title": "Common Patterns"},
                    {"title": "Practical Framework"}
                ]
            },
            {
                "title": "Chapter 3: Getting Started",
                "sections": [
                    {"title": "Prerequisites"},
                    {"title": "First Steps"},
                    {"title": "Common Pitfalls"},
                    {"title": "Success Metrics"}
                ]
            }
        ]
    },
    {
        "title": "Part 2: Applications",
        "chapters": [
            {
                "title": "Chapter 4: Real-World Applications",
                "sections": [
                    {"title": "Industry Use Cases"},
                    {"title": "Implementation Strategies"},
                    {"title": "Case Study Analysis"},
                    {"title": "Lessons Learned"}
                ]
            },
            {
                "title": "Chapter 5: Advanced Techniques",
                "sections": [
                    {"title": "Beyond Basics"},
                    {"title": "Optimization Methods"},
                    {"title": "Scaling Considerations"},
                    {"title": "Performance Tuning"}
                ]
            }
        ]
    },
    {
        "title": "Part 3: Mastery",
        "chapters": [
            {
                "title": "Chapter 6: Expert Strategies",
                "sections": [
                    {"title": "Advanced Concepts"},
                    {"title": "Expert Insights"},
                    {"title": "Cutting-Edge Approaches"},
                    {"title": "Innovation Patterns"}
                ]
            },
            {
                "title": "Chapter 7: Future Directions",
                "sections": [
                    {"title": "Emerging Trends"},
                    {"title": "Technology Roadmap"},
                    {"title": "Preparing for Change"},
                    {"title": "Continuous Learning"}
                ]
            }
        ]
    }
]
```'''

    def _generate_outline(self) -> str:
        return '''```json
{
    "summary": "This section covers essential concepts and provides a foundation for understanding the broader topic.",
    "points": [
        {"content": "Opening Hook - Engaging introduction", "words": 150, "notes": "Use a real-world example"},
        {"content": "Context and Background", "words": 300, "notes": "Provide necessary background"},
        {"content": "Core Concepts explained clearly", "words": 400, "notes": "Clear explanations with examples"},
        {"content": "Practical Example walkthrough", "words": 350, "notes": "Make it relatable"},
        {"content": "Key Insights and implications", "words": 200, "notes": "Summarize takeaways"},
        {"content": "Transition to next section", "words": 100, "notes": "Smooth flow"}
    ]
}
```'''

    def _generate_section_content(self) -> str:
        paragraphs = [
            "The foundation of any successful endeavor lies in understanding the core principles that govern it. When we examine the landscape of modern practices, we find a rich tapestry of interconnected concepts that have evolved over decades of research and practical application. These principles, while sometimes appearing abstract, have profound implications for how we approach challenges and opportunities in our daily work.",
            "Consider, for example, the way experts in this field approach problem-solving. Rather than jumping directly to solutions, they first seek to understand the underlying dynamics at play. This systematic approach, refined through years of experience, allows them to identify patterns that might otherwise go unnoticed. The ability to recognize these patterns is what separates novices from masters.",
            "Historical context provides valuable insights into how current practices developed. In the early days, practitioners worked with limited tools and resources, yet they managed to establish frameworks that continue to influence our thinking today. Understanding this evolution helps us appreciate not only where we are but also where we might be heading.",
            "The practical applications of these concepts extend far beyond theoretical discussions. In real-world settings, professionals apply these principles to solve complex problems and create innovative solutions. Whether in large enterprises or small startups, the fundamental approaches remain consistent, though their implementation may vary based on context and constraints.",
            "One particularly illuminating case study comes from a major organization that faced significant challenges in this area. Their initial attempts at addressing the problem followed conventional approaches, but results fell short of expectations. It was only when they stepped back and reconsidered their fundamental assumptions that breakthroughs began to emerge.",
            "The team realized that their previous approach had been too narrowly focused. By expanding their perspective and incorporating insights from adjacent fields, they discovered new possibilities that had previously been invisible. This cross-disciplinary thinking has since become a hallmark of successful practitioners in this space.",
            "Implementation requires careful attention to both strategic and tactical considerations. At the strategic level, leaders must ensure alignment between organizational goals and the methods employed. Tactically, teams need clear guidelines and appropriate tools to execute effectively. The balance between these levels often determines the ultimate success of any initiative.",
            "Data plays an increasingly important role in modern practice. The ability to collect, analyze, and act on relevant information provides significant advantages. However, data alone is insufficient. It must be combined with experience and judgment to yield meaningful insights. This synthesis of quantitative and qualitative understanding represents the cutting edge of current practice.",
            "Looking ahead, several trends are likely to shape the future of this field. Technological advances continue to create new possibilities, while changing social and economic conditions present fresh challenges. Successful practitioners will be those who can adapt to these changes while maintaining fidelity to core principles.",
            "The journey toward mastery in any domain requires dedication, practice, and continuous learning. Those who commit to this path find that their efforts are rewarded not only with professional success but also with the deep satisfaction that comes from genuine expertise. The road may be long, but the destination is worth the journey.",
        ]
        return "\n\n".join(paragraphs)

    def _generate_expanded_content(self, prompt: str) -> str:
        if "CURRENT CONTENT:" in prompt:
            parts = prompt.split("CURRENT CONTENT:")[1].split("---")
            if len(parts) > 1:
                original = parts[1]
            else:
                original = ""

            additional = "\n\nFurthermore, it is essential to consider the broader implications of these concepts. When we examine how leading organizations have implemented these principles, we find consistent patterns of success. These patterns, while varying in their specific manifestations, share common elements that can be adapted to different contexts.\n\nThe research conducted over the past decade has revealed several key insights. First, successful implementation requires strong leadership commitment. Without buy-in from senior stakeholders, even the best-designed initiatives tend to falter. Second, organizational culture plays a crucial role in determining outcomes.\n\nConsider the experience of a technology company that embarked on a transformation journey. Initially, they faced significant resistance from various stakeholders who were comfortable with existing practices. However, through persistent communication and demonstration of early wins, the transformation team gradually built momentum. Within two years, the new approaches had become embedded in the organization's DNA.\n\nMoving forward, practitioners should focus on building capabilities that will remain relevant as the field continues to evolve. This means developing both technical skills and the softer skills of communication, collaboration, and critical thinking."

            return original.strip() + additional

        return self._generate_section_content()

    def _generate_generic_content(self) -> str:
        return "This is generated content that provides valuable information on the topic at hand. " * 50
