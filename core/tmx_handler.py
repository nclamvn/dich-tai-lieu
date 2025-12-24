#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TMX Handler - Import/Export TMX files (Translation Memory eXchange format)
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import html

from .translation_memory import TranslationMemory, TMSegment


class TMXHandler:
    """Handle TMX import/export operations"""

    def __init__(self, tm: TranslationMemory):
        """
        Initialize TMX handler

        Args:
            tm: TranslationMemory instance
        """
        self.tm = tm

    def export_to_tmx(
        self,
        output_path: Path,
        source_lang: str = "en",
        target_lang: str = "vi",
        domain: Optional[str] = None,
        min_quality: float = 0.0
    ) -> int:
        """
        Export TM to TMX file

        Args:
            output_path: Path to save TMX file
            source_lang: Source language code
            target_lang: Target language code
            domain: Optional domain filter
            min_quality: Minimum quality score

        Returns:
            Number of segments exported
        """
        # Get segments from database
        cursor = self.tm.conn.cursor()

        query = """
            SELECT * FROM segments
            WHERE source_lang = ? AND target_lang = ?
            AND quality_score >= ?
        """
        params = [source_lang, target_lang, min_quality]

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY id"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            return 0

        # Build TMX XML
        root = ET.Element('tmx', version="1.4")

        # Header
        header = ET.SubElement(root, 'header', {
            'creationtool': 'AI Translator Pro',
            'creationtoolversion': '2.1.0',
            'segtype': 'sentence',
            'o-tmf': 'AI Translator Pro',
            'adminlang': 'en',
            'srclang': source_lang,
            'datatype': 'plaintext',
            'creationdate': datetime.now().strftime('%Y%m%dT%H%M%S')
        })

        # Body
        body = ET.SubElement(root, 'body')

        segment_count = 0
        for row in rows:
            segment = self.tm._row_to_segment(row)

            # Create TU (Translation Unit)
            tu_attribs = {
                'tuid': str(segment.id),
                'datatype': 'plaintext'
            }

            if segment.created_at:
                tu_attribs['creationdate'] = datetime.fromtimestamp(
                    segment.created_at
                ).strftime('%Y%m%dT%H%M%S')

            if segment.updated_at:
                tu_attribs['changedate'] = datetime.fromtimestamp(
                    segment.updated_at
                ).strftime('%Y%m%dT%H%M%S')

            tu = ET.SubElement(body, 'tu', tu_attribs)

            # Add custom properties
            if segment.domain and segment.domain != 'default':
                prop_domain = ET.SubElement(tu, 'prop', type='domain')
                prop_domain.text = segment.domain

            if segment.project_name:
                prop_project = ET.SubElement(tu, 'prop', type='project')
                prop_project.text = segment.project_name

            if segment.quality_score < 1.0:
                prop_quality = ET.SubElement(tu, 'prop', type='quality')
                prop_quality.text = str(segment.quality_score)

            if segment.use_count > 0:
                prop_usage = ET.SubElement(tu, 'prop', type='x-usage-count')
                prop_usage.text = str(segment.use_count)

            # Source TUV (Translation Unit Variant)
            tuv_source = ET.SubElement(tu, 'tuv', {
                'xml:lang': source_lang
            })
            seg_source = ET.SubElement(tuv_source, 'seg')
            seg_source.text = segment.source

            # Target TUV
            tuv_target = ET.SubElement(tu, 'tuv', {
                'xml:lang': target_lang
            })
            seg_target = ET.SubElement(tuv_target, 'seg')
            seg_target.text = segment.target

            segment_count += 1

        # Write to file
        tree = ET.ElementTree(root)
        ET.indent(tree, space='  ')  # Pretty print (Python 3.9+)

        with open(output_path, 'wb') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)

        return segment_count

    def import_from_tmx(
        self,
        tmx_path: Path,
        domain: Optional[str] = None,
        project_name: Optional[str] = None,
        overwrite: bool = False
    ) -> tuple[int, int]:
        """
        Import segments from TMX file

        Args:
            tmx_path: Path to TMX file
            domain: Domain to assign to imported segments
            project_name: Project name to assign
            overwrite: Whether to overwrite existing segments

        Returns:
            Tuple of (imported_count, skipped_count)
        """
        if not tmx_path.exists():
            raise FileNotFoundError(f"TMX file not found: {tmx_path}")

        # Parse TMX
        try:
            tree = ET.parse(tmx_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Invalid TMX file: {e}")

        # Get header info
        header = root.find('header')
        if header is None:
            raise ValueError("TMX file missing header")

        source_lang = header.get('srclang', 'en')

        # Process translation units
        body = root.find('body')
        if body is None:
            raise ValueError("TMX file missing body")

        imported_count = 0
        skipped_count = 0

        for tu in body.findall('tu'):
            try:
                # Extract TUVs (Translation Unit Variants)
                tuvs = tu.findall('tuv')
                if len(tuvs) < 2:
                    skipped_count += 1
                    continue

                # Get source and target
                source_tuv = None
                target_tuv = None

                for tuv in tuvs:
                    lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang') or tuv.get('lang')

                    if not lang:
                        continue

                    seg = tuv.find('seg')
                    if seg is None or seg.text is None:
                        continue

                    if lang.startswith('en'):
                        source_tuv = seg.text
                        source_lang_actual = lang
                    elif lang.startswith('vi'):
                        target_tuv = seg.text
                        target_lang_actual = lang

                if not source_tuv or not target_tuv:
                    skipped_count += 1
                    continue

                # Extract properties
                tu_domain = domain
                tu_project = project_name
                tu_quality = 1.0

                for prop in tu.findall('prop'):
                    prop_type = prop.get('type', '')
                    if prop_type == 'domain' and not domain:
                        tu_domain = prop.text
                    elif prop_type == 'project' and not project_name:
                        tu_project = prop.text
                    elif prop_type == 'quality' and prop.text:
                        try:
                            tu_quality = float(prop.text)
                        except ValueError:
                            pass

                # Create segment
                segment = TMSegment(
                    source=source_tuv.strip(),
                    target=target_tuv.strip(),
                    source_lang=source_lang_actual[:2],  # Use first 2 chars
                    target_lang=target_lang_actual[:2],
                    domain=tu_domain or 'imported',
                    quality_score=tu_quality,
                    project_name=tu_project or '',
                    created_by='tmx_import'
                )

                # Check if segment exists
                if not overwrite:
                    existing = self.tm.get_exact_match(
                        segment.source,
                        segment.source_lang,
                        segment.target_lang
                    )
                    if existing:
                        skipped_count += 1
                        continue

                # Add to TM
                self.tm.add_segment(segment)
                imported_count += 1

            except Exception as e:
                print(f"⚠️  Error importing TU: {e}")
                skipped_count += 1
                continue

        return imported_count, skipped_count

    def export_domain_to_tmx(
        self,
        domain: str,
        output_dir: Path,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> Optional[Path]:
        """
        Export a specific domain to TMX file

        Args:
            domain: Domain to export
            output_dir: Output directory
            source_lang: Source language
            target_lang: Target language

        Returns:
            Path to created TMX file, or None if no segments
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        output_file = output_dir / f"tm_{domain}_{source_lang}_{target_lang}.tmx"

        count = self.export_to_tmx(
            output_file,
            source_lang=source_lang,
            target_lang=target_lang,
            domain=domain
        )

        if count == 0:
            if output_file.exists():
                output_file.unlink()
            return None

        return output_file

    def export_all_domains_to_tmx(
        self,
        output_dir: Path,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> Dict[str, Path]:
        """
        Export all domains to separate TMX files

        Args:
            output_dir: Output directory
            source_lang: Source language
            target_lang: Target language

        Returns:
            Dict mapping domain names to TMX file paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        # Get all domains
        cursor = self.tm.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT domain FROM segments
            WHERE source_lang = ? AND target_lang = ?
        """, (source_lang, target_lang))

        domains = [row['domain'] for row in cursor.fetchall()]

        exported_files = {}
        for domain in domains:
            tmx_file = self.export_domain_to_tmx(
                domain,
                output_dir,
                source_lang,
                target_lang
            )
            if tmx_file:
                exported_files[domain] = tmx_file

        return exported_files


def create_sample_tmx(output_path: Path):
    """Create a sample TMX file for testing"""
    root = ET.Element('tmx', version="1.4")

    header = ET.SubElement(root, 'header', {
        'creationtool': 'Sample Generator',
        'creationtoolversion': '1.0',
        'segtype': 'sentence',
        'srclang': 'en',
        'adminlang': 'en',
        'datatype': 'plaintext',
        'creationdate': datetime.now().strftime('%Y%m%dT%H%M%S')
    })

    body = ET.SubElement(root, 'body')

    # Sample segments
    samples = [
        ("Hello, world!", "Xin chào thế giới!"),
        ("This is a test.", "Đây là một bài kiểm tra."),
        ("Artificial Intelligence is transforming the world.", "Trí tuệ nhân tạo đang thay đổi thế giới."),
    ]

    for i, (source, target) in enumerate(samples, 1):
        tu = ET.SubElement(body, 'tu', {
            'tuid': str(i),
            'datatype': 'plaintext'
        })

        tuv_source = ET.SubElement(tu, 'tuv', {'xml:lang': 'en'})
        seg_source = ET.SubElement(tuv_source, 'seg')
        seg_source.text = source

        tuv_target = ET.SubElement(tu, 'tuv', {'xml:lang': 'vi'})
        seg_target = ET.SubElement(tuv_target, 'seg')
        seg_target.text = target

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')

    with open(output_path, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
