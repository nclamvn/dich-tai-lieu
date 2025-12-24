#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Demo Phase 2 - Showcase all Phase 2 features
- Domain-specific glossaries
- Enhanced quality validation
- Parallel processing
- Performance analytics
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.chunker import SmartChunker
from core.cache import TranslationCache
from core.validator import QualityValidator
from core.glossary import GlossaryManager
from core.translator import TranslatorEngine
from core.merger import SmartMerger
from core.analytics import PerformanceAnalyzer


# Sample texts for different domains
SAMPLE_TEXTS = {
    "finance": """
Investment Strategy Overview

Understanding diversification is crucial for long-term success. A well-balanced portfolio
typically includes stocks, bonds, and ETFs. The P/E ratio is an important valuation metric
that investors should monitor regularly.

According to Warren Buffett, "Price is what you pay, value is what you get." This philosophy
emphasizes the importance of fundamental analysis over market speculation.

Key metrics to watch:
- Market cap and liquidity
- Dividend yield (typically 2-4% for stable companies)
- ROI expectations should be realistic
- Volatility and risk tolerance

The S&P 500 has historically returned about 10% annually over the long term, but past
performance doesn't guarantee future results. IPOs can be exciting but often come with
higher volatility.
""",

    "literature": """
Chapter 3: The Discovery

Detective Morrison stood in the dimly lit library, examining the ancient manuscript.
"This changes everything," she whispered to her partner.

The mystery had deepened with each passing hour. What they'd thought was a simple
investigation had transformed into something far more sinister. The protagonist's
journey was just beginning.

Through the window, shadows danced across the walls. A sudden flashback reminded her
of similar cases—the pattern was unmistakable. This was no coincidence.

"We need to find the witness before it's too late," she said urgently. The climax
was approaching, and with it, answers to questions that had haunted them for weeks.

The atmosphere was tense as they uncovered clue after clue, each revelation bringing
them closer to the truth.
""",

    "medical": """
Patient Treatment Protocol

The patient presented with acute symptoms requiring immediate attention. After thorough
examination, the diagnosis indicated a bacterial infection requiring antibiotic treatment.

Dosage Instructions:
- Amoxicillin 500mg, three times daily for 7 days
- Take with food to minimize side effects
- Complete the full course even if symptoms improve

The physician explained potential adverse reactions including nausea and dizziness.
Regular blood tests will monitor the therapy's effectiveness.

CRITICAL: If symptoms worsen or new symptoms appear, seek emergency care immediately.
Patients with allergies to penicillin should not take this medication. The ICU stands
ready for any complications.

Follow-up examination scheduled in two weeks. The prognosis is good with proper
treatment adherence. MRI and CT scans showed no concerning findings.
""",

    "technology": """
API Integration Guide

To implement the authentication system, first create an HTTP endpoint:

```python
@app.route('/api/auth', methods=['POST'])
def authenticate():
    token = generate_jwt_token(user_id)
    return jsonify({'token': token})
```

The REST API uses standard HTTPS protocol for secure communication. Your API key
should be stored in environment variables, never hardcoded.

Key considerations:
- Database queries should use connection pooling
- Implement proper error handling with try-catch blocks
- Use caching for frequently accessed data
- SQL injection prevention is critical

The frontend makes asynchronous calls using the Fetch API. JSON responses follow
standard formatting conventions. URL parameters are validated server-side.

For machine learning integration, the model uses TensorFlow with GPU acceleration.
The algorithm processes data in batches, with hyperparameter tuning for optimal
performance.
"""
}


async def demo_translation(domain: str, sample_text: str):
    """Demo translation for a specific domain"""

    print("\n" + "=" * 80)
    print(f"DEMO: {domain.upper()} DOMAIN TRANSLATION".center(80))
    print("=" * 80)

    # Initialize components
    model_config = settings.get_model_config()

    print(f"\n📋 Configuration:")
    print(f"   Provider: {settings.provider}")
    print(f"   Model: {model_config['model']}")
    print(f"   Domain: {domain}")
    print(f"   Concurrency: {settings.concurrency}")

    # Load domain-specific glossary
    glossary_mgr = GlossaryManager(settings.glossary_dir, domain)
    print(f"\n📚 Glossary: Loaded {glossary_mgr.get_term_count()} terms for {domain} domain")

    # Initialize other components
    chunker = SmartChunker(
        max_chars=model_config['max_chars'],
        context_window=model_config['context_window']
    )
    cache = TranslationCache(settings.cache_dir, settings.cache_enabled)
    validator = QualityValidator()

    translator = TranslatorEngine(
        provider=settings.provider,
        model=model_config['model'],
        api_key=settings.get_api_key(),
        glossary_mgr=glossary_mgr,
        cache=cache,
        validator=validator
    )

    # Create chunks
    chunks = chunker.create_chunks(sample_text)
    print(f"\n🔪 Created {len(chunks)} chunks")

    # Setup analytics
    analytics = PerformanceAnalyzer(settings.analytics_dir)
    session = analytics.create_session(
        project_name=f"demo_{domain}",
        domain=domain,
        provider=settings.provider,
        model=model_config['model']
    )

    print(f"\n🚀 Starting parallel translation...")
    print(f"   Session ID: {session.session_id}")

    # Translate with parallel processing
    results, stats = await translator.translate_parallel(
        chunks,
        max_concurrency=settings.concurrency,
        show_progress=True
    )

    print(f"\n✅ Translation complete!")
    print(f"   Completed: {stats.completed}/{stats.total_tasks}")
    print(f"   Failed: {stats.failed}")
    print(f"   Cache hits: {stats.cache_hits}")

    # Finalize session and generate analytics
    analytics.finalize_session(session, results, stats)

    # Show quality breakdown
    print(f"\n📊 Quality Analysis:")
    for quality_level, count in session.quality_distribution.items():
        if count > 0:
            percentage = (count / session.total_chunks) * 100
            print(f"   {quality_level:12s}: {count} chunks ({percentage:.1f}%)")

    print(f"\n   Average quality: {session.avg_quality_score:.3f}")
    print(f"   Warnings issued: {session.warnings_count}")

    # Show domain-specific validation results
    if results:
        print(f"\n🔍 Domain-Specific Validation Examples:")
        for i, result in enumerate(results[:2], 1):  # Show first 2
            if result.domain_scores:
                print(f"\n   Chunk {i}:")
                for metric, score in result.domain_scores.items():
                    if metric != 'length' and metric != 'completeness':  # Focus on interesting metrics
                        print(f"      {metric:20s}: {score:.3f}")

    # Merge translations
    merger = SmartMerger()
    final_text = merger.merge_translations(results)

    # Show sample output
    print(f"\n📝 Translation Sample (first 300 chars):")
    print("─" * 80)
    print(final_text[:300] + "...")
    print("─" * 80)

    # Performance summary
    print(f"\n⚡ Performance Metrics:")
    print(f"   Processing time: {session.processing_time:.2f}s")
    print(f"   Throughput: {session.chunks_per_minute:.1f} chunks/min")
    print(f"   Translation speed: {session.chars_per_second:.0f} chars/sec")

    # Cost estimation
    print(f"\n💰 Cost Estimation:")
    print(f"   Estimated tokens: {session.estimated_tokens:,}")
    print(f"   Estimated cost: ${session.estimated_cost_usd:.4f}")

    # Save cache
    cache.save()

    return session, final_text


async def main():
    """Main demo function"""

    print("=" * 80)
    print("AI TRANSLATOR PRO - PHASE 2 DEMO".center(80))
    print("=" * 80)
    print("\nShowcasing:")
    print("  ✓ Domain-Specific Glossaries")
    print("  ✓ Enhanced Quality Validation")
    print("  ✓ Parallel Processing")
    print("  ✓ Performance Analytics")

    # Check API key
    if not settings.get_api_key():
        print("\n❌ ERROR: No API key found!")
        print("   Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        return

    sessions = []

    # Demo each domain
    for domain in ["finance", "literature", "medical", "technology"]:
        try:
            session, translated = await demo_translation(domain, SAMPLE_TEXTS[domain])
            sessions.append(session)

            # Save translated output
            output_file = settings.output_dir / f"demo_{domain}.txt"
            output_file.write_text(translated, encoding='utf-8')
            print(f"\n💾 Saved to: {output_file}")

        except Exception as e:
            print(f"\n❌ Error in {domain} domain: {e}")
            import traceback
            traceback.print_exc()

    # Generate summary report
    if sessions:
        print("\n" + "=" * 80)
        print("FINAL SUMMARY".center(80))
        print("=" * 80)

        analytics = PerformanceAnalyzer(settings.analytics_dir)
        summary = analytics.generate_summary_report(sessions)
        print(summary)

        # Save summary
        summary_file = settings.analytics_dir / "phase2_demo_summary.txt"
        summary_file.write_text(summary, encoding='utf-8')
        print(f"\n💾 Summary saved to: {summary_file}")

    print("\n" + "=" * 80)
    print("✅ DEMO COMPLETE!".center(80))
    print("=" * 80)
    print("\nCheck the following directories for results:")
    print(f"   📁 Translations: {settings.output_dir}")
    print(f"   📊 Analytics: {settings.analytics_dir}")
    print(f"   💾 Cache: {settings.cache_dir}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
