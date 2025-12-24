#!/usr/bin/env python3
"""
Phase 3.6 - Real Book Testing Script

Test AST pipeline with large synthetic documents (200-500 pages)
to verify stability, performance, and typography consistency.

Usage:
    python scripts/test_real_book_docs.py --mode novel --chapters 20 --paras-per-chapter 50
    python scripts/test_real_book_docs.py --mode academic --chapters 15 --paras-per-chapter 30
    python scripts/test_real_book_docs.py --mode mixed --chapters 25 --paras-per-chapter 40
    python scripts/test_real_book_docs.py --all-scenarios  # Run all 3 scenarios
"""

import argparse
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any
import random
import psutil
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.structure.semantic_model import DocNode, DocNodeType, DocNodeList
from core.rendering.ast_builder import build_book_ast, build_academic_ast
from core.rendering.docx_adapter import render_docx_from_ast
from core.rendering.document_ast import DocumentMetadata

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# Synthetic Content Generation
# ============================================================================

class SyntheticDocumentGenerator:
    """Generate realistic synthetic documents for testing."""

    # Sample text fragments for realistic documents
    NOVEL_PARAGRAPHS = [
        "The rain began to fall harder now, drumming against the window panes with increasing intensity. She watched the droplets race down the glass, each one a small river carving its path through the condensation.",
        "John turned the corner and stopped abruptly. The street was empty, but he could have sworn he heard footsteps behind him just moments ago. His breath formed small clouds in the cold morning air.",
        "The old house stood at the end of the lane, its windows dark and empty. Nobody had lived there for years, yet the garden was somehow still well-tended, roses blooming impossibly in the winter frost.",
        "She opened the letter with trembling hands. After all these years, she had finally received a reply. The words on the page blurred as tears welled up in her eyes.",
        "The market square bustled with activity. Vendors called out their wares, children laughed and played, and somewhere a street musician played a melancholy tune on a worn violin.",
    ]

    ACADEMIC_PARAGRAPHS = [
        "The fundamental theorem establishes a direct relationship between the derivative and the integral. This connection forms the cornerstone of calculus and enables powerful techniques for solving complex problems.",
        "Recent experimental results have confirmed the theoretical predictions with remarkable accuracy. The data shows a clear correlation between the input parameters and the observed outcomes.",
        "This methodology builds upon previous work in the field while introducing novel approaches to address computational complexity. The algorithm achieves O(n log n) time complexity in the average case.",
        "The analysis reveals several interesting properties of the proposed model. First, it demonstrates convergence under reasonable assumptions. Second, it provides explicit error bounds for finite approximations.",
        "These findings have significant implications for future research. They suggest that the traditional approach may need to be revised in light of new evidence from large-scale simulations.",
    ]

    BLOCKQUOTES = [
        ("All that we are is the result of what we have thought.", "Buddha"),
        ("The only way to do great work is to love what you do.", "Steve Jobs"),
        ("In the middle of difficulty lies opportunity.", "Albert Einstein"),
        ("Be yourself; everyone else is already taken.", "Oscar Wilde"),
        ("Life is what happens when you're busy making other plans.", "John Lennon"),
    ]

    EPIGRAPHS = [
        ("Not all those who wander are lost.", "J.R.R. Tolkien"),
        ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
        ("To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment.", "Ralph Waldo Emerson"),
    ]

    EQUATIONS = [
        r"E = mc^2",
        r"\int_{a}^{b} f(x) dx = F(b) - F(a)",
        r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}",
        r"\frac{\partial f}{\partial x} = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}",
        r"\nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}",
    ]

    def __init__(self, mode: str = "novel"):
        """
        Initialize generator.

        Args:
            mode: "novel", "academic", or "mixed"
        """
        self.mode = mode
        random.seed(42)  # Reproducible results

    def generate_document(
        self,
        chapters: int = 20,
        paras_per_chapter: int = 50,
        blockquote_ratio: float = 0.05,
        epigraph_ratio: float = 0.1,
        scene_break_ratio: float = 0.02
    ) -> DocNodeList:
        """
        Generate a synthetic document.

        Args:
            chapters: Number of chapters
            paras_per_chapter: Average paragraphs per chapter
            blockquote_ratio: Probability of paragraph being a blockquote
            epigraph_ratio: Probability of chapter having an epigraph
            scene_break_ratio: Probability of inserting a scene break

        Returns:
            DocNodeList ready for AST building
        """
        nodes = []

        logger.info(f"Generating {self.mode} document: {chapters} chapters, ~{paras_per_chapter} paras/chapter")

        for chapter_num in range(1, chapters + 1):
            # Add chapter heading
            nodes.append(self._make_chapter(chapter_num))

            # Add epigraph (10% chance)
            if random.random() < epigraph_ratio:
                nodes.append(self._make_epigraph())

            # Add paragraphs
            num_paras = random.randint(
                int(paras_per_chapter * 0.8),
                int(paras_per_chapter * 1.2)
            )

            for para_num in range(num_paras):
                # Scene break (2% chance)
                if para_num > 0 and random.random() < scene_break_ratio:
                    nodes.append(self._make_scene_break())

                # Blockquote (5% chance)
                if random.random() < blockquote_ratio:
                    nodes.append(self._make_blockquote())
                else:
                    # Regular paragraph (or theorem/equation in academic mode)
                    if self.mode == "academic" and random.random() < 0.1:
                        # 10% chance of theorem/equation in academic mode
                        if random.random() < 0.5:
                            nodes.append(self._make_theorem(chapter_num, para_num))
                        else:
                            nodes.append(self._make_equation(chapter_num, para_num))
                    elif self.mode == "mixed" and random.random() < 0.05:
                        # 5% chance of theorem/equation in mixed mode
                        nodes.append(self._make_equation(chapter_num, para_num))
                    else:
                        nodes.append(self._make_paragraph())

        logger.info(f"Generated document: {len(nodes)} total blocks")
        return nodes

    def _make_chapter(self, num: int) -> DocNode:
        """Create a chapter heading."""
        if self.mode == "academic":
            title = f"Chapter {num}: Theoretical Foundations"
        elif self.mode == "novel":
            title = f"Chapter {num}"
        else:
            title = f"Chapter {num}: Mixed Content"

        return DocNode(
            node_type=DocNodeType.CHAPTER,
            text=title,
            level=1,
            metadata={'number': str(num)}
        )

    def _make_paragraph(self) -> DocNode:
        """Create a regular paragraph."""
        if self.mode == "academic":
            text = random.choice(self.ACADEMIC_PARAGRAPHS)
        else:
            text = random.choice(self.NOVEL_PARAGRAPHS)

        return DocNode(
            node_type=DocNodeType.PARAGRAPH,
            text=text,
            metadata={}
        )

    def _make_blockquote(self) -> DocNode:
        """Create a blockquote."""
        text, attribution = random.choice(self.BLOCKQUOTES)
        return DocNode(
            node_type=DocNodeType.BLOCKQUOTE,
            text=text,
            metadata={'attribution': attribution}
        )

    def _make_epigraph(self) -> DocNode:
        """Create an epigraph."""
        text, attribution = random.choice(self.EPIGRAPHS)
        return DocNode(
            node_type=DocNodeType.EPIGRAPH,
            text=text,
            metadata={'attribution': attribution}
        )

    def _make_scene_break(self) -> DocNode:
        """Create a scene break."""
        return DocNode(
            node_type=DocNodeType.SCENE_BREAK,
            text="* * *",
            metadata={}
        )

    def _make_theorem(self, chapter: int, num: int) -> DocNode:
        """Create a theorem."""
        return DocNode(
            node_type=DocNodeType.THEOREM,
            text="If f is continuous on [a,b] and differentiable on (a,b), then there exists c in (a,b) such that f'(c) = (f(b)-f(a))/(b-a).",
            title="Mean Value Theorem",
            metadata={'number': f"{chapter}.{num}"}
        )

    def _make_equation(self, chapter: int, num: int) -> DocNode:
        """Create an equation."""
        latex = random.choice(self.EQUATIONS)
        return DocNode(
            node_type=DocNodeType.EQUATION_BLOCK,
            text=f"$${latex}$$",
            metadata={'equation_number': f"({chapter}.{num})"}
        )


# ============================================================================
# Benchmark & Testing
# ============================================================================

class DocumentBenchmark:
    """Benchmark document generation and rendering."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def measure_memory(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def run_benchmark(
        self,
        mode: str,
        chapters: int,
        paras_per_chapter: int,
        output_dir: Path
    ) -> Dict[str, Any]:
        """
        Run a complete benchmark.

        Returns:
            Dict with benchmark results
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"=" * 70)
        logger.info(f"BENCHMARK: {mode.upper()} MODE")
        logger.info(f"=" * 70)

        # Memory baseline
        mem_start = self.measure_memory()

        # Step 1: Generate synthetic document
        logger.info("Step 1: Generating synthetic document...")
        gen = SyntheticDocumentGenerator(mode=mode)

        gen_start = time.perf_counter()
        doc_nodes = gen.generate_document(
            chapters=chapters,
            paras_per_chapter=paras_per_chapter
        )
        gen_time = time.perf_counter() - gen_start

        mem_after_gen = self.measure_memory()

        # Step 2: Build AST
        logger.info("Step 2: Building DocumentAST...")

        ast_start = time.perf_counter()
        if mode == "academic":
            ast = build_academic_ast(doc_nodes, language='vi')
        else:
            ast = build_book_ast(doc_nodes, language='vi')
        ast_time = time.perf_counter() - ast_start

        mem_after_ast = self.measure_memory()

        # Step 3: Render to DOCX
        logger.info("Step 3: Rendering to DOCX...")

        output_path = output_dir / f"phase36_test_{mode}_{chapters}ch.docx"

        render_start = time.perf_counter()
        render_docx_from_ast(ast, output_path)
        render_time = time.perf_counter() - render_start

        mem_after_render = self.measure_memory()

        # Get file size
        file_size_mb = output_path.stat().st_size / 1024 / 1024

        # Collect stats
        stats = ast.get_statistics()

        # Build result
        result = {
            'mode': mode,
            'chapters': chapters,
            'paras_per_chapter': paras_per_chapter,
            'total_blocks': len(doc_nodes),
            'headings': stats['headings'],
            'paragraphs': stats['paragraphs'],
            'equations': stats['equations'],
            'blockquotes': stats.get('blockquotes', 0),
            'epigraphs': stats.get('epigraphs', 0),
            'scene_breaks': stats.get('scene_breaks', 0),
            'theorems': stats.get('theorems', 0),
            'gen_time_sec': gen_time,
            'ast_time_sec': ast_time,
            'render_time_sec': render_time,
            'total_time_sec': gen_time + ast_time + render_time,
            'mem_baseline_mb': mem_start,
            'mem_after_gen_mb': mem_after_gen,
            'mem_after_ast_mb': mem_after_ast,
            'mem_after_render_mb': mem_after_render,
            'mem_peak_mb': mem_after_render,
            'mem_delta_mb': mem_after_render - mem_start,
            'file_size_mb': file_size_mb,
            'output_path': str(output_path)
        }

        self._print_result(result)

        return result

    def _print_result(self, result: Dict[str, Any]):
        """Pretty print benchmark result."""
        logger.info("")
        logger.info(f"{'='*70}")
        logger.info(f"BENCHMARK RESULTS: {result['mode'].upper()}")
        logger.info(f"{'='*70}")
        logger.info("")
        logger.info(f"📊 Document Structure:")
        logger.info(f"  Total blocks:     {result['total_blocks']}")
        logger.info(f"  Chapters:         {result['chapters']}")
        logger.info(f"  Headings:         {result['headings']}")
        logger.info(f"  Paragraphs:       {result['paragraphs']}")
        logger.info(f"  Blockquotes:      {result['blockquotes']}")
        logger.info(f"  Epigraphs:        {result['epigraphs']}")
        logger.info(f"  Scene breaks:     {result['scene_breaks']}")
        if result['equations'] > 0:
            logger.info(f"  Equations:        {result['equations']}")
        if result['theorems'] > 0:
            logger.info(f"  Theorems:         {result['theorems']}")
        logger.info("")
        logger.info(f"⏱️  Performance:")
        logger.info(f"  Generation time:  {result['gen_time_sec']:.3f}s")
        logger.info(f"  AST build time:   {result['ast_time_sec']:.3f}s")
        logger.info(f"  Render time:      {result['render_time_sec']:.3f}s")
        logger.info(f"  TOTAL TIME:       {result['total_time_sec']:.3f}s")
        logger.info("")
        logger.info(f"💾 Memory:")
        logger.info(f"  Baseline:         {result['mem_baseline_mb']:.1f} MB")
        logger.info(f"  After generation: {result['mem_after_gen_mb']:.1f} MB")
        logger.info(f"  After AST build:  {result['mem_after_ast_mb']:.1f} MB")
        logger.info(f"  After render:     {result['mem_after_render_mb']:.1f} MB")
        logger.info(f"  Peak memory:      {result['mem_peak_mb']:.1f} MB")
        logger.info(f"  Memory delta:     {result['mem_delta_mb']:.1f} MB")
        logger.info("")
        logger.info(f"📄 Output:")
        logger.info(f"  File size:        {result['file_size_mb']:.2f} MB")
        logger.info(f"  Location:         {result['output_path']}")
        logger.info("")

    def run_all_scenarios(self, output_dir: Path) -> List[Dict[str, Any]]:
        """Run all 3 standard test scenarios."""
        scenarios = [
            {
                'name': 'Novel (200-300 pages)',
                'mode': 'novel',
                'chapters': 25,
                'paras_per_chapter': 50,
            },
            {
                'name': 'Academic (100-200 pages)',
                'mode': 'academic',
                'chapters': 15,
                'paras_per_chapter': 35,
            },
            {
                'name': 'Mixed Content (150-250 pages)',
                'mode': 'mixed',
                'chapters': 20,
                'paras_per_chapter': 40,
            }
        ]

        results = []

        for scenario in scenarios:
            logger.info("")
            logger.info(f"🚀 Running scenario: {scenario['name']}")
            logger.info("")

            result = self.run_benchmark(
                mode=scenario['mode'],
                chapters=scenario['chapters'],
                paras_per_chapter=scenario['paras_per_chapter'],
                output_dir=output_dir
            )

            results.append(result)

            # Small pause between tests
            time.sleep(2)

        # Print summary
        self._print_summary(results)

        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print summary comparison of all scenarios."""
        logger.info("")
        logger.info(f"{'='*70}")
        logger.info(f"SUMMARY COMPARISON - ALL SCENARIOS")
        logger.info(f"{'='*70}")
        logger.info("")

        # Table header
        logger.info(f"{'Mode':<15} {'Blocks':<8} {'Time(s)':<10} {'Memory(MB)':<12} {'File(MB)':<10}")
        logger.info(f"{'-'*15} {'-'*8} {'-'*10} {'-'*12} {'-'*10}")

        # Table rows
        for r in results:
            logger.info(
                f"{r['mode']:<15} "
                f"{r['total_blocks']:<8} "
                f"{r['total_time_sec']:<10.2f} "
                f"{r['mem_delta_mb']:<12.1f} "
                f"{r['file_size_mb']:<10.2f}"
            )

        logger.info("")
        logger.info("✅ All scenarios completed successfully!")
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info("  1. Open the generated DOCX files in Microsoft Word")
        logger.info("  2. Verify typography consistency throughout the document:")
        logger.info("     - Headings: H1=16pt, H2=14pt, H3=12pt")
        logger.info("     - Body: 11pt Georgia, 1.15 line spacing")
        logger.info("     - First paragraph after heading: 0pt indent")
        logger.info("     - Body paragraphs: ~23pt indent")
        logger.info("  3. Check for any spacing/indent anomalies in later chapters")
        logger.info("  4. Verify special blocks (blockquotes, epigraphs, scene breaks)")
        logger.info("")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Phase 3.6 - Real Book Testing (AST Pipeline Stability Test)"
    )

    parser.add_argument(
        '--mode',
        choices=['novel', 'academic', 'mixed'],
        help='Document mode (novel/academic/mixed)'
    )

    parser.add_argument(
        '--chapters',
        type=int,
        default=20,
        help='Number of chapters (default: 20)'
    )

    parser.add_argument(
        '--paras-per-chapter',
        type=int,
        default=50,
        help='Average paragraphs per chapter (default: 50)'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./phase36_test_output'),
        help='Output directory for test files (default: ./phase36_test_output)'
    )

    parser.add_argument(
        '--all-scenarios',
        action='store_true',
        help='Run all 3 standard scenarios (novel/academic/mixed)'
    )

    args = parser.parse_args()

    # Print banner
    logger.info("")
    logger.info("=" * 70)
    logger.info("PHASE 3.6 - REAL BOOK TESTING")
    logger.info("AST Pipeline Stability & Performance Verification")
    logger.info("=" * 70)
    logger.info("")

    benchmark = DocumentBenchmark()

    if args.all_scenarios:
        # Run all 3 scenarios
        benchmark.run_all_scenarios(args.output_dir)
    elif args.mode:
        # Run single scenario
        benchmark.run_benchmark(
            mode=args.mode,
            chapters=args.chapters,
            paras_per_chapter=args.paras_per_chapter,
            output_dir=args.output_dir
        )
    else:
        parser.error("Must specify either --mode or --all-scenarios")

    logger.info("=" * 70)
    logger.info("TESTING COMPLETE")
    logger.info("=" * 70)
    logger.info("")


if __name__ == '__main__':
    main()
