"""
Data Models for Author Engine (Phase 4.1 MVP + Phase 4.3 Memory)

Simplified architecture using prompt-based style control.
No corpus learning (Phase 4.2 skipped).
Phase 4.3 adds memory tracking for consistency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING
from pathlib import Path
import json

if TYPE_CHECKING:
    from .memory_store import MemoryStore
    from .vector_memory import VectorMemory


@dataclass
class Variation:
    """A generated text variation with metadata"""
    text: str
    style: str = "neutral"  # e.g., "formal", "casual", "narrative", "academic"
    confidence: float = 0.0
    word_count: int = 0

    def __post_init__(self):
        """Calculate word count"""
        if self.word_count == 0:
            self.word_count = len(self.text.split())


@dataclass
class AuthorConfig:
    """Configuration for author engine behavior"""
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 1000
    n_variations: int = 3
    default_style: str = "neutral"

    # Phase 4.3: Memory settings
    enable_memory: bool = True
    memory_context_chapters: int = 3  # How many previous chapters to include
    memory_chunk_size: int = 1000  # Chunk size for vector memory

    # Style presets (replaces Phase 4.2 corpus learning)
    style_instructions: Dict[str, str] = field(default_factory=lambda: {
        "neutral": "Write in a clear, balanced style suitable for general audiences.",
        "formal": "Write in a formal, professional style with precise language and structured sentences.",
        "casual": "Write in a conversational, approachable style as if talking to a friend.",
        "narrative": "Write in an engaging narrative style with vivid descriptions and flowing prose.",
        "academic": "Write in an academic style with analytical depth and scholarly tone.",
        "technical": "Write in a technical style with precision and domain-specific terminology.",
        "creative": "Write in a creative, expressive style with rich imagery and unique voice.",
        "journalistic": "Write in a journalistic style with objectivity, clarity, and concise reporting.",
    })


@dataclass
class AuthorProject:
    """A writing project (book, article, essay, etc.)"""
    project_id: str
    author_id: str
    title: str
    description: str
    genre: str  # e.g., "fiction", "non-fiction", "academic", "business"
    style: str = "neutral"  # Prompt-based style selection

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Content structure
    outline: List[str] = field(default_factory=list)  # Chapter/section titles
    chapters: Dict[int, str] = field(default_factory=dict)  # chapter_num -> content

    # Metadata
    target_word_count: int = 50000
    current_word_count: int = 0
    status: str = "draft"  # draft, in_progress, review, completed

    # Settings
    config: AuthorConfig = field(default_factory=AuthorConfig)

    # Phase 4.3: Memory (not serialized, initialized on load)
    _memory_store: Optional["MemoryStore"] = field(default=None, repr=False, compare=False)
    _vector_memory: Optional["VectorMemory"] = field(default=None, repr=False, compare=False)

    def initialize_memory(self, base_path: Path) -> None:
        """Initialize memory stores for this project (Phase 4.3)"""
        if not self.config.enable_memory:
            return

        project_dir = base_path / self.author_id / self.project_id

        # Lazy import to avoid circular dependency
        from .memory_store import MemoryStore
        from .vector_memory import VectorMemory

        self._memory_store = MemoryStore(project_dir)
        self._vector_memory = VectorMemory(project_dir)

    @property
    def memory(self) -> Optional["MemoryStore"]:
        """Get structured memory store"""
        return self._memory_store

    @property
    def vector_memory(self) -> Optional["VectorMemory"]:
        """Get vector memory store"""
        return self._vector_memory

    def add_content(self, chapter_num: int, content: str, update_memory: bool = True):
        """Add or update chapter content"""
        if chapter_num not in self.chapters:
            self.chapters[chapter_num] = ""

        self.chapters[chapter_num] += content
        self.current_word_count = sum(len(text.split()) for text in self.chapters.values())
        self.updated_at = datetime.now()

        # Phase 4.3: Update vector memory
        if update_memory and self._vector_memory:
            self._vector_memory.add_chapter_content(
                chapter=chapter_num,
                content=self.chapters[chapter_num],
                chunk_size=self.config.memory_chunk_size
            )

    def get_context(self, chapter_num: int, context_chars: int = 2000) -> str:
        """Get recent context for co-writing (last N chars from current chapter)"""
        if chapter_num not in self.chapters:
            return ""

        content = self.chapters[chapter_num]
        return content[-context_chars:] if len(content) > context_chars else content

    def completion_percentage(self) -> float:
        """Calculate project completion based on word count"""
        if self.target_word_count == 0:
            return 0.0
        return min(100.0, (self.current_word_count / self.target_word_count) * 100)

    def save(self, base_path: Path):
        """Save project to disk"""
        project_dir = base_path / self.author_id / self.project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        metadata = {
            "project_id": self.project_id,
            "author_id": self.author_id,
            "title": self.title,
            "description": self.description,
            "genre": self.genre,
            "style": self.style,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "outline": self.outline,
            "target_word_count": self.target_word_count,
            "current_word_count": self.current_word_count,
            "status": self.status,
        }

        with open(project_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save chapters as separate files
        chapters_dir = project_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for chapter_num, content in self.chapters.items():
            with open(chapters_dir / f"chapter_{chapter_num:03d}.txt", "w", encoding="utf-8") as f:
                f.write(content)

    @classmethod
    def load(cls, base_path: Path, author_id: str, project_id: str) -> Optional["AuthorProject"]:
        """Load project from disk"""
        project_dir = base_path / author_id / project_id
        metadata_file = project_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Load chapters
        chapters = {}
        chapters_dir = project_dir / "chapters"
        if chapters_dir.exists():
            for chapter_file in sorted(chapters_dir.glob("chapter_*.txt")):
                chapter_num = int(chapter_file.stem.split("_")[1])
                with open(chapter_file, "r", encoding="utf-8") as f:
                    chapters[chapter_num] = f.read()

        return cls(
            project_id=metadata["project_id"],
            author_id=metadata["author_id"],
            title=metadata["title"],
            description=metadata["description"],
            genre=metadata["genre"],
            style=metadata.get("style", "neutral"),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            outline=metadata["outline"],
            chapters=chapters,
            target_word_count=metadata["target_word_count"],
            current_word_count=metadata["current_word_count"],
            status=metadata["status"],
        )
