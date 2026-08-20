"""Markdown inline emphasis → ``InlineRun`` spans.

Shared by the extractor and every renderer so paragraphs, list items, blockquotes
and table cells all format bold / italic / code the same way. Kept separate from
``document_ast`` (pure model) and ``document_extractor`` (block structure) so the
renderers can parse inline text without importing the extractor.
"""

from __future__ import annotations

import re
from typing import List, Optional

from core.rendering.document_ast import InlineRun

# Emphasis markers, most specific first. Code (backticks) has highest precedence
# and its content is literal. Underscore forms are guarded by ``(?<!\w)``/``(?!\w)``
# so identifiers and file paths (snake_case, file_name.ext) are left untouched;
# asterisk forms need no guard.
_MD_INLINE = re.compile(
    r"(?P<code>`+)(?P<code_text>.+?)(?P=code)"
    r"|\*\*\*(?P<bi_a>.+?)\*\*\*"
    r"|\*\*(?P<b_a>.+?)\*\*"
    r"|\*(?P<i_a>.+?)\*"
    r"|(?<!\w)___(?P<bi_u>.+?)___(?!\w)"
    r"|(?<!\w)__(?P<b_u>.+?)__(?!\w)"
    r"|(?<!\w)_(?P<i_u>.+?)_(?!\w)"
)


def parse_inline(text: str) -> Optional[List[InlineRun]]:
    """Parse Markdown inline emphasis in *text* into ``InlineRun`` spans.

    Returns ``None`` when *text* carries no inline markup — callers then keep the
    plain text and stay fully backward-compatible. Otherwise returns the spans
    whose concatenated ``.text`` equals *text* with the markers stripped: bold
    (``**``/``__``), italic (``*``/``_``), bold+italic (``***``/``___``) and
    inline code (`` `…` ``, content kept literal, no nested emphasis).
    """
    runs: List[InlineRun] = []
    pos = 0
    matched = False
    for m in _MD_INLINE.finditer(text):
        if m.start() > pos:
            runs.append(InlineRun(text=text[pos:m.start()]))
        if m.group("code") is not None:
            runs.append(InlineRun(text=m.group("code_text"), code=True))
        elif m.group("bi_a") is not None:
            runs.append(InlineRun(text=m.group("bi_a"), bold=True, italic=True))
        elif m.group("b_a") is not None:
            runs.append(InlineRun(text=m.group("b_a"), bold=True))
        elif m.group("i_a") is not None:
            runs.append(InlineRun(text=m.group("i_a"), italic=True))
        elif m.group("bi_u") is not None:
            runs.append(InlineRun(text=m.group("bi_u"), bold=True, italic=True))
        elif m.group("b_u") is not None:
            runs.append(InlineRun(text=m.group("b_u"), bold=True))
        elif m.group("i_u") is not None:
            runs.append(InlineRun(text=m.group("i_u"), italic=True))
        pos = m.end()
        matched = True

    if not matched:
        return None
    if pos < len(text):
        runs.append(InlineRun(text=text[pos:]))
    runs = [r for r in runs if r.text]
    return runs or None


def runs_or_plain(text: str) -> List[InlineRun]:
    """Always return a run list for *text*: the parsed emphasis spans, or a single
    plain run when there is no markup. Convenience for renderers that iterate runs
    uniformly (list items, table cells, blockquotes)."""
    return parse_inline(text) or [InlineRun(text=text)]
