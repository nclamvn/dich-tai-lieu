"""
Glossary Repository
Database access layer for glossary operations.
"""
import logging
from typing import Optional, List, Tuple
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path

from .models import Base, Glossary, GlossaryTerm, generate_uuid

logger = logging.getLogger(__name__)


class GlossaryRepository:
    """
    Repository for glossary database operations.

    Handles all CRUD operations for glossaries and terms.
    """

    def __init__(self, db_path: str = "data/glossary.db"):
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

    # ==================== GLOSSARY OPERATIONS ====================

    def create_glossary(
        self,
        name: str,
        description: Optional[str] = None,
        domain: str = "general",
        source_language: str = "en",
        target_language: str = "vi",
        is_prebuilt: bool = False,
    ) -> Glossary:
        """Create a new glossary."""
        with self.get_session() as session:
            glossary = Glossary(
                id=generate_uuid(),
                name=name,
                description=description,
                domain=domain,
                source_language=source_language,
                target_language=target_language,
                is_prebuilt=is_prebuilt,
            )
            session.add(glossary)
            session.commit()
            session.refresh(glossary)
            logger.info(f"Created glossary: {glossary.name} ({glossary.id})")
            return glossary

    def get_glossary(self, glossary_id: str) -> Optional[Glossary]:
        """Get glossary by ID."""
        with self.get_session() as session:
            return session.query(Glossary).filter(
                Glossary.id == glossary_id,
                Glossary.is_active == True
            ).first()

    def list_glossaries(
        self,
        domain: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        include_prebuilt: bool = True,
        search: Optional[str] = None,
    ) -> List[Glossary]:
        """List glossaries with optional filters."""
        with self.get_session() as session:
            query = session.query(Glossary).filter(Glossary.is_active == True)

            if domain:
                query = query.filter(Glossary.domain == domain)
            if source_language:
                query = query.filter(Glossary.source_language == source_language)
            if target_language:
                query = query.filter(Glossary.target_language == target_language)
            if not include_prebuilt:
                query = query.filter(Glossary.is_prebuilt == False)
            if search:
                query = query.filter(Glossary.name.ilike(f"%{search}%"))

            return query.order_by(Glossary.name).all()

    def update_glossary(
        self,
        glossary_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        domain: Optional[str] = None,
    ) -> Optional[Glossary]:
        """Update glossary metadata."""
        with self.get_session() as session:
            glossary = session.query(Glossary).filter(
                Glossary.id == glossary_id,
                Glossary.is_active == True
            ).first()

            if not glossary:
                return None

            if name is not None:
                glossary.name = name
            if description is not None:
                glossary.description = description
            if domain is not None:
                glossary.domain = domain

            session.commit()
            session.refresh(glossary)
            return glossary

    def delete_glossary(self, glossary_id: str) -> bool:
        """Soft delete a glossary."""
        with self.get_session() as session:
            glossary = session.query(Glossary).filter(
                Glossary.id == glossary_id
            ).first()

            if not glossary:
                return False

            glossary.is_active = False
            session.commit()
            logger.info(f"Deleted glossary: {glossary_id}")
            return True

    def update_term_count(self, glossary_id: str) -> int:
        """Update cached term count for glossary."""
        with self.get_session() as session:
            count = session.query(func.count(GlossaryTerm.id)).filter(
                GlossaryTerm.glossary_id == glossary_id
            ).scalar()

            session.query(Glossary).filter(Glossary.id == glossary_id).update(
                {"term_count": count}
            )
            session.commit()
            return count

    def find_term_by_source(
        self,
        glossary_id: str,
        source_term: str
    ) -> Optional[GlossaryTerm]:
        """Find term by source term text."""
        with self.get_session() as session:
            return session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id,
                GlossaryTerm.source_term_lower == source_term.lower()
            ).first()

    # ==================== TERM OPERATIONS ====================

    def add_term(
        self,
        glossary_id: str,
        source_term: str,
        target_term: str,
        context: Optional[str] = None,
        part_of_speech: Optional[str] = None,
        case_sensitive: bool = False,
        priority: int = 5,
    ) -> Optional[GlossaryTerm]:
        """Add a term to glossary."""
        with self.get_session() as session:
            term = GlossaryTerm(
                id=generate_uuid(),
                glossary_id=glossary_id,
                source_term=source_term,
                source_term_lower=source_term.lower(),
                target_term=target_term,
                context=context,
                part_of_speech=part_of_speech,
                case_sensitive=case_sensitive,
                priority=priority,
            )
            try:
                session.add(term)
                session.commit()
                session.refresh(term)
                self.update_term_count(glossary_id)
                return term
            except IntegrityError:
                session.rollback()
                logger.warning(f"Duplicate term: {source_term}")
                return None

    def add_terms_bulk(
        self,
        glossary_id: str,
        terms: List[dict],
        skip_duplicates: bool = True,
    ) -> Tuple[int, int, List[dict]]:
        """
        Add multiple terms to glossary.

        Returns:
            Tuple of (added_count, skipped_count, errors)
        """
        added = 0
        skipped = 0
        errors = []

        with self.get_session() as session:
            for i, term_data in enumerate(terms):
                try:
                    source = term_data.get("source_term", "")
                    target = term_data.get("target_term", "")

                    if not source or not target:
                        errors.append({
                            "index": i,
                            "source_term": source,
                            "error": "Missing source_term or target_term"
                        })
                        continue

                    # Check for existing
                    existing = session.query(GlossaryTerm).filter(
                        GlossaryTerm.glossary_id == glossary_id,
                        GlossaryTerm.source_term_lower == source.lower()
                    ).first()

                    if existing:
                        if skip_duplicates:
                            skipped += 1
                            continue
                        else:
                            errors.append({
                                "index": i,
                                "source_term": source,
                                "error": "Term already exists"
                            })
                            continue

                    term = GlossaryTerm(
                        id=generate_uuid(),
                        glossary_id=glossary_id,
                        source_term=source,
                        source_term_lower=source.lower(),
                        target_term=target,
                        context=term_data.get("context"),
                        part_of_speech=term_data.get("part_of_speech"),
                        case_sensitive=term_data.get("case_sensitive", False),
                        priority=term_data.get("priority", 5),
                    )
                    session.add(term)
                    added += 1

                except Exception as e:
                    errors.append({
                        "index": i,
                        "source_term": term_data.get("source_term", ""),
                        "error": str(e)
                    })

            session.commit()
            self.update_term_count(glossary_id)

        return added, skipped, errors

    def get_term(self, glossary_id: str, term_id: str) -> Optional[GlossaryTerm]:
        """Get a specific term."""
        with self.get_session() as session:
            return session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id,
                GlossaryTerm.id == term_id
            ).first()

    def list_terms(
        self,
        glossary_id: str,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        sort: str = "source_term",
        order: str = "asc",
    ) -> Tuple[List[GlossaryTerm], int]:
        """
        List terms with pagination.

        Returns:
            Tuple of (terms, total_count)
        """
        with self.get_session() as session:
            query = session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id
            )

            if search:
                search_filter = or_(
                    GlossaryTerm.source_term.ilike(f"%{search}%"),
                    GlossaryTerm.target_term.ilike(f"%{search}%")
                )
                query = query.filter(search_filter)

            # Get total count
            total = query.count()

            # Sort
            sort_col = getattr(GlossaryTerm, sort, GlossaryTerm.source_term)
            if order == "desc":
                sort_col = sort_col.desc()
            query = query.order_by(sort_col)

            # Paginate
            offset = (page - 1) * limit
            terms = query.offset(offset).limit(limit).all()

            return terms, total

    def update_term(
        self,
        glossary_id: str,
        term_id: str,
        **kwargs
    ) -> Optional[GlossaryTerm]:
        """Update a term."""
        with self.get_session() as session:
            term = session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id,
                GlossaryTerm.id == term_id
            ).first()

            if not term:
                return None

            for key, value in kwargs.items():
                if value is not None and hasattr(term, key):
                    setattr(term, key, value)

            # Update source_term_lower if source_term changed
            if "source_term" in kwargs and kwargs["source_term"]:
                term.source_term_lower = kwargs["source_term"].lower()

            session.commit()
            session.refresh(term)
            return term

    def delete_term(self, glossary_id: str, term_id: str) -> bool:
        """Delete a term."""
        with self.get_session() as session:
            term = session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id,
                GlossaryTerm.id == term_id
            ).first()

            if not term:
                return False

            session.delete(term)
            session.commit()
            self.update_term_count(glossary_id)
            return True

    def delete_terms_bulk(self, glossary_id: str, term_ids: List[str]) -> int:
        """Delete multiple terms."""
        with self.get_session() as session:
            deleted = session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id,
                GlossaryTerm.id.in_(term_ids)
            ).delete(synchronize_session=False)

            session.commit()
            self.update_term_count(glossary_id)
            return deleted

    def get_all_terms(self, glossary_id: str) -> List[GlossaryTerm]:
        """Get all terms for a glossary (for matching)."""
        with self.get_session() as session:
            return session.query(GlossaryTerm).filter(
                GlossaryTerm.glossary_id == glossary_id
            ).order_by(
                GlossaryTerm.priority.desc(),
                func.length(GlossaryTerm.source_term).desc()
            ).all()

    def increment_usage_count(self, term_ids: List[str]):
        """Increment usage count for terms."""
        with self.get_session() as session:
            session.query(GlossaryTerm).filter(
                GlossaryTerm.id.in_(term_ids)
            ).update(
                {GlossaryTerm.usage_count: GlossaryTerm.usage_count + 1},
                synchronize_session=False
            )
            session.commit()


# Global instance
_repository: Optional[GlossaryRepository] = None


def get_repository() -> GlossaryRepository:
    """Get or create the global repository instance."""
    global _repository
    if _repository is None:
        _repository = GlossaryRepository()
    return _repository
