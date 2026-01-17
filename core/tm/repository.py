"""
Translation Memory Repository
Database access layer for TM operations.
"""
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path

from .models import Base, TranslationMemory, TMSegment, generate_uuid, compute_hash

logger = logging.getLogger(__name__)


class TMRepository:
    """
    Repository for Translation Memory database operations.

    Handles all CRUD operations for TMs and segments.
    """

    def __init__(self, db_path: str = "data/tm.db"):
        """Initialize repository with database path."""
        self.db_path = db_path
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        """Get or create SQLAlchemy engine."""
        if self._engine is None:
            Path(self.db_path).parent.mkdir(exist_ok=True)
            self._engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,
                connect_args={"check_same_thread": False}
            )
            Base.metadata.create_all(self._engine)
        return self._engine

    @property
    def session_factory(self):
        """Get session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.session_factory()

    # ==================== TM OPERATIONS ====================

    def create_tm(
        self,
        name: str,
        description: Optional[str] = None,
        source_language: str = "en",
        target_language: str = "vi",
        domain: str = "general",
    ) -> TranslationMemory:
        """Create a new Translation Memory."""
        with self.get_session() as session:
            tm = TranslationMemory(
                id=generate_uuid(),
                name=name,
                description=description,
                source_language=source_language,
                target_language=target_language,
                domain=domain,
            )
            session.add(tm)
            session.commit()
            session.refresh(tm)
            logger.info(f"Created TM: {tm.name} ({tm.id})")
            return tm

    def get_tm(self, tm_id: str) -> Optional[TranslationMemory]:
        """Get TM by ID."""
        with self.get_session() as session:
            return session.query(TranslationMemory).filter(
                TranslationMemory.id == tm_id,
                TranslationMemory.is_active == True
            ).first()

    def list_tms(
        self,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        domain: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[TranslationMemory]:
        """List TMs with optional filters."""
        with self.get_session() as session:
            query = session.query(TranslationMemory).filter(
                TranslationMemory.is_active == True
            )

            if source_language:
                query = query.filter(TranslationMemory.source_language == source_language)
            if target_language:
                query = query.filter(TranslationMemory.target_language == target_language)
            if domain:
                query = query.filter(TranslationMemory.domain == domain)
            if search:
                query = query.filter(TranslationMemory.name.ilike(f"%{search}%"))

            return query.order_by(TranslationMemory.name).all()

    def update_tm(
        self,
        tm_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[TranslationMemory]:
        """Update TM metadata."""
        with self.get_session() as session:
            tm = session.query(TranslationMemory).filter(
                TranslationMemory.id == tm_id,
                TranslationMemory.is_active == True
            ).first()

            if not tm:
                return None

            if name is not None:
                tm.name = name
            if description is not None:
                tm.description = description
            if domain is not None:
                tm.domain = domain

            session.commit()
            session.refresh(tm)
            return tm

    def delete_tm(self, tm_id: str) -> bool:
        """Soft delete a TM."""
        with self.get_session() as session:
            tm = session.query(TranslationMemory).filter(
                TranslationMemory.id == tm_id
            ).first()

            if not tm:
                return False

            tm.is_active = False
            session.commit()
            logger.info(f"Deleted TM: {tm_id}")
            return True

    def update_segment_count(self, tm_id: str) -> Tuple[int, int]:
        """Update cached segment count and total words for TM."""
        with self.get_session() as session:
            stats = session.query(
                func.count(TMSegment.id),
                func.sum(TMSegment.source_length)
            ).filter(
                TMSegment.tm_id == tm_id
            ).first()

            count = stats[0] or 0
            words = stats[1] or 0

            session.query(TranslationMemory).filter(
                TranslationMemory.id == tm_id
            ).update({
                "segment_count": count,
                "total_words": words
            })
            session.commit()

            return count, words

    # ==================== SEGMENT OPERATIONS ====================

    def add_segment(
        self,
        tm_id: str,
        source_text: str,
        target_text: str,
        quality_score: float = 0.8,
        source_type: str = "ai",
        context_before: Optional[str] = None,
        context_after: Optional[str] = None,
        project_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[TMSegment]:
        """Add a segment to TM."""
        with self.get_session() as session:
            segment = TMSegment(
                id=generate_uuid(),
                tm_id=tm_id,
                source_text=source_text,
                target_text=target_text,
                source_hash=compute_hash(source_text),
                source_normalized=source_text.lower().strip(),
                source_length=len(source_text.split()),
                quality_score=quality_score,
                source_type=source_type,
                context_before=context_before,
                context_after=context_after,
                project_name=project_name,
                notes=notes,
            )

            try:
                session.add(segment)
                session.commit()
                session.refresh(segment)
                self.update_segment_count(tm_id)
                return segment
            except IntegrityError:
                session.rollback()
                logger.warning(f"Duplicate segment: {source_text[:50]}...")
                return None

    def add_segments_bulk(
        self,
        tm_id: str,
        segments: List[dict],
        skip_duplicates: bool = True,
    ) -> Tuple[int, int, List[dict]]:
        """
        Add multiple segments to TM.

        Returns:
            Tuple of (added_count, skipped_count, errors)
        """
        added = 0
        skipped = 0
        errors = []

        with self.get_session() as session:
            for i, seg_data in enumerate(segments):
                try:
                    source = seg_data.get("source_text", "")
                    target = seg_data.get("target_text", "")

                    if not source or not target:
                        errors.append({
                            "index": i,
                            "source_text": source[:50] if source else "",
                            "error": "Missing source_text or target_text"
                        })
                        continue

                    # Check for existing
                    source_hash = compute_hash(source)
                    existing = session.query(TMSegment).filter(
                        TMSegment.tm_id == tm_id,
                        TMSegment.source_hash == source_hash
                    ).first()

                    if existing:
                        if skip_duplicates:
                            skipped += 1
                            continue
                        else:
                            # Update existing
                            existing.target_text = target
                            existing.updated_at = datetime.utcnow()
                            added += 1
                            continue

                    segment = TMSegment(
                        id=generate_uuid(),
                        tm_id=tm_id,
                        source_text=source,
                        target_text=target,
                        source_hash=source_hash,
                        source_normalized=source.lower().strip(),
                        source_length=len(source.split()),
                        quality_score=seg_data.get("quality_score", 0.8),
                        source_type=seg_data.get("source_type", "ai"),
                        context_before=seg_data.get("context_before"),
                        context_after=seg_data.get("context_after"),
                        project_name=seg_data.get("project_name"),
                        notes=seg_data.get("notes"),
                    )
                    session.add(segment)
                    added += 1

                except Exception as e:
                    errors.append({
                        "index": i,
                        "source_text": seg_data.get("source_text", "")[:50],
                        "error": str(e)
                    })

            session.commit()
            self.update_segment_count(tm_id)

        return added, skipped, errors

    def get_segment(self, tm_id: str, segment_id: str) -> Optional[TMSegment]:
        """Get a specific segment."""
        with self.get_session() as session:
            return session.query(TMSegment).filter(
                TMSegment.tm_id == tm_id,
                TMSegment.id == segment_id
            ).first()

    def list_segments(
        self,
        tm_id: str,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> Tuple[List[TMSegment], int]:
        """
        List segments with pagination.

        Returns:
            Tuple of (segments, total_count)
        """
        with self.get_session() as session:
            query = session.query(TMSegment).filter(
                TMSegment.tm_id == tm_id
            )

            if search:
                query = query.filter(
                    TMSegment.source_text.ilike(f"%{search}%") |
                    TMSegment.target_text.ilike(f"%{search}%")
                )

            total = query.count()

            # Sort
            sort_col = getattr(TMSegment, sort, TMSegment.created_at)
            if order == "desc":
                sort_col = sort_col.desc()
            query = query.order_by(sort_col)

            # Paginate
            offset = (page - 1) * limit
            segments = query.offset(offset).limit(limit).all()

            return segments, total

    def update_segment(
        self,
        tm_id: str,
        segment_id: str,
        **kwargs
    ) -> Optional[TMSegment]:
        """Update a segment."""
        with self.get_session() as session:
            segment = session.query(TMSegment).filter(
                TMSegment.tm_id == tm_id,
                TMSegment.id == segment_id
            ).first()

            if not segment:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(segment, key):
                    setattr(segment, key, value)

            session.commit()
            session.refresh(segment)
            return segment

    def delete_segment(self, tm_id: str, segment_id: str) -> bool:
        """Delete a segment."""
        with self.get_session() as session:
            segment = session.query(TMSegment).filter(
                TMSegment.tm_id == tm_id,
                TMSegment.id == segment_id
            ).first()

            if not segment:
                return False

            session.delete(segment)
            session.commit()
            self.update_segment_count(tm_id)
            return True

    def get_all_segments(self, tm_id: str) -> List[TMSegment]:
        """Get all segments for a TM (for matching)."""
        with self.get_session() as session:
            return session.query(TMSegment).filter(
                TMSegment.tm_id == tm_id
            ).order_by(
                TMSegment.quality_score.desc()
            ).all()

    def get_segments_by_hash(
        self,
        tm_ids: List[str],
        source_hash: str
    ) -> List[TMSegment]:
        """Get segments by hash across multiple TMs."""
        with self.get_session() as session:
            return session.query(TMSegment).filter(
                TMSegment.tm_id.in_(tm_ids),
                TMSegment.source_hash == source_hash
            ).order_by(
                TMSegment.quality_score.desc()
            ).all()

    def increment_usage_count(self, segment_ids: List[str]):
        """Increment usage count for segments."""
        with self.get_session() as session:
            session.query(TMSegment).filter(
                TMSegment.id.in_(segment_ids)
            ).update(
                {
                    TMSegment.usage_count: TMSegment.usage_count + 1,
                    TMSegment.last_used_at: datetime.utcnow()
                },
                synchronize_session=False
            )
            session.commit()


# Global instance
_repository: Optional[TMRepository] = None


def get_repository() -> TMRepository:
    """Get or create the global repository instance."""
    global _repository
    if _repository is None:
        _repository = TMRepository()
    return _repository
