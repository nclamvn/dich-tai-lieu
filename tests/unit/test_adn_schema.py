"""
Unit Tests for ADN (Content DNA) Schema

Tests all data structures for document DNA extraction.
"""

import pytest
import json
from typing import Dict, Any

from core.adn.schema import (
    ProperNounType,
    PatternType,
    ProperNoun,
    Character,
    Term,
    Pattern,
    ContentADN,
)


class TestProperNounType:
    """Tests for ProperNounType enum."""
    
    def test_all_types_exist(self):
        """Verify all proper noun types are defined."""
        expected = ["person", "place", "organization", "product", 
                   "event", "work_of_art", "other"]
        actual = [t.value for t in ProperNounType]
        assert set(expected) == set(actual)
    
    def test_type_values(self):
        """Test individual type values."""
        assert ProperNounType.PERSON.value == "person"
        assert ProperNounType.PLACE.value == "place"
        assert ProperNounType.ORGANIZATION.value == "organization"
        assert ProperNounType.PRODUCT.value == "product"
        assert ProperNounType.EVENT.value == "event"
        assert ProperNounType.WORK_OF_ART.value == "work_of_art"
        assert ProperNounType.OTHER.value == "other"


class TestPatternType:
    """Tests for PatternType enum."""
    
    def test_all_types_exist(self):
        """Verify all pattern types are defined."""
        expected = ["chapter_start", "section_break", "quote_block",
                   "emphasis", "list_structure", "dialogue", 
                   "footnote", "header_footer", "other"]
        actual = [t.value for t in PatternType]
        assert set(expected) == set(actual)
    
    def test_type_values(self):
        """Test individual type values."""
        assert PatternType.CHAPTER_START.value == "chapter_start"
        assert PatternType.DIALOGUE.value == "dialogue"
        assert PatternType.FOOTNOTE.value == "footnote"


class TestProperNoun:
    """Tests for ProperNoun dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic proper noun."""
        noun = ProperNoun(
            text="John Smith",
            type=ProperNounType.PERSON
        )
        assert noun.text == "John Smith"
        assert noun.type == ProperNounType.PERSON
    
    def test_default_values(self):
        """Test default values."""
        noun = ProperNoun(text="Test", type=ProperNounType.OTHER)
        assert noun.translations == {}
        assert noun.occurrences == []
        assert noun.confidence == 1.0
        assert noun.variants == []
    
    def test_full_proper_noun(self):
        """Test fully populated proper noun."""
        noun = ProperNoun(
            text="New York",
            type=ProperNounType.PLACE,
            translations={"vi": "Niu Oóc", "ja": "ニューヨーク"},
            occurrences=[0, 5, 12],
            confidence=0.95,
            variants=["NYC", "New York City"]
        )
        assert noun.translations["vi"] == "Niu Oóc"
        assert len(noun.occurrences) == 3
        assert noun.confidence == 0.95
        assert "NYC" in noun.variants
    
    def test_to_dict(self):
        """Test serialization to dict."""
        noun = ProperNoun(
            text="Apple Inc.",
            type=ProperNounType.ORGANIZATION,
            translations={"vi": "Công ty Apple"},
            occurrences=[1, 3],
            confidence=0.99
        )
        result = noun.to_dict()
        
        assert isinstance(result, dict)
        assert result["text"] == "Apple Inc."
        assert result["type"] == "organization"
        assert result["translations"]["vi"] == "Công ty Apple"
        assert result["confidence"] == 0.99


class TestCharacter:
    """Tests for Character dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic character."""
        char = Character(name="John")
        assert char.name == "John"
    
    def test_default_values(self):
        """Test default values."""
        char = Character(name="Test")
        assert char.variants == []
        assert char.role is None
        assert char.first_appearance == 0
        assert char.occurrences == []
        assert char.attributes == {}
    
    def test_full_character(self):
        """Test fully populated character."""
        char = Character(
            name="Sherlock Holmes",
            variants=["Holmes", "Mr. Holmes", "the detective"],
            role="protagonist",
            first_appearance=1,
            occurrences=[1, 5, 8, 12, 20],
            attributes={"profession": "consulting detective", "location": "221B Baker Street"}
        )
        assert len(char.variants) == 3
        assert char.role == "protagonist"
        assert char.first_appearance == 1
        assert len(char.occurrences) == 5
        assert char.attributes["profession"] == "consulting detective"
    
    def test_to_dict(self):
        """Test serialization to dict."""
        char = Character(
            name="Watson",
            role="supporting",
            occurrences=[2, 6, 10]
        )
        result = char.to_dict()
        
        assert isinstance(result, dict)
        assert result["name"] == "Watson"
        assert result["role"] == "supporting"
        assert result["occurrences"] == [2, 6, 10]


class TestTerm:
    """Tests for Term dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic term."""
        term = Term(
            original="machine learning",
            translation="học máy"
        )
        assert term.original == "machine learning"
        assert term.translation == "học máy"
    
    def test_default_values(self):
        """Test default values."""
        term = Term(original="test", translation="kiểm tra")
        assert term.domain == "general"
        assert term.frequency == 1
        assert term.context_examples == []
    
    def test_full_term(self):
        """Test fully populated term."""
        term = Term(
            original="neural network",
            translation="mạng nơ-ron",
            domain="AI/ML",
            frequency=15,
            context_examples=[
                "The neural network was trained on...",
                "Using a deep neural network...",
                "The convolutional neural network achieved..."
            ]
        )
        assert term.domain == "AI/ML"
        assert term.frequency == 15
        assert len(term.context_examples) == 3
    
    def test_to_dict(self):
        """Test serialization to dict."""
        term = Term(
            original="API",
            translation="giao diện lập trình ứng dụng",
            domain="tech",
            frequency=8,
            context_examples=["Example 1", "Example 2", "Example 3", "Example 4"]
        )
        result = term.to_dict()
        
        assert result["original"] == "API"
        assert result["domain"] == "tech"
        assert result["frequency"] == 8
        # Should be limited to 3 examples
        assert len(result["context_examples"]) == 3


class TestPattern:
    """Tests for Pattern dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic pattern."""
        pattern = Pattern(type=PatternType.CHAPTER_START)
        assert pattern.type == PatternType.CHAPTER_START
    
    def test_default_values(self):
        """Test default values."""
        pattern = Pattern(type=PatternType.DIALOGUE)
        assert pattern.markers == []
        assert pattern.regex is None
        assert pattern.occurrences == 0
        assert pattern.examples == []
    
    def test_full_pattern(self):
        """Test fully populated pattern."""
        pattern = Pattern(
            type=PatternType.CHAPTER_START,
            markers=["Chapter", "CHAPTER", "chapter"],
            regex=r"^(Chapter|CHAPTER)\s+\d+",
            occurrences=12,
            examples=["Chapter 1", "Chapter 2: The Beginning", "CHAPTER 3"]
        )
        assert len(pattern.markers) == 3
        assert pattern.regex is not None
        assert pattern.occurrences == 12
        assert len(pattern.examples) == 3
    
    def test_to_dict(self):
        """Test serialization to dict."""
        pattern = Pattern(
            type=PatternType.QUOTE_BLOCK,
            markers=['"', '"'],
            occurrences=45,
            examples=["Quote 1", "Quote 2", "Quote 3", "Quote 4", "Quote 5"]
        )
        result = pattern.to_dict()
        
        assert result["type"] == "quote_block"
        assert len(result["markers"]) == 2
        assert result["occurrences"] == 45
        # Should be limited to 3 examples
        assert len(result["examples"]) == 3


class TestContentADN:
    """Tests for ContentADN dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic ADN."""
        adn = ContentADN()
        assert adn.version == "1.0"
    
    def test_default_values(self):
        """Test default values."""
        adn = ContentADN()
        assert adn.source_language == ""
        assert adn.target_language == ""
        assert adn.document_type == "unknown"
        assert adn.characters == []
        assert adn.terms == []
        assert adn.proper_nouns == []
        assert adn.patterns == []
        assert adn.total_segments == 0
        assert adn.total_characters == 0
        assert adn.unique_terms == 0
    
    def test_full_adn(self):
        """Test fully populated ADN."""
        char = Character(name="John", role="protagonist")
        term = Term(original="test", translation="kiểm tra")
        noun = ProperNoun(text="London", type=ProperNounType.PLACE)
        pattern = Pattern(type=PatternType.DIALOGUE, occurrences=10)
        
        adn = ContentADN(
            version="1.1",
            source_language="en",
            target_language="vi",
            document_type="novel",
            characters=[char],
            terms=[term],
            proper_nouns=[noun],
            patterns=[pattern],
            total_segments=100,
            total_characters=50000,
            unique_terms=250
        )
        
        assert adn.source_language == "en"
        assert adn.target_language == "vi"
        assert adn.document_type == "novel"
        assert len(adn.characters) == 1
        assert len(adn.terms) == 1
        assert len(adn.proper_nouns) == 1
        assert len(adn.patterns) == 1
        assert adn.total_segments == 100
    
    def test_to_dict(self):
        """Test serialization to dict."""
        char = Character(name="Alice")
        term = Term(original="hello", translation="xin chào")
        
        adn = ContentADN(
            source_language="en",
            target_language="vi",
            characters=[char],
            terms=[term],
            total_segments=50
        )
        
        result = adn.to_dict()
        
        assert isinstance(result, dict)
        assert result["version"] == "1.0"
        assert result["metadata"]["source_language"] == "en"
        assert result["metadata"]["target_language"] == "vi"
        assert len(result["adn"]["characters"]) == 1
        assert len(result["adn"]["terms"]) == 1
        assert result["statistics"]["total_segments"] == 50
    
    def test_to_json(self):
        """Test JSON serialization."""
        adn = ContentADN(
            source_language="en",
            target_language="ja",
            document_type="article"
        )
        
        json_str = adn.to_json()
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["metadata"]["source_language"] == "en"
        assert parsed["metadata"]["target_language"] == "ja"
    
    def test_to_json_with_indent(self):
        """Test JSON serialization with custom indent."""
        adn = ContentADN()
        json_str = adn.to_json(indent=4)
        
        # 4-space indent should be present
        assert "    " in json_str
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "version": "1.0",
            "metadata": {
                "source_language": "en",
                "target_language": "vi",
                "document_type": "novel"
            },
            "adn": {
                "characters": [
                    {"name": "John", "role": "protagonist", "variants": ["Johnny"]}
                ],
                "terms": [
                    {"original": "magic", "translation": "phép thuật", "domain": "fantasy"}
                ],
                "proper_nouns": [
                    {"text": "Hogwarts", "type": "place", "confidence": 0.99}
                ],
                "patterns": [
                    {"type": "chapter_start", "occurrences": 20}
                ]
            },
            "statistics": {
                "total_segments": 500,
                "total_characters": 100000,
                "unique_terms": 350
            }
        }
        
        adn = ContentADN.from_dict(data)
        
        assert adn.source_language == "en"
        assert adn.target_language == "vi"
        assert adn.document_type == "novel"
        assert len(adn.characters) == 1
        assert adn.characters[0].name == "John"
        assert adn.characters[0].role == "protagonist"
        assert len(adn.terms) == 1
        assert adn.terms[0].domain == "fantasy"
        assert len(adn.proper_nouns) == 1
        assert adn.proper_nouns[0].type == ProperNounType.PLACE
        assert len(adn.patterns) == 1
        assert adn.patterns[0].occurrences == 20
        assert adn.total_segments == 500
    
    def test_from_dict_minimal(self):
        """Test from_dict with minimal data."""
        adn = ContentADN.from_dict({})
        
        assert adn.version == "1.0"
        assert adn.source_language == ""
        assert adn.characters == []
    
    def test_from_json(self):
        """Test creating from JSON string."""
        json_str = '''
        {
            "version": "1.0",
            "metadata": {
                "source_language": "ja",
                "target_language": "en",
                "document_type": "manga"
            },
            "adn": {
                "characters": [{"name": "Naruto", "role": "protagonist"}],
                "terms": [],
                "proper_nouns": [],
                "patterns": []
            },
            "statistics": {
                "total_segments": 200
            }
        }
        '''
        
        adn = ContentADN.from_json(json_str)
        
        assert adn.source_language == "ja"
        assert adn.target_language == "en"
        assert len(adn.characters) == 1
        assert adn.characters[0].name == "Naruto"
    
    def test_roundtrip_serialization(self):
        """Test that to_json -> from_json preserves data."""
        original = ContentADN(
            source_language="en",
            target_language="vi",
            document_type="book",
            characters=[
                Character(name="Hero", role="protagonist", variants=["The Hero"])
            ],
            terms=[
                Term(original="sword", translation="kiếm", domain="weapons")
            ],
            proper_nouns=[
                ProperNoun(text="Westeros", type=ProperNounType.PLACE, confidence=0.95)
            ],
            patterns=[
                Pattern(type=PatternType.DIALOGUE, occurrences=100)
            ],
            total_segments=1000,
            total_characters=500000,
            unique_terms=800
        )
        
        # Serialize and deserialize
        json_str = original.to_json()
        restored = ContentADN.from_json(json_str)
        
        # Compare key fields
        assert restored.source_language == original.source_language
        assert restored.target_language == original.target_language
        assert restored.document_type == original.document_type
        assert len(restored.characters) == len(original.characters)
        assert restored.characters[0].name == original.characters[0].name
        assert len(restored.terms) == len(original.terms)
        assert len(restored.proper_nouns) == len(original.proper_nouns)
        assert len(restored.patterns) == len(original.patterns)
        assert restored.total_segments == original.total_segments


class TestADNIntegration:
    """Integration tests for ADN schema."""
    
    def test_build_complete_adn(self):
        """Test building a complete ADN structure."""
        # Create characters
        protagonist = Character(
            name="Frodo Baggins",
            variants=["Frodo", "Mr. Baggins"],
            role="protagonist",
            first_appearance=0,
            occurrences=list(range(0, 100, 5)),
            attributes={"race": "hobbit", "home": "The Shire"}
        )
        
        antagonist = Character(
            name="Sauron",
            variants=["The Dark Lord", "The Enemy"],
            role="antagonist",
            first_appearance=10,
            occurrences=[10, 50, 75, 99]
        )
        
        # Create terms
        terms = [
            Term(original="ring", translation="chiếc nhẫn", domain="fantasy", frequency=200),
            Term(original="hobbit", translation="người hobbit", domain="fantasy", frequency=150),
            Term(original="wizard", translation="phù thủy", domain="fantasy", frequency=50)
        ]
        
        # Create proper nouns
        proper_nouns = [
            ProperNoun(text="Middle-earth", type=ProperNounType.PLACE, 
                      translations={"vi": "Trung Địa"}),
            ProperNoun(text="Gandalf", type=ProperNounType.PERSON,
                      translations={"vi": "Gandalf"}),
            ProperNoun(text="The One Ring", type=ProperNounType.PRODUCT)
        ]
        
        # Create patterns
        patterns = [
            Pattern(type=PatternType.CHAPTER_START, 
                   markers=["Chapter", "Book"],
                   occurrences=22),
            Pattern(type=PatternType.DIALOGUE,
                   markers=['"', "'"],
                   occurrences=500)
        ]
        
        # Build ADN
        adn = ContentADN(
            version="1.0",
            source_language="en",
            target_language="vi",
            document_type="novel",
            characters=[protagonist, antagonist],
            terms=terms,
            proper_nouns=proper_nouns,
            patterns=patterns,
            total_segments=500,
            total_characters=250000,
            unique_terms=400
        )
        
        # Verify structure
        assert len(adn.characters) == 2
        assert len(adn.terms) == 3
        assert len(adn.proper_nouns) == 3
        assert len(adn.patterns) == 2
        
        # Export and reimport
        json_data = adn.to_json()
        restored = ContentADN.from_json(json_data)
        
        assert restored.characters[0].name == "Frodo Baggins"
        assert restored.characters[1].role == "antagonist"
        assert restored.terms[0].frequency == 200
        assert restored.proper_nouns[0].translations["vi"] == "Trung Địa"
