"""
Unit tests for api/services/layout_dna.py — LayoutDNA, Region, RegionType.

Target: comprehensive coverage of the data model, serialization, and queries.
"""

import json
import pytest

from api.services.layout_dna import LayoutDNA, Region, RegionType


# ---------------------------------------------------------------------------
# RegionType
# ---------------------------------------------------------------------------

class TestRegionType:
    def test_all_types(self):
        expected = {"text", "table", "formula", "heading", "list", "image", "code"}
        actual = {rt.value for rt in RegionType}
        assert actual == expected

    def test_string_enum(self):
        assert RegionType.TEXT == "text"
        assert str(RegionType.TABLE) == "RegionType.TABLE"


# ---------------------------------------------------------------------------
# Region
# ---------------------------------------------------------------------------

class TestRegion:
    def test_basic_creation(self):
        r = Region(type=RegionType.TEXT, content="Hello world")
        assert r.type == RegionType.TEXT
        assert r.content == "Hello world"
        assert r.level == 0
        assert r.metadata == {}
        assert r.page == -1

    def test_heading_with_level(self):
        r = Region(type=RegionType.HEADING, content="Introduction", level=2)
        assert r.level == 2
        assert r.is_structural is True
        assert r.is_special is False

    def test_table_is_special(self):
        r = Region(type=RegionType.TABLE, content="| A | B |")
        assert r.is_special is True
        assert r.is_structural is False

    def test_formula_is_special(self):
        r = Region(type=RegionType.FORMULA, content="$$x^2$$")
        assert r.is_special is True

    def test_code_is_special(self):
        r = Region(type=RegionType.CODE, content="print('hello')")
        assert r.is_special is True

    def test_image_is_special(self):
        r = Region(type=RegionType.IMAGE, content="![alt](url)")
        assert r.is_special is True

    def test_list_is_structural(self):
        r = Region(type=RegionType.LIST, content="- item 1\n- item 2")
        assert r.is_structural is True

    def test_char_count(self):
        r = Region(type=RegionType.TEXT, content="Hello")
        assert r.char_count == 5

    def test_to_dict(self):
        r = Region(
            type=RegionType.HEADING,
            content="Title",
            level=1,
            metadata={"style": "bold"},
            page=3,
            start_offset=10,
            end_offset=15,
        )
        d = r.to_dict()
        assert d["type"] == "heading"
        assert d["content"] == "Title"
        assert d["level"] == 1
        assert d["metadata"] == {"style": "bold"}
        assert d["page"] == 3
        assert d["start_offset"] == 10
        assert d["end_offset"] == 15

    def test_from_dict(self):
        d = {
            "type": "formula",
            "content": "$$E=mc^2$$",
            "level": 0,
            "metadata": {"mode": "display"},
            "page": 1,
            "start_offset": 50,
            "end_offset": 60,
        }
        r = Region.from_dict(d)
        assert r.type == RegionType.FORMULA
        assert r.content == "$$E=mc^2$$"
        assert r.metadata == {"mode": "display"}

    def test_from_dict_defaults(self):
        d = {"type": "text", "content": "hello"}
        r = Region.from_dict(d)
        assert r.level == 0
        assert r.page == -1
        assert r.start_offset == 0

    def test_roundtrip(self):
        r = Region(
            type=RegionType.TABLE,
            content="| A |\n|---|\n| 1 |",
            level=0,
            metadata={"rows": 2},
            page=5,
            start_offset=100,
            end_offset=120,
        )
        r2 = Region.from_dict(r.to_dict())
        assert r2.type == r.type
        assert r2.content == r.content
        assert r2.metadata == r.metadata
        assert r2.page == r.page


# ---------------------------------------------------------------------------
# LayoutDNA — core properties
# ---------------------------------------------------------------------------

class TestLayoutDNACore:
    def test_empty(self):
        dna = LayoutDNA()
        assert dna.region_count == 0
        assert dna.full_text == ""
        assert len(dna) == 0
        assert str(dna) == ""

    def test_single_region(self):
        dna = LayoutDNA(regions=[
            Region(type=RegionType.TEXT, content="Hello"),
        ])
        assert dna.full_text == "Hello"
        assert len(dna) == 5
        assert dna.region_count == 1

    def test_full_text_joins(self):
        dna = LayoutDNA(regions=[
            Region(type=RegionType.HEADING, content="Title"),
            Region(type=RegionType.TEXT, content="Paragraph"),
        ])
        assert dna.full_text == "Title\n\nParagraph"

    def test_str_returns_full_text(self):
        dna = LayoutDNA(regions=[
            Region(type=RegionType.TEXT, content="ABC"),
        ])
        assert str(dna) == "ABC"

    def test_len_counts_content_chars(self):
        dna = LayoutDNA(regions=[
            Region(type=RegionType.TEXT, content="ABC"),
            Region(type=RegionType.TEXT, content="DE"),
        ])
        assert len(dna) == 5  # 3 + 2, not including join chars


# ---------------------------------------------------------------------------
# LayoutDNA — queries
# ---------------------------------------------------------------------------

class TestLayoutDNAQueries:
    def _make_dna(self):
        dna = LayoutDNA()
        dna.regions = [
            Region(type=RegionType.HEADING, content="Title", level=1),
            Region(type=RegionType.TEXT, content="Paragraph 1"),
            Region(type=RegionType.TABLE, content="| A | B |"),
            Region(type=RegionType.FORMULA, content="$$x^2$$"),
            Region(type=RegionType.TEXT, content="Paragraph 2"),
            Region(type=RegionType.CODE, content="print('hi')"),
            Region(type=RegionType.LIST, content="- a\n- b"),
        ]
        return dna

    def test_regions_of_type(self):
        dna = self._make_dna()
        texts = dna.regions_of_type(RegionType.TEXT)
        assert len(texts) == 2

    def test_tables_property(self):
        dna = self._make_dna()
        assert len(dna.tables) == 1

    def test_formulas_property(self):
        dna = self._make_dna()
        assert len(dna.formulas) == 1

    def test_headings_property(self):
        dna = self._make_dna()
        assert len(dna.headings) == 1

    def test_code_blocks_property(self):
        dna = self._make_dna()
        assert len(dna.code_blocks) == 1

    def test_has_tables(self):
        dna = self._make_dna()
        assert dna.has_tables is True
        assert LayoutDNA().has_tables is False

    def test_has_formulas(self):
        dna = self._make_dna()
        assert dna.has_formulas is True

    def test_has_code(self):
        dna = self._make_dna()
        assert dna.has_code is True

    def test_type_distribution(self):
        dna = self._make_dna()
        dist = dna.type_distribution()
        assert dist["text"] == 2
        assert dist["table"] == 1
        assert dist["heading"] == 1
        assert dist["formula"] == 1
        assert dist["code"] == 1
        assert dist["list"] == 1

    def test_empty_distribution(self):
        dna = LayoutDNA()
        assert dna.type_distribution() == {}


# ---------------------------------------------------------------------------
# LayoutDNA — add_region
# ---------------------------------------------------------------------------

class TestLayoutDNAAddRegion:
    def test_add_region(self):
        dna = LayoutDNA()
        r = dna.add_region(RegionType.HEADING, "Title", level=1)
        assert r.type == RegionType.HEADING
        assert r.content == "Title"
        assert r.level == 1
        assert dna.region_count == 1

    def test_add_region_metadata(self):
        dna = LayoutDNA()
        r = dna.add_region(
            RegionType.TABLE, "| A |",
            metadata={"rows": 1}, page=2,
        )
        assert r.metadata == {"rows": 1}
        assert r.page == 2

    def test_add_region_offsets_tracked(self):
        dna = LayoutDNA()
        r1 = dna.add_region(RegionType.TEXT, "Hello")
        r2 = dna.add_region(RegionType.TEXT, "World")
        assert r1.start_offset == 0
        assert r1.end_offset == 5
        assert r2.start_offset > 5  # accounts for join chars


# ---------------------------------------------------------------------------
# LayoutDNA — serialization
# ---------------------------------------------------------------------------

class TestLayoutDNASerialization:
    def test_to_dict(self):
        dna = LayoutDNA(metadata={"source": "test"})
        dna.add_region(RegionType.TEXT, "Hello")
        d = dna.to_dict()
        assert d["region_count"] == 1
        assert d["metadata"]["source"] == "test"
        assert "type_distribution" in d
        assert len(d["regions"]) == 1

    def test_from_dict(self):
        d = {
            "regions": [
                {"type": "heading", "content": "Title", "level": 1},
                {"type": "text", "content": "Paragraph"},
            ],
            "metadata": {"version": "2.0"},
        }
        dna = LayoutDNA.from_dict(d)
        assert dna.region_count == 2
        assert dna.metadata["version"] == "2.0"
        assert dna.regions[0].type == RegionType.HEADING

    def test_to_json(self):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Hello")
        j = dna.to_json()
        parsed = json.loads(j)
        assert parsed["region_count"] == 1

    def test_from_json(self):
        original = LayoutDNA()
        original.add_region(RegionType.FORMULA, "$$x$$")
        original.add_region(RegionType.TEXT, "text here")
        j = original.to_json()
        restored = LayoutDNA.from_json(j)
        assert restored.region_count == 2
        assert restored.regions[0].type == RegionType.FORMULA

    def test_roundtrip_json(self):
        dna = LayoutDNA(metadata={"lang": "en"})
        dna.add_region(RegionType.HEADING, "Title", level=1)
        dna.add_region(RegionType.TEXT, "Body text")
        dna.add_region(RegionType.TABLE, "| A | B |", metadata={"rows": 1})

        restored = LayoutDNA.from_json(dna.to_json())
        assert restored.region_count == 3
        assert restored.metadata["lang"] == "en"
        assert restored.tables[0].metadata["rows"] == 1

    def test_summary(self):
        dna = LayoutDNA()
        dna.add_region(RegionType.TEXT, "Hello world")
        s = dna.summary()
        assert "LayoutDNA" in s
        assert "1 regions" in s
        assert "1 text" in s
