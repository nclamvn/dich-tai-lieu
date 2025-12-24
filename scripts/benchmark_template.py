#!/usr/bin/env python3
"""
Benchmark: Template-based DOCX Renderer

Compare all DOCX rendering approaches:
1. Original (DocxRenderer)
2. Optimized (OptimizedDocxRenderer)
3. Template (TemplateDocxRenderer)
"""

import time
from pathlib import Path
import sys
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.contracts import ManuscriptCoreOutput, Segment, SegmentType
from core.editorial import EditorialAgent
from core.layout import LayoutAgent


def generate_test_manuscript(num_segments: int = 500):
    """Generate test manuscript"""
    segments = []

    for i in range(num_segments):
        if i % 20 == 0:
            text = f"Chapter {i // 20 + 1}: Important Title for This Chapter"
            seg_type = SegmentType.CHAPTER
            level = 1
        elif i % 10 == 0:
            text = f"Section {i}: Detailed Section Heading"
            seg_type = SegmentType.HEADING
            level = 2
        else:
            text = f"This is paragraph {i} with substantial content about various topics. " * 8
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
        source_file="benchmark.txt",
        source_language="en",
        target_language="vi",
    )
    manuscript.segments = segments

    return manuscript


def benchmark_layout_agent(lip, name: str, use_template: bool, use_optimized: bool, iterations: int = 5):
    """Benchmark a single renderer configuration"""
    times = []

    for i in range(iterations):
        layout = LayoutAgent(
            template="book",
            page_size="A4",
            use_template=use_template,
            use_optimized=use_optimized,
        )

        output_path = f"/tmp/bench_{name}_{i}.docx"

        start = time.perf_counter()
        layout.process(lip, output_path)
        elapsed = time.perf_counter() - start

        times.append(elapsed)

        # Get file size
        file_size = Path(output_path).stat().st_size

        # Cleanup
        Path(output_path).unlink(missing_ok=True)

    return {
        "name": name,
        "avg": statistics.mean(times),
        "min": min(times),
        "max": max(times),
        "std": statistics.stdev(times) if len(times) > 1 else 0,
        "file_size": file_size,
    }


def run_benchmark():
    """Run full benchmark"""
    print("\n" + "="*70)
    print("   PERF-003: DOCX RENDERER BENCHMARK")
    print("   Original vs Optimized vs Template")
    print("="*70)

    # Test sizes
    sizes = [
        ("Small (50 segments)", 50),
        ("Medium (200 segments)", 200),
        ("Large (500 segments)", 500),
        ("XLarge (1000 segments)", 1000),
        ("Book (2000 segments)", 2000),
    ]

    results = []

    for size_name, num_segments in sizes:
        print(f"\n{'-'*70}")
        print(f"Testing: {size_name}")
        print(f"{'-'*70}")

        # Generate test data
        manuscript = generate_test_manuscript(num_segments)
        total_chars = sum(len(s.translated_text) for s in manuscript.segments)
        print(f"Segments: {num_segments}, Characters: {total_chars:,}")

        # Create LIP (shared across all renderers)
        editorial = EditorialAgent(template="book")
        lip = editorial.process(manuscript)
        print(f"Blocks: {len(lip.blocks)}")

        # Benchmark configurations
        configs = [
            ("Original", False, False),
            ("Optimized", False, True),
            ("Template", True, True),
        ]

        size_results = {"size": size_name, "segments": num_segments, "chars": total_chars}

        for name, use_template, use_optimized in configs:
            result = benchmark_layout_agent(lip, name, use_template, use_optimized)
            print(f"  {name:12}: {result['avg']:.4f}s (min={result['min']:.4f}s, std={result['std']:.4f}s)")
            size_results[name] = result["avg"]

        # Calculate speedups
        if size_results.get("Original", 0) > 0:
            size_results["opt_speedup"] = size_results["Original"] / size_results.get("Optimized", 1)
            size_results["tpl_speedup"] = size_results["Original"] / size_results.get("Template", 1)

        results.append(size_results)

    # Summary
    print("\n" + "="*70)
    print("                           SUMMARY")
    print("="*70)

    print(f"\n{'Size':<25} {'Original':>10} {'Optimized':>10} {'Template':>10} {'Tpl Speedup':>12}")
    print("-"*70)

    for r in results:
        print(f"{r['size']:<25} {r.get('Original', 0):>9.4f}s {r.get('Optimized', 0):>9.4f}s {r.get('Template', 0):>9.4f}s {r.get('tpl_speedup', 0):>11.2f}x")

    # Overall speedup
    total_original = sum(r.get("Original", 0) for r in results)
    total_optimized = sum(r.get("Optimized", 0) for r in results)
    total_template = sum(r.get("Template", 0) for r in results)

    print("-"*70)
    tpl_overall = total_original / total_template if total_template > 0 else 1
    print(f"{'TOTAL':<25} {total_original:>9.4f}s {total_optimized:>9.4f}s {total_template:>9.4f}s {tpl_overall:>11.2f}x")

    # Visual summary
    print("\n" + "="*70)
    print("                      RESULTS")
    print("="*70)

    print(f"""
    Renderer Comparison (vs Original):

    Original:  1.00x (baseline)
    Optimized: {total_original/total_optimized:.2f}x
    Template:  {tpl_overall:.2f}x
    """)

    if tpl_overall >= 1.8:
        print(f"    Template renderer achieves {tpl_overall:.2f}x speedup - USE IN PRODUCTION!")
    elif tpl_overall >= 1.3:
        print(f"    Template renderer achieves {tpl_overall:.2f}x speedup - Good improvement!")
    else:
        print(f"    Template renderer achieves {tpl_overall:.2f}x speedup - Marginal improvement")

    print("\n" + "="*70)

    return results


if __name__ == "__main__":
    run_benchmark()
