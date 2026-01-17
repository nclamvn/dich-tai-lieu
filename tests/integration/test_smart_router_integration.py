import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from core_v2.batch_processor import BatchProcessor
from core_v2.router.types import ProcessingPipeline, DocumentComplexity

@pytest.mark.asyncio
async def test_smart_router_integration():
    # Setup
    mock_publisher = Mock()
    mock_publisher.publish = AsyncMock()
    mock_publisher.publish.return_value = Mock(status=Mock(value="complete"), job_id="test_job")
    
    processor = BatchProcessor(publisher=mock_publisher)
    
    # Mock Analyzer
    mock_analyzer = Mock()
    processor.analyzer = mock_analyzer
    
    # Case 1: Complex File (Math) -> Should use Vision
    mock_analyzer.analyze.return_value = (
        DocumentComplexity(math_count=10), 
        ProcessingPipeline.VISION_ENHANCED
    )
    
    batch = processor.create_batch(
        files=[("math.docx", "/path/to/math.docx")],
        use_vision=True  # Batch allow vision
    )
    
    await processor._process_batch(batch, None)
    
    # Check publisher call
    args, kwargs = mock_publisher.publish.call_args_list[0]
    assert kwargs['use_vision'] is True, "Complex file should use Vision"
    
    # Case 2: Simple File -> Should Downgrade to Native
    mock_publisher.publish.reset_mock()
    mock_analyzer.analyze.return_value = (
        DocumentComplexity(), 
        ProcessingPipeline.NATIVE_TEXT
    )
    
    batch_simple = processor.create_batch(
        files=[("simple.docx", "/path/to/simple.docx")],
        use_vision=True  # Batch still allows vision/auto
    )
    
    await processor._process_batch(batch_simple, None)
    
    args, kwargs = mock_publisher.publish.call_args_list[0]
    assert kwargs['use_vision'] is False, "Simple file should downgrade to Native"
