from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.export.config import AcademicLayoutConfig
from core.export.docx_styles import StyleManager

def _setup_page_layout(doc: Document, config: AcademicLayoutConfig, style_manager: StyleManager):

    from docx.enum.section import WD_SECTION, WD_ORIENT
    from docx.shared import Inches, Cm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    section = doc.sections[0]
    
    # 1. Page Size (Default A4)
    # Could be configurable in ThemeConfig/LayoutConfig
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)

    # 2. Margins & Mirror Margins
    # Access layout margin constants if needed, or use defaults
    # "Mirror Margins" logic requires Oxml injection
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.25) # Inside margin (Gutter)
    section.right_margin = Inches(0.75) # Outside margin
    
    # Enable Mirror Margins (Odd/Even pages flip left/right)
    sectPr = section._sectPr
    pgMar = sectPr.find(qn('w:pgMar'))
    if pgMar is not None:
        # Standard DOCX mirror margins attribute
        # <w:mirrorMargins/>
        mirror = OxmlElement('w:mirrorMargins')
        sectPr.append(mirror)

    # 3. Headers & Footers
    section.different_first_page_header_footer = True
    section.header_distance = Cm(1.27)
    section.footer_distance = Cm(1.27)

    # Footer: Page Numbers (Center)
    footer = section.footer
    para = footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_page_number(para)
    style_manager.apply_body_style(para)


def _add_page_number(paragraph):
    """Add dynamic page number field."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    run = paragraph.add_run()
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = "PAGE"

    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
