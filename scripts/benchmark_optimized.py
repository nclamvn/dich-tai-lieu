#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark: Original vs Optimized

Compare performance of optimized components:
- ADN Extractor: Original vs Optimized
- DOCX Renderer: Original vs Optimized

Usage:
    python scripts/benchmark_optimized.py
"""

import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.contracts import ManuscriptCoreOutput, Segment, SegmentType
from core.editorial import EditorialAgent
from core.layout import LayoutAgent
from core.adn import ADNExtractor
from core.adn.extractor_optimized import OptimizedADNExtractor


def generate_test_data(num_segments: int = 500):
    """Generate test data for benchmarking"""
    segments = []
    for i in range(num_segments):
        if i % 50 == 0:
            text = f"Chapter {i // 50 + 1}: Important Title Here"
            seg_type = SegmentType.CHAPTER
            level = 1
        elif i % 10 == 0:
            text = f"Section {i // 10}: Detailed Heading"
            seg_type = SegmentType.HEADING
            level = 2
        else:
            # Mix of content with proper nouns
            names = ["Dr. Smith", "Prof. Johnson", "Mr. Williams", "Harvard University", "MIT"]
            name = names[i % len(names)]
            text = f"This is paragraph {i} with some content about {name}. " * 5
            seg_type = SegmentType.PARAGRAPH
            level = 0

        segments.append(Segment(
            id=f"seg_{i:04d}",
            type=seg_type,
            level=level,
            original_text=text,
            translated_text=text,
        ))

    manuscript = ManuscriptCoreOutput(
        source_file="benchmark_test.txt",
        source_language="en",
        target_language="vi",
    )
    manuscript.segments = segments

    return manuscript, [s.translated_text for s in segments]


def benchmark_adn(texts: list, iterations: int = 5):
    """Compare ADN extractors"""
    print("\n" + "=" * 60)
    print("ADN EXTRACTOR COMPARISON")
    print("=" * 60)
    print(f"Text size: {sum(len(t) for t in texts):,} characters")
    print(f"Segments: {len(texts)}")
    print(f"Iterations: {iterations}")
    print("-" * 60)

    # Warmup
    extractor = ADNExtractor(source_lang="en", target_lang="vi")
    _ = extractor.extract(texts[:10], "book")
    opt_extractor = OptimizedADNExtractor(source_lang="en", target_lang="vi")
    _ = opt_extractor.extract(texts[:10], "book")

    # Original
    times_original = []
    for i in range(iterations):
        extractor = ADNExtractor(source_lang="en", target_lang="vi")
        start = time.perf_counter()
        adn = extractor.extract(texts, "book")
        elapsed = time.perf_counter() - start
        times_original.append(elapsed)
        if i == 0:
            orig_nouns = len(adn.proper_nouns)
            orig_patterns = len(adn.patterns)

    avg_original = sum(times_original) / len(times_original)
    min_original = min(times_original)

    print(f"Original:  avg={avg_original:.4f}s  min={min_original:.4f}s")
    print(f"           nouns={orig_nouns}, patterns={orig_patterns}")

    # Optimized
    times_optimized = []
    for i in range(iterations):
        extractor = OptimizedADNExtractor(source_lang="en", target_lang="vi")
        start = time.perf_counter()
        adn = extractor.extract(texts, "book")
        elapsed = time.perf_counter() - start
        times_optimized.append(elapsed)
        if i == 0:
            opt_nouns = len(adn.proper_nouns)
            opt_patterns = len(adn.patterns)

    avg_optimized = sum(times_optimized) / len(times_optimized)
    min_optimized = min(times_optimized)

    print(f"Optimized: avg={avg_optimized:.4f}s  min={min_optimized:.4f}s")
    print(f"           nouns={opt_nouns}, patterns={opt_patterns}")

    speedup = avg_original / avg_optimized if avg_optimized > 0 else 0
    print("-" * 60)
    print(f"Speedup:   {speedup:.2f}x faster")

    return avg_original, avg_optimized


def benchmark_docx(manuscript, iterations: int = 3):
    """Compare DOCX renderers"""
    print("\n" + "=" * 60)
    print("DOCX RENDERER COMPARISON")
    print("=" * 60)
    print(f"Segments: {len(manuscript.segments)}")
    print(f"Iterations: {iterations}")
    print("-" * 60)

    # Create LIP (this is the same for both)
    editorial = EditorialAgent(template="book")
    lip = editorial.process(manuscript)

    # Warmup
    layout_orig = LayoutAgent(template="book", use_optimized=False)
    _ = layout_orig.process(lip, "/tmp/warmup_orig.docx")
    layout_opt = LayoutAgent(template="book", use_optimized=True)
    _ = layout_opt.process(lip, "/tmp/warmup_opt.docx")

    # Original renderer
    times_original = []
    for i in range(iterations):
        layout = LayoutAgent(template="book", use_optimized=False)
        output_path = f"/tmp/bench_original_{i}.docx"
        start = time.perf_counter()
        layout.process(lip, output_path)
        elapsed = time.perf_counter() - start
        times_original.append(elapsed)
        Path(output_path).unlink(missing_ok=True)

    avg_original = sum(times_original) / len(times_original)
    min_original = min(times_original)
    print(f"Original:  avg={avg_original:.4f}s  min={min_original:.4f}s")

    # Optimized renderer
    times_optimized = []
    for i in range(iterations):
        layout = LayoutAgent(template="book", use_optimized=True)
        output_path = f"/tmp/bench_optimized_{i}.docx"
        start = time.perf_counter()
        layout.process(lip, output_path)
        elapsed = time.perf_counter() - start
        times_optimized.append(elapsed)
        Path(output_path).unlink(missing_ok=True)

    avg_optimized = sum(times_optimized) / len(times_optimized)
    min_optimized = min(times_optimized)
    print(f"Optimized: avg={avg_optimized:.4f}s  min={min_optimized:.4f}s")

    speedup = avg_original / avg_optimized if avg_optimized > 0 else 0
    print("-" * 60)
    print(f"Speedup:   {speedup:.2f}x faster")

    # Cleanup warmup files
    Path("/tmp/warmup_orig.docx").unlink(missing_ok=True)
    Path("/tmp/warmup_opt.docx").unlink(missing_ok=True)

    return avg_original, avg_optimized


def main():
    print("\n" + "=" * 60)
    print("       PERF-002: OPTIMIZATION BENCHMARK")
    print("=" * 60)

    # Generate test data
    print("\nGenerating test data (500 segments)...")
    manuscript, texts = generate_test_data(500)
    total_chars = sum(len(t) for t in texts)
    print(f"Total characters: {total_chars:,}")

    # Benchmark ADN
    try:
        adn_orig, adn_opt = benchmark_adn(texts)
    except Exception as e:
        print(f"ADN benchmark error: {e}")
        adn_orig, adn_opt = 0.1, 0.1

    # Benchmark DOCX
    try:
        docx_orig, docx_opt = benchmark_docx(manuscript)
    except Exception as e:
        print(f"DOCX benchmark error: {e}")
        docx_orig, docx_opt = 0.3, 0.3

    # Summary
    print("\n" + "=" * 60)
    print("                    SUMMARY")
    print("=" * 60)
    print(f"\n{'Component':<20} {'Original':>12} {'Optimized':>12} {'Speedup':>10}")
    print("-" * 60)

    adn_speedup = adn_orig / adn_opt if adn_opt > 0 else 0
    docx_speedup = docx_orig / docx_opt if docx_opt > 0 else 0

    print(f"{'ADN Extraction':<20} {adn_orig:>11.4f}s {adn_opt:>11.4f}s {adn_speedup:>9.2f}x")
    print(f"{'DOCX Rendering':<20} {docx_orig:>11.4f}s {docx_opt:>11.4f}s {docx_speedup:>9.2f}x")

    total_orig = adn_orig + docx_orig
    total_opt = adn_opt + docx_opt
    total_speedup = total_orig / total_opt if total_opt > 0 else 0

    print("-" * 60)
    print(f"{'TOTAL':<20} {total_orig:>11.4f}s {total_opt:>11.4f}s {total_speedup:>9.2f}x")

    # Visual summary
    print("\n" + "=" * 60)
    print("                  RESULTS")
    print("=" * 60)
    print(f"""
    ADN Extraction:   {'IMPROVED' if adn_speedup > 1.1 else 'SIMILAR'} ({adn_speedup:.2f}x)
    DOCX Rendering:   {'IMPROVED' if docx_speedup > 1.1 else 'SIMILAR'} ({docx_speedup:.2f}x)

    Overall Speedup: {total_speedup:.2f}x faster
    """)

    print("=" * 60)


if __name__ == "__main__":
    main()
