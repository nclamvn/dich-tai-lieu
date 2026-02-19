"""
Pytest Configuration and Fixtures
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from core.book_writer_v2.config import BookWriterConfig
from core.book_writer_v2.models import (
    BookProject, BookBlueprint, Part, Chapter, Section, WordCountTarget
)


@pytest.fixture
def config():
    """Default test configuration"""
    return BookWriterConfig(
        words_per_page=300,
        target_words_per_section=1500,
        min_total_completion=95.0,
        max_expansion_attempts=2,
    )


@pytest.fixture
def mock_ai_client():
    """Mock AI client"""
    client = MagicMock()
    client.generate = AsyncMock(return_value="Generated content " * 500)
    return client


@pytest.fixture
def sample_blueprint():
    """Sample book blueprint for testing"""
    blueprint = BookBlueprint(
        title="Test Book",
        target_pages=100,
        words_per_page=300,
    )

    part = Part(
        id="1",
        number=1,
        title="Test Part",
        word_count=WordCountTarget(30000),
    )

    chapter = Chapter(
        id="1.1",
        number=1,
        title="Test Chapter",
        part_id="1",
        word_count=WordCountTarget(10000),
    )

    for i in range(4):
        section = Section(
            id=f"1.1.{i+1}",
            number=i + 1,
            title=f"Test Section {i+1}",
            chapter_id="1.1",
            word_count=WordCountTarget(2500),
        )
        chapter.sections.append(section)

    part.chapters.append(chapter)
    blueprint.parts.append(part)

    return blueprint


@pytest.fixture
def sample_project(sample_blueprint):
    """Sample book project for testing"""
    project = BookProject(
        user_request="Test book about testing",
        blueprint=sample_blueprint,
    )
    return project
