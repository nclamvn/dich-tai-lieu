#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translation Memory - SQLite-based TM system with fuzzy matching
"""

import sqlite3
import hashlib
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import re


@dataclass
class TMSegment:
    """Translation Memory segment"""
    id: Optional[int] = None
    source: str = ""
    target: str = ""
    source_lang: str = "en"
    target_lang: str = "vi"
    domain: str = "default"

    # Metadata
    quality_score: float = 1.0
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    use_count: int = 0

    # Context
    context_before: str = ""
    context_after: str = ""

    # Additional metadata
    project_name: str = ""
    created_by: str = "ai_translator"
    notes: str = ""

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def get_hash(self) -> str:
        """Get unique hash for source segment"""
        content = f"{self.source_lang}:{self.target_lang}:{self.source}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class TMMatch:
    """A TM match result"""
    segment: TMSegment
    similarity: float  # 0.0 to 1.0
    match_type: str  # "exact", "fuzzy", "context"

    def __repr__(self):
        return f"TMMatch(similarity={self.similarity:.2%}, type={self.match_type})"


class TranslationMemory:
    """SQLite-based Translation Memory with fuzzy matching"""

    def __init__(self, db_path: Path):
        """
        Initialize Translation Memory

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)

        self.conn = None
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Main segments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_hash TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                source_lang TEXT DEFAULT 'en',
                target_lang TEXT DEFAULT 'vi',
                domain TEXT DEFAULT 'default',
                quality_score REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                use_count INTEGER DEFAULT 0,
                context_before TEXT,
                context_after TEXT,
                project_name TEXT,
                created_by TEXT DEFAULT 'ai_translator',
                notes TEXT
            )
        """)

        # Indexes for fast lookup
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_hash
            ON segments(source_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_text
            ON segments(source)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain
            ON segments(domain)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality
            ON segments(quality_score)
        """)

        # Full-text search (FTS5)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS segments_fts
            USING fts5(source, target, content=segments, content_rowid=id)
        """)

        # Triggers to keep FTS in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS segments_ai AFTER INSERT ON segments BEGIN
                INSERT INTO segments_fts(rowid, source, target)
                VALUES (new.id, new.source, new.target);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS segments_ad AFTER DELETE ON segments BEGIN
                DELETE FROM segments_fts WHERE rowid = old.id;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS segments_au AFTER UPDATE ON segments BEGIN
                UPDATE segments_fts
                SET source = new.source, target = new.target
                WHERE rowid = new.id;
            END
        """)

        # Statistics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tm_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date TEXT NOT NULL,
                total_segments INTEGER DEFAULT 0,
                total_matches INTEGER DEFAULT 0,
                exact_matches INTEGER DEFAULT 0,
                fuzzy_matches INTEGER DEFAULT 0,
                avg_similarity REAL DEFAULT 0.0,
                cost_saved_usd REAL DEFAULT 0.0
            )
        """)

        self.conn.commit()

    def add_segment(self, segment: TMSegment) -> int:
        """
        Add or update a segment in TM

        Args:
            segment: TMSegment to add

        Returns:
            Segment ID
        """
        cursor = self.conn.cursor()
        source_hash = segment.get_hash()

        # Check if segment exists
        cursor.execute(
            "SELECT id, use_count FROM segments WHERE source_hash = ?",
            (source_hash,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing segment
            segment_id = existing['id']
            use_count = existing['use_count'] + 1

            cursor.execute("""
                UPDATE segments
                SET target = ?,
                    quality_score = ?,
                    updated_at = ?,
                    use_count = ?,
                    domain = ?,
                    context_before = ?,
                    context_after = ?,
                    project_name = ?,
                    notes = ?
                WHERE id = ?
            """, (
                segment.target,
                segment.quality_score,
                time.time(),
                use_count,
                segment.domain,
                segment.context_before,
                segment.context_after,
                segment.project_name,
                segment.notes,
                segment_id
            ))
        else:
            # Insert new segment
            cursor.execute("""
                INSERT INTO segments (
                    source_hash, source, target, source_lang, target_lang,
                    domain, quality_score, created_at, updated_at,
                    use_count, context_before, context_after,
                    project_name, created_by, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_hash,
                segment.source,
                segment.target,
                segment.source_lang,
                segment.target_lang,
                segment.domain,
                segment.quality_score,
                segment.created_at,
                segment.updated_at,
                segment.use_count,
                segment.context_before,
                segment.context_after,
                segment.project_name,
                segment.created_by,
                segment.notes
            ))
            segment_id = cursor.lastrowid

        self.conn.commit()
        return segment_id

    def get_exact_match(
        self,
        source: str,
        source_lang: str = "en",
        target_lang: str = "vi"
    ) -> Optional[TMMatch]:
        """
        Get exact match from TM

        Args:
            source: Source text
            source_lang: Source language
            target_lang: Target language

        Returns:
            TMMatch if found, None otherwise
        """
        cursor = self.conn.cursor()

        # Create hash
        content = f"{source_lang}:{target_lang}:{source}"
        source_hash = hashlib.sha256(content.encode()).hexdigest()

        cursor.execute("""
            SELECT * FROM segments
            WHERE source_hash = ?
            AND source_lang = ?
            AND target_lang = ?
            ORDER BY quality_score DESC, use_count DESC
            LIMIT 1
        """, (source_hash, source_lang, target_lang))

        row = cursor.fetchone()

        if row:
            segment = self._row_to_segment(row)

            # Update use count
            cursor.execute(
                "UPDATE segments SET use_count = use_count + 1 WHERE id = ?",
                (segment.id,)
            )
            self.conn.commit()

            return TMMatch(
                segment=segment,
                similarity=1.0,
                match_type="exact"
            )

        return None

    def get_fuzzy_matches(
        self,
        source: str,
        source_lang: str = "en",
        target_lang: str = "vi",
        threshold: float = 0.7,
        max_results: int = 5,
        domain: Optional[str] = None
    ) -> List[TMMatch]:
        """
        Get fuzzy matches from TM

        Args:
            source: Source text
            source_lang: Source language
            target_lang: Target language
            threshold: Minimum similarity (0.0-1.0)
            max_results: Maximum number of results
            domain: Optional domain filter

        Returns:
            List of TMMatch objects
        """
        cursor = self.conn.cursor()

        # Build query
        query = """
            SELECT * FROM segments
            WHERE source_lang = ? AND target_lang = ?
        """
        params = [source_lang, target_lang]

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        # Use FTS for initial filtering
        query += " AND id IN (SELECT rowid FROM segments_fts WHERE segments_fts MATCH ?)"

        # Extract keywords for FTS
        keywords = self._extract_keywords(source)
        fts_query = " OR ".join(keywords[:5])  # Use top 5 keywords
        params.append(fts_query)

        query += " ORDER BY quality_score DESC, use_count DESC LIMIT ?"
        params.append(max_results * 3)  # Get more candidates for filtering

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Calculate similarity for each candidate
        matches = []
        for row in rows:
            segment = self._row_to_segment(row)
            similarity = self._calculate_similarity(source, segment.source)

            if similarity >= threshold:
                matches.append(TMMatch(
                    segment=segment,
                    similarity=similarity,
                    match_type="fuzzy"
                ))

        # Sort by similarity and return top results
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:max_results]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords for FTS search"""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'was', 'are', 'were'}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using multiple methods

        Combines:
        - Levenshtein distance (edit distance)
        - Character-based similarity
        - Word overlap
        """
        if str1 == str2:
            return 1.0

        # Normalize
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        if not s1 or not s2:
            return 0.0

        # 1. Levenshtein distance (40% weight)
        lev_similarity = 1.0 - (self._levenshtein_distance(s1, s2) / max(len(s1), len(s2)))

        # 2. Character bigram similarity (30% weight)
        char_similarity = self._bigram_similarity(s1, s2)

        # 3. Word overlap (30% weight)
        word_similarity = self._word_overlap_similarity(s1, s2)

        # Weighted average
        similarity = (
            lev_similarity * 0.4 +
            char_similarity * 0.3 +
            word_similarity * 0.3
        )

        return similarity

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance (edit distance)"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _bigram_similarity(self, s1: str, s2: str) -> float:
        """Calculate character bigram similarity"""
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s) - 1))

        bigrams1 = get_bigrams(s1)
        bigrams2 = get_bigrams(s2)

        if not bigrams1 or not bigrams2:
            return 0.0

        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)

        return intersection / union if union > 0 else 0.0

    def _word_overlap_similarity(self, s1: str, s2: str) -> float:
        """Calculate word overlap similarity"""
        words1 = set(re.findall(r'\b\w+\b', s1.lower()))
        words2 = set(re.findall(r'\b\w+\b', s2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _row_to_segment(self, row: sqlite3.Row) -> TMSegment:
        """Convert database row to TMSegment"""
        return TMSegment(
            id=row['id'],
            source=row['source'],
            target=row['target'],
            source_lang=row['source_lang'],
            target_lang=row['target_lang'],
            domain=row['domain'],
            quality_score=row['quality_score'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            use_count=row['use_count'],
            context_before=row['context_before'] or "",
            context_after=row['context_after'] or "",
            project_name=row['project_name'] or "",
            created_by=row['created_by'],
            notes=row['notes'] or ""
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive TM statistics"""
        cursor = self.conn.cursor()

        # Total segments
        cursor.execute("SELECT COUNT(*) as count FROM segments")
        total_segments = cursor.fetchone()['count']

        # Segments by domain
        cursor.execute("""
            SELECT domain, COUNT(*) as count
            FROM segments
            GROUP BY domain
            ORDER BY count DESC
        """)
        by_domain = {row['domain']: row['count'] for row in cursor.fetchall()}

        # Segments by language pair
        cursor.execute("""
            SELECT source_lang, target_lang, COUNT(*) as count
            FROM segments
            GROUP BY source_lang, target_lang
            ORDER BY count DESC
        """)
        by_language = [
            {
                'pair': f"{row['source_lang']}→{row['target_lang']}",
                'count': row['count']
            }
            for row in cursor.fetchall()
        ]

        # Quality distribution
        cursor.execute("""
            SELECT
                SUM(CASE WHEN quality_score >= 0.9 THEN 1 ELSE 0 END) as excellent,
                SUM(CASE WHEN quality_score >= 0.7 AND quality_score < 0.9 THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN quality_score >= 0.5 AND quality_score < 0.7 THEN 1 ELSE 0 END) as acceptable,
                SUM(CASE WHEN quality_score < 0.5 THEN 1 ELSE 0 END) as poor,
                AVG(quality_score) as avg_quality
            FROM segments
        """)
        quality_row = cursor.fetchone()
        quality_dist = {
            'excellent': quality_row['excellent'] or 0,
            'good': quality_row['good'] or 0,
            'acceptable': quality_row['acceptable'] or 0,
            'poor': quality_row['poor'] or 0,
            'average': quality_row['avg_quality'] or 0.0
        }

        # Usage statistics
        cursor.execute("""
            SELECT
                COUNT(*) as used_segments,
                SUM(use_count) as total_uses,
                AVG(use_count) as avg_uses_per_segment
            FROM segments
            WHERE use_count > 0
        """)
        usage_row = cursor.fetchone()
        usage_stats = {
            'segments_used': usage_row['used_segments'] or 0,
            'total_uses': usage_row['total_uses'] or 0,
            'avg_uses_per_segment': usage_row['avg_uses_per_segment'] or 0.0,
            'unused_segments': total_segments - (usage_row['used_segments'] or 0)
        }

        # Most used segments
        cursor.execute("""
            SELECT source, target, use_count, domain, quality_score
            FROM segments
            WHERE use_count > 0
            ORDER BY use_count DESC
            LIMIT 10
        """)
        most_used = [dict(row) for row in cursor.fetchall()]

        # Recently added
        cursor.execute("""
            SELECT source, target, domain, quality_score, created_at
            FROM segments
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recent = [dict(row) for row in cursor.fetchall()]

        # Database size
        db_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
        db_size_mb = db_size_bytes / (1024 * 1024)

        # Creation date range
        cursor.execute("""
            SELECT MIN(created_at) as first, MAX(created_at) as last
            FROM segments
        """)
        date_row = cursor.fetchone()
        date_range = None
        if date_row['first'] and date_row['last']:
            date_range = {
                'first': datetime.fromtimestamp(date_row['first']).strftime('%Y-%m-%d %H:%M'),
                'last': datetime.fromtimestamp(date_row['last']).strftime('%Y-%m-%d %H:%M')
            }

        return {
            'total_segments': total_segments,
            'by_domain': by_domain,
            'by_language': by_language,
            'quality_distribution': quality_dist,
            'usage_statistics': usage_stats,
            'most_used': most_used,
            'recently_added': recent,
            'date_range': date_range,
            'db_size_mb': db_size_mb
        }

    def generate_report(self) -> str:
        """Generate detailed text report of TM statistics"""
        stats = self.get_statistics()

        lines = [
            "=" * 80,
            "TRANSLATION MEMORY REPORT".center(80),
            "=" * 80,
            "",
            f"📊 Database: {self.db_path.name}",
            f"💾 Size: {stats['db_size_mb']:.2f} MB",
            "",
            "─" * 80,
            "OVERVIEW",
            "─" * 80,
            f"Total segments:        {stats['total_segments']:,}",
            ""
        ]

        # Date range
        if stats['date_range']:
            lines.extend([
                f"First entry:           {stats['date_range']['first']}",
                f"Latest entry:          {stats['date_range']['last']}",
                ""
            ])

        # Language pairs
        lines.extend([
            "─" * 80,
            "LANGUAGE PAIRS",
            "─" * 80
        ])
        for lang_info in stats['by_language']:
            count = lang_info['count']
            percentage = (count / max(stats['total_segments'], 1)) * 100
            lines.append(f"  {lang_info['pair']:15s} {count:6,} segments ({percentage:5.1f}%)")

        # Domains
        lines.extend([
            "",
            "─" * 80,
            "DOMAINS",
            "─" * 80
        ])
        for domain, count in stats['by_domain'].items():
            percentage = (count / max(stats['total_segments'], 1)) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length
            lines.append(f"  {domain:15s} {count:6,} ({percentage:5.1f}%) {bar}")

        # Quality distribution
        lines.extend([
            "",
            "─" * 80,
            "QUALITY DISTRIBUTION",
            "─" * 80,
            f"Average quality:       {stats['quality_distribution']['average']:.3f}",
            ""
        ])

        qual_dist = stats['quality_distribution']
        for level in ['excellent', 'good', 'acceptable', 'poor']:
            count = qual_dist[level]
            if stats['total_segments'] > 0:
                percentage = (count / stats['total_segments']) * 100
                bar_length = int(percentage / 2)
                bar = "█" * bar_length
                lines.append(f"  {level.capitalize():12s} {count:6,} ({percentage:5.1f}%) {bar}")

        # Usage statistics
        usage = stats['usage_statistics']
        lines.extend([
            "",
            "─" * 80,
            "USAGE STATISTICS",
            "─" * 80,
            f"Segments used:         {usage['segments_used']:,} / {stats['total_segments']:,}",
            f"Unused segments:       {usage['unused_segments']:,}",
            f"Total uses:            {usage['total_uses']:,}",
            f"Avg uses per segment:  {usage['avg_uses_per_segment']:.1f}",
            ""
        ])

        # Calculate reuse rate
        if stats['total_segments'] > 0:
            reuse_rate = (usage['segments_used'] / stats['total_segments']) * 100
            lines.append(f"Reuse rate:            {reuse_rate:.1f}%")

        # Most used segments
        if stats['most_used']:
            lines.extend([
                "",
                "─" * 80,
                "TOP 10 MOST USED SEGMENTS",
                "─" * 80
            ])
            for i, seg in enumerate(stats['most_used'], 1):
                source_preview = seg['source'][:50] + "..." if len(seg['source']) > 50 else seg['source']
                lines.append(f"{i:2d}. [{seg['use_count']:3d} uses] ({seg['domain']:10s}) {source_preview}")

        lines.extend([
            "",
            "=" * 80
        ])

        return "\n".join(lines)

    def print_statistics(self):
        """Print TM statistics to console"""
        report = self.generate_report()
        print(report)

    def clear_domain(self, domain: str):
        """Clear all segments from a specific domain"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM segments WHERE domain = ?", (domain,))
        self.conn.commit()

    def clear_all(self):
        """Clear all segments (use with caution!)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM segments")
        cursor.execute("DELETE FROM tm_stats")
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
