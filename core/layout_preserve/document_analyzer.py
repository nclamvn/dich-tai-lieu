"""
LLM-Native Document Analyzer
AI Publisher Pro

Uses Vision LLM to extract structured content from business documents
while preserving layout (tables, columns, headers).

Philosophy: Let LLM do the heavy lifting, minimal dependencies.
"""

import json
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from dataclasses import dataclass, field
from enum import Enum
import asyncio


class ContentType(Enum):
    """Types of content blocks"""
    HEADER = "header"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    LIST = "list"
    IMAGE_CAPTION = "image_caption"
    FOOTER = "footer"
    PAGE_NUMBER = "page_number"


@dataclass
class TableCell:
    """Single cell in a table"""
    content: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    is_header: bool = False


@dataclass
class Table:
    """Structured table representation"""
    cells: List[TableCell]
    num_rows: int
    num_cols: int
    caption: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "type": "table",
            "num_rows": self.num_rows,
            "num_cols": self.num_cols,
            "caption": self.caption,
            "cells": [
                {
                    "content": c.content,
                    "row": c.row,
                    "col": c.col,
                    "rowspan": c.rowspan,
                    "colspan": c.colspan,
                    "is_header": c.is_header
                }
                for c in self.cells
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Table":
        cells = [
            TableCell(
                content=c["content"],
                row=c["row"],
                col=c["col"],
                rowspan=c.get("rowspan", 1),
                colspan=c.get("colspan", 1),
                is_header=c.get("is_header", False)
            )
            for c in data.get("cells", [])
        ]
        return cls(
            cells=cells,
            num_rows=data.get("num_rows", 0),
            num_cols=data.get("num_cols", 0),
            caption=data.get("caption")
        )


@dataclass
class ContentBlock:
    """A block of content with type and structure"""
    type: ContentType
    content: Any  # str for text, Table for tables, List[str] for lists
    level: int = 0  # For headers: h1=1, h2=2, etc.
    style: Optional[Dict] = None  # bold, italic, alignment, etc.
    
    def to_dict(self) -> Dict:
        result = {
            "type": self.type.value,
            "level": self.level,
        }
        
        if self.type == ContentType.TABLE:
            result["content"] = self.content.to_dict() if isinstance(self.content, Table) else self.content
        else:
            result["content"] = self.content
            
        if self.style:
            result["style"] = self.style
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ContentBlock":
        content_type = ContentType(data["type"])
        
        if content_type == ContentType.TABLE:
            content = Table.from_dict(data["content"])
        else:
            content = data["content"]
        
        return cls(
            type=content_type,
            content=content,
            level=data.get("level", 0),
            style=data.get("style")
        )


@dataclass
class DocumentPage:
    """A single page with structured content"""
    page_number: int
    blocks: List[ContentBlock] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "page_number": self.page_number,
            "blocks": [b.to_dict() for b in self.blocks]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DocumentPage":
        return cls(
            page_number=data["page_number"],
            blocks=[ContentBlock.from_dict(b) for b in data.get("blocks", [])]
        )


@dataclass
class StructuredDocument:
    """Complete structured document"""
    pages: List[DocumentPage] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "metadata": self.metadata,
            "pages": [p.to_dict() for p in self.pages]
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StructuredDocument":
        return cls(
            pages=[DocumentPage.from_dict(p) for p in data.get("pages", [])],
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "StructuredDocument":
        return cls.from_dict(json.loads(json_str))


# =========================================
# LLM-Native Document Analyzer
# =========================================

EXTRACTION_SYSTEM_PROMPT = """You are a document structure analyzer. Your job is to extract ALL content from a business document image while PRESERVING the exact layout structure.

Output ONLY valid JSON with this structure:
{
  "page_number": 1,
  "blocks": [
    {
      "type": "header",
      "content": "Document Title",
      "level": 1
    },
    {
      "type": "paragraph", 
      "content": "Regular text paragraph..."
    },
    {
      "type": "table",
      "content": {
        "num_rows": 3,
        "num_cols": 4,
        "caption": "Table 1: Sales Data",
        "cells": [
          {"content": "Header 1", "row": 0, "col": 0, "is_header": true},
          {"content": "Header 2", "row": 0, "col": 1, "is_header": true},
          {"content": "Data 1", "row": 1, "col": 0, "is_header": false},
          ...
        ]
      }
    },
    {
      "type": "list",
      "content": ["Item 1", "Item 2", "Item 3"]
    }
  ]
}

RULES:
1. Extract ALL text, don't skip anything
2. Preserve table structure with exact rows/columns
3. Maintain reading order (top to bottom, left to right for multi-column)
4. Identify headers by size/style (level 1 = largest, level 2 = medium, etc.)
5. For tables: include ALL cells, mark header rows with is_header: true
6. Output ONLY the JSON, no explanations"""


TRANSLATION_SYSTEM_PROMPT = """You are a professional translator. You will receive a JSON structure containing document content.

CRITICAL RULES:
1. Translate ONLY the text values (content fields)
2. DO NOT modify the JSON structure
3. DO NOT translate keys, types, or structural elements
4. Preserve all formatting markers
5. For tables: translate each cell's content while keeping structure
6. Maintain professional business terminology
7. Output ONLY the translated JSON, no explanations

Source language: {source_lang}
Target language: {target_lang}"""


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class AnalyzerConfig:
    """Configuration for document analyzer"""
    # Provider selection
    vision_provider: LLMProvider = LLMProvider.OPENAI
    translation_provider: LLMProvider = LLMProvider.OPENAI
    
    # Models
    vision_model: str = "gpt-4o"  # Need vision capability
    translation_model: str = "gpt-4o-mini"  # Cheaper for text
    
    # Languages
    source_lang: str = "Chinese"
    target_lang: str = "Vietnamese"
    
    # Processing
    max_retries: int = 3
    temperature: float = 0.1  # Low for consistency


class DocumentAnalyzer:
    """
    LLM-Native Document Analyzer
    
    Uses Vision LLM to extract structured content,
    then Text LLM to translate while preserving structure.
    """
    
    def __init__(self, config: Optional[AnalyzerConfig] = None):
        self.config = config or AnalyzerConfig()
        self._init_clients()
    
    def _init_clients(self):
        """Initialize API clients based on config"""
        if self.config.vision_provider == LLMProvider.OPENAI or \
           self.config.translation_provider == LLMProvider.OPENAI:
            from openai import AsyncOpenAI
            self.openai_client = AsyncOpenAI()
        
        if self.config.vision_provider == LLMProvider.ANTHROPIC or \
           self.config.translation_provider == LLMProvider.ANTHROPIC:
            from anthropic import AsyncAnthropic
            self.anthropic_client = AsyncAnthropic()
    
    async def _call_openai_vision(self, image_base64: str, prompt: str) -> str:
        """Call OpenAI Vision API"""
        response = await self.openai_client.chat.completions.create(
            model=self.config.vision_model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=self.config.temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content
    
    async def _call_anthropic_vision(self, image_base64: str, prompt: str) -> str:
        """Call Anthropic Vision API"""
        response = await self.anthropic_client.messages.create(
            model=self.config.vision_model,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            system=EXTRACTION_SYSTEM_PROMPT
        )
        return response.content[0].text
    
    async def _call_openai_text(self, system: str, user: str) -> str:
        """Call OpenAI Text API"""
        response = await self.openai_client.chat.completions.create(
            model=self.config.translation_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            temperature=self.config.temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content
    
    async def _call_anthropic_text(self, system: str, user: str) -> str:
        """Call Anthropic Text API"""
        response = await self.anthropic_client.messages.create(
            model=self.config.translation_model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return response.content[0].text
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from LLM"""
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return response.strip()
    
    async def extract_structure(self, image_path: str, page_number: int = 1) -> DocumentPage:
        """
        Extract structured content from a document image.
        
        Args:
            image_path: Path to the image file
            page_number: Page number for tracking
            
        Returns:
            DocumentPage with structured content
        """
        # Convert image to base64
        image_base64 = self._image_to_base64(image_path)
        
        # Call Vision LLM
        prompt = f"Extract all content from this business document (page {page_number}). Preserve exact table structure with all rows and columns."
        
        for attempt in range(self.config.max_retries):
            try:
                if self.config.vision_provider == LLMProvider.OPENAI:
                    response = await self._call_openai_vision(image_base64, prompt)
                else:
                    response = await self._call_anthropic_vision(image_base64, prompt)
                
                # Parse JSON response
                cleaned = self._clean_json_response(response)
                data = json.loads(cleaned)
                
                return DocumentPage.from_dict(data)
                
            except json.JSONDecodeError as e:
                if attempt == self.config.max_retries - 1:
                    raise ValueError(f"Failed to parse LLM response as JSON: {e}")
                continue
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                continue
        
        raise RuntimeError("Failed to extract structure after max retries")
    
    async def translate_structure(self, page: DocumentPage) -> DocumentPage:
        """
        Translate structured content while preserving structure.
        
        Args:
            page: DocumentPage with original content
            
        Returns:
            DocumentPage with translated content
        """
        # Convert to JSON for translation
        page_json = json.dumps(page.to_dict(), ensure_ascii=False)
        
        # Prepare translation prompt
        system = TRANSLATION_SYSTEM_PROMPT.format(
            source_lang=self.config.source_lang,
            target_lang=self.config.target_lang
        )
        
        user = f"Translate this document structure:\n\n{page_json}"
        
        for attempt in range(self.config.max_retries):
            try:
                if self.config.translation_provider == LLMProvider.OPENAI:
                    response = await self._call_openai_text(system, user)
                else:
                    response = await self._call_anthropic_text(system, user)
                
                # Parse JSON response
                cleaned = self._clean_json_response(response)
                data = json.loads(cleaned)
                
                return DocumentPage.from_dict(data)
                
            except json.JSONDecodeError as e:
                if attempt == self.config.max_retries - 1:
                    raise ValueError(f"Failed to parse translated JSON: {e}")
                continue
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                continue
        
        raise RuntimeError("Failed to translate after max retries")
    
    async def process_page(self, image_path: str, page_number: int = 1) -> tuple[DocumentPage, DocumentPage]:
        """
        Extract and translate a single page.
        
        Returns:
            Tuple of (original_page, translated_page)
        """
        # Step 1: Extract structure
        original = await self.extract_structure(image_path, page_number)
        
        # Step 2: Translate
        translated = await self.translate_structure(original)
        
        return original, translated
    
    async def process_document(
        self,
        image_paths: List[str],
        on_progress: Optional[callable] = None
    ) -> tuple[StructuredDocument, StructuredDocument]:
        """
        Process entire document.
        
        Returns:
            Tuple of (original_doc, translated_doc)
        """
        original_pages = []
        translated_pages = []
        
        for i, image_path in enumerate(image_paths):
            original, translated = await self.process_page(image_path, i + 1)
            original_pages.append(original)
            translated_pages.append(translated)
            
            if on_progress:
                on_progress(i + 1, len(image_paths))
        
        original_doc = StructuredDocument(pages=original_pages)
        translated_doc = StructuredDocument(pages=translated_pages)
        
        return original_doc, translated_doc


# =========================================
# Convenience Functions
# =========================================

async def analyze_business_document(
    image_path: str,
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese",
    provider: str = "openai"  # or "anthropic"
) -> tuple[DocumentPage, DocumentPage]:
    """
    Quick function to analyze and translate a single page.
    
    Example:
        original, translated = await analyze_business_document(
            "page1.png",
            source_lang="Chinese",
            target_lang="Vietnamese"
        )
        print(translated.to_dict())
    """
    config = AnalyzerConfig(
        vision_provider=LLMProvider(provider),
        translation_provider=LLMProvider.OPENAI,  # Always use OpenAI for translation (cheaper)
        source_lang=source_lang,
        target_lang=target_lang
    )
    
    analyzer = DocumentAnalyzer(config)
    return await analyzer.process_page(image_path)


def create_analyzer(
    vision_model: str = "gpt-4o",
    translation_model: str = "gpt-4o-mini",
    source_lang: str = "Chinese",
    target_lang: str = "Vietnamese"
) -> DocumentAnalyzer:
    """
    Create a configured document analyzer.
    
    Example:
        analyzer = create_analyzer(
            vision_model="gpt-4o",
            translation_model="gpt-4o-mini"
        )
        original, translated = await analyzer.process_page("page.png")
    """
    config = AnalyzerConfig(
        vision_model=vision_model,
        translation_model=translation_model,
        source_lang=source_lang,
        target_lang=target_lang
    )
    return DocumentAnalyzer(config)
