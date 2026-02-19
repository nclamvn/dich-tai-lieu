"""
Unit tests for api/services/epub_styles.py — EPUB CSS + templates.

Target: 85%+ coverage.
"""

import pytest

from api.services.epub_styles import (
    EPUB_CSS,
    LANGUAGE_CSS_MAP,
    TITLE_PAGE_TEMPLATE,
    get_css,
    get_title_page_html,
    get_lang_code,
    _escape_html,
)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

class TestEpubCSS:
    def test_css_not_empty(self):
        css = get_css()
        assert len(css) > 100

    def test_css_has_body(self):
        css = get_css()
        assert "body {" in css or "body{" in css

    def test_css_has_headings(self):
        css = get_css()
        assert "h1 {" in css or "h1{" in css
        assert "h2 {" in css or "h2{" in css

    def test_css_has_vietnamese(self):
        css = get_css()
        assert ":lang(vi)" in css

    def test_css_has_cjk(self):
        css = get_css()
        assert ":lang(ja)" in css
        assert ":lang(zh)" in css
        assert ":lang(ko)" in css

    def test_css_has_rtl(self):
        css = get_css()
        assert ":lang(ar)" in css
        assert "direction: rtl" in css

    def test_css_has_tables(self):
        css = get_css()
        assert "table {" in css or "table{" in css
        assert "th {" in css or "th," in css

    def test_css_has_formula_styles(self):
        css = get_css()
        assert ".formula-block" in css
        assert ".formula-inline" in css

    def test_css_has_code_blocks(self):
        css = get_css()
        assert "pre {" in css or "pre{" in css
        assert "code {" in css or "code{" in css

    def test_css_has_lists(self):
        css = get_css()
        assert "ul," in css or "ul {" in css
        assert "li {" in css or "li{" in css

    def test_css_has_title_page(self):
        css = get_css()
        assert ".title-page" in css

    def test_css_returns_same_value(self):
        assert get_css() == get_css()


# ---------------------------------------------------------------------------
# Title Page
# ---------------------------------------------------------------------------

class TestTitlePage:
    def test_basic_title_page(self):
        html = get_title_page_html("My Book", author="Author")
        assert "My Book" in html
        assert "Author" in html
        assert "<?xml" in html
        assert "xhtml" in html

    def test_title_only(self):
        html = get_title_page_html("Solo Title")
        assert "Solo Title" in html
        assert 'class="author"' not in html

    def test_no_author(self):
        html = get_title_page_html("Title", author="")
        assert 'class="author"' not in html

    def test_with_publisher(self):
        html = get_title_page_html("Title", publisher="My Press")
        assert "My Press" in html
        assert 'class="publisher"' in html

    def test_no_publisher(self):
        html = get_title_page_html("Title", publisher="")
        assert 'class="publisher"' not in html

    def test_title_escaping(self):
        html = get_title_page_html("Book <script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_author_escaping(self):
        html = get_title_page_html("Title", author="A & B")
        assert "A &amp; B" in html

    def test_language_attribute(self):
        html = get_title_page_html("Title", language="vi")
        assert 'xml:lang="vi"' in html

    def test_japanese_language(self):
        html = get_title_page_html("Title", language="ja")
        assert 'xml:lang="ja"' in html

    def test_unknown_language(self):
        html = get_title_page_html("Title", language="xyz")
        assert 'xml:lang="xyz"' in html


# ---------------------------------------------------------------------------
# Language Map
# ---------------------------------------------------------------------------

class TestLanguageMap:
    def test_known_languages(self):
        assert get_lang_code("en") == "en"
        assert get_lang_code("vi") == "vi"
        assert get_lang_code("ja") == "ja"
        assert get_lang_code("zh") == "zh"
        assert get_lang_code("ko") == "ko"
        assert get_lang_code("ar") == "ar"

    def test_unknown_language_passthrough(self):
        assert get_lang_code("xyz") == "xyz"
        assert get_lang_code("sw") == "sw"

    def test_map_completeness(self):
        expected = {"en", "vi", "ja", "zh", "ko", "fr", "de", "es",
                    "it", "pt", "ru", "ar", "he", "fa", "th", "hi"}
        assert set(LANGUAGE_CSS_MAP.keys()) == expected


# ---------------------------------------------------------------------------
# HTML Escaping
# ---------------------------------------------------------------------------

class TestEscapeHTML:
    def test_ampersand(self):
        assert _escape_html("A & B") == "A &amp; B"

    def test_less_than(self):
        assert _escape_html("a < b") == "a &lt; b"

    def test_greater_than(self):
        assert _escape_html("a > b") == "a &gt; b"

    def test_quotes(self):
        assert _escape_html('say "hi"') == 'say &quot;hi&quot;'

    def test_no_escaping_needed(self):
        assert _escape_html("hello world") == "hello world"

    def test_mixed(self):
        result = _escape_html('<a href="x">&</a>')
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&quot;" in result
