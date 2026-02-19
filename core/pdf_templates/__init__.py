"""
PDF Templates System - AI Publisher Pro
Professional book typography templates for Vietnamese text.

Available Templates:

Literary Templates (Văn học):
1. ClassicSerif - Traditional book design
2. ModernMinimal - Clean contemporary look
3. LiteraryElegant - Refined literary style
4. CompactPocket - Pocket-size books
5. PremiumHardcover - Luxury collector editions
6. EasyRead - Accessibility-focused

Professional Templates (Chuyên nghiệp):
7. BusinessReport - Business reports and proposals
8. AcademicPaper - Academic papers and thesis
9. TechnicalDoc - Technical documentation
10. LegalDocument - Contracts and legal documents
11. Newsletter - Magazines and newsletters
12. Presentation - Slide decks and pitch decks

Usage:
    from core.pdf_templates import get_template, list_templates

    # Get a template
    template = get_template("classic_serif")

    # List available templates
    templates = list_templates()

    # List by category
    templates = list_templates(category="literary")
"""

from typing import Dict, Type, List, Optional
from .base_template import BaseTemplate, TemplateConfig

# Literary Templates
from .classic_serif import ClassicSerifTemplate
from .modern_minimal import ModernMinimalTemplate
from .literary_elegant import LiteraryElegantTemplate
from .compact_pocket import CompactPocketTemplate
from .premium_hardcover import PremiumHardcoverTemplate
from .easy_read import EasyReadTemplate

# Professional Templates
from .business_report import BusinessReportTemplate
from .academic_paper import AcademicPaperTemplate
from .technical_doc import TechnicalDocTemplate
from .legal_document import LegalDocumentTemplate
from .newsletter import NewsletterTemplate
from .presentation import PresentationTemplate

# Template Registry with categories
TEMPLATES: Dict[str, Dict] = {
    # Literary Templates
    "classic_serif": {"class": ClassicSerifTemplate, "category": "literary"},
    "modern_minimal": {"class": ModernMinimalTemplate, "category": "literary"},
    "literary_elegant": {"class": LiteraryElegantTemplate, "category": "literary"},
    "compact_pocket": {"class": CompactPocketTemplate, "category": "literary"},
    "premium_hardcover": {"class": PremiumHardcoverTemplate, "category": "literary"},
    "easy_read": {"class": EasyReadTemplate, "category": "literary"},
    # Professional Templates
    "business_report": {"class": BusinessReportTemplate, "category": "business"},
    "academic_paper": {"class": AcademicPaperTemplate, "category": "academic"},
    "technical_doc": {"class": TechnicalDocTemplate, "category": "technical"},
    "legal_document": {"class": LegalDocumentTemplate, "category": "legal"},
    "newsletter": {"class": NewsletterTemplate, "category": "media"},
    "presentation": {"class": PresentationTemplate, "category": "media"},
}

# Category labels
CATEGORIES = {
    "literary": "Văn học (Literary)",
    "business": "Kinh doanh (Business)",
    "academic": "Học thuật (Academic)",
    "technical": "Kỹ thuật (Technical)",
    "legal": "Pháp lý (Legal)",
    "media": "Truyền thông (Media)",
}

# Default template
DEFAULT_TEMPLATE = "classic_serif"


def get_template(name: str = DEFAULT_TEMPLATE) -> BaseTemplate:
    """
    Get a template instance by name.

    Args:
        name: Template name (e.g., "classic_serif", "modern_minimal")

    Returns:
        Template instance

    Raises:
        ValueError: If template not found
    """
    name = name.lower().replace("-", "_").replace(" ", "_")

    if name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        raise ValueError(f"Template '{name}' not found. Available: {available}")

    return TEMPLATES[name]["class"]()


def list_templates(category: Optional[str] = None) -> List[Dict]:
    """
    List all available templates with metadata.

    Args:
        category: Optional filter by category (literary, business, academic, etc.)

    Returns:
        List of template info dicts
    """
    result = []
    for name, info in TEMPLATES.items():
        # Filter by category if specified
        if category and info["category"] != category:
            continue

        template = info["class"]()
        result.append({
            "id": name,
            "name": template.display_name,
            "description": template.description,
            "page_size": template.config.page_size_name,
            "font_style": template.font_style,
            "best_for": template.best_for,
            "category": info["category"],
            "category_label": CATEGORIES.get(info["category"], info["category"]),
        })
    return result


def list_categories() -> List[Dict]:
    """
    List all template categories.

    Returns:
        List of category info dicts
    """
    result = []
    for cat_id, label in CATEGORIES.items():
        count = sum(1 for t in TEMPLATES.values() if t["category"] == cat_id)
        result.append({
            "id": cat_id,
            "label": label,
            "count": count,
        })
    return result


def get_template_info(name: str) -> Optional[Dict]:
    """Get detailed info about a specific template."""
    name = name.lower().replace("-", "_").replace(" ", "_")

    if name not in TEMPLATES:
        return None

    try:
        info = TEMPLATES[name]
        template = info["class"]()
        return {
            "id": name,
            "name": template.display_name,
            "description": template.description,
            "category": info["category"],
            "category_label": CATEGORIES.get(info["category"], info["category"]),
            "config": {
                "page_size": template.config.page_size_name,
                "page_width_mm": template.config.page_width_mm,
                "page_height_mm": template.config.page_height_mm,
                "margins": {
                    "top": template.config.margin_top,
                    "bottom": template.config.margin_bottom,
                    "inner": template.config.margin_inner,
                    "outer": template.config.margin_outer,
                },
                "typography": {
                    "body_font": template.config.body_font,
                    "heading_font": template.config.heading_font,
                    "body_size": template.config.body_size,
                    "line_height": template.config.line_height,
                },
            },
            "font_style": template.font_style,
            "best_for": template.best_for,
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).debug("Failed to get template info for '%s': %s", name, e)
        return None


__all__ = [
    "get_template",
    "list_templates",
    "list_categories",
    "get_template_info",
    "TEMPLATES",
    "CATEGORIES",
    "DEFAULT_TEMPLATE",
    "BaseTemplate",
    "TemplateConfig",
]
