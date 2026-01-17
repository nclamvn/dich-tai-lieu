"""
Glossary Database Models
SQLAlchemy models for glossary and terms.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime,
    ForeignKey, Index, event, create_engine
)
from sqlalchemy.orm import relationship, Mapped, mapped_column, declarative_base
import uuid

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

Base = declarative_base()


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Glossary(Base):
    """
    Glossary model - contains metadata for a glossary.

    Attributes:
        id: Unique identifier (UUID)
        name: Display name
        description: Optional description
        domain: Domain type (medical, legal, tech, etc.)
        source_language: Source language code (en, vi, etc.)
        target_language: Target language code
        is_prebuilt: Whether this is a system pre-built glossary
        is_active: Soft delete flag
        term_count: Cached count of terms
    """

    __tablename__ = "glossaries"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Classification
    domain: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False
    )
    source_language: Mapped[str] = mapped_column(
        String(10), default="en", nullable=False
    )
    target_language: Mapped[str] = mapped_column(
        String(10), default="vi", nullable=False
    )

    # Flags
    is_prebuilt: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Stats
    term_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    terms: Mapped[List["GlossaryTerm"]] = relationship(
        "GlossaryTerm",
        back_populates="glossary",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<Glossary {self.name} ({self.term_count} terms)>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "is_prebuilt": self.is_prebuilt,
            "term_count": self.term_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class GlossaryTerm(Base):
    """
    GlossaryTerm model - individual term pairs.

    Attributes:
        id: Unique identifier (UUID)
        glossary_id: Parent glossary ID
        source_term: Original term in source language
        source_term_lower: Lowercase version for matching
        target_term: Translation in target language
        context: Optional usage context
        part_of_speech: Word type (noun, verb, etc.)
        case_sensitive: Whether to match case
        priority: 1-10, higher means prefer this translation
        usage_count: How many times used in translations
    """

    __tablename__ = "glossary_terms"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )

    # Foreign key
    glossary_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("glossaries.id", ondelete="CASCADE"), nullable=False
    )

    # Term data
    source_term: Mapped[str] = mapped_column(String(500), nullable=False)
    source_term_lower: Mapped[str] = mapped_column(String(500), nullable=False)
    target_term: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Optional metadata
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    part_of_speech: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Matching options
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=5)

    # Stats
    usage_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    glossary: Mapped["Glossary"] = relationship(
        "Glossary", back_populates="terms"
    )

    # Table indexes
    __table_args__ = (
        Index("idx_terms_glossary", "glossary_id"),
        Index("idx_terms_source_lower", "source_term_lower"),
        Index("idx_terms_unique", "glossary_id", "source_term_lower", unique=True),
    )

    def __repr__(self):
        return f"<Term {self.source_term} → {self.target_term}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "glossary_id": self.glossary_id,
            "source_term": self.source_term,
            "target_term": self.target_term,
            "context": self.context,
            "part_of_speech": self.part_of_speech,
            "case_sensitive": self.case_sensitive,
            "priority": self.priority,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ==================== EVENT LISTENERS ====================

@event.listens_for(GlossaryTerm, "before_insert")
def set_source_lower_on_insert(mapper, connection, target):
    """Auto-set source_term_lower before insert."""
    if target.source_term:
        target.source_term_lower = target.source_term.lower()


@event.listens_for(GlossaryTerm, "before_update")
def set_source_lower_on_update(mapper, connection, target):
    """Auto-set source_term_lower before update."""
    if target.source_term:
        target.source_term_lower = target.source_term.lower()


# ==================== DATABASE SETUP ====================

def get_engine(db_path: str = "data/glossary.db"):
    """Create SQLAlchemy engine."""
    from pathlib import Path
    Path(db_path).parent.mkdir(exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def create_tables(engine=None):
    """Create all glossary tables."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    return engine
