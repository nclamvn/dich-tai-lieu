from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class ProcessingPipeline(str, Enum):
    """
    Determines how the document should be processed.
    """
    NATIVE_TEXT = "native_text"  # Standard text extraction (fast, cheap)
    VISION_ENHANCED = "vision_enhanced"  # OCR/Vision for complex layouts/math
    HYBRID = "hybrid"  # Mix of both (e.g., text for body, vision for formulas/tables)

@dataclass
class DocumentComplexity:
    """
    Stats regarding document complexity.
    """
    page_count: int = 0
    text_density: float = 0.0  # chars per page average
    
    # Complexity Markers
    math_count: int = 0  # OMML tags
    image_count: int = 0  # Drawing/Image tags
    table_count: int = 0
    
    # Computed
    is_scanned: bool = False  # If text density is low but images exist
    requires_vision: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_count": self.page_count,
            "math_count": self.math_count,
            "image_count": self.image_count,
            "table_count": self.table_count,
            "is_scanned": self.is_scanned,
            "requires_vision": self.requires_vision
        }
