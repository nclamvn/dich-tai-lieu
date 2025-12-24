"""
Agent 2 → Agent 3 Output Contract
AI Publisher Pro

Defines the STANDARD output format from Agent 2 (Translator) that
Agent 3 (Publisher) can consume for streaming PDF rendering.

Key principle:
- Agent 2 outputs a STRUCTURED FOLDER, not a single file
- Each chapter is a separate file
- manifest.json is the DNA of the document
- Agent 3 can process ANY length document by streaming chapters

Output structure:
    book_output/
    ├── manifest.json       # Document DNA
    ├── metadata.json       # Book info
    ├── chapters/
    │   ├── 001_chapter.md
    │   ├── 002_chapter.md
    │   └── ...
    └── assets/
        └── glossary.json   # Term consistency
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class DocumentType(Enum):
    """Type of document being translated"""
    EBOOK = "ebook"           # Novel, biography, non-fiction book
    ACADEMIC = "academic"     # Research paper, thesis, journal article
    BUSINESS = "business"     # Report, proposal, documentation


class RenderMode(Enum):
    """How Agent 3 should render this document"""
    EBOOK = "ebook"           # Trade paperback, cover, TOC
    ACADEMIC = "academic"     # A4, LaTeX, theorems, formulas
    BUSINESS = "business"     # A4, tables, charts


@dataclass
class SectionInfo:
    """Information about a section within a chapter"""
    title: str
    level: int                # 2 for ##, 3 for ###
    word_count: int = 0


@dataclass
class ChapterInfo:
    """Information about a chapter"""
    id: str                   # "001", "002", etc.
    file: str                 # Relative path: "chapters/001_chapter.md"
    title: str
    level: int = 1            # 1 for top-level chapter
    word_count: int = 0
    paragraph_count: int = 0
    sections: List[SectionInfo] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "file": self.file,
            "title": self.title,
            "level": self.level,
            "word_count": self.word_count,
            "paragraph_count": self.paragraph_count,
            "sections": [{"title": s.title, "level": s.level, "word_count": s.word_count} for s in self.sections]
        }


@dataclass
class DocumentStructure:
    """Overall document structure"""
    total_chapters: int = 0
    total_sections: int = 0
    total_paragraphs: int = 0
    total_words: int = 0
    has_toc: bool = True
    has_cover: bool = True
    has_footnotes: bool = False
    has_bibliography: bool = False
    has_images: bool = False
    has_tables: bool = False


@dataclass
class RenderHints:
    """Hints for Agent 3 on how to render"""
    page_break_before_chapter: bool = True
    first_paragraph_no_indent: bool = True
    blockquote_style: str = "italic"        # italic, indent, box
    heading_style: str = "centered"         # centered, left
    page_number_position: str = "bottom"    # bottom, top, none


@dataclass
class Manifest:
    """
    The DNA of the document.
    Agent 3 reads this FIRST to understand what it's rendering.
    """
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    document_type: DocumentType = DocumentType.EBOOK
    render_mode: RenderMode = RenderMode.EBOOK

    structure: DocumentStructure = field(default_factory=DocumentStructure)
    chapters: List[ChapterInfo] = field(default_factory=list)
    render_hints: RenderHints = field(default_factory=RenderHints)

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "document_type": self.document_type.value,
            "render_mode": self.render_mode.value,
            "structure": asdict(self.structure),
            "chapters": [c.to_dict() for c in self.chapters],
            "render_hints": asdict(self.render_hints)
        }

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "Manifest":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        manifest = cls()
        manifest.version = data.get("version", "1.0")
        manifest.created_at = data.get("created_at", "")
        manifest.document_type = DocumentType(data.get("document_type", "ebook"))
        manifest.render_mode = RenderMode(data.get("render_mode", "ebook"))

        struct = data.get("structure", {})
        manifest.structure = DocumentStructure(**struct)

        chapters = data.get("chapters", [])
        manifest.chapters = [
            ChapterInfo(
                id=c["id"],
                file=c["file"],
                title=c["title"],
                level=c.get("level", 1),
                word_count=c.get("word_count", 0),
                paragraph_count=c.get("paragraph_count", 0),
                sections=[SectionInfo(**s) for s in c.get("sections", [])]
            )
            for c in chapters
        ]

        hints = data.get("render_hints", {})
        manifest.render_hints = RenderHints(**hints)

        return manifest


@dataclass
class Metadata:
    """Book/document metadata"""
    title: str = "Untitled"
    subtitle: Optional[str] = None
    author: str = "Unknown"
    translator: str = "AI Publisher Pro"

    source_language: str = "en"
    target_language: str = "vi"

    year: Optional[int] = None
    publisher: Optional[str] = None
    isbn: Optional[str] = None

    # For academic
    institution: Optional[str] = None
    email: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "translator": self.translator,
            "language": {
                "source": self.source_language,
                "target": self.target_language
            },
            "publication": {
                "year": self.year,
                "publisher": self.publisher,
                "isbn": self.isbn
            },
            "academic": {
                "institution": self.institution,
                "email": self.email,
                "abstract": self.abstract,
                "keywords": self.keywords
            }
        }

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "Metadata":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        lang = data.get("language", {})
        pub = data.get("publication", {})
        acad = data.get("academic", {})

        return cls(
            title=data.get("title", "Untitled"),
            subtitle=data.get("subtitle"),
            author=data.get("author", "Unknown"),
            translator=data.get("translator", "AI Publisher Pro"),
            source_language=lang.get("source", "en"),
            target_language=lang.get("target", "vi"),
            year=pub.get("year"),
            publisher=pub.get("publisher"),
            isbn=pub.get("isbn"),
            institution=acad.get("institution"),
            email=acad.get("email"),
            abstract=acad.get("abstract"),
            keywords=acad.get("keywords", [])
        )


@dataclass
class Glossary:
    """Term glossary for consistency across chapters"""
    terms: Dict[str, str] = field(default_factory=dict)
    names: Dict[str, str] = field(default_factory=dict)
    places: Dict[str, str] = field(default_factory=dict)

    def add_term(self, original: str, translated: str):
        self.terms[original] = translated

    def add_name(self, original: str, translated: str):
        self.names[original] = translated

    def add_place(self, original: str, translated: str):
        self.places[original] = translated

    def get_translation(self, term: str) -> Optional[str]:
        """Look up a term across all categories"""
        return (self.terms.get(term) or
                self.names.get(term) or
                self.places.get(term))

    def to_dict(self) -> Dict:
        return {
            "terms": self.terms,
            "names": self.names,
            "places": self.places
        }

    def save(self, path: str):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "Glossary":
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(
            terms=data.get("terms", {}),
            names=data.get("names", {}),
            places=data.get("places", {})
        )


# =========================================
# AGENT 2 OUTPUT BUILDER
# =========================================

class Agent2OutputBuilder:
    """
    Builder for Agent 2 output structure.

    Usage:
        builder = Agent2OutputBuilder("./output/my_book")

        # Setup
        builder.set_metadata(
            title="Tiểu sử Sam Altman",
            author="Chu Hằng Tinh"
        )
        builder.set_document_type(DocumentType.EBOOK)

        # Add chapters one by one (as they're translated)
        builder.add_chapter(
            chapter_id="001",
            title="Khởi đầu",
            content="# Khởi đầu\\n\\nNội dung chapter 1..."
        )

        # Finalize
        builder.finalize()
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.chapters_dir = self.output_dir / "chapters"
        self.assets_dir = self.output_dir / "assets"

        # Initialize structures
        self.manifest = Manifest()
        self.metadata = Metadata()
        self.glossary = Glossary()

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chapters_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)

    def set_metadata(
        self,
        title: str,
        author: str,
        subtitle: Optional[str] = None,
        source_language: str = "en",
        target_language: str = "vi",
        **kwargs
    ):
        """Set document metadata"""
        self.metadata.title = title
        self.metadata.author = author
        self.metadata.subtitle = subtitle
        self.metadata.source_language = source_language
        self.metadata.target_language = target_language

        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)

    def set_document_type(
        self,
        doc_type: DocumentType,
        render_mode: Optional[RenderMode] = None
    ):
        """Set document type and render mode"""
        self.manifest.document_type = doc_type
        self.manifest.render_mode = render_mode or RenderMode(doc_type.value)

    def set_render_hints(self, **hints):
        """Set render hints for Agent 3"""
        for key, value in hints.items():
            if hasattr(self.manifest.render_hints, key):
                setattr(self.manifest.render_hints, key, value)

    def add_glossary_term(self, original: str, translated: str, category: str = "terms"):
        """Add a term to the glossary"""
        if category == "terms":
            self.glossary.add_term(original, translated)
        elif category == "names":
            self.glossary.add_name(original, translated)
        elif category == "places":
            self.glossary.add_place(original, translated)

    def add_chapter(
        self,
        chapter_id: str,
        title: str,
        content: str,
        sections: Optional[List[Dict]] = None
    ):
        """
        Add a translated chapter.

        Args:
            chapter_id: "001", "002", etc.
            title: Chapter title
            content: Markdown content (with frontmatter)
            sections: Optional list of {"title": str, "level": int}
        """
        # Create chapter file path
        filename = f"{chapter_id}_chapter.md"
        file_path = self.chapters_dir / filename
        relative_path = f"chapters/{filename}"

        # Add frontmatter if not present
        if not content.startswith("---"):
            frontmatter = f"""---
chapter_id: "{chapter_id}"
chapter_title: "{title}"
chapter_number: {int(chapter_id)}
---

"""
            content = frontmatter + content

        # Write chapter file
        file_path.write_text(content, encoding='utf-8')

        # Calculate stats
        word_count = len(content.split())
        paragraph_count = len([p for p in content.split('\n\n') if p.strip() and not p.startswith('#') and not p.startswith('---')])

        # Parse sections if not provided
        if sections is None:
            sections = self._extract_sections(content)

        section_infos = [
            SectionInfo(title=s["title"], level=s.get("level", 2))
            for s in sections
        ]

        # Create chapter info
        chapter_info = ChapterInfo(
            id=chapter_id,
            file=relative_path,
            title=title,
            level=1,
            word_count=word_count,
            paragraph_count=paragraph_count,
            sections=section_infos
        )

        # Add to manifest
        self.manifest.chapters.append(chapter_info)

        # Update structure counts
        self.manifest.structure.total_chapters = len(self.manifest.chapters)
        self.manifest.structure.total_sections += len(section_infos)
        self.manifest.structure.total_paragraphs += paragraph_count
        self.manifest.structure.total_words += word_count

    def _extract_sections(self, content: str) -> List[Dict]:
        """Extract section headers from markdown content"""
        sections = []
        for line in content.split('\n'):
            if line.startswith('## ') and not line.startswith('###'):
                sections.append({"title": line[3:].strip(), "level": 2})
            elif line.startswith('### '):
                sections.append({"title": line[4:].strip(), "level": 3})
        return sections

    def finalize(self):
        """
        Finalize the output:
        - Update manifest with final counts
        - Save all JSON files
        - Validate structure
        """
        # Set creation time
        self.manifest.created_at = datetime.now().isoformat()

        # Update structure
        self.manifest.structure.has_toc = len(self.manifest.chapters) > 1

        # Save files
        self.manifest.save(str(self.output_dir / "manifest.json"))
        self.metadata.save(str(self.output_dir / "metadata.json"))
        self.glossary.save(str(self.assets_dir / "glossary.json"))

        # Validate
        self._validate()

        return self.output_dir

    def _validate(self):
        """Validate the output structure"""
        # Check all chapter files exist
        for chapter in self.manifest.chapters:
            chapter_path = self.output_dir / chapter.file
            if not chapter_path.exists():
                raise ValueError(f"Chapter file missing: {chapter.file}")

        # Check counts match
        actual_files = list(self.chapters_dir.glob("*_chapter.md"))
        if len(actual_files) != len(self.manifest.chapters):
            raise ValueError(
                f"Chapter count mismatch: {len(actual_files)} files vs "
                f"{len(self.manifest.chapters)} in manifest"
            )

        print(f"✓ Validation passed: {len(self.manifest.chapters)} chapters")


# =========================================
# AGENT 3 INPUT READER
# =========================================

class Agent3InputReader:
    """
    Reader for Agent 3 to consume Agent 2 output.

    Usage:
        reader = Agent3InputReader("./output/my_book")

        # Get document info
        manifest = reader.get_manifest()
        metadata = reader.get_metadata()

        # Stream chapters (memory efficient)
        for chapter in reader.iter_chapters():
            print(f"Processing: {chapter['title']}")
            content = chapter['content']
            # Render chapter...
    """

    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)

        if not self.input_dir.exists():
            raise ValueError(f"Input directory not found: {input_dir}")

        # Load manifest
        manifest_path = self.input_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"manifest.json not found in {input_dir}")

        self.manifest = Manifest.load(str(manifest_path))

        # Load metadata
        metadata_path = self.input_dir / "metadata.json"
        if metadata_path.exists():
            self.metadata = Metadata.load(str(metadata_path))
        else:
            self.metadata = Metadata()

        # Load glossary
        glossary_path = self.input_dir / "assets" / "glossary.json"
        if glossary_path.exists():
            self.glossary = Glossary.load(str(glossary_path))
        else:
            self.glossary = Glossary()

    def get_manifest(self) -> Manifest:
        """Get document manifest"""
        return self.manifest

    def get_metadata(self) -> Metadata:
        """Get document metadata"""
        return self.metadata

    def get_glossary(self) -> Glossary:
        """Get glossary"""
        return self.glossary

    def get_document_type(self) -> DocumentType:
        """Get document type"""
        return self.manifest.document_type

    def get_render_mode(self) -> RenderMode:
        """Get render mode"""
        return self.manifest.render_mode

    def get_chapter_count(self) -> int:
        """Get total chapter count"""
        return len(self.manifest.chapters)

    def iter_chapters(self):
        """
        Iterate over chapters (generator - memory efficient).

        Yields:
            Dict with:
            - id: chapter id
            - title: chapter title
            - file: file path
            - content: markdown content
            - info: ChapterInfo object
        """
        for chapter_info in self.manifest.chapters:
            chapter_path = self.input_dir / chapter_info.file

            if not chapter_path.exists():
                raise ValueError(f"Chapter file not found: {chapter_info.file}")

            content = chapter_path.read_text(encoding='utf-8')

            yield {
                "id": chapter_info.id,
                "title": chapter_info.title,
                "file": chapter_info.file,
                "content": content,
                "info": chapter_info
            }

    def get_chapter(self, chapter_id: str) -> Optional[Dict]:
        """Get a specific chapter by ID"""
        for chapter_info in self.manifest.chapters:
            if chapter_info.id == chapter_id:
                chapter_path = self.input_dir / chapter_info.file
                content = chapter_path.read_text(encoding='utf-8')
                return {
                    "id": chapter_info.id,
                    "title": chapter_info.title,
                    "file": chapter_info.file,
                    "content": content,
                    "info": chapter_info
                }
        return None


# =========================================
# CONVENIENCE FUNCTIONS
# =========================================

def create_output_builder(output_dir: str, **metadata_kwargs) -> Agent2OutputBuilder:
    """Create and setup an output builder"""
    builder = Agent2OutputBuilder(output_dir)
    if metadata_kwargs:
        builder.set_metadata(**metadata_kwargs)
    return builder


def read_agent2_output(input_dir: str) -> Agent3InputReader:
    """Read Agent 2 output for Agent 3"""
    return Agent3InputReader(input_dir)
