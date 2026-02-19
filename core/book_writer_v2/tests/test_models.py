"""
Tests for data models
"""

import pytest
from core.book_writer_v2.models import (
    WordCountTarget, Section, Chapter, Part,
    BookBlueprint, BookProject, SectionStatus, BookStatus
)


class TestWordCountTarget:
    """Tests for WordCountTarget"""

    def test_completion_calculation(self):
        wc = WordCountTarget(target=1000, actual=800)
        assert wc.completion == 80.0

    def test_is_complete(self):
        wc = WordCountTarget(target=1000, actual=950)
        assert wc.is_complete is True

        wc2 = WordCountTarget(target=1000, actual=800)
        assert wc2.is_complete is False

    def test_needs_expansion(self):
        wc = WordCountTarget(target=1000, actual=850)
        assert wc.needs_expansion is True

        wc2 = WordCountTarget(target=1000, actual=920)
        assert wc2.needs_expansion is False

    def test_remaining(self):
        wc = WordCountTarget(target=1000, actual=600)
        assert wc.remaining == 400

    def test_is_over(self):
        wc = WordCountTarget(target=1000, actual=1100)
        assert wc.is_over is True

        wc2 = WordCountTarget(target=1000, actual=1000)
        assert wc2.is_over is False

    def test_zero_target(self):
        wc = WordCountTarget(target=0, actual=0)
        assert wc.completion == 100.0

    def test_to_dict(self):
        wc = WordCountTarget(target=1000, actual=500)
        d = wc.to_dict()
        assert d["target"] == 1000
        assert d["actual"] == 500
        assert d["completion"] == 50.0
        assert d["remaining"] == 500


class TestSection:
    """Tests for Section"""

    def test_update_word_count(self):
        section = Section(
            id="1.1",
            number=1,
            title="Test",
            chapter_id="1",
            word_count=WordCountTarget(1500),
        )
        section.content = "word " * 1000
        count = section.update_word_count()
        assert count == 1000
        assert section.word_count.actual == 1000

    def test_needs_expansion(self):
        section = Section(
            id="1.1",
            number=1,
            title="Test",
            chapter_id="1",
            word_count=WordCountTarget(1500, 1000),
        )
        assert section.needs_expansion() is True

        section.expansion_attempts = 3
        assert section.needs_expansion() is False

    def test_mark_complete(self):
        section = Section(
            id="1.1",
            number=1,
            title="Test",
            chapter_id="1",
        )
        section.mark_complete()
        assert section.status == SectionStatus.COMPLETE

    def test_empty_content_word_count(self):
        section = Section(
            id="1.1",
            number=1,
            title="Test",
            chapter_id="1",
        )
        assert section.update_word_count() == 0


class TestChapter:
    """Tests for Chapter"""

    def test_update_word_count(self):
        chapter = Chapter(
            id="1",
            number=1,
            title="Test Chapter",
            part_id="1",
        )
        section = Section(
            id="1.1",
            number=1,
            title="Test Section",
            chapter_id="1",
        )
        section.content = "word " * 500
        chapter.sections.append(section)

        count = chapter.update_word_count()
        assert count == 500

    def test_progress(self):
        chapter = Chapter(
            id="1",
            number=1,
            title="Test",
            part_id="1",
        )
        s1 = Section(id="1.1", number=1, title="S1", chapter_id="1")
        s1.status = SectionStatus.COMPLETE
        s2 = Section(id="1.2", number=2, title="S2", chapter_id="1")
        s2.status = SectionStatus.PENDING
        chapter.sections = [s1, s2]

        assert chapter.progress == 50.0

    def test_empty_chapter_progress(self):
        chapter = Chapter(id="1", number=1, title="Test", part_id="1")
        assert chapter.progress == 0.0


class TestBookBlueprint:
    """Tests for BookBlueprint"""

    def test_target_words(self):
        blueprint = BookBlueprint(
            title="Test",
            target_pages=300,
            words_per_page=300,
        )
        assert blueprint.target_words == 90000

    def test_all_sections(self, sample_blueprint):
        sections = sample_blueprint.all_sections
        assert len(sections) == 4

    def test_all_chapters(self, sample_blueprint):
        chapters = sample_blueprint.all_chapters
        assert len(chapters) == 1

    def test_get_section(self, sample_blueprint):
        section = sample_blueprint.get_section("1.1.1")
        assert section is not None
        assert section.title == "Test Section 1"

    def test_get_section_not_found(self, sample_blueprint):
        section = sample_blueprint.get_section("99.99")
        assert section is None

    def test_completion(self, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = "word " * 2000
            section.update_word_count()

        assert sample_blueprint.completion > 0

    def test_get_sections_needing_expansion(self, sample_blueprint):
        for section in sample_blueprint.all_sections:
            section.content = "word " * 100
            section.update_word_count()

        needing = sample_blueprint.get_sections_needing_expansion()
        assert len(needing) == 4

    def test_to_dict(self, sample_blueprint):
        d = sample_blueprint.to_dict()
        assert d["title"] == "Test Book"
        assert d["target_pages"] == 100
        assert d["total_sections"] == 4


class TestBookProject:
    """Tests for BookProject"""

    def test_progress_percentage(self, sample_project):
        sample_project.sections_total = 10
        sample_project.sections_completed = 5
        assert sample_project.progress_percentage == 50.0

    def test_add_error(self, sample_project):
        sample_project.add_error("Test error", "TestAgent", True)
        assert len(sample_project.errors) == 1
        assert sample_project.errors[0]["error"] == "Test error"

    def test_update_progress(self, sample_project):
        for section in sample_project.blueprint.all_sections:
            section.status = SectionStatus.COMPLETE
        sample_project.update_progress()
        assert sample_project.sections_completed == 4

    def test_to_dict(self, sample_project):
        d = sample_project.to_dict()
        assert "id" in d
        assert d["status"] == "created"

    def test_to_json(self, sample_project):
        j = sample_project.to_json()
        assert "Test book about testing" in j
