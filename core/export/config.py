from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class AcademicLayoutConfig:
    """
    Configuration for academic DOCX layout.
    Updated Phase 9: Theme support.
    """
    theme: str = "academic" # 'academic', 'modern', 'classic'
    
    # Legacy overrides (can still function but themes are preferred)
    font_name: Optional[str] = None 
    font_size: Optional[int] = None
    
    equation_rendering_mode: Literal["latex_text", "omml"] = "latex_text"

    # Phase 2.0.5: Professional styling features
    enable_theorem_boxes: bool = True
    enable_proof_indent: bool = True
    enable_advanced_equation_layout: bool = True
