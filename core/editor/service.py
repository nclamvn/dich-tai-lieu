import logging
from typing import List, Dict, Any, Optional
from config.settings import settings
from core.cache.checkpoint_manager import CheckpointManager
from core.editor.schemas import SegmentResponse, EditorJobResponse

logger = logging.getLogger(__name__)

class EditorService:
    """
    Service for managing translation segments updates via Checkpoints.
    """

    def __init__(self):
        db_path = settings.checkpoint_dir / "checkpoints.db"
        self.checkpoint_manager = CheckpointManager(db_path)

    def get_job_segments(self, job_id: str) -> Optional[EditorJobResponse]:
        """
        Get all segments for a job from its checkpoint.
        """
        checkpoint = self.checkpoint_manager.load_checkpoint(job_id)
        if not checkpoint:
            return None

        segments: List[SegmentResponse] = []
        
        # results_data is Dict[chunk_id, TranslationResult-like-dict]
        # We need to sort them. Assuming chunk_id is numeric or sortable string.
        # Try to parse chunk_id to int for sorting if possible.
        
        sorted_keys = sorted(
            checkpoint.results_data.keys(),
            key=lambda k: int(k) if str(k).isdigit() else str(k)
        )

        for i, chunk_id in enumerate(sorted_keys):
            data = checkpoint.results_data[chunk_id]
            # data matches serialize_translation_result format
            
            segments.append(SegmentResponse(
                chunk_id=str(chunk_id),
                index=i,
                source=data.get('source', ''),
                translated=data.get('translated', ''),
                quality_score=data.get('quality_score', 0.0),
                is_edited=data.get('is_edited', False), # Custom field we might add
                warnings=data.get('warnings', [])
            ))

        return EditorJobResponse(
            job_id=job_id,
            segments=segments,
            completion_percentage=checkpoint.completion_percentage(),
            can_export=checkpoint.completion_percentage() >= 1.0
        )

    def update_segment(self, job_id: str, chunk_id: str, new_text: str) -> bool:
        """
        Update the translation of a specific segment.
        """
        # 1. Load entire checkpoint
        checkpoint = self.checkpoint_manager.load_checkpoint(job_id)
        if not checkpoint:
            logger.warning(f"Checkpoint not found for job {job_id}")
            return False

        # 2. Check if chunk exists (handle int/str mismatch)
        # CheckpointManager.load_checkpoint fixes keys to match original types (int or str)
        # But our input chunk_id is str (from URL).
        # We try both str and int keys.
        
        target_key = chunk_id
        if chunk_id not in checkpoint.results_data:
            if chunk_id.isdigit() and int(chunk_id) in checkpoint.results_data:
                target_key = int(chunk_id)
            else:
                logger.warning(f"Chunk {chunk_id} not found in checkpoint for job {job_id}")
                return False

        # 3. Update data
        original_data = checkpoint.results_data[target_key]
        
        # Preserve other fields, just update text
        original_data['translated'] = new_text
        original_data['is_edited'] = True # Mark as edited
        
        # 4. Save back
        # Note: save_checkpoint takes arguments, not a CheckpointState object
        # We need to pass all fields back.
        
        self.checkpoint_manager.save_checkpoint(
            job_id=checkpoint.job_id,
            input_file=checkpoint.input_file,
            output_file=checkpoint.output_file,
            total_chunks=checkpoint.total_chunks,
            completed_chunk_ids=checkpoint.completed_chunk_ids,
            results_data=checkpoint.results_data,
            job_metadata=checkpoint.job_metadata
        )
        
        logger.info(f"Updated segment {chunk_id} for job {job_id}")
        return True

_editor_service = None

def get_editor_service() -> EditorService:
    global _editor_service
    if _editor_service is None:
        _editor_service = EditorService()
    return _editor_service
