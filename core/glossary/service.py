"""
Glossary Service
Business logic layer for glossary operations.
"""
import logging
import json
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from io import BytesIO

from .models import Glossary, GlossaryTerm
from .schemas import (
    GlossaryCreate, GlossaryUpdate, GlossaryResponse,
    TermCreate, TermUpdate, TermResponse, TermListResponse,
    BulkTermResult, ImportResult, MatchResponse, TermMatch,
    PrebuiltGlossaryInfo,
)
from .repository import GlossaryRepository, get_repository
from .matcher import TermMatcher, get_matcher
from .io import (
    GlossaryExporter, GlossaryImporter,
    export_glossary_to_csv, export_glossary_to_json, export_glossary_to_tbx,
    import_glossary_from_csv, import_glossary_from_json, import_glossary_from_tbx,
)

logger = logging.getLogger(__name__)

# Path to pre-built glossaries
PREBUILT_DIR = Path(__file__).parent / "prebuilt"


class GlossaryService:
    """
    Service layer for glossary operations.

    Handles business logic, validation, and coordination
    between repository, matcher, and import/export.
    """

    def __init__(self):
        """Initialize service."""
        self.repository = get_repository()
        self.matcher = get_matcher()

    # ==================== GLOSSARY OPERATIONS ====================

    async def create_glossary(self, data: GlossaryCreate) -> GlossaryResponse:
        """Create a new glossary."""
        glossary = self.repository.create_glossary(
            name=data.name,
            description=data.description,
            domain=data.domain,
            source_language=data.source_language,
            target_language=data.target_language,
        )
        return GlossaryResponse.model_validate(glossary.to_dict())

    async def get_glossary(self, glossary_id: str) -> Optional[GlossaryResponse]:
        """Get glossary by ID."""
        glossary = self.repository.get_glossary(glossary_id)
        if glossary:
            return GlossaryResponse.model_validate(glossary.to_dict())
        return None

    async def list_glossaries(
        self,
        domain: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        include_prebuilt: bool = True,
        search: Optional[str] = None,
    ) -> List[GlossaryResponse]:
        """List glossaries with filters."""
        glossaries = self.repository.list_glossaries(
            domain=domain,
            source_language=source_language,
            target_language=target_language,
            include_prebuilt=include_prebuilt,
            search=search,
        )
        return [GlossaryResponse.model_validate(g.to_dict()) for g in glossaries]

    async def update_glossary(
        self,
        glossary_id: str,
        data: GlossaryUpdate,
    ) -> Optional[GlossaryResponse]:
        """Update glossary metadata."""
        # Check if prebuilt
        existing = self.repository.get_glossary(glossary_id)
        if existing and existing.is_prebuilt:
            raise ValueError("Cannot modify pre-built glossary")

        glossary = self.repository.update_glossary(
            glossary_id=glossary_id,
            name=data.name,
            description=data.description,
            domain=data.domain,
        )
        if glossary:
            return GlossaryResponse.model_validate(glossary.to_dict())
        return None

    async def delete_glossary(self, glossary_id: str) -> bool:
        """Delete glossary."""
        existing = self.repository.get_glossary(glossary_id)
        if existing and existing.is_prebuilt:
            raise ValueError("Cannot delete pre-built glossary")

        # Clear matcher cache
        self.matcher.clear_cache(glossary_id)

        return self.repository.delete_glossary(glossary_id)

    async def duplicate_glossary(
        self,
        glossary_id: str,
        new_name: Optional[str] = None,
    ) -> Optional[GlossaryResponse]:
        """Duplicate a glossary with all its terms."""
        original = self.repository.get_glossary(glossary_id)
        if not original:
            return None

        # Create new glossary
        name = new_name or f"Copy of {original.name}"
        new_glossary = self.repository.create_glossary(
            name=name,
            description=original.description,
            domain=original.domain,
            source_language=original.source_language,
            target_language=original.target_language,
        )

        # Copy terms
        terms = self.repository.get_all_terms(glossary_id)
        term_data = [
            {
                "source_term": t.source_term,
                "target_term": t.target_term,
                "context": t.context,
                "part_of_speech": t.part_of_speech,
                "case_sensitive": t.case_sensitive,
                "priority": t.priority,
            }
            for t in terms
        ]

        if term_data:
            self.repository.add_terms_bulk(new_glossary.id, term_data)

        # Refresh
        new_glossary = self.repository.get_glossary(new_glossary.id)
        return GlossaryResponse.model_validate(new_glossary.to_dict())

    # ==================== TERM OPERATIONS ====================

    async def add_term(
        self,
        glossary_id: str,
        data: TermCreate,
    ) -> TermResponse:
        """Add a term to glossary."""
        # Check glossary exists
        glossary = self.repository.get_glossary(glossary_id)
        if not glossary:
            raise ValueError("Glossary not found")

        term = self.repository.add_term(
            glossary_id=glossary_id,
            source_term=data.source_term,
            target_term=data.target_term,
            context=data.context,
            part_of_speech=data.part_of_speech,
            case_sensitive=data.case_sensitive,
            priority=data.priority,
        )

        if not term:
            raise ValueError("Term already exists in glossary")

        # Clear matcher cache
        self.matcher.clear_cache(glossary_id)

        return TermResponse.model_validate(term.to_dict())

    async def add_terms_bulk(
        self,
        glossary_id: str,
        terms: List[TermCreate],
        skip_duplicates: bool = True,
    ) -> BulkTermResult:
        """Add multiple terms to glossary."""
        term_data = [t.model_dump() for t in terms]
        added, skipped, errors = self.repository.add_terms_bulk(
            glossary_id=glossary_id,
            terms=term_data,
            skip_duplicates=skip_duplicates,
        )

        # Clear matcher cache
        self.matcher.clear_cache(glossary_id)

        return BulkTermResult(added=added, skipped=skipped, errors=errors)

    async def list_terms(
        self,
        glossary_id: str,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        sort: str = "source_term",
        order: str = "asc",
    ) -> TermListResponse:
        """List terms with pagination."""
        terms, total = self.repository.list_terms(
            glossary_id=glossary_id,
            page=page,
            limit=limit,
            search=search,
            sort=sort,
            order=order,
        )

        pages = (total + limit - 1) // limit

        return TermListResponse(
            terms=[TermResponse.model_validate(t.to_dict()) for t in terms],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_term(
        self,
        glossary_id: str,
        term_id: str,
    ) -> Optional[TermResponse]:
        """Get a specific term."""
        term = self.repository.get_term(glossary_id, term_id)
        if term:
            return TermResponse.model_validate(term.to_dict())
        return None

    async def update_term(
        self,
        glossary_id: str,
        term_id: str,
        data: TermUpdate,
    ) -> Optional[TermResponse]:
        """Update a term."""
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        term = self.repository.update_term(glossary_id, term_id, **update_data)

        if term:
            # Clear matcher cache
            self.matcher.clear_cache(glossary_id)
            return TermResponse.model_validate(term.to_dict())
        return None

    async def delete_term(self, glossary_id: str, term_id: str) -> bool:
        """Delete a term."""
        success = self.repository.delete_term(glossary_id, term_id)
        if success:
            self.matcher.clear_cache(glossary_id)
        return success

    async def delete_terms_bulk(
        self,
        glossary_id: str,
        term_ids: List[str],
    ) -> int:
        """Delete multiple terms."""
        deleted = self.repository.delete_terms_bulk(glossary_id, term_ids)
        if deleted > 0:
            self.matcher.clear_cache(glossary_id)
        return deleted

    # ==================== IMPORT/EXPORT ====================

    async def import_terms(
        self,
        glossary_id: str,
        file,
        format: str = "auto",
        skip_duplicates: bool = True,
        update_existing: bool = False,
    ) -> ImportResult:
        """
        Import terms from file.

        Supports: csv, json, tbx
        """
        # Verify glossary exists
        glossary = self.repository.get_glossary(glossary_id)
        if not glossary:
            return ImportResult(
                status="error",
                added=0, updated=0, skipped=0,
                errors=[{"error": "Glossary not found"}]
            )

        try:
            # Read file content
            content = await file.read()
            content_str = content.decode("utf-8")
            filename = file.filename.lower() if file.filename else ""

            # Auto-detect format
            if format == "auto":
                if filename.endswith(".csv"):
                    format = "csv"
                elif filename.endswith(".json"):
                    format = "json"
                elif filename.endswith(".tbx"):
                    format = "tbx"
                else:
                    format = "csv"  # Default to CSV

            # Parse file
            if format == "csv":
                metadata, term_data = import_glossary_from_csv(
                    content_str,
                    glossary.source_language,
                    glossary.target_language
                )
            elif format == "json":
                metadata, term_data = import_glossary_from_json(content_str)
            elif format == "tbx":
                metadata, term_data = import_glossary_from_tbx(content_str)
            else:
                return ImportResult(
                    status="error",
                    added=0, updated=0, skipped=0,
                    errors=[{"error": f"Unsupported format: {format}"}]
                )

            # Add terms to glossary
            added = 0
            updated = 0
            skipped = 0
            errors = []

            for term in term_data:
                try:
                    # Check if term exists
                    existing = self.repository.find_term_by_source(
                        glossary_id, term.source_term
                    )

                    if existing:
                        if update_existing:
                            self.repository.update_term(
                                glossary_id, existing.id,
                                target_term=term.target_term,
                                context=term.context,
                            )
                            updated += 1
                        elif skip_duplicates:
                            skipped += 1
                        else:
                            errors.append({"term": term.source_term, "error": "Duplicate"})
                    else:
                        self.repository.add_term(
                            glossary_id=glossary_id,
                            source_term=term.source_term,
                            target_term=term.target_term,
                            context=term.context,
                            part_of_speech=term.part_of_speech,
                            priority=term.priority,
                            case_sensitive=term.case_sensitive,
                        )
                        added += 1

                except Exception as e:
                    errors.append({"term": term.source_term, "error": str(e)})

            # Update term count
            self.repository.update_term_count(glossary_id)

            logger.info(f"Imported {added} terms to glossary {glossary_id}")

            return ImportResult(
                status="completed",
                added=added,
                updated=updated,
                skipped=skipped,
                errors=errors[:10]  # Limit errors returned
            )

        except Exception as e:
            logger.error(f"Import error: {e}")
            return ImportResult(
                status="error",
                added=0, updated=0, skipped=0,
                errors=[{"error": str(e)}]
            )

    async def export_terms(
        self,
        glossary_id: str,
        format: str = "csv",
    ) -> Tuple[BytesIO, str, str]:
        """
        Export terms to file.

        Supports: csv, json, tbx

        Returns:
            Tuple of (file_content, filename, media_type)
        """
        # Get glossary
        glossary = self.repository.get_glossary(glossary_id)
        if not glossary:
            raise ValueError("Glossary not found")

        # Get all terms
        terms = self.repository.list_terms(glossary_id, page=1, limit=10000)
        term_dicts = [t.to_dict() for t in terms]

        # Export based on format
        if format == "csv":
            content_str = export_glossary_to_csv(term_dicts)
            filename = f"glossary_{glossary_id}.csv"
            media_type = "text/csv"
        elif format == "json":
            content_str = export_glossary_to_json(
                glossary.name,
                term_dicts,
                glossary.source_language,
                glossary.target_language
            )
            filename = f"glossary_{glossary_id}.json"
            media_type = "application/json"
        elif format == "tbx":
            content_str = export_glossary_to_tbx(
                glossary.name,
                term_dicts,
                glossary.source_language,
                glossary.target_language
            )
            filename = f"glossary_{glossary_id}.tbx"
            media_type = "application/xml"
        else:
            raise ValueError(f"Unsupported format: {format}")

        content = BytesIO(content_str.encode("utf-8"))
        return content, filename, media_type

    def get_import_template(self, format: str = "csv") -> Tuple[BytesIO, str, str]:
        """Get import template file."""
        if format == "csv":
            template = "source_term,target_term,context,part_of_speech,priority,case_sensitive\n"
            template += "example,ví dụ,Used in examples,noun,5,false\n"
            template += "API,API,Application Programming Interface,noun,8,true\n"
            filename = "glossary_template.csv"
            media_type = "text/csv"
        elif format == "json":
            template_data = {
                "name": "My Glossary",
                "source_language": "en",
                "target_language": "vi",
                "domain": "general",
                "terms": [
                    {"source_term": "example", "target_term": "ví dụ", "context": "Used in examples"},
                    {"source_term": "API", "target_term": "API", "priority": 8, "case_sensitive": True},
                ]
            }
            template = json.dumps(template_data, ensure_ascii=False, indent=2)
            filename = "glossary_template.json"
            media_type = "application/json"
        else:
            template = ""
            filename = f"glossary_template.{format}"
            media_type = "application/octet-stream"

        content = BytesIO(template.encode("utf-8"))
        return content, filename, media_type

    # ==================== PRE-BUILT GLOSSARIES ====================

    async def list_prebuilt_glossaries(self) -> Dict[str, List[PrebuiltGlossaryInfo]]:
        """List available pre-built glossaries."""
        glossaries = []

        for file_path in PREBUILT_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    glossaries.append(PrebuiltGlossaryInfo(
                        id=file_path.stem,
                        name=data.get("name", file_path.stem),
                        description=data.get("description", ""),
                        domain=data.get("domain", "general"),
                        term_count=len(data.get("terms", [])),
                        source_language=data.get("source_language", "en"),
                        target_language=data.get("target_language", "vi"),
                    ))
            except Exception as e:
                logger.error(f"Error loading prebuilt glossary {file_path}: {e}")

        return {"glossaries": glossaries}

    async def clone_prebuilt(
        self,
        prebuilt_id: str,
        new_name: Optional[str] = None,
    ) -> Optional[GlossaryResponse]:
        """Clone a pre-built glossary."""
        file_path = PREBUILT_DIR / f"{prebuilt_id}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Create glossary
            name = new_name or data.get("name", prebuilt_id)
            glossary = self.repository.create_glossary(
                name=name,
                description=data.get("description"),
                domain=data.get("domain", "general"),
                source_language=data.get("source_language", "en"),
                target_language=data.get("target_language", "vi"),
            )

            # Add terms
            terms = data.get("terms", [])
            if terms:
                term_data = [
                    {
                        "source_term": t.get("source") or t.get("source_term"),
                        "target_term": t.get("target") or t.get("target_term"),
                        "context": t.get("context"),
                        "part_of_speech": t.get("part_of_speech"),
                        "priority": t.get("priority", 5),
                    }
                    for t in terms
                ]
                self.repository.add_terms_bulk(glossary.id, term_data)

            # Refresh
            glossary = self.repository.get_glossary(glossary.id)
            return GlossaryResponse.model_validate(glossary.to_dict())

        except Exception as e:
            logger.error(f"Error cloning prebuilt glossary {prebuilt_id}: {e}")
            return None

    # ==================== MATCHING ====================

    async def match_terms(
        self,
        glossary_ids: List[str],
        text: str,
        highlight: bool = False,
    ) -> MatchResponse:
        """Find matching terms in text."""
        matches = self.matcher.find_matches(text, glossary_ids)

        highlighted_text = None
        if highlight and matches:
            highlighted_text = self.matcher.highlight_matches(text, matches)

        unique_terms = self.matcher.get_unique_terms(matches)

        return MatchResponse(
            matches=[
                TermMatch(
                    source_term=m.source_term,
                    target_term=m.target_term,
                    start=m.start,
                    end=m.end,
                    glossary_id=m.glossary_id,
                    priority=m.priority,
                )
                for m in matches
            ],
            highlighted_text=highlighted_text,
            match_count=len(matches),
            unique_terms=len(unique_terms),
        )


# Global instance
_service: Optional[GlossaryService] = None


def get_glossary_service() -> GlossaryService:
    """Get or create the global service instance."""
    global _service
    if _service is None:
        _service = GlossaryService()
    return _service
