"""
EPUB 3.0 Stylesheet — Typography + Layout for ebooks.

Supports:
- Latin scripts (English, French, German, ...)
- Vietnamese (diacritics, tone marks)
- CJK (Chinese, Japanese, Korean)
- Arabic/Hebrew (RTL)
- Math formulas (inline + block)
- Tables (responsive for small screens)
- Code blocks (monospace)

Standalone module — no extraction or translation imports.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Main Stylesheet
# ---------------------------------------------------------------------------

EPUB_CSS = """\
/* ═══════════════════════════════════════
   AI Publisher Pro — EPUB 3.0 Stylesheet
   ═══════════════════════════════════════ */

/* ─── Base Typography ─── */

body {
    font-family: "Georgia", "Noto Serif", "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.7;
    margin: 1em;
    padding: 0;
    color: #1a1a1a;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}

/* ─── Vietnamese Typography ─── */

:lang(vi) {
    font-family: "Noto Serif", "Times New Roman", serif;
    line-height: 1.8;
    word-spacing: 0.05em;
}

/* ─── CJK Typography ─── */

:lang(ja), :lang(zh), :lang(ko) {
    font-family: "Noto Serif CJK", "Hiragino Mincho", "MS Mincho",
                 "SimSun", "Batang", serif;
    line-height: 1.9;
    text-align: justify;
    text-justify: inter-ideograph;
    word-break: normal;
    overflow-wrap: break-word;
}

/* ─── RTL Support ─── */

:lang(ar), :lang(he), :lang(fa) {
    direction: rtl;
    text-align: right;
    font-family: "Noto Naskh Arabic", "Scheherazade", serif;
}

/* ─── Headings ─── */

h1 {
    font-size: 1.8em;
    font-weight: bold;
    margin: 1.5em 0 0.8em 0;
    line-height: 1.3;
    text-align: left;
    page-break-after: avoid;
    color: #2c3e50;
}

h2 {
    font-size: 1.4em;
    font-weight: bold;
    margin: 1.3em 0 0.6em 0;
    line-height: 1.3;
    text-align: left;
    page-break-after: avoid;
    border-bottom: 1px solid #eee;
    padding-bottom: 0.3em;
}

h3 {
    font-size: 1.2em;
    font-weight: bold;
    margin: 1.2em 0 0.5em 0;
    line-height: 1.3;
    text-align: left;
    page-break-after: avoid;
}

h4, h5, h6 {
    font-size: 1.05em;
    font-weight: bold;
    margin: 1em 0 0.4em 0;
    text-align: left;
}

/* ─── Paragraphs ─── */

p {
    margin: 0 0 0.8em 0;
    text-indent: 0;
}

p + p {
    text-indent: 1.5em;
}

/* ─── Tables ─── */

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.9em;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #ccc;
    padding: 0.4em 0.6em;
    text-align: left;
    vertical-align: top;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}

caption {
    font-style: italic;
    margin-bottom: 0.5em;
    text-align: center;
    color: #666;
}

/* ─── Formulas ─── */

.formula-block {
    display: block;
    text-align: center;
    margin: 1.2em 0;
    padding: 0.8em;
    background: #fafafa;
    border-radius: 4px;
    font-family: "STIX Two Math", "Cambria Math", serif;
    font-size: 1.1em;
    page-break-inside: avoid;
}

.formula-inline {
    font-family: "STIX Two Math", "Cambria Math", serif;
    font-style: italic;
}

code.latex {
    font-family: "Courier New", monospace;
    font-size: 0.85em;
    background: #f4f4f4;
    padding: 0.1em 0.3em;
    border-radius: 3px;
}

/* ─── Lists ─── */

ul, ol {
    margin: 0.8em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.3em;
    line-height: 1.6;
}

/* ─── Blockquotes ─── */

blockquote {
    margin: 1em 0;
    padding: 0.5em 1em;
    border-left: 3px solid #ccc;
    color: #555;
    font-style: italic;
}

/* ─── Images ─── */

figure {
    margin: 1em 0;
    text-align: center;
    page-break-inside: avoid;
}

figure img {
    max-width: 100%;
    height: auto;
}

figcaption {
    font-size: 0.85em;
    font-style: italic;
    color: #666;
    margin-top: 0.3em;
}

/* ─── Code Blocks ─── */

pre {
    font-family: "Courier New", "Consolas", monospace;
    font-size: 0.85em;
    background: #f4f4f4;
    padding: 1em;
    margin: 1em 0;
    border-radius: 4px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    page-break-inside: avoid;
}

code {
    font-family: "Courier New", "Consolas", monospace;
    font-size: 0.85em;
}

/* ─── Title Page ─── */

.title-page {
    text-align: center;
    margin-top: 30%;
}

.title-page h1 {
    font-size: 2.5em;
    text-align: center;
    border: none;
    color: #1a1a1a;
}

.title-page .author {
    font-size: 1.3em;
    margin-top: 1em;
    color: #555;
}

.title-page .publisher {
    font-size: 0.9em;
    margin-top: 3em;
    color: #999;
}

/* ─── Chapter Breaks ─── */

.chapter-break {
    page-break-before: always;
}
"""

# ---------------------------------------------------------------------------
# Language mapping
# ---------------------------------------------------------------------------

LANGUAGE_CSS_MAP = {
    "en": "en", "vi": "vi", "ja": "ja", "zh": "zh",
    "ko": "ko", "fr": "fr", "de": "de", "es": "es",
    "it": "it", "pt": "pt", "ru": "ru", "ar": "ar",
    "he": "he", "fa": "fa", "th": "th", "hi": "hi",
}

# ---------------------------------------------------------------------------
# Title page template
# ---------------------------------------------------------------------------

TITLE_PAGE_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="{lang}">
<head>
    <title>{title}</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
    <div class="title-page">
        <h1>{title}</h1>
        {author_block}
        {publisher_block}
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_css() -> str:
    """Get the main EPUB stylesheet."""
    return EPUB_CSS


def get_title_page_html(
    title: str,
    author: str = "",
    publisher: str = "",
    language: str = "en",
) -> str:
    """Generate title page XHTML."""
    author_block = f'<p class="author">{_escape_html(author)}</p>' if author else ""
    publisher_block = f'<p class="publisher">{_escape_html(publisher)}</p>' if publisher else ""
    lang = LANGUAGE_CSS_MAP.get(language, language)

    return TITLE_PAGE_TEMPLATE.format(
        title=_escape_html(title),
        author_block=author_block,
        publisher_block=publisher_block,
        lang=lang,
    )


def get_lang_code(language: str) -> str:
    """Map language code for CSS/XHTML."""
    return LANGUAGE_CSS_MAP.get(language, language)


def _escape_html(text: str) -> str:
    """Basic HTML escaping."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
