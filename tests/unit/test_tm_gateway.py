"""Unit tests for core_v2.tm_gateway.TMGateway.

Every test drives a REAL temporary sqlite-backed TranslationMemory (or a small
dummy object for the guard case), so the gateway is exercised end-to-end without
mocking the TM internals.
"""

import os
import tempfile
from pathlib import Path

import pytest

from core.translation_memory import TranslationMemory, TMSegment
from core_v2.tm_gateway import TMGateway, TMHint


@pytest.fixture
def tm_factory():
    """Yield a factory that makes real temp-file TMs and cleans them all up."""
    created = []  # list of (tm, base_path)

    def _make():
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        f.close()
        tm = TranslationMemory(Path(f.name))
        created.append((tm, f.name))
        return tm

    yield _make

    for tm, path in created:
        try:
            tm.close()
        except Exception:
            pass
        # WAL journal mode leaves -wal / -shm sidecar files behind.
        for p in (path, path + "-wal", path + "-shm"):
            try:
                os.unlink(p)
            except OSError:
                pass


def test_empty_tm_is_inactive_and_lookup_is_free(tm_factory):
    # AC: empty TM => gateway inactive => lookup returns [] with no cost.
    tm = tm_factory()
    g = TMGateway(tm=tm)
    assert g._active is False
    assert g.lookup_hints("anything at all.", "en", "vi") == []


def test_populated_tm_returns_exact_hint(tm_factory):
    # AC: an exact sentence match yields an exact hint (similarity 1.0).
    tm = tm_factory()
    tm.add_segment(
        TMSegment(
            source="Hello world.",
            target="Xin chào thế giới.",
            source_lang="en",
            target_lang="vi",
        )
    )
    g = TMGateway(tm=tm)
    assert g._active is True

    hints = g.lookup_hints("Hello world. Something else.", "en", "vi")
    matching = [h for h in hints if h.source == "Hello world."]
    assert matching, hints
    hint = matching[0]
    assert hint.target == "Xin chào thế giới."
    assert hint.match_type == "exact"
    assert hint.similarity == 1.0


def test_fuzzy_hint(tm_factory):
    # AC: a near-miss sentence returns a fuzzy hint (similarity in [threshold, 1)).
    tm = tm_factory()
    tm.add_segment(
        TMSegment(
            source="The cat sat on the mat.",
            target="Con mèo ngồi trên thảm.",
            source_lang="en",
            target_lang="vi",
        )
    )
    g = TMGateway(tm=tm, threshold=0.6)

    hints = g.lookup_hints("The cat sat on a mat.", "en", "vi")
    assert len(hints) == 1
    hint = hints[0]
    assert hint.match_type == "fuzzy"
    assert hint.target == "Con mèo ngồi trên thảm."
    assert 0.6 <= hint.similarity < 1.0


def test_render_hints_block():
    # AC: [] renders empty; non-empty renders header + "src → tgt" arrow lines.
    g = TMGateway(tm=None, enabled=False)  # config-only gateway, no TM needed.
    assert g.render_hints_block([]) == ""

    hints = [TMHint(source="Hello world.", target="Xin chào.", similarity=1.0, match_type="exact")]
    block = g.render_hints_block(hints)
    assert "TRANSLATION MEMORY" in block
    assert "→" in block
    assert "Hello world." in block
    assert "Xin chào." in block


def test_store_flips_empty_gateway_to_active(tm_factory):
    # AC: store() returns True and flips an empty gateway to active + retrievable.
    tm = tm_factory()
    g = TMGateway(tm=tm)
    assert g._active is False

    assert g.store("Hello world.", "Xin chào thế giới.", "en", "vi") is True
    assert g._active is True

    hints = g.lookup_hints("Hello world.", "en", "vi")
    assert len(hints) == 1
    assert hints[0].source == "Hello world."
    assert hints[0].target == "Xin chào thế giới."
    assert hints[0].match_type == "exact"


def test_store_rejects_blank_sides(tm_factory):
    # store() is a no-op for a blank source or target.
    tm = tm_factory()
    g = TMGateway(tm=tm)
    assert g.store("", "Xin chào.", "en", "vi") is False
    assert g.store("Hello.", "   ", "en", "vi") is False


def test_disabled_gateway_is_inert(tm_factory):
    # AC: an explicitly disabled gateway never looks up and never stores.
    tm = tm_factory()
    tm.add_segment(
        TMSegment(source="Hello world.", target="Xin chào.", source_lang="en", target_lang="vi")
    )
    g = TMGateway(tm=tm, enabled=False)
    assert g._active is False
    assert g.lookup_hints("Hello world.", "en", "vi") == []
    assert g.store("New source.", "Nguồn mới.", "en", "vi") is False


def test_lookup_never_raises_when_tm_errors():
    # AC: a TM that raises on get_exact_match => lookup returns [] without raising.
    class RaisingTM:
        def get_statistics(self):
            return {"total_segments": 3}  # non-empty => gateway is active.

        def get_exact_match(self, *args, **kwargs):
            raise RuntimeError("boom in exact match")

        def get_fuzzy_matches(self, *args, **kwargs):
            raise RuntimeError("boom in fuzzy match")

        def close(self):
            pass

    g = TMGateway(tm=RaisingTM())
    assert g._active is True  # count came back > 0
    assert g.lookup_hints("Hello world. Another sentence.", "en", "vi") == []


def test_close_is_safe(tm_factory):
    # close() is best-effort and idempotent-ish; never raises.
    tm = tm_factory()
    g = TMGateway(tm=tm)
    g.close()
    g.close()  # second close must not raise
