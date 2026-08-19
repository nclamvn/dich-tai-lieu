"""Live-path EPUB no longer needs pandoc — it renders via ebooklib (option C)."""

import ebooklib
from ebooklib import epub

from core_v2.output_converter import OutputConverter

_MD = (
    "# Chương 1\n\n"
    "Đoạn văn tiếng Việt đủ dấu.\n\n"
    "- mục a\n- mục b\n\n"
    "# Chương 2\n\n"
    "Nội dung chương hai.\n"
)


def _epub_text(path) -> str:
    book = epub.read_epub(str(path))
    docs = [i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT]
    return " ".join(d.get_content().decode("utf-8") for d in docs)


async def test_markdown_to_epub_without_pandoc(tmp_path):
    converter = OutputConverter(temp_dir=tmp_path / "tmp")
    converter.has_pandoc = False  # force: EPUB must still work with pandoc absent

    out = tmp_path / "book.epub"
    ok = await converter._markdown_math_to_epub(_MD, out, "Sách", "Tác giả")

    assert ok is True
    assert out.exists() and out.stat().st_size > 500


async def test_epub_content_and_chapters(tmp_path):
    converter = OutputConverter(temp_dir=tmp_path / "tmp")
    converter.has_pandoc = False

    out = tmp_path / "book.epub"
    await converter._markdown_math_to_epub(_MD, out, "Sách", None)

    content = _epub_text(out)
    assert "Chương 1" in content and "Chương 2" in content
    assert "<li>mục a</li>" in content


async def test_epub_title_metadata_applied(tmp_path):
    converter = OutputConverter(temp_dir=tmp_path / "tmp")
    converter.has_pandoc = False

    out = tmp_path / "titled.epub"
    await converter._markdown_math_to_epub(_MD, out, "Tiêu đề sách", "Tác giả X")

    book = epub.read_epub(str(out))
    titles = [t[0] for t in book.get_metadata("DC", "title")]
    assert "Tiêu đề sách" in titles
