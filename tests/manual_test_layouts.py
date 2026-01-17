
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from core.structure.semantic_model import DocNode, DocNodeType
from core.export.docx_academic_builder import build_academic_docx
from core.export.config import AcademicLayoutConfig

def generate_test_docs():
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    # Create sample content
    nodes = [
        DocNode(DocNodeType.CHAPTER, "Preface"),
        DocNode(DocNodeType.PARAGRAPH, "This is a sample document validating the Premium Print Engine."),
        
        DocNode(DocNodeType.CHAPTER, "Fundamentals of Typography"),
        DocNode(DocNodeType.SECTION, "The Importance of Style"),
        DocNode(DocNodeType.PARAGRAPH, "Typography is the art and technique of arranging type to make written language legible, readable, and appealing."),
        
        DocNode(DocNodeType.THEOREM, "Legibility vs Readability. Legibility refers to being able to distinguish one letter from another.", title="Theorem 1"),
        DocNode(DocNodeType.PROOF, "Consider two fonts. One has distinct shapes... Thus, it is more legible.", title="Proof of Theorem 1"),
        
        DocNode(DocNodeType.SECTION, "Mathematical Beauty"),
        DocNode(DocNodeType.PARAGRAPH, "Here is an equation:"),
        DocNode(DocNodeType.EQUATION_BLOCK, "E = mc^2"),
        
        DocNode(DocNodeType.DEFINITION, "A serif is a small line or stroke regularly attached to the end of a larger stroke.", title="Definition 1.1"),
    ]
    
    themes = ['academic', 'modern', 'classic']
    
    print("Generating layouts...")
    for theme in themes:
        print(f"  - Generating {theme}...")
        config = AcademicLayoutConfig(theme=theme)
        output_path = output_dir / f"layout_test_{theme}.docx"
        
        metadata = {
            'title': f'Premium Document ({theme.title()})',
            'author': 'AI Publisher Pro',
            'subject': 'Demonstration of Commercial Print Engine'
        }
        
        try:
            build_academic_docx(nodes, str(output_path), config, metadata)
            print(f"    ✅ Success: {output_path}")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generate_test_docs()
