"""
Book Writer v2.0 Data Models

Core data structures for book generation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import json


class BookStatus(Enum):
    """Book project status"""
    CREATED = "created"
    ANALYZING = "analyzing"
    ARCHITECTING = "architecting"
    OUTLINING = "outlining"
    WRITING = "writing"
    EXPANDING = "expanding"
    ENRICHING = "enriching"
    EDITING = "editing"
    QUALITY_CHECK = "quality_check"
    PUBLISHING = "publishing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class SectionStatus(Enum):
    """Section writing status"""
    PENDING = "pending"
    OUTLINED = "outlined"
    WRITING = "writing"
    WRITTEN = "written"
    NEEDS_EXPANSION = "needs_expansion"
    EXPANDING = "expanding"
    ENRICHING = "enriching"
    EDITING = "editing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WordCountTarget:
    """
    Track word count targets vs actuals.

    The core metric for ensuring page count delivery.
    """
    target: int
    actual: int = 0

    @property
    def completion(self) -> float:
        """Completion percentage (0-100+)"""
        if self.target == 0:
            return 100.0
        return (self.actual / self.target) * 100

    @property
    def remaining(self) -> int:
        """Words remaining to reach target"""
        return max(0, self.target - self.actual)

    @property
    def is_complete(self) -> bool:
        """Target reached (>= 95%)"""
        return self.completion >= 95.0

    @property
    def needs_expansion(self) -> bool:
        """Below threshold (< 90%)"""
        return self.completion < 90.0

    @property
    def is_over(self) -> bool:
        """Over target (> 105%)"""
        return self.completion > 105.0

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "actual": self.actual,
            "completion": round(self.completion, 1),
            "remaining": self.remaining,
            "is_complete": self.is_complete,
        }


@dataclass
class OutlinePoint:
    """A single point in a section outline"""
    id: str
    content: str
    target_words: int
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "target_words": self.target_words,
            "notes": self.notes,
        }


@dataclass
class Section:
    """
    A section within a chapter.

    This is the ATOMIC WRITING UNIT - each section is written
    in a single API call for optimal quality and word count control.
    """
    id: str
    number: int
    title: str
    chapter_id: str

    word_count: WordCountTarget = field(default_factory=lambda: WordCountTarget(1500))

    outline_points: List[OutlinePoint] = field(default_factory=list)
    outline_summary: str = ""

    content: str = ""

    status: SectionStatus = SectionStatus.PENDING
    expansion_attempts: int = 0

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_word_count(self) -> int:
        """Recalculate word count from content"""
        self.word_count.actual = len(self.content.split()) if self.content else 0
        self.updated_at = datetime.now()
        return self.word_count.actual

    def needs_expansion(self) -> bool:
        """Check if section needs expansion"""
        return (
            self.word_count.needs_expansion
            and self.expansion_attempts < 3
        )

    def mark_complete(self):
        """Mark section as complete"""
        self.status = SectionStatus.COMPLETE
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "chapter_id": self.chapter_id,
            "word_count": self.word_count.to_dict(),
            "outline_points": [p.to_dict() for p in self.outline_points],
            "outline_summary": self.outline_summary,
            "content_preview": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "content_length": len(self.content),
            "status": self.status.value,
            "expansion_attempts": self.expansion_attempts,
        }


@dataclass
class Chapter:
    """A chapter containing multiple sections."""
    id: str
    number: int
    title: str
    part_id: str

    word_count: WordCountTarget = field(default_factory=lambda: WordCountTarget(6000))

    sections: List[Section] = field(default_factory=list)

    introduction: str = ""
    summary: str = ""
    key_takeaways: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_word_count(self) -> int:
        """Recalculate total word count"""
        intro_words = len(self.introduction.split()) if self.introduction else 0
        summary_words = len(self.summary.split()) if self.summary else 0
        takeaway_words = sum(len(t.split()) for t in self.key_takeaways)
        section_words = sum(s.update_word_count() for s in self.sections)

        self.word_count.actual = intro_words + section_words + summary_words + takeaway_words
        self.updated_at = datetime.now()
        return self.word_count.actual

    @property
    def is_complete(self) -> bool:
        """All sections complete and word count met"""
        sections_complete = all(s.status == SectionStatus.COMPLETE for s in self.sections)
        return sections_complete and self.word_count.is_complete

    @property
    def progress(self) -> float:
        """Chapter completion percentage"""
        if not self.sections:
            return 0.0
        completed = sum(1 for s in self.sections if s.status == SectionStatus.COMPLETE)
        return (completed / len(self.sections)) * 100

    def get_section(self, section_id: str) -> Optional[Section]:
        """Get section by ID"""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "part_id": self.part_id,
            "word_count": self.word_count.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
            "introduction_preview": self.introduction[:100] + "..." if self.introduction else "",
            "summary_preview": self.summary[:100] + "..." if self.summary else "",
            "key_takeaways": self.key_takeaways,
            "is_complete": self.is_complete,
            "progress": round(self.progress, 1),
        }


@dataclass
class Part:
    """A part/division of the book containing chapters."""
    id: str
    number: int
    title: str

    word_count: WordCountTarget = field(default_factory=lambda: WordCountTarget(30000))

    chapters: List[Chapter] = field(default_factory=list)

    introduction: str = ""

    def update_word_count(self) -> int:
        """Recalculate total word count"""
        intro_words = len(self.introduction.split()) if self.introduction else 0
        chapter_words = sum(c.update_word_count() for c in self.chapters)

        self.word_count.actual = intro_words + chapter_words
        return self.word_count.actual

    @property
    def is_complete(self) -> bool:
        """All chapters complete"""
        return all(c.is_complete for c in self.chapters)

    @property
    def progress(self) -> float:
        """Part completion percentage"""
        if not self.chapters:
            return 0.0
        completed = sum(1 for c in self.chapters if c.is_complete)
        return (completed / len(self.chapters)) * 100

    def get_chapter(self, chapter_id: str) -> Optional[Chapter]:
        """Get chapter by ID"""
        for chapter in self.chapters:
            if chapter.id == chapter_id:
                return chapter
        return None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "title": self.title,
            "word_count": self.word_count.to_dict(),
            "chapters": [c.to_dict() for c in self.chapters],
            "introduction_preview": self.introduction[:100] + "..." if self.introduction else "",
            "is_complete": self.is_complete,
            "progress": round(self.progress, 1),
        }


@dataclass
class FrontMatter:
    """Book front matter content"""
    title_page: str = ""
    copyright_page: str = ""
    dedication: str = ""
    table_of_contents: str = ""
    preface: str = ""
    acknowledgments: str = ""

    def word_count(self) -> int:
        """Total words in front matter"""
        texts = [
            self.dedication,
            self.preface,
            self.acknowledgments,
        ]
        return sum(len(t.split()) for t in texts if t)

    def to_dict(self) -> dict:
        return {
            "dedication": self.dedication,
            "preface": self.preface,
            "acknowledgments": self.acknowledgments,
            "word_count": self.word_count(),
        }


@dataclass
class BackMatter:
    """Book back matter content"""
    conclusion: str = ""
    appendices: List[Dict[str, str]] = field(default_factory=list)
    glossary: Dict[str, str] = field(default_factory=dict)
    bibliography: List[str] = field(default_factory=list)
    index: Dict[str, List[int]] = field(default_factory=dict)
    about_author: str = ""

    def word_count(self) -> int:
        """Total words in back matter"""
        conclusion_words = len(self.conclusion.split()) if self.conclusion else 0
        appendix_words = sum(
            len(a.get("content", "").split())
            for a in self.appendices
        )
        glossary_words = sum(
            len(term.split()) + len(definition.split())
            for term, definition in self.glossary.items()
        )
        about_words = len(self.about_author.split()) if self.about_author else 0

        return conclusion_words + appendix_words + glossary_words + about_words

    def to_dict(self) -> dict:
        return {
            "conclusion_preview": self.conclusion[:200] + "..." if self.conclusion else "",
            "appendices_count": len(self.appendices),
            "glossary_terms": len(self.glossary),
            "bibliography_count": len(self.bibliography),
            "word_count": self.word_count(),
        }


@dataclass
class BookBlueprint:
    """
    The complete book structure with page/word allocations.

    Created by the Architect agent, this is the master plan
    that all other agents follow.
    """
    title: str
    subtitle: Optional[str] = None
    author: str = "AI Publisher Pro"
    genre: str = "non-fiction"
    language: str = "en"

    target_pages: int = 300
    words_per_page: int = 300

    parts: List[Part] = field(default_factory=list)
    front_matter: FrontMatter = field(default_factory=FrontMatter)
    back_matter: BackMatter = field(default_factory=BackMatter)

    @property
    def target_words(self) -> int:
        """Total target word count"""
        return self.target_pages * self.words_per_page

    @property
    def actual_words(self) -> int:
        """Current total word count"""
        front = self.front_matter.word_count()
        parts = sum(p.update_word_count() for p in self.parts)
        back = self.back_matter.word_count()
        return front + parts + back

    @property
    def actual_pages(self) -> int:
        """Current page count"""
        return self.actual_words // self.words_per_page

    @property
    def completion(self) -> float:
        """Overall completion percentage"""
        if self.target_words == 0:
            return 0.0
        return (self.actual_words / self.target_words) * 100

    @property
    def all_sections(self) -> List[Section]:
        """Flatten all sections for iteration"""
        sections = []
        for part in self.parts:
            for chapter in part.chapters:
                sections.extend(chapter.sections)
        return sections

    @property
    def all_chapters(self) -> List[Chapter]:
        """Flatten all chapters"""
        chapters = []
        for part in self.parts:
            chapters.extend(part.chapters)
        return chapters

    @property
    def total_sections(self) -> int:
        """Total number of sections"""
        return len(self.all_sections)

    @property
    def total_chapters(self) -> int:
        """Total number of chapters"""
        return len(self.all_chapters)

    def get_section(self, section_id: str) -> Optional[Section]:
        """Get section by ID"""
        for section in self.all_sections:
            if section.id == section_id:
                return section
        return None

    def get_chapter(self, chapter_id: str) -> Optional[Chapter]:
        """Get chapter by ID"""
        for chapter in self.all_chapters:
            if chapter.id == chapter_id:
                return chapter
        return None

    def get_incomplete_sections(self) -> List[Section]:
        """Get sections that need more work"""
        return [s for s in self.all_sections if s.status != SectionStatus.COMPLETE]

    def get_sections_needing_expansion(self) -> List[Section]:
        """Get sections below word count threshold"""
        return [s for s in self.all_sections if s.needs_expansion()]

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "genre": self.genre,
            "language": self.language,
            "target_pages": self.target_pages,
            "actual_pages": self.actual_pages,
            "target_words": self.target_words,
            "actual_words": self.actual_words,
            "completion": round(self.completion, 1),
            "parts": [p.to_dict() for p in self.parts],
            "front_matter": self.front_matter.to_dict(),
            "back_matter": self.back_matter.to_dict(),
            "total_chapters": self.total_chapters,
            "total_sections": self.total_sections,
        }


@dataclass
class AnalysisResult:
    """Result from Analyst agent"""
    topic_summary: str
    target_audience: str
    audience_profile: Dict[str, Any]
    key_themes: List[str]
    key_messages: List[str]
    unique_value: str
    competitive_landscape: List[Dict[str, str]]
    recommended_structure: Dict[str, Any]
    tone_and_style: str
    content_warnings: List[str]
    research_notes: str

    def to_dict(self) -> dict:
        return {
            "topic_summary": self.topic_summary,
            "target_audience": self.target_audience,
            "audience_profile": self.audience_profile,
            "key_themes": self.key_themes,
            "key_messages": self.key_messages,
            "unique_value": self.unique_value,
            "competitive_landscape": self.competitive_landscape,
            "recommended_structure": self.recommended_structure,
            "tone_and_style": self.tone_and_style,
            "content_warnings": self.content_warnings,
        }


@dataclass
class QualityCheckResult:
    """Result from Quality Gate agent"""
    passed: bool
    total_word_check: Dict[str, Any]
    chapter_balance_check: Dict[str, Any]
    section_coverage_check: Dict[str, Any]
    content_quality_check: Dict[str, Any]
    structure_integrity_check: Dict[str, Any]
    issues: List[str]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "total_word_check": self.total_word_check,
            "chapter_balance_check": self.chapter_balance_check,
            "section_coverage_check": self.section_coverage_check,
            "content_quality_check": self.content_quality_check,
            "structure_integrity_check": self.structure_integrity_check,
            "issues": self.issues,
            "recommendations": self.recommendations,
        }


@dataclass
class BookProject:
    """
    The complete book project with all tracking.

    This is the main entity saved to database.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    user_request: str = ""
    user_description: str = ""
    draft_chapters: Optional[list] = field(default_factory=list)

    blueprint: Optional[BookBlueprint] = None

    analysis: Optional[AnalysisResult] = None

    status: BookStatus = BookStatus.CREATED
    current_agent: str = ""
    current_task: str = ""

    sections_completed: int = 0
    sections_total: int = 0

    quality_checks: List[QualityCheckResult] = field(default_factory=list)
    expansion_rounds: int = 0

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    output_files: Dict[str, str] = field(default_factory=dict)

    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float:
        """Overall progress percentage"""
        if self.sections_total == 0:
            return 0.0
        return (self.sections_completed / self.sections_total) * 100

    @property
    def word_progress(self) -> float:
        """Word count progress"""
        if self.blueprint:
            return self.blueprint.completion
        return 0.0

    def update_progress(self):
        """Update progress from blueprint"""
        if self.blueprint:
            self.sections_total = self.blueprint.total_sections
            self.sections_completed = sum(
                1 for s in self.blueprint.all_sections
                if s.status == SectionStatus.COMPLETE
            )
        self.updated_at = datetime.now()

    def add_error(self, error: str, agent: str = "", recoverable: bool = True):
        """Add error to log"""
        self.errors.append({
            "error": error,
            "agent": agent,
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat(),
        })

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "draft_chapters": self.draft_chapters or [],
            "status": self.status.value,
            "current_agent": self.current_agent,
            "current_task": self.current_task,
            "sections_completed": self.sections_completed,
            "sections_total": self.sections_total,
            "progress_percentage": round(self.progress_percentage, 1),
            "word_progress": round(self.word_progress, 1),
            "expansion_rounds": self.expansion_rounds,
            "blueprint": self.blueprint.to_dict() if self.blueprint else None,
            "analysis": self.analysis.to_dict() if self.analysis else None,
            "quality_checks": [q.to_dict() for q in self.quality_checks],
            "output_files": self.output_files,
            "errors": self.errors[-10:],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def to_json(self) -> str:
        """Serialize to JSON"""
        return json.dumps(self.to_dict(), indent=2, default=str)
