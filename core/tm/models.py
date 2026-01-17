"""
Translation Memory Database Models
SQLAlchemy models for TM and segments.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Index, event, create_engine
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_base
import uuid
import hashlib

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def compute_hash(text: str, source_lang: str = "en", target_lang: str = "vi") -> str:
    """Compute SHA-256 hash for segment lookup."""
    content = f"{source_lang}:{target_lang}:{text.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy matching."""
    import re
    # Lowercase, remove extra whitespace, keep alphanumeric
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


class TranslationMemory(Base):
    """
    Translation Memory - a collection of translated segments.

    Each TM has a source/target language pair and domain.
    """

    __tablename__ = "translation_memories"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Language pair
    source_language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False
    )
    target_language: Mapped[str] = mapped_column(
        String(10), default="vi", nullable=False
    )

    # Classification
    domain: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )

    # Stats
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    total_words: Mapped[int] = mapped_column(Integer, default=0)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    segments: Mapped[List["TMSegment"]] = relationship(
        "TMSegment",
        back_populates="tm",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<TM {self.name} ({self.segment_count} segments)>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "domain": self.domain,
            "segment_count": self.segment_count,
            "total_words": self.total_words,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TMSegment(Base):
    """
    Translation Memory Segment - a source/target text pair.

    Segments are the atomic unit of translation memory.
    """

    __tablename__ = "tm_segments"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Foreign key
    tm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("translation_memories.id", ondelete="CASCADE"),
        nullable=False
    )

    # Text content
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Lookup optimization
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_normalized: Mapped[str] = mapped_column(Text, nullable=False)

    # Metrics
    source_length: Mapped[int] = mapped_column(Integer, default=0)  # word count

    # Quality
    quality_score: Mapped[float] = mapped_column(Float, default=0.8)
    source_type: Mapped[str] = mapped_column(
        String(20), default="ai"
    )  # ai, human, verified

    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Context (optional)
    context_before: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_after: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    project_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    tm: Mapped["TranslationMemory"] = relationship(
        "TranslationMemory", back_populates="segments"
    )

    # Indexes
    __table_args__ = (
        Index("idx_segment_tm", "tm_id"),
        Index("idx_segment_hash", "source_hash"),
        Index("idx_segment_tm_hash", "tm_id", "source_hash", unique=True),
        Index("idx_segment_quality", "quality_score"),
    )

    def __repr__(self):
        src = self.source_text[:30] + "..." if len(self.source_text) > 30 else self.source_text
        return f"<Segment {src}>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tm_id": self.tm_id,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "source_length": self.source_length,
            "quality_score": self.quality_score,
            "source_type": self.source_type,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "project_name": self.project_name,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ==================== EVENT LISTENERS ====================

@event.listens_for(TMSegment, "before_insert")
def compute_segment_fields_on_insert(mapper, connection, target):
    """Auto-compute hash and normalized text before insert."""
    if target.source_text:
        target.source_hash = compute_hash(target.source_text)
        target.source_normalized = normalize_text(target.source_text)
        target.source_length = len(target.source_text.split())


@event.listens_for(TMSegment, "before_update")
def compute_segment_fields_on_update(mapper, connection, target):
    """Auto-compute hash and normalized text before update."""
    if target.source_text:
        target.source_hash = compute_hash(target.source_text)
        target.source_normalized = normalize_text(target.source_text)
        target.source_length = len(target.source_text.split())


# ==================== DATABASE SETUP ====================

def get_engine(db_path: str = "data/tm.db"):
    """Create SQLAlchemy engine."""
    from pathlib import Path
    Path(db_path).parent.mkdir(exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def create_tables(engine=None):
    """Create all TM tables."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
