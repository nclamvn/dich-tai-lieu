"""
Glossary Import/Export Module

Supports:
- CSV (Simple format for spreadsheets)
- TBX (TermBase eXchange) - Industry standard for terminology
- Excel (XLSX) - Coming soon
"""

import csv
import io
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GlossaryTermData:
    """Term data for import/export"""
    source_term: str
    target_term: str
    context: Optional[str] = None
    part_of_speech: Optional[str] = None
    priority: int = 5
    case_sensitive: bool = False
    notes: Optional[str] = None


class GlossaryExporter:
    """Export Glossary to various formats"""

    @staticmethod
    def to_csv(
        terms: List[Dict],
        include_metadata: bool = True
    ) -> str:
        """
        Export terms to CSV format.

        Args:
            terms: List of term dicts
            include_metadata: Include context, part_of_speech, etc.

        Returns:
            CSV string
        """
        output = io.StringIO()

        if include_metadata:
            fieldnames = [
                "source_term", "target_term", "context",
                "part_of_speech", "priority", "case_sensitive"
            ]
        else:
            fieldnames = ["source_term", "target_term"]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for term in terms:
            row = {k: term.get(k, "") for k in fieldnames}
            # Convert bool to string for CSV
            if "case_sensitive" in row:
                row["case_sensitive"] = "true" if row["case_sensitive"] else "false"
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def to_json(
        glossary_name: str,
        terms: List[Dict],
        source_lang: str = "en",
        target_lang: str = "vi",
        domain: str = "general"
    ) -> str:
        """
        Export terms to JSON format.

        Args:
            glossary_name: Name of the glossary
            terms: List of term dicts
            source_lang: Source language code
            target_lang: Target language code
            domain: Domain classification

        Returns:
            JSON string
        """
        data = {
            "name": glossary_name,
            "source_language": source_lang,
            "target_language": target_lang,
            "domain": domain,
            "exported_at": datetime.utcnow().isoformat(),
            "term_count": len(terms),
            "terms": [
                {
                    "source_term": t.get("source_term", ""),
                    "target_term": t.get("target_term", ""),
                    "context": t.get("context"),
                    "part_of_speech": t.get("part_of_speech"),
                    "priority": t.get("priority", 5),
                    "case_sensitive": t.get("case_sensitive", False),
                }
                for t in terms
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def to_tbx(
        glossary_name: str,
        terms: List[Dict],
        source_lang: str = "en",
        target_lang: str = "vi",
    ) -> str:
        """
        Export terms to TBX (TermBase eXchange) format.

        Args:
            glossary_name: Name of the glossary
            terms: List of term dicts
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TBX XML string
        """
        # TBX namespace
        ns = "urn:iso:std:iso:30042:ed-2"

        # Create root
        root = ET.Element("tbx", type="TBX-Basic")
        root.set("style", "dca")
        root.set("xmlns", ns)
        root.set("{http://www.w3.org/XML/1998/namespace}lang", "en")

        # Header
        header = ET.SubElement(root, "tbxHeader")
        file_desc = ET.SubElement(header, "fileDesc")

        title_stmt = ET.SubElement(file_desc, "titleStmt")
        title = ET.SubElement(title_stmt, "title")
        title.text = glossary_name

        source_desc = ET.SubElement(file_desc, "sourceDesc")
        p = ET.SubElement(source_desc, "p")
        p.text = f"Exported from AI Publisher Pro on {datetime.utcnow().isoformat()}"

        # Body
        text = ET.SubElement(root, "text")
        body = ET.SubElement(text, "body")

        for i, term in enumerate(terms):
            # Concept entry
            concept = ET.SubElement(body, "conceptEntry", id=f"c{i+1}")

            # Admin info (context as definition)
            if term.get("context"):
                admin = ET.SubElement(concept, "descrip", type="definition")
                admin.text = term["context"]

            # Source language section
            lang_sec_src = ET.SubElement(concept, "langSec")
            lang_sec_src.set("{http://www.w3.org/XML/1998/namespace}lang", source_lang)

            term_sec_src = ET.SubElement(lang_sec_src, "termSec")
            term_elem = ET.SubElement(term_sec_src, "term")
            term_elem.text = term.get("source_term", "")

            if term.get("part_of_speech"):
                pos = ET.SubElement(term_sec_src, "termNote", type="partOfSpeech")
                pos.text = term["part_of_speech"]

            # Target language section
            lang_sec_tgt = ET.SubElement(concept, "langSec")
            lang_sec_tgt.set("{http://www.w3.org/XML/1998/namespace}lang", target_lang)

            term_sec_tgt = ET.SubElement(lang_sec_tgt, "termSec")
            term_elem_tgt = ET.SubElement(term_sec_tgt, "term")
            term_elem_tgt.text = term.get("target_term", "")

        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'


class GlossaryImporter:
    """Import Glossary from various formats"""

    @staticmethod
    def from_csv(
        content: str,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> tuple[Dict, List[GlossaryTermData]]:
        """
        Import terms from CSV format.

        Expected columns: source_term, target_term
        Optional columns: context, part_of_speech, priority, case_sensitive

        Args:
            content: CSV string
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Tuple of (metadata dict, list of GlossaryTermData)
        """
        terms = []
        metadata = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "name": "Imported from CSV",
        }

        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            source_term = row.get("source_term", "").strip()
            target_term = row.get("target_term", "").strip()

            if not source_term or not target_term:
                continue

            priority = 5
            if row.get("priority"):
                try:
                    priority = int(row["priority"])
                    priority = max(1, min(10, priority))  # Clamp 1-10
                except (ValueError, TypeError):
                    # Invalid priority format
                    pass

            case_sensitive = False
            if row.get("case_sensitive"):
                case_sensitive = row["case_sensitive"].lower() in ("true", "1", "yes")

            terms.append(GlossaryTermData(
                source_term=source_term,
                target_term=target_term,
                context=row.get("context"),
                part_of_speech=row.get("part_of_speech"),
                priority=priority,
                case_sensitive=case_sensitive,
            ))

        logger.info(f"Imported {len(terms)} terms from CSV")
        return metadata, terms

    @staticmethod
    def from_json(content: str) -> tuple[Dict, List[GlossaryTermData]]:
        """
        Import terms from JSON format.

        Expected structure:
        {
            "name": "...",
            "terms": [{"source_term": "...", "target_term": "..."}, ...]
        }

        Args:
            content: JSON string

        Returns:
            Tuple of (metadata dict, list of GlossaryTermData)
        """
        terms = []

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        metadata = {
            "name": data.get("name", "Imported from JSON"),
            "source_lang": data.get("source_language", "en"),
            "target_lang": data.get("target_language", "vi"),
            "domain": data.get("domain", "general"),
        }

        for t in data.get("terms", []):
            source_term = t.get("source_term", "").strip()
            target_term = t.get("target_term", "").strip()

            if not source_term or not target_term:
                continue

            terms.append(GlossaryTermData(
                source_term=source_term,
                target_term=target_term,
                context=t.get("context"),
                part_of_speech=t.get("part_of_speech"),
                priority=t.get("priority", 5),
                case_sensitive=t.get("case_sensitive", False),
            ))

        logger.info(f"Imported {len(terms)} terms from JSON")
        return metadata, terms

    @staticmethod
    def from_tbx(content: str) -> tuple[Dict, List[GlossaryTermData]]:
        """
        Import terms from TBX format.

        Args:
            content: TBX XML string

        Returns:
            Tuple of (metadata dict, list of GlossaryTermData)
        """
        terms = []
        metadata = {
            "name": "Imported from TBX",
            "source_lang": "en",
            "target_lang": "vi",
        }

        try:
            root = ET.fromstring(content)

            # Get namespace if present
            ns = {"tbx": "urn:iso:std:iso:30042:ed-2"}

            # Try to get title
            title = root.find(".//title") or root.find(".//tbx:title", ns)
            if title is not None and title.text:
                metadata["name"] = title.text

            # Find all concept entries
            concepts = root.findall(".//conceptEntry") or root.findall(".//tbx:conceptEntry", ns)

            for concept in concepts:
                source_term = ""
                target_term = ""
                context = None
                part_of_speech = None

                # Get definition/context
                descrip = concept.find(".//descrip[@type='definition']")
                if descrip is not None and descrip.text:
                    context = descrip.text

                # Get language sections
                lang_secs = concept.findall(".//langSec") or concept.findall(".//tbx:langSec", ns)

                for i, lang_sec in enumerate(lang_secs):
                    lang = lang_sec.get("{http://www.w3.org/XML/1998/namespace}lang")

                    term_elem = lang_sec.find(".//term") or lang_sec.find(".//tbx:term", ns)
                    if term_elem is not None and term_elem.text:
                        if i == 0:  # First is source
                            source_term = term_elem.text
                            if lang:
                                metadata["source_lang"] = lang
                        else:  # Second is target
                            target_term = term_elem.text
                            if lang:
                                metadata["target_lang"] = lang

                    # Get part of speech
                    pos = lang_sec.find(".//termNote[@type='partOfSpeech']")
                    if pos is not None and pos.text:
                        part_of_speech = pos.text

                if source_term and target_term:
                    terms.append(GlossaryTermData(
                        source_term=source_term,
                        target_term=target_term,
                        context=context,
                        part_of_speech=part_of_speech,
                    ))

        except ET.ParseError as e:
            logger.error(f"TBX parse error: {e}")
            raise ValueError(f"Invalid TBX format: {e}")

        logger.info(f"Imported {len(terms)} terms from TBX")
        return metadata, terms


# ==================== CONVENIENCE FUNCTIONS ====================

def export_glossary_to_csv(terms: List[Dict]) -> str:
    """Export glossary to CSV format (convenience function)"""
    return GlossaryExporter.to_csv(terms)


def export_glossary_to_json(
    glossary_name: str,
    terms: List[Dict],
    source_lang: str = "en",
    target_lang: str = "vi"
) -> str:
    """Export glossary to JSON format (convenience function)"""
    return GlossaryExporter.to_json(glossary_name, terms, source_lang, target_lang)


def export_glossary_to_tbx(
    glossary_name: str,
    terms: List[Dict],
    source_lang: str = "en",
    target_lang: str = "vi"
) -> str:
    """Export glossary to TBX format (convenience function)"""
    return GlossaryExporter.to_tbx(glossary_name, terms, source_lang, target_lang)


def import_glossary_from_csv(
    content: str,
    source_lang: str = "en",
    target_lang: str = "vi"
) -> tuple[Dict, List[GlossaryTermData]]:
    """Import glossary from CSV format (convenience function)"""
    return GlossaryImporter.from_csv(content, source_lang, target_lang)


def import_glossary_from_json(content: str) -> tuple[Dict, List[GlossaryTermData]]:
    """Import glossary from JSON format (convenience function)"""
    return GlossaryImporter.from_json(content)


def import_glossary_from_tbx(content: str) -> tuple[Dict, List[GlossaryTermData]]:
    """Import glossary from TBX format (convenience function)"""
    return GlossaryImporter.from_tbx(content)
