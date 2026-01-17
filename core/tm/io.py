"""
Translation Memory Import/Export Module

Supports:
- TMX 1.4b (Translation Memory eXchange) - Industry standard
- CSV (Simple format for spreadsheets)
"""

import csv
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, BinaryIO, TextIO
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TMSegmentData:
    """Segment data for import/export"""
    source_text: str
    target_text: str
    source_lang: str = "en"
    target_lang: str = "vi"
    quality_score: float = 0.8
    source_type: str = "imported"
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class TMExporter:
    """Export Translation Memory to various formats"""

    @staticmethod
    def to_tmx(
        tm_name: str,
        segments: List[Dict],
        source_lang: str = "en",
        target_lang: str = "vi",
        created_by: str = "AI Publisher Pro"
    ) -> str:
        """
        Export segments to TMX 1.4b format.

        Args:
            tm_name: Name of the translation memory
            segments: List of segment dicts with source_text, target_text
            source_lang: Source language code
            target_lang: Target language code
            created_by: Creator attribution

        Returns:
            TMX XML string
        """
        # Create TMX root
        root = ET.Element("tmx", version="1.4")

        # Header
        header = ET.SubElement(root, "header")
        header.set("creationtool", "AI Publisher Pro")
        header.set("creationtoolversion", "3.0")
        header.set("datatype", "plaintext")
        header.set("segtype", "sentence")
        header.set("adminlang", "en")
        header.set("srclang", source_lang)
        header.set("o-tmf", "AI Publisher Pro TM")
        header.set("creationdate", datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))
        header.set("creationid", created_by)

        # Add note with TM name
        note = ET.SubElement(header, "note")
        note.text = f"Translation Memory: {tm_name}"

        # Body with translation units
        body = ET.SubElement(root, "body")

        for i, seg in enumerate(segments):
            tu = ET.SubElement(body, "tu")
            tu.set("tuid", str(i + 1))

            # Add creation date if available
            if seg.get("created_at"):
                try:
                    dt = datetime.fromisoformat(seg["created_at"].replace("Z", "+00:00"))
                    tu.set("creationdate", dt.strftime("%Y%m%dT%H%M%SZ"))
                except (ValueError, AttributeError):
                    # Invalid date format
                    pass

            # Add quality score as prop
            if seg.get("quality_score"):
                prop = ET.SubElement(tu, "prop", type="quality")
                prop.text = str(seg["quality_score"])

            # Add source type as prop
            if seg.get("source_type"):
                prop = ET.SubElement(tu, "prop", type="source_type")
                prop.text = seg["source_type"]

            # Add notes if present
            if seg.get("notes"):
                note = ET.SubElement(tu, "note")
                note.text = seg["notes"]

            # Source segment
            tuv_source = ET.SubElement(tu, "tuv")
            tuv_source.set("{http://www.w3.org/XML/1998/namespace}lang", source_lang)
            seg_source = ET.SubElement(tuv_source, "seg")
            seg_source.text = seg.get("source_text", "")

            # Target segment
            tuv_target = ET.SubElement(tu, "tuv")
            tuv_target.set("{http://www.w3.org/XML/1998/namespace}lang", target_lang)
            seg_target = ET.SubElement(tuv_target, "seg")
            seg_target.text = seg.get("target_text", "")

        # Convert to string with proper declaration
        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    @staticmethod
    def to_csv(
        segments: List[Dict],
        include_metadata: bool = True
    ) -> str:
        """
        Export segments to CSV format.

        Args:
            segments: List of segment dicts
            include_metadata: Include quality score, notes, etc.

        Returns:
            CSV string
        """
        output = io.StringIO()

        if include_metadata:
            fieldnames = [
                "source_text", "target_text", "quality_score",
                "source_type", "notes", "created_at"
            ]
        else:
            fieldnames = ["source_text", "target_text"]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for seg in segments:
            row = {k: seg.get(k, "") for k in fieldnames}
            writer.writerow(row)

        return output.getvalue()


class TMImporter:
    """Import Translation Memory from various formats"""

    @staticmethod
    def from_tmx(content: str) -> tuple[Dict, List[TMSegmentData]]:
        """
        Import segments from TMX format.

        Args:
            content: TMX XML string

        Returns:
            Tuple of (metadata dict, list of TMSegmentData)
        """
        segments = []
        metadata = {
            "source_lang": "en",
            "target_lang": "vi",
            "name": "Imported TM",
            "tool": None,
        }

        try:
            root = ET.fromstring(content)

            # Parse header
            header = root.find("header")
            if header is not None:
                metadata["source_lang"] = header.get("srclang", "en")
                metadata["tool"] = header.get("creationtool")

                # Get TM name from note
                note = header.find("note")
                if note is not None and note.text:
                    if note.text.startswith("Translation Memory: "):
                        metadata["name"] = note.text[20:]
                    else:
                        metadata["name"] = note.text

            # Parse body
            body = root.find("body")
            if body is None:
                return metadata, segments

            for tu in body.findall("tu"):
                source_text = ""
                target_text = ""
                source_lang = metadata["source_lang"]
                target_lang = metadata.get("target_lang", "vi")
                quality_score = 0.8
                source_type = "imported"
                notes = None
                created_at = None

                # Parse creation date
                if tu.get("creationdate"):
                    try:
                        created_at = datetime.strptime(
                            tu.get("creationdate"), "%Y%m%dT%H%M%SZ"
                        )
                    except ValueError:
                        # Invalid date format
                        pass

                # Parse properties
                for prop in tu.findall("prop"):
                    prop_type = prop.get("type")
                    if prop_type == "quality" and prop.text:
                        try:
                            quality_score = float(prop.text)
                        except ValueError:
                            # Invalid quality score format
                            pass
                    elif prop_type == "source_type" and prop.text:
                        source_type = prop.text

                # Parse notes
                note = tu.find("note")
                if note is not None:
                    notes = note.text

                # Parse TUVs (translation unit variants)
                for tuv in tu.findall("tuv"):
                    lang = tuv.get("{http://www.w3.org/XML/1998/namespace}lang")
                    seg = tuv.find("seg")

                    if seg is not None and seg.text:
                        if lang == source_lang or lang == metadata["source_lang"]:
                            source_text = seg.text
                        else:
                            target_text = seg.text
                            target_lang = lang or target_lang

                if source_text and target_text:
                    segments.append(TMSegmentData(
                        source_text=source_text,
                        target_text=target_text,
                        source_lang=source_lang,
                        target_lang=target_lang,
                        quality_score=quality_score,
                        source_type=source_type,
                        notes=notes,
                        created_at=created_at,
                    ))

            # Update target_lang if found
            if segments:
                metadata["target_lang"] = segments[0].target_lang

        except ET.ParseError as e:
            logger.error(f"TMX parse error: {e}")
            raise ValueError(f"Invalid TMX format: {e}")

        logger.info(f"Imported {len(segments)} segments from TMX")
        return metadata, segments

    @staticmethod
    def from_csv(
        content: str,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> tuple[Dict, List[TMSegmentData]]:
        """
        Import segments from CSV format.

        Expected columns: source_text, target_text
        Optional columns: quality_score, source_type, notes

        Args:
            content: CSV string
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Tuple of (metadata dict, list of TMSegmentData)
        """
        segments = []
        metadata = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "name": "Imported from CSV",
        }

        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            source_text = row.get("source_text", "").strip()
            target_text = row.get("target_text", "").strip()

            if not source_text or not target_text:
                continue

            quality_score = 0.8
            if row.get("quality_score"):
                try:
                    quality_score = float(row["quality_score"])
                except (ValueError, TypeError):
                    # Invalid quality score format
                    pass

            segments.append(TMSegmentData(
                source_text=source_text,
                target_text=target_text,
                source_lang=source_lang,
                target_lang=target_lang,
                quality_score=quality_score,
                source_type=row.get("source_type", "imported"),
                notes=row.get("notes"),
            ))

        logger.info(f"Imported {len(segments)} segments from CSV")
        return metadata, segments


# ==================== CONVENIENCE FUNCTIONS ====================

def export_tm_to_tmx(
    tm_name: str,
    segments: List[Dict],
    source_lang: str = "en",
    target_lang: str = "vi"
) -> str:
    """Export TM to TMX format (convenience function)"""
    return TMExporter.to_tmx(tm_name, segments, source_lang, target_lang)


def export_tm_to_csv(segments: List[Dict]) -> str:
    """Export TM to CSV format (convenience function)"""
    return TMExporter.to_csv(segments)


def import_tm_from_tmx(content: str) -> tuple[Dict, List[TMSegmentData]]:
    """Import TM from TMX format (convenience function)"""
    return TMImporter.from_tmx(content)


def import_tm_from_csv(
    content: str,
    source_lang: str = "en",
    target_lang: str = "vi"
) -> tuple[Dict, List[TMSegmentData]]:
    """Import TM from CSV format (convenience function)"""
    return TMImporter.from_csv(content, source_lang, target_lang)
