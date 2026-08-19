"""L0: AST completeness + round-trippable serialization (no API key needed)."""

import json

from core.rendering.ast_serialization import (
    ast_from_dict,
    ast_from_json,
    ast_to_dict,
    ast_to_json,
)
from core.rendering.document_ast import (
    BlockType,
    Caption,
    DocumentAST,
    DocumentMetadata,
    Equation,
    EquationMode,
    Figure,
    Heading,
    HeadingLevel,
    ListBlock,
    PageBreak,
    Paragraph,
    StyleSheet,
    TableBlock,
)


def _sample_doc() -> DocumentAST:
    doc = DocumentAST(
        metadata=DocumentMetadata(title="Sách", author="Tác giả"),
        styles=StyleSheet(),
    )
    doc.add_block(Heading(level=HeadingLevel.H1, text="Chương 1", number="1"))
    doc.add_block(Paragraph(text="Một đoạn văn tiếng Việt.", metadata={"page": 1}))
    doc.add_block(Equation(latex=r"L = -\sum y \log p", mode=EquationMode.DISPLAY, number="1"))
    doc.add_block(TableBlock(rows=[["A", "B"], ["1", "2"]], header_rows=1, caption="Bảng 1"))
    doc.add_block(Figure(image_ref="img/fig1.png", caption="Hình 1", number="1"))
    doc.add_block(ListBlock(items=["một", "hai", "ba"], ordered=True))
    doc.add_block(Caption(text="Chú thích", target="figure", number="1"))
    doc.add_block(PageBreak())
    return doc


def test_round_trip_dict_is_equal():
    doc = _sample_doc()
    assert ast_from_dict(ast_to_dict(doc)) == doc


def test_round_trip_json_is_equal():
    doc = _sample_doc()
    assert ast_from_json(ast_to_json(doc)) == doc


def test_json_is_valid_and_keeps_unicode():
    text = ast_to_json(_sample_doc())
    json.loads(text)  # must be valid JSON
    assert "Chương 1" in text  # ensure_ascii=False keeps Vietnamese readable


def test_statistics_count_new_layout_blocks():
    st = _sample_doc().get_statistics()
    assert st["tables"] == 1
    assert st["figures"] == 1
    assert st["lists"] == 1
    assert st["captions"] == 1
    assert st["page_breaks"] == 1
    assert st["headings"] == 1 and st["paragraphs"] == 1 and st["equations"] == 1


def test_enum_and_container_fidelity():
    back = ast_from_dict(ast_to_dict(_sample_doc()))

    heading = back.blocks[0]
    assert isinstance(heading, Heading) and heading.level == HeadingLevel.H1

    table = next(b for b in back.blocks if isinstance(b, TableBlock))
    assert table.rows == [["A", "B"], ["1", "2"]] and table.header_rows == 1

    lst = next(b for b in back.blocks if isinstance(b, ListBlock))
    assert lst.items == ["một", "hai", "ba"] and lst.ordered is True


def test_block_type_is_restored_from_post_init():
    back = ast_from_dict(ast_to_dict(_sample_doc()))
    assert back.blocks[0].block_type == BlockType.HEADING
    assert back.blocks[-1].block_type == BlockType.PAGE_BREAK


def test_metadata_survives_round_trip():
    back = ast_from_dict(ast_to_dict(_sample_doc()))
    para = next(b for b in back.blocks if isinstance(b, Paragraph))
    assert para.metadata == {"page": 1}
