import unittest
from unittest.mock import MagicMock, patch, mock_open
from core_v2.router.analyzer import DocumentAnalyzer
from core_v2.router.types import ProcessingPipeline

class TestDocumentAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = DocumentAnalyzer()
        
    @patch('zipfile.ZipFile')
    @patch('pathlib.Path.exists')
    def test_analyze_simple_text(self, mock_exists, mock_zip):
        # Setup
        mock_exists.return_value = True
        
        # Mock DOCX content
        mock_doc = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_doc
        
        # Simple text xml
        mock_doc.read.side_effect = lambda name: \
            b'<w:document><w:body><w:p><w:t>Hello World</w:t></w:p></w:body></w:document>' \
            if name == 'word/document.xml' else b'<Pages>1</Pages>'
            
        # Analysis
        complexity, pipeline = self.analyzer.analyze("simple.docx")
        
        # Verify
        self.assertEqual(complexity.math_count, 0)
        self.assertEqual(pipeline, ProcessingPipeline.NATIVE_TEXT)

    @patch('zipfile.ZipFile')
    @patch('pathlib.Path.exists')
    def test_analyze_heavy_math(self, mock_exists, mock_zip):
        # Setup
        mock_exists.return_value = True
        mock_doc = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_doc
        
        # Heavy math xml (6 math tags)
        math_xml = b'<w:document>' + (b'<m:oMath>x</m:oMath>' * 6) + b'</w:document>'
        
        mock_doc.read.side_effect = lambda name: \
            math_xml if name == 'word/document.xml' else b'<Pages>1</Pages>'
            
        # Analysis
        complexity, pipeline = self.analyzer.analyze("math.docx")
        
        # Verify
        self.assertEqual(complexity.math_count, 6)
        self.assertEqual(pipeline, ProcessingPipeline.VISION_ENHANCED)

    @patch('zipfile.ZipFile')
    @patch('pathlib.Path.exists')
    def test_analyze_scanned_pdf_simulation(self, mock_exists, mock_zip):
        # Setup: Simulation of docx that wraps scanned images
        mock_exists.return_value = True
        mock_doc = MagicMock()
        mock_zip.return_value.__enter__.return_value = mock_doc
        
        # 10 pages, 10 images, very little text
        doc_xml = b'<w:document>' + (b'<w:drawing>img</w:drawing>' * 11) + b'<w:t>Short</w:t></w:document>'
        app_xml = b'<Properties><Pages>10</Pages></Properties>'
        
        mock_doc.read.side_effect = lambda name: \
            doc_xml if name == 'word/document.xml' else app_xml
            
        # Analysis
        complexity, pipeline = self.analyzer.analyze("scan.docx")
        
        # Verify
        self.assertTrue(complexity.is_scanned)
        self.assertEqual(pipeline, ProcessingPipeline.VISION_ENHANCED)

if __name__ == '__main__':
    unittest.main()
