#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E smoke test for the core_v2 translation engine (Vibecode Phases 1–7).

Runs a real multi-chunk document through UniversalPublisher.publish() with a
REAL provider API key and asserts business-level outcomes + side effects. This is
the live acceptance check the sandbox could not perform (no API key there).

Philosophy (tester-ao-e2e): truthful assertions — if no API key is configured we
SKIP loudly (exit 0, nothing verified), never fake a pass; we read back the chunk
cache DB, not just "it returned"; and we re-run to prove cache reuse.

USAGE
-----
    # from the repo root, with your venv active and deps installed:
    export OPENAI_API_KEY=sk-...          # or ANTHROPIC_API_KEY / GOOGLE_API_KEY / DEEPSEEK_API_KEY
    python3 scripts/e2e_translation_smoke.py

    # deeper checks (optional, each adds LLM calls):
    export TRANSLATION_SEMANTIC_VERIFY_ENABLED=true   # Phase 7 semantic faithfulness pass
    export TRANSLATION_CONTEXT_SUMMARY_ENABLED=true    # Phase 5 LLM summary pre-pass
    export TM_REUSE_ENABLED=true                        # Phase 6 (needs a populated TM to have effect)

Exit code 0 = all hard checks passed (or skipped for lack of key); 1 = a check failed.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Make the repo root importable when run as `python3 scripts/e2e_translation_smoke.py`.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PROVIDER_ENV_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY",
]

# A recurring proper noun ("Aurora Protocol") + a heading, long enough to force
# multiple chunks so chunking, rolling context, terminology and the repair pass
# all engage. ~ several paragraphs of real prose.
_PARA = (
    "The Aurora Protocol is a distributed coordination framework for autonomous "
    "agents. It was designed so that every agent shares a single, consistent view "
    "of the mission state. When an agent joins, the Aurora Protocol assigns it a "
    "role and a budget of actions. Faithful adherence to the protocol keeps the "
    "swarm coherent even under partial network failure. "
)


def build_document() -> str:
    parts = ["# Chapter 1: Foundations of the Aurora Protocol\n"]
    for i in range(1, 7):
        parts.append(f"\nSection {i}. " + (_PARA * 3))
    parts.append("\n# Chapter 2: Operating the Aurora Protocol\n")
    for i in range(1, 6):
        parts.append(f"\nSection {i}. " + (_PARA * 3))
    return "\n".join(parts)


def _vietnamese_ratio(text: str) -> float:
    vi = set(
        "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệ"
        "ìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
        "ùúủũụưứừửữựỳýỷỹỵđ"
    )
    vi |= {c.upper() for c in vi}
    alpha = sum(1 for c in text if c.isalpha())
    if not alpha:
        return 0.0
    return sum(1 for c in text if c in vi) / alpha


class _Adapter:
    """Mirrors api.aps_v2_service.LLMClientAdapter (max_tokens=8192, forwards
    temperature/cache_system) without importing the FastAPI layer."""

    def __init__(self, unified):
        self._u = unified

    async def chat(self, messages, response_format=None, max_tokens=8192,
                   temperature=None, cache_system=False):
        return await self._u.chat(
            messages=messages, max_tokens=max_tokens, response_format=response_format,
            temperature=temperature, cache_system=cache_system,
        )

    def get_current_provider(self):
        return self._u.get_current_provider()


async def _run_once(doc: str):
    from ai_providers.unified_client import UnifiedLLMClient
    from core_v2.orchestrator import UniversalPublisher, JobStatus

    client = UnifiedLLMClient()
    publisher = UniversalPublisher(llm_client=_Adapter(client), enable_verification=False)
    t0 = time.time()
    job = await publisher.publish(
        source_text=doc, source_lang="en", target_lang="vi",
        profile_id="essay", output_format="md", use_vision=False,
    )
    return job, JobStatus, time.time() - t0, client


def main() -> int:
    keys = [k for k in PROVIDER_ENV_KEYS if os.environ.get(k)]
    print("=" * 68)
    print(" core_v2 translation E2E smoke test (Vibecode Phases 1–7)")
    print("=" * 68)
    if not keys:
        print("\n[SKIP] No provider API key found in the environment.")
        print("       Set one of:", ", ".join(PROVIDER_ENV_KEYS))
        print("       e.g.  export OPENAI_API_KEY=sk-...   then re-run.")
        print("       (Nothing was verified — this is a truthful skip, not a pass.)")
        return 0
    print(f"\nProvider key(s) present: {', '.join(keys)}")

    from config.settings import settings
    from core_v2.token_chunking import estimate_tokens

    doc = build_document()
    print(f"Sample document: {len(doc):,} chars\n")

    checks: list[tuple[str, bool, str]] = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

    # ---- Run 1 ----
    print("Run 1 (fresh)...")
    job, JobStatus, dt1, client = asyncio.run(_run_once(doc))

    if job.error:
        print(f"  job.error = {job.error}")
    check("job completed", job.status == JobStatus.COMPLETE,
          f"status={job.status.value}")
    check("produced >= 2 chunks (multi-chunk path)", len(job.chunks) >= 2,
          f"chunks={len(job.chunks)}")
    check("translated all chunks", len(job.translated_chunks) == len(job.chunks)
          and len(job.translated_chunks) > 0,
          f"translated={len(job.translated_chunks)}")
    joined = "\n".join(job.translated_chunks)
    check("no [TRANSLATION ERROR] holes (Phase 1 fail-loud)",
          "[TRANSLATION ERROR" not in joined)
    check("output is Vietnamese", _vietnamese_ratio(joined) > 0.02,
          f"vi_ratio={_vietnamese_ratio(joined):.3f}")

    budget = int(getattr(settings, "chunk_max_tokens", 2000))
    oversized = [i for i, c in enumerate(job.chunks)
                 if estimate_tokens(c.content) > budget]
    check(f"no source chunk exceeds token budget {budget} (Phase 3)",
          not oversized, f"oversized={oversized}")

    if len(job.chunks) >= 2:
        check("rolling context set from previous chunk (Phase 5)",
              job.chunks[1].previous_summary is not None,
              "previous_summary present on chunk[1]")

    # ---- Side effect: chunk cache DB populated (Phase 1 wiring) ----
    cache_db = Path(getattr(settings, "cache_dir", REPO_ROOT / "data" / "cache")) / "chunks.db"
    entries = -1
    if cache_db.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(cache_db))
            entries = conn.execute("SELECT COUNT(*) FROM chunk_cache").fetchone()[0]
            conn.close()
        except Exception as e:
            print(f"  (could not read cache db: {e})")
    check("chunk cache DB populated (Phase 1)", entries > 0,
          f"{cache_db} entries={entries}")

    # ---- Run 2: prove cache reuse (same doc -> identical, faster) ----
    print("\nRun 2 (same document — expect cache reuse)...")
    job2, _, dt2, _ = asyncio.run(_run_once(doc))
    same = job2.translated_chunks == job.translated_chunks
    check("re-run reuses cache: identical translation (Phase 1)", same,
          f"run1={dt1:.1f}s run2={dt2:.1f}s")

    # ---- Usage / cost ----
    try:
        usage = client.get_usage_dict()
        print(f"\nUsage (run 1): {usage.get('total_tokens', '?')} tokens, "
              f"~${usage.get('estimated_cost_usd', '?')}, provider={client.get_current_provider()}")
    except Exception:
        pass

    # ---- Eyeball sample ----
    print("\n--- first translated chunk (eyeball terminology/fluency) ---")
    print((job.translated_chunks[0] if job.translated_chunks else "")[:600])
    print("--- end sample ---")

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print("\n" + "=" * 68)
    print(f" RESULT: {passed}/{total} checks passed")
    print("=" * 68)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
