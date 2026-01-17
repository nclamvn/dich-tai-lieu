import zipfile
import re
import os
from pathlib import Path
from typing import Tuple

from .types import DocumentComplexity, ProcessingPipeline

class DocumentAnalyzer:
    """
    Analyzes document structure to determine complexity and routing.
    """
    
    def __init__(self):
        # Thresholds for routing
        self.MATH_THRESHOLD = 5       # If > 5 math formulas, use Vision/Hybrid
        self.IMAGE_THRESHOLD = 5      # If > 5 images, might need vision for layout
        self.SCANNED_TEXT_RATIO = 50  # If < 50 chars per page (and has images), likely scanned
        
    def analyze(self, file_path: str) -> Tuple[DocumentComplexity, ProcessingPipeline]:
        """
        Analyze the document and recommend a pipeline.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        ext = path.suffix.lower()
        
        if ext == ".docx":
            complexity = self._analyze_docx(file_path)
        elif ext == ".pdf":
            # For PDF, we'd need pypdf or pdfminer. 
            # For now, assume PDF always benefits from Vision if it's not pure text,
            # but we'll default to high complexity for safety.
            complexity = DocumentComplexity(requires_vision=True) 
        else:
            # Default fallback for txt, md etc.
            complexity = DocumentComplexity()

        pipeline = self._recommend_pipeline(complexity)
        return complexity, pipeline

    def _analyze_docx(self, file_path: str) -> DocumentComplexity:
        """
        Deep scan of DOCX xml structure.
        """
        stats = DocumentComplexity()
        
        try:
            with zipfile.ZipFile(file_path, 'r') as doc:
                # 1. Read word/document.xml (Main Content)
                try:
                    xml_content = doc.read('word/document.xml').decode('utf-8')
                    
                    # Count features using fast regex
                    # Math (OMML)
                    stats.math_count = len(re.findall(r'<m:oMath>', xml_content)) + \
                                     len(re.findall(r'<m:oMathPara>', xml_content))
                    
                    # Images/Drawings
                    stats.image_count = len(re.findall(r'<w:drawing>', xml_content)) + \
                                      len(re.findall(r'<w:object>', xml_content))
                    
                    # Tables
                    stats.table_count = len(re.findall(r'<w:tbl>', xml_content))
                    
                    # Text Density (Approximate)
                    # Remove tags to estimate text length
                    text_only = re.sub(r'<[^>]+>', '', xml_content)
                    char_count = len(text_only)
                    
                    # 2. Estimate Page Count (from app.xml if available)
                    # word/app.xml usually contains <Pages>N</Pages>
                    try:
                        app_xml = doc.read('docProps/app.xml').decode('utf-8')
                        pages_match = re.search(r'<Pages>(\d+)</Pages>', app_xml)
                        if pages_match:
                            stats.page_count = int(pages_match.group(1))
                    except (KeyError, UnicodeDecodeError):
                        # app.xml not present or malformed
                        pass
                        
                    if stats.page_count > 0:
                        stats.text_density = char_count / stats.page_count
                    
                    # Check for scanned (Low text density + images)
                    if stats.page_count > 0 and stats.text_density < self.SCANNED_TEXT_RATIO and stats.image_count > stats.page_count:
                         stats.is_scanned = True
                         
                except KeyError:
                    # Invalid docx structure
                    pass
                    
        except zipfile.BadZipFile:
            print(f"Error: Bad Zip File {file_path}")
            
        # Determine vision requirement
        if stats.is_scanned or \
           stats.math_count > self.MATH_THRESHOLD or \
           stats.image_count > self.IMAGE_THRESHOLD:
            stats.requires_vision = True
            
        return stats

    def _recommend_pipeline(self, stats: DocumentComplexity) -> ProcessingPipeline:
        """
        Decision logic for routing.
        """
        if stats.is_scanned:
            return ProcessingPipeline.VISION_ENHANCED
        
        if stats.math_count > self.MATH_THRESHOLD:
            # Heavy math -> Vision is safer for preserving layout/formulas
            return ProcessingPipeline.VISION_ENHANCED
            
        if stats.image_count > self.IMAGE_THRESHOLD:
            return ProcessingPipeline.VISION_ENHANCED
            
        return ProcessingPipeline.NATIVE_TEXT
