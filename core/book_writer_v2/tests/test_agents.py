"""
Tests for agents
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.agents import (
    AnalystAgent, ArchitectAgent, OutlinerAgent,
    WriterAgent, ExpanderAgent, QualityGateAgent
)
from core.book_writer_v2.agents.base import AgentContext
from core.book_writer_v2.models import (
    BookBlueprint, Part, Chapter, Section,
    WordCountTarget, SectionStatus
)


@pytest.fixture
def context(config):
    """Test context"""
    return AgentContext(
        project_id="test-123",
        config=config,
        progress_callback=MagicMock(),
    )


class TestAnalystAgent:
    """Tests for Analyst Agent"""

    @pytest.mark.asyncio
    async def test_execute_returns_analysis(self, config, mock_ai_client, context):
        mock_ai_client.generate = AsyncMock(return_value='''```json
{
    "topic_summary": "A test book",
    "target_audience": "Developers",
    "audience_profile": {},
    "key_themes": ["Theme 1", "Theme 2"],
    "key_messages": ["Message 1"],
    "unique_value": "Unique value",
    "competitive_landscape": [],
    "recommended_structure": {},
    "tone_and_style": "Professional",
    "content_warnings": [],
    "research_notes": ""
}
```''')

        agent = AnalystAgent(config, mock_ai_client)
        result = await agent.execute({
            "title": "Test Book",
            "description": "A test description",
            "target_pages": 100,
            "genre": "non-fiction",
        }, context)

        assert result.topic_summary == "A test book"
        assert result.target_audience == "Developers"
        assert len(result.key_themes) == 2

    @pytest.mark.asyncio
    async def test_fallback_parsing(self, config, mock_ai_client, context):
        mock_ai_client.generate = AsyncMock(return_value="No JSON here, just text about summary and themes")

        agent = AnalystAgent(config, mock_ai_client)
        result = await agent.execute({
            "title": "Test Book",
            "description": "A test description",
            "target_pages": 100,
            "genre": "non-fiction",
        }, context)

        # Should still return a result even with bad JSON
        assert result is not None


class TestArchitectAgent:
    """Tests for Architect Agent"""

    @pytest.mark.asyncio
    async def test_creates_blueprint(self, config, mock_ai_client, context):
        mock_ai_client.generate = AsyncMock(return_value='''```json
[
    {
        "title": "Part 1: Introduction",
        "chapters": [
            {
                "title": "Chapter 1: Getting Started",
                "sections": [
                    {"title": "Section 1.1"},
                    {"title": "Section 1.2"}
                ]
            }
        ]
    }
]
```''')

        agent = ArchitectAgent(config, mock_ai_client)
        blueprint = await agent.execute({
            "title": "Test Book",
            "target_pages": 100,
            "analysis": None,
            "genre": "non-fiction",
        }, context)

        assert blueprint.title == "Test Book"
        assert blueprint.target_pages == 100
        assert len(blueprint.parts) >= 1

    @pytest.mark.asyncio
    async def test_fallback_structure(self, config, mock_ai_client, context):
        mock_ai_client.generate = AsyncMock(return_value="Invalid response")

        agent = ArchitectAgent(config, mock_ai_client)
        blueprint = await agent.execute({
            "title": "Test Book",
            "target_pages": 100,
            "analysis": None,
            "genre": "non-fiction",
        }, context)

        # Should create default structure
        assert len(blueprint.parts) >= 1
        assert blueprint.total_sections > 0


class TestWriterAgent:
    """Tests for Writer Agent"""

    @pytest.mark.asyncio
    async def test_writes_content(self, config, mock_ai_client, context, sample_blueprint):
        mock_ai_client.generate = AsyncMock(return_value="word " * 1500)

        agent = WriterAgent(config, mock_ai_client)
        blueprint = await agent.execute(sample_blueprint, context)

        for section in blueprint.all_sections:
            assert section.content != ""
            assert section.word_count.actual > 0

    @pytest.mark.asyncio
    async def test_skips_complete_sections(self, config, mock_ai_client, context, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.status = SectionStatus.COMPLETE
            section.content = "existing content"

        agent = WriterAgent(config, mock_ai_client)
        await agent.execute(sample_blueprint, context)

        # AI should not have been called since all sections are complete
        mock_ai_client.generate.assert_not_called()


class TestExpanderAgent:
    """Tests for Expander Agent"""

    @pytest.mark.asyncio
    async def test_expands_short_sections(self, config, mock_ai_client, context):
        blueprint = BookBlueprint(
            title="Test",
            target_pages=100,
        )
        part = Part(id="1", number=1, title="Part 1", word_count=WordCountTarget(30000))
        chapter = Chapter(
            id="1.1", number=1, title="Chapter 1",
            part_id="1", word_count=WordCountTarget(10000)
        )

        section = Section(
            id="1.1.1",
            number=1,
            title="Short Section",
            chapter_id="1.1",
            word_count=WordCountTarget(1500, 500),
        )
        section.content = "word " * 500
        section.status = SectionStatus.NEEDS_EXPANSION

        chapter.sections.append(section)
        part.chapters.append(chapter)
        blueprint.parts.append(part)

        mock_ai_client.generate = AsyncMock(return_value="expanded word " * 1500)

        agent = ExpanderAgent(config, mock_ai_client)
        result = await agent.execute(blueprint, context)

        expanded_section = result.all_sections[0]
        assert expanded_section.expansion_attempts == 1

    @pytest.mark.asyncio
    async def test_skips_when_no_expansion_needed(self, config, mock_ai_client, context, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = "word " * 2500
            section.update_word_count()

        agent = ExpanderAgent(config, mock_ai_client)
        result = await agent.execute(sample_blueprint, context)

        mock_ai_client.generate.assert_not_called()


class TestQualityGateAgent:
    """Tests for Quality Gate Agent"""

    @pytest.mark.asyncio
    async def test_passes_complete_book(self, config, mock_ai_client, context, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = "word " * 2500
            section.update_word_count()
            section.status = SectionStatus.COMPLETE

        # Adjust target to match content (4 sections * 2500 words = 10000 words)
        sample_blueprint.target_pages = 34  # ~10200 words target at 300 wpp
        sample_blueprint.front_matter.preface = "A test preface."
        sample_blueprint.back_matter.conclusion = "A test conclusion."

        agent = QualityGateAgent(config, mock_ai_client)
        result = await agent.execute(sample_blueprint, context)

        assert result.total_word_check["passed"] is True
        assert result.section_coverage_check["passed"] is True

    @pytest.mark.asyncio
    async def test_fails_incomplete_book(self, config, mock_ai_client, context, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = ""

        agent = QualityGateAgent(config, mock_ai_client)
        result = await agent.execute(sample_blueprint, context)

        assert result.passed is False
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_detects_low_word_count(self, config, mock_ai_client, context, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = "short " * 100
            section.update_word_count()

        agent = QualityGateAgent(config, mock_ai_client)
        result = await agent.execute(sample_blueprint, context)

        assert result.total_word_check["passed"] is False
