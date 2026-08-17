"""
Single-call semantic faithfulness check for translated chunks.

The deterministic :mod:`core_v2.quality_gate` catches *structural* silent
failures (empty, truncated, wrong-language, dropped LaTeX) but is blind to
*meaning* errors: a chunk can be fluent, correctly-sized, and in the right
language yet still drop a clause, invent a fact, or mistranslate a key sentence.
This module adds one optional LLM pass that judges whether a translation is a
FAITHFUL rendering of its source and reports a small, typed verdict:

- ``SemanticVerdict`` — ``faithful`` + a ``severity`` bucket + a short ``issue``.
- ``verify_chunk`` — an async, single-call check that NEVER raises and defaults
  to "faithful" on any failure (empty input, client error, malformed reply), so
  a flaky check can never trigger a spurious, costly re-translate.
- ``is_unfaithful`` — a caller-side gate that only fires above a configurable
  severity floor, letting callers require a "major" error before re-translating.

Only the standard library is imported at module load time (no anthropic/openai),
so this module can be unit-tested in isolation and is safe to import anywhere.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)

# Severity buckets ordered from harmless to meaning-changing. This dict is the
# single source of truth for both the allowed set and the ``is_unfaithful``
# threshold comparison (none < minor < major).
_SEVERITY_ORDER: Dict[str, int] = {"none": 0, "minor": 1, "major": 2}
_ALLOWED_SEVERITIES = frozenset(_SEVERITY_ORDER)


@dataclass
class SemanticVerdict:
    """The outcome of a faithfulness check for one translated chunk.

    - ``faithful`` — ``True`` when the translation preserves the source meaning.
    - ``severity`` — one of ``"none"`` | ``"minor"`` | ``"major"`` describing how
      damaging the problem is (``"none"`` when faithful).
    - ``issue`` — a short human-readable reason, or ``""`` when there is none.
    """

    faithful: bool = True
    severity: str = "none"
    issue: str = ""


def _strip_code_fences(text: str) -> str:
    """Remove a leading ```/```json fence and its trailing ``` if present."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    newline = text.find("\n")
    text = text[newline + 1:] if newline != -1 else ""
    fence = text.rfind("```")
    if fence != -1:
        text = text[:fence]
    return text


def _coerce_bool(value: object, *, default: bool = True) -> bool:
    """Coerce an LLM-supplied ``faithful`` value to a bool.

    Accepts a real bool, or the strings ``"true"``/``"false"``/``"yes"``/``"no"``
    (case-insensitive, trimmed). Anything else (missing key, ``None``, number,
    unrecognized string) falls back to ``default`` — which is ``True`` so an
    ambiguous reply fails open to "faithful" rather than flagging.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("true", "yes"):
            return True
        if v in ("false", "no"):
            return False
    return default


def _parse_verdict(content: str) -> SemanticVerdict:
    """Parse a raw LLM response into a :class:`SemanticVerdict`, failing open.

    Mirrors the defensive JSON handling used elsewhere in the pipeline: strip a
    markdown code fence, slice from the first ``{`` to the last ``}``, and
    ``json.loads`` that. Then read ``faithful`` (coerced to bool), ``severity``
    (defaulting to ``"none"`` and clamped to the allowed set, else ``"minor"``),
    and ``issue`` (str, default ``""``).

    On ANY exception (no JSON object, malformed JSON, non-object payload) a
    faithful verdict is returned so a parse failure never flags a chunk.
    """
    try:
        text = _strip_code_fences(content)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("no JSON object found in response")
        data = json.loads(text[start:end + 1])
        if not isinstance(data, dict):
            raise ValueError("parsed JSON is not an object")

        faithful = _coerce_bool(data.get("faithful"))

        severity = data.get("severity", "none")
        if not isinstance(severity, str):
            severity = "minor"
        severity = severity.strip().lower()
        if severity not in _ALLOWED_SEVERITIES:
            severity = "minor"

        issue = data.get("issue", "")
        if not isinstance(issue, str):
            issue = ""

        return SemanticVerdict(faithful=faithful, severity=severity, issue=issue)
    except Exception as exc:  # noqa: BLE001 — fail open, never flag on parse failure
        logger.debug("semantic verdict parse failed, defaulting to faithful: %s", exc)
        return SemanticVerdict(faithful=True, severity="none", issue="")


async def verify_chunk(
    source: str,
    translated: str,
    source_lang: str,
    target_lang: str,
    llm_client,
    *,
    max_chars: int = 2000,
) -> SemanticVerdict:
    """Ask an LLM whether ``translated`` faithfully renders ``source``.

    A single ``llm_client.chat`` call at ``temperature=0.0`` judges FAITHFULNESS
    of meaning only. Source and translation are each truncated to ``max_chars``
    to bound cost.

    Fail-open by design:

    - If either side is empty/whitespace, a faithful verdict is returned WITHOUT
      calling the client (the deterministic gate already handles empties).
    - On ANY error (client raises, malformed reply) a warning is logged and a
      faithful verdict is returned. This function never raises into its caller.
    """
    if not source or not source.strip() or not translated or not translated.strip():
        return SemanticVerdict(faithful=True, severity="none", issue="")

    src = source[:max_chars]
    tgt = translated[:max_chars]

    prompt = (
        f"You are a bilingual translation reviewer. Judge whether the "
        f"{target_lang} TRANSLATION below is a FAITHFUL rendering of the "
        f"{source_lang} SOURCE — that is, it preserves the same meaning without "
        f"dropping, adding, or mistranslating content.\n\n"
        f"Judge FAITHFULNESS of meaning ONLY. Set faithful=false ONLY for real "
        f"accuracy problems (dropped meaning, added meaning, or mistranslation). "
        f"Do NOT penalize differences of style, phrasing, word choice, tone, or "
        f"formatting.\n"
        f'Set severity to "major" for meaning-changing errors, "minor" for small '
        f'omissions or nuance loss, and "none" when the translation is faithful.\n\n'
        f"Reply with STRICT JSON and NOTHING else, shaped EXACTLY as:\n"
        f'{{"faithful": true|false, "severity": "none|minor|major", "issue": '
        f'"<short reason or empty>"}}\n\n'
        f"SOURCE ({source_lang}):\n{src}\n\n"
        f"TRANSLATION ({target_lang}):\n{tgt}"
    )

    try:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = getattr(response, "content", "") or ""
        return _parse_verdict(content)
    except Exception as exc:  # noqa: BLE001 — must never raise to the caller
        logger.warning("verify_chunk failed, defaulting to faithful: %s", exc)
        return SemanticVerdict(faithful=True, severity="none", issue="")


def is_unfaithful(verdict: SemanticVerdict, *, min_severity: str = "major") -> bool:
    """Return ``True`` only for an unfaithful verdict at or above ``min_severity``.

    The severity scale is ``none < minor < major``. A faithful verdict is never
    unfaithful. When the verdict IS unfaithful, its severity must reach the
    ``min_severity`` floor — so a caller can require ``"major"`` (the default) to
    trigger a costly re-translate while ignoring ``"minor"`` blips.

    An unrecognized ``min_severity`` is treated conservatively as ``"major"``,
    and an unrecognized verdict severity as ``"none"``, so ambiguity never fires.
    """
    if verdict.faithful:
        return False
    threshold = _SEVERITY_ORDER.get(min_severity, _SEVERITY_ORDER["major"])
    level = _SEVERITY_ORDER.get(verdict.severity, _SEVERITY_ORDER["none"])
    return level >= threshold
