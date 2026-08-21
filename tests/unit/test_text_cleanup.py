"""Running header/footer ("page furniture") stripping.

Reproduces the real defect seen translating a novel PDF: the running header
(book title) and footer (``Author ◆ page-number``) repeated on every page were
captured as content, so the title littered the whole body 100+ times and flooded
the generated table of contents. The stripper must remove that furniture while
leaving real prose — and real headings that happen to contain the title — intact.
"""

from core_v2.text_cleanup import (
    detect_furniture_tokens,
    strip_running_furniture,
)

TITLE = "KHỞI NGUỒN"
SEP = ""  # decorative PUA separator glyph, as PyMuPDF extracts it


def _novel_like():
    """A page stream mimicking fitz get_text over a book with running head/foot."""
    lines = ["KHỞI NGUỒN", "Nguyễn Cảnh Lâm", "", "Table of Contents", ""]
    body = [
        "The Devil's Flame",
        "0:30 AM. The Phu My Bridge silently slithered into the night.",
        "The birthday party took place in Nhung's penthouse.",
        "The Dance of Numbers",
        "He explained the Riemann Hypothesis to the room.",
    ]
    # 20 "pages": each contributes a body line plus a running header + footer.
    for i, line in enumerate([body[i % len(body)] for i in range(20)], start=1):
        lines.append(TITLE)                        # running header (standalone)
        lines.append(f"Nguyen Canh Lam  {SEP}  {i}")  # running footer (standalone)
        lines.append(line)
    return "\n".join(lines)


def test_detect_finds_only_repeated_short_lines():
    text = _novel_like()
    tokens = detect_furniture_tokens(text.split("\n"), floor=5)
    forms = set(tokens)
    assert "khởi nguồn" in forms          # title, repeated ~21x
    assert "nguyen canh lam" in forms     # footer name, digits normalized away
    # a real chapter title appears a handful of times but stays below the floor
    assert "the devil s flame" not in forms


def test_standalone_title_repeats_removed():
    cleaned, report = strip_running_furniture(_novel_like())
    # The 20 running-header occurrences are gone; the cover title (line 1) may be
    # dropped too — that's fine, the renderer re-adds it from metadata.
    assert cleaned.count(TITLE) <= 1
    assert report.standalone_removed >= 20
    # real content survives
    assert "The Phu My Bridge silently slithered" in cleaned
    assert "Riemann Hypothesis" in cleaned


def test_inline_footer_glued_to_body_is_stripped():
    # A sentence that spans a page break: footer lands mid-sentence.
    text = "\n".join(
        [TITLE, "Nguyễn Cảnh Lâm", ""]
        + [f"Nguyen Canh Lam  {SEP}  {i}" for i in range(1, 6)]  # seed the token
        + [f"...the shadow clung to the wall. Nguyen Canh Lam  {SEP}  17 bones lay scattered."]
    )
    cleaned, report = strip_running_furniture(text)
    assert SEP not in cleaned                       # separator glyph gone
    assert "17" not in cleaned.split("bones")[0][-6:]  # page number gone
    assert "the shadow clung to the wall." in cleaned
    assert "bones lay scattered." in cleaned
    assert "Nguyen Canh Lam" not in cleaned.split("bones")[0]  # name prefix stripped


def test_pagenum_then_title_header_glued_is_stripped():
    text = "\n".join(
        [TITLE, "author", ""]
        + [TITLE for _ in range(6)]                 # seed the title token
        + [f"22  {SEP}  KHỞI NGUỒN 3:25 AM. The room was silent."]
    )
    cleaned, _ = strip_running_furniture(text)
    assert "3:25 AM. The room was silent." in cleaned
    assert "22" not in cleaned.split("3:25")[0]
    assert SEP not in cleaned


def test_real_heading_containing_title_is_preserved():
    """"Chapter 1: KHỞI NGUỒN" is a genuine heading, not furniture — keep it."""
    text = "\n".join([TITLE] * 8 + ["Chapter 1: KHỞI NGUỒN", "Body paragraph one."])
    cleaned, _ = strip_running_furniture(text)
    assert "Chapter 1: KHỞI NGUỒN" in cleaned


def test_clean_document_is_unchanged():
    text = (
        "A Perfectly Ordinary Report\n\n"
        "Section one discusses the background.\n"
        "Section two discusses the method.\n"
        "Section three discusses the results.\n"
    )
    cleaned, report = strip_running_furniture(text)
    assert cleaned == text
    assert not report.detected
    assert report.standalone_removed == 0


def test_repeated_short_sentence_is_not_furniture():
    """Dialogue like "Yes." can repeat, but it reads as a sentence — keep it."""
    text = "\n".join(['"Yes."'] * 9 + ["A real narrative line follows here."])
    cleaned, report = strip_running_furniture(text)
    assert cleaned.count('"Yes."') == 9
    assert report.standalone_removed == 0
