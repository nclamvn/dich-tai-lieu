#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Analytics Module - Performance metrics và reporting
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

from .validator import TranslationResult
from .parallel import ProcessingStats


@dataclass
class TranslationSession:
    """Một session dịch thuật"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    project_name: str = ""
    domain: str = "default"

    # Input/Output
    total_chunks: int = 0
    source_chars: int = 0
    translated_chars: int = 0

    # Processing
    processing_time: float = 0.0
    avg_chunk_time: float = 0.0

    # Quality
    avg_quality_score: float = 0.0
    quality_distribution: Dict[str, int] = field(default_factory=dict)  # score_range -> count

    # Performance
    chunks_per_minute: float = 0.0
    chars_per_second: float = 0.0

    # Cache
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # Errors
    failed_chunks: int = 0
    retried_chunks: int = 0
    warnings_count: int = 0

    # Cost (estimated)
    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Provider info
    provider: str = ""
    model: str = ""

    def calculate_metrics(self):
        """Calculate derived metrics"""
        if self.end_time:
            self.processing_time = self.end_time - self.start_time

        if self.processing_time > 0:
            self.chunks_per_minute = (self.total_chunks / self.processing_time) * 60
            self.chars_per_second = self.translated_chars / self.processing_time

        cache_total = self.cache_hits + self.cache_misses
        if cache_total > 0:
            self.cache_hit_rate = self.cache_hits / cache_total

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization"""
        return asdict(self)


class PerformanceAnalyzer:
    """Analyze translation performance and generate reports"""

    def __init__(self, analytics_dir: Path):
        self.analytics_dir = Path(analytics_dir)
        self.analytics_dir.mkdir(exist_ok=True, parents=True)

        self.sessions_dir = self.analytics_dir / "sessions"
        self.sessions_dir.mkdir(exist_ok=True)

    def create_session(
        self,
        project_name: str,
        domain: str = "default",
        provider: str = "",
        model: str = ""
    ) -> TranslationSession:
        """Create a new translation session"""
        session_id = f"{project_name}_{int(time.time())}"

        return TranslationSession(
            session_id=session_id,
            start_time=time.time(),
            project_name=project_name,
            domain=domain,
            provider=provider,
            model=model
        )

    def finalize_session(
        self,
        session: TranslationSession,
        results: List[TranslationResult],
        stats: ProcessingStats
    ):
        """Finalize session with results and stats"""
        session.end_time = time.time()
        session.total_chunks = len(results)

        # Calculate quality metrics
        quality_scores = [r.quality_score for r in results if r.quality_score > 0]
        if quality_scores:
            session.avg_quality_score = sum(quality_scores) / len(quality_scores)

        # Quality distribution
        quality_ranges = {
            "excellent": 0,  # >= 0.9
            "good": 0,       # 0.7-0.9
            "acceptable": 0, # 0.5-0.7
            "poor": 0        # < 0.5
        }

        for score in quality_scores:
            if score >= 0.9:
                quality_ranges["excellent"] += 1
            elif score >= 0.7:
                quality_ranges["good"] += 1
            elif score >= 0.5:
                quality_ranges["acceptable"] += 1
            else:
                quality_ranges["poor"] += 1

        session.quality_distribution = quality_ranges

        # Character counts
        session.source_chars = sum(len(r.source) for r in results)
        session.translated_chars = sum(len(r.translated) for r in results)

        # Stats from processor
        session.failed_chunks = stats.failed
        session.retried_chunks = stats.retried
        session.cache_hits = stats.cache_hits
        session.cache_misses = stats.cache_misses
        session.avg_chunk_time = stats.avg_time_per_task

        # Count warnings
        session.warnings_count = sum(len(r.warnings) for r in results)

        # Estimate tokens and cost
        session.estimated_tokens = self._estimate_tokens(session.source_chars, session.translated_chars)
        session.estimated_cost_usd = self._estimate_cost(session.estimated_tokens, session.model)

        # Calculate derived metrics
        session.calculate_metrics()

        # Save session
        self.save_session(session)

        return session

    def _estimate_tokens(self, source_chars: int, translated_chars: int) -> int:
        """Estimate tokens used (rough approximation)"""
        # Rough estimate: 1 token ≈ 4 characters for English/Vietnamese
        # Include both input and output
        total_chars = source_chars + translated_chars
        return int(total_chars / 4 * 1.3)  # 30% overhead for prompts

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost in USD"""
        # Price per 1M tokens (as of 2024)
        PRICING = {
            "gpt-4o-mini": 0.15,      # $0.15 per 1M input tokens
            "gpt-4o": 2.50,           # $2.50 per 1M input tokens
            "gpt-4-turbo": 10.00,     # $10 per 1M tokens
            "claude-3-5-haiku": 0.80,  # $0.80 per 1M input tokens
            "claude-3-5-sonnet": 3.00, # $3.00 per 1M input tokens
        }

        price_per_million = PRICING.get(model, 1.0)
        return (tokens / 1_000_000) * price_per_million

    @staticmethod
    def estimate_time_from_chunks(chunks: int, concurrency: int = 5, model: str = "gpt-4o-mini") -> dict:
        """
        Phase 4.3: Estimate translation time accounting for parallel processing.

        Calculates realistic time estimates by considering that chunks are processed
        in parallel, not sequentially. This prevents overestimating time for large documents.

        Args:
            chunks: Number of 3000-word chunks
            concurrency: Number of parallel translation workers (default: 5)
            model: AI model name (affects processing speed)

        Returns:
            Dictionary with:
                - estimated_seconds: Total estimated time in seconds
                - estimated_minutes: Total estimated time in minutes
                - estimated_display: Human-readable time (e.g., "2m 30s")
                - breakdown: Detailed timing breakdown
                - assumptions: Assumptions used for estimation

        Algorithm:
            1. Sequential time = chunks * avg_time_per_chunk
            2. Parallel time = (chunks / concurrency) * avg_time_per_chunk + overhead
            3. Account for model-specific speeds (GPT-4o faster than GPT-4o-mini, etc.)
            4. Add overhead for queue management and API rate limits

        Example:
            - 10 chunks, concurrency=5, GPT-4o-mini
            - Sequential: 10 * 3s = 30s
            - Parallel: (10 / 5) * 3s = 6s + overhead ≈ 8-10s
        """
        # Model-specific average times per chunk (3000 words)
        # Based on empirical data from real translation jobs
        AVG_CHUNK_TIME = {
            "gpt-4o-mini": 3.0,      # ~3 seconds per 3000-word chunk
            "gpt-4o": 2.5,           # Slightly faster
            "gpt-4-turbo": 4.0,      # Slower but higher quality
            "claude-3-5-haiku": 2.8, # Fast
            "claude-3-5-sonnet": 3.5 # Balanced
        }

        avg_time = AVG_CHUNK_TIME.get(model, 3.0)

        # Calculate sequential time (if no parallelization)
        sequential_time = chunks * avg_time

        # Calculate parallel time with overhead
        if chunks <= concurrency:
            # All chunks processed in one batch
            parallel_time = avg_time
            overhead = 2.0  # Initial setup time
        else:
            # Multiple batches needed
            num_batches = (chunks + concurrency - 1) // concurrency  # Ceiling division
            parallel_time = num_batches * avg_time
            # Overhead: queue management, rate limits, batch switching
            overhead = 2.0 + (num_batches * 0.5)  # 0.5s per batch switch

        total_time = parallel_time + overhead

        # Format display string
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)

        if minutes > 0:
            display = f"{minutes}m {seconds}s"
        else:
            display = f"{seconds}s"

        return {
            "estimated_seconds": int(total_time),
            "estimated_minutes": round(total_time / 60, 1),
            "estimated_display": display,
            "breakdown": {
                "chunks": chunks,
                "concurrency": concurrency,
                "avg_time_per_chunk": avg_time,
                "sequential_time": int(sequential_time),
                "parallel_time": int(parallel_time),
                "overhead": round(overhead, 1),
                "speedup_factor": round(sequential_time / max(total_time, 1), 1)
            },
            "assumptions": f"{concurrency} parallel workers, {avg_time}s per chunk ({model})"
        }

    @staticmethod
    def estimate_cost_from_word_count(word_count: int, model: str, target_lang: str = "vi") -> dict:
        """
        Phase 4.3: Unified cost estimation from word count for UI and API consistency.

        Converts word count → character count → token count → cost using the same
        algorithm as post-translation analytics for accurate upfront cost estimation.

        Args:
            word_count: Number of words in source document
            model: AI model name (e.g., "gpt-4o-mini", "gpt-4o")
            target_lang: Target language code (affects translation expansion ratio)

        Returns:
            Dictionary with:
                - estimated_tokens: Estimated tokens for translation
                - estimated_cost_usd: Estimated cost in USD
                - source_chars: Estimated source characters
                - translated_chars: Estimated translated characters

        Algorithm:
            1. Words → Characters: Average 5 chars/word for English, 3 chars/word for Vietnamese
            2. Source → Translation expansion: English→Vietnamese typically 1.1x-1.3x
            3. Characters → Tokens: 1 token ≈ 4 characters (OpenAI standard)
            4. Overhead: +30% for prompts and formatting
            5. Tokens → Cost: Model-specific pricing per 1M tokens
        """
        # Step 1: Estimate source character count from words
        # English: ~5 chars/word average
        # Vietnamese: ~3 chars/word average (when source is Vietnamese)
        chars_per_word = 5  # Conservative estimate for English source
        source_chars = word_count * chars_per_word

        # Step 2: Estimate translated character count (with expansion ratio)
        # English→Vietnamese typically expands 1.1x-1.3x due to diacritics and compound words
        # Use 1.2x as safe middle ground
        expansion_ratio = 1.2 if target_lang == "vi" else 1.0
        translated_chars = int(source_chars * expansion_ratio)

        # Step 3: Estimate tokens (same formula as _estimate_tokens)
        total_chars = source_chars + translated_chars
        estimated_tokens = int(total_chars / 4 * 1.3)  # 30% overhead for prompts

        # Step 4: Calculate cost (same formula as _estimate_cost)
        PRICING = {
            "gpt-4o-mini": 0.15,      # $0.15 per 1M input tokens
            "gpt-4o": 2.50,           # $2.50 per 1M input tokens
            "gpt-4-turbo": 10.00,     # $10 per 1M tokens
            "claude-3-5-haiku": 0.80,  # $0.80 per 1M input tokens
            "claude-3-5-sonnet": 3.00, # $3.00 per 1M input tokens
        }

        price_per_million = PRICING.get(model, 1.0)
        estimated_cost_usd = (estimated_tokens / 1_000_000) * price_per_million

        return {
            "estimated_tokens": estimated_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "source_chars": source_chars,
            "translated_chars": translated_chars,
            "pricing_model": "token-based",  # Indicate this uses accurate token-based pricing
            "price_per_million_tokens": price_per_million
        }

    def save_session(self, session: TranslationSession):
        """Save session to JSON"""
        session_file = self.sessions_dir / f"{session.session_id}.json"

        session_data = session.to_dict()
        session_data['timestamp'] = datetime.fromtimestamp(session.start_time).isoformat()

        session_file.write_text(
            json.dumps(session_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def load_session(self, session_id: str) -> Optional[TranslationSession]:
        """Load session from JSON"""
        session_file = self.sessions_dir / f"{session_id}.json"

        if not session_file.exists():
            return None

        data = json.loads(session_file.read_text(encoding='utf-8'))

        # Remove timestamp field (not in dataclass)
        data.pop('timestamp', None)

        return TranslationSession(**data)

    def get_all_sessions(self) -> List[TranslationSession]:
        """Load all sessions"""
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            session_id = session_file.stem
            session = self.load_session(session_id)
            if session:
                sessions.append(session)

        # Sort by start time (newest first)
        sessions.sort(key=lambda s: s.start_time, reverse=True)
        return sessions

    def generate_report(self, session: TranslationSession) -> str:
        """Generate detailed text report for a session"""
        lines = [
            "=" * 80,
            f"TRANSLATION SESSION REPORT".center(80),
            "=" * 80,
            "",
            f"📋 Project: {session.project_name}",
            f"🏷️  Domain: {session.domain}",
            f"🆔 Session ID: {session.session_id}",
            f"📅 Date: {datetime.fromtimestamp(session.start_time).strftime('%Y-%m-%d %H:%M:%S')}",
            f"🤖 Provider: {session.provider} ({session.model})",
            "",
            "─" * 80,
            "INPUT/OUTPUT METRICS",
            "─" * 80,
            f"Total chunks:          {session.total_chunks}",
            f"Source characters:     {session.source_chars:,}",
            f"Translated characters: {session.translated_chars:,}",
            f"Length ratio:          {session.translated_chars/max(session.source_chars, 1):.2f}x",
            "",
            "─" * 80,
            "QUALITY METRICS",
            "─" * 80,
            f"Average quality score: {session.avg_quality_score:.3f}",
            "",
            "Quality distribution:",
        ]

        for quality_level, count in session.quality_distribution.items():
            percentage = (count / max(session.total_chunks, 1)) * 100
            bar_length = int(percentage / 2)  # Scale to 50 chars max
            bar = "█" * bar_length
            lines.append(f"  {quality_level:12s} {count:4d} ({percentage:5.1f}%) {bar}")

        lines.extend([
            "",
            f"Warnings issued:       {session.warnings_count}",
            f"Failed chunks:         {session.failed_chunks}",
            f"Retried chunks:        {session.retried_chunks}",
            "",
            "─" * 80,
            "PERFORMANCE METRICS",
            "─" * 80,
            f"Total processing time: {session.processing_time:.2f}s ({session.processing_time/60:.1f} min)",
            f"Avg time per chunk:    {session.avg_chunk_time:.2f}s",
            f"Throughput:            {session.chunks_per_minute:.1f} chunks/min",
            f"Translation speed:     {session.chars_per_second:.0f} chars/sec",
            "",
            "─" * 80,
            "CACHE METRICS",
            "─" * 80,
            f"Cache hits:            {session.cache_hits}",
            f"Cache misses:          {session.cache_misses}",
            f"Cache hit rate:        {session.cache_hit_rate*100:.1f}%",
            "",
        ])

        if session.cache_hit_rate > 0:
            saved_time = session.cache_hits * session.avg_chunk_time
            saved_cost = (session.cache_hits / max(session.total_chunks, 1)) * session.estimated_cost_usd
            lines.extend([
                f"Estimated time saved:  {saved_time:.1f}s ({saved_time/60:.1f} min)",
                f"Estimated cost saved:  ${saved_cost:.4f}",
                "",
            ])

        lines.extend([
            "─" * 80,
            "COST ESTIMATION",
            "─" * 80,
            f"Estimated tokens:      {session.estimated_tokens:,}",
            f"Estimated cost:        ${session.estimated_cost_usd:.4f}",
            "",
            "=" * 80,
        ])

        return "\n".join(lines)

    def generate_summary_report(self, sessions: Optional[List[TranslationSession]] = None) -> str:
        """Generate summary report across multiple sessions"""
        if sessions is None:
            sessions = self.get_all_sessions()

        if not sessions:
            return "No translation sessions found."

        # Aggregate stats
        total_chunks = sum(s.total_chunks for s in sessions)
        total_chars = sum(s.translated_chars for s in sessions)
        total_time = sum(s.processing_time for s in sessions)
        total_cost = sum(s.estimated_cost_usd for s in sessions)
        avg_quality = sum(s.avg_quality_score for s in sessions) / len(sessions)

        # Domain breakdown
        domain_counts = defaultdict(int)
        for s in sessions:
            domain_counts[s.domain] += 1

        # Model usage
        model_counts = defaultdict(int)
        for s in sessions:
            model_counts[s.model] += 1

        lines = [
            "=" * 80,
            f"TRANSLATION SUMMARY REPORT".center(80),
            "=" * 80,
            "",
            f"Total sessions:        {len(sessions)}",
            f"Date range:            {datetime.fromtimestamp(sessions[-1].start_time).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(sessions[0].start_time).strftime('%Y-%m-%d')}",
            "",
            "─" * 80,
            "AGGREGATE METRICS",
            "─" * 80,
            f"Total chunks translated:     {total_chunks:,}",
            f"Total characters translated: {total_chars:,}",
            f"Total processing time:       {total_time/3600:.1f} hours",
            f"Average quality score:       {avg_quality:.3f}",
            f"Total estimated cost:        ${total_cost:.2f}",
            "",
            "─" * 80,
            "DOMAIN BREAKDOWN",
            "─" * 80,
        ]

        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(sessions)) * 100
            lines.append(f"  {domain:15s} {count:4d} sessions ({percentage:5.1f}%)")

        lines.extend([
            "",
            "─" * 80,
            "MODEL USAGE",
            "─" * 80,
        ])

        for model, count in sorted(model_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(sessions)) * 100
            lines.append(f"  {model:25s} {count:4d} sessions ({percentage:5.1f}%)")

        lines.extend([
            "",
            "=" * 80,
        ])

        return "\n".join(lines)

    def export_sessions_csv(self, output_path: Path):
        """Export all sessions to CSV"""
        import csv

        sessions = self.get_all_sessions()
        if not sessions:
            return

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            # Get all field names from first session
            fieldnames = list(sessions[0].to_dict().keys())

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for session in sessions:
                writer.writerow(session.to_dict())

    def print_session_report(self, session: TranslationSession):
        """Print session report to console"""
        report = self.generate_report(session)
        print(report)

        # Save to file
        report_file = self.analytics_dir / f"report_{session.session_id}.txt"
        report_file.write_text(report, encoding='utf-8')
        print(f"\n💾 Report saved to: {report_file}")
