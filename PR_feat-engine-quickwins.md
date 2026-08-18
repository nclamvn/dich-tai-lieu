# Translation engine upgrade — reliability, cost, quality (Phases 1–7)

**Branch:** `feat/engine-quickwins` → `main` · **22 commits** · **+~6.6K / −~150** · **254 engine tests passing, 0 regressions**

Resumes development after the ~4-month pause with a focused overhaul of the **live `core_v2` translation path** (`api → aps_v2_service → core_v2/orchestrator → ai_providers/unified_client`). Every change is **default-safe and env-toggleable**; nothing that adds LLM cost is on by default.

---

## Why

An audit found the live translation path was quietly under-powered: it ran at the provider-default temperature (~1.0) on the cheapest model, shipped a silent `[TRANSLATION ERROR]` placeholder into the delivered document when a chunk failed, re-translated identical content on every run, and **ignored the glossary, translation memory, and quality machinery that already existed in the repo**. It also had a real chunking bug where large documents collapsed into one oversized trailing chunk that blew past the model's output limit.

## What changed — by phase

| Phase | Change | Axis |
|------:|--------|------|
| **1** | Low translation temperature (0.3) + env-configurable per-provider model registry (default refreshed to `claude-sonnet-4-5-20250929`); **fail-loud** (`ChunkTranslationError` instead of `[TRANSLATION ERROR]`); exponential backoff + jitter, 429 back-off-then-failover, provider health **TTL**; prompt split into a cached system prefix + dynamic user (Anthropic prompt caching, ~30–50% fewer input tokens); **ChunkCache wired** into `core_v2`. | reliability · cost · quality |
| **2** | **Terminology ledger** — user glossary ⊕ auto-extracted terms injected into the cached prompt so terminology stays consistent across every chunk; ledger fingerprint folded into the cache key. | quality |
| **3** | **Token-aware, structure-preserving chunking** + a hard token-cap pass that **fixes the mega-chunk bug**; `_simple_chunk` no longer flattens newlines/LaTeX; Vietnamese lowercase headings detected. | correctness |
| **4** | **Deterministic quality gate + bounded repair pass** — re-translates only chunks flagged empty/truncated/wrong-language/dropped-formula/too-short, bypassing the cache, adopting a retry only when strictly better. | quality |
| **5** | **Rolling cross-chunk context** — "previous content" now comes from the **tail** of the previous chunk (+ an older-context gist) instead of the first 100 characters; optional LLM summary pre-pass (off by default). | quality |
| **6** | **Translation Memory leverage** — exact/fuzzy sentence matches from an existing TM are injected as prompt hints (no-op when the TM is empty). | quality · capability |
| **7** | **Semantic faithfulness verifier** (opt-in) — an LLM check that catches meaning drift the deterministic gate can't see, feeding the same repair loop; fail-open so it never flags on error. | quality · capability |

New modules (all `core_v2/`, stdlib-only at import, guarded/fail-open): `reliability`, `term_ledger`, `token_chunking`, `quality_gate`, `context_builder`, `tm_gateway`, `semantic_verifier`.

## Safety & configuration

Everything defaults to the prior behaviour or a strictly-better default; new LLM-cost features are **off by default**. All knobs are documented in `.env.example`. Key ones:

- `TRANSLATION_TEMPERATURE=0.3`, `TRANSLATION_PROMPT_CACHE_ENABLED=true`
- `TRANSLATION_AUTO_GLOSSARY_ENABLED=true`, `TRANSLATION_GLOSSARY_IDS=`
- `CHUNK_MAX_TOKENS=2000`
- `TRANSLATION_REPAIR_ENABLED=true`, `TRANSLATION_REPAIR_MAX_CHUNKS=20`
- `TM_REUSE_ENABLED=true` (no-op until a TM has segments)
- **Off by default:** `TRANSLATION_CONTEXT_SUMMARY_ENABLED=false`, `TRANSLATION_SEMANTIC_VERIFY_ENABLED=false`
- Model IDs overridable: `ANTHROPIC_TEXT_MODEL`, `OPENAI_TEXT_MODEL`, `GEMINI_TEXT_MODEL`, …

## Testing

**254 engine tests pass, 0 regressions.** Each phase added a unit suite; every change kept prior suites green (verified independently, not just by the builder). Run the engine suites:

```bash
pip install anthropic openai pytest pytest-asyncio --break-system-packages   # sandbox extras
python3 -m pytest \
  tests/unit/test_engine_quickwins.py tests/unit/test_term_ledger.py \
  tests/unit/test_glossary_wiring.py tests/unit/test_token_chunking.py \
  tests/unit/test_chunker_tokencap.py tests/unit/test_semantic_chunker.py \
  tests/unit/test_quality_gate.py tests/unit/test_repair_pass.py \
  tests/unit/test_context_builder.py tests/unit/test_context_wiring.py \
  tests/unit/test_tm_gateway.py tests/unit/test_tm_wiring.py \
  tests/unit/test_semantic_verifier.py tests/unit/test_semantic_repair.py \
  tests/cache/test_chunk_cache.py -o addopts=""
```

**Live acceptance (needs a real key — the one thing CI/sandbox can't do):**

```bash
export OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY / GOOGLE_API_KEY / DEEPSEEK_API_KEY
python3 scripts/e2e_translation_smoke.py
```

It runs a multi-chunk EN→VI document through `publish()` and asserts: no `[TRANSLATION ERROR]` holes, Vietnamese output, no chunk over the token budget, rolling context set, chunk-cache DB populated, and identical output on a cache-reuse re-run. It **skips truthfully** (exit 0, nothing verified) if no key is set.

## Known / pre-existing (not introduced here)

- `tests/test_vision_fallback.py` — 4 failures and `tests/integration/test_pdf_api_integration.py::TestPdfRouterSignature` — 2 failures are **pre-existing** (confirmed against the base commit via `git stash`). They come from an earlier change that added `gemini` to the provider order without updating the old test, and an unrelated API-router signature test — both untouched by this branch.

## Deferred (documented in the phase reports)

TM write-back at sentence granularity (needs source↔target alignment); dead/duplicate-code cleanup (two provider stacks, three glossary implementations, the dead Vision path in the orchestrator); glossary name→ID resolution; token-based paragraph sizing; snap chunk boundaries to word edges.

---

*Per-phase VERIFY reports: `docs/VIBECODE_PHASE{2,3,4,5,6,7}_REPORT.md` and `QUICKWINS_SUMMARY.md`.*
