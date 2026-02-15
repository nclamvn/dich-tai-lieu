"""
Cinema Chunker - Scene-Optimized Text Chunking

Extends the existing SmartChunker and SemanticChunker to create
chunks optimized for cinematic scene conversion.

Target: ~500-1000 words per chunk (2-3 minutes of video)
"""

import re
import uuid
import logging
from typing import List, Optional, Any

from .models import CinematicChunk

# Import existing chunkers
try:
    from core.chunker import SmartChunker
    from core_v2.semantic_chunker import SemanticChunker, SemanticChunk, ChunkType
except ImportError:
    # Fallback if running standalone
    SmartChunker = None
    SemanticChunker = None

logger = logging.getLogger(__name__)


class CinemaChunker:
    """
    Scene-optimized text chunking for book-to-cinema conversion.
    
    Leverages existing SmartChunker and SemanticChunker but optimizes
    for cinematic scene lengths (~500-1000 words per scene).
    
    Usage:
        chunker = CinemaChunker()
        chunks = await chunker.chunk_for_cinema(book_text)
    """
    
    # Optimal scene size in words (2-3 minutes of video)
    SCENE_MIN_WORDS = 300
    SCENE_TARGET_WORDS = 750
    SCENE_MAX_WORDS = 1200
    
    # Character limits
    SCENE_MIN_CHARS = 1500
    SCENE_TARGET_CHARS = 4000
    SCENE_MAX_CHARS = 6500
    
    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize CinemaChunker.
        
        Args:
            llm_client: Optional LLM client for intelligent boundary detection
        """
        self.llm_client = llm_client
        
        # Initialize underlying chunkers
        if SemanticChunker:
            self.semantic_chunker = SemanticChunker(llm_client)
        else:
            self.semantic_chunker = None
            
        if SmartChunker:
            self.smart_chunker = SmartChunker(
                max_chars=self.SCENE_TARGET_CHARS,
                context_window=200
            )
        else:
            self.smart_chunker = None
    
    async def chunk_for_cinema(self, text: str) -> List[CinematicChunk]:
        """
        Chunk text into cinema-optimized segments.
        
        Strategy:
        1. Use SemanticChunker to identify chapters/sections
        2. Further split each semantic chunk into scene-sized pieces
        3. Preserve context between scenes for continuity
        
        Args:
            text: Full book/document text
            
        Returns:
            List of CinematicChunk objects optimized for scene conversion
        """
        text = text.strip()
        
        # Step 1: Get semantic structure (chapters, sections)
        if self.semantic_chunker:
            semantic_chunks = await self.semantic_chunker.chunk(text)
            logger.info(f"SemanticChunker produced {len(semantic_chunks)} chunks")
        else:
            # Fallback: simple paragraph splitting
            semantic_chunks = self._simple_chunk(text)
        
        # Step 2: Convert to cinematic chunks with scene-optimized sizes
        cinematic_chunks = []
        chunk_index = 0
        
        for sem_chunk in semantic_chunks:
            # Get the content from semantic chunk
            content = sem_chunk.content if hasattr(sem_chunk, 'content') else str(sem_chunk)
            title = getattr(sem_chunk, 'title', None)
            
            # Check if chunk needs further splitting
            word_count = len(content.split())
            
            if word_count <= self.SCENE_MAX_WORDS:
                # Chunk is already scene-sized
                cinematic_chunks.append(CinematicChunk(
                    chunk_id=f"scene_{uuid.uuid4().hex[:8]}",
                    text=content,
                    chapter_title=title,
                    index=chunk_index,
                    char_start=getattr(sem_chunk, 'char_start', 0),
                    char_end=getattr(sem_chunk, 'char_end', len(content)),
                ))
                chunk_index += 1
            else:
                # Split into multiple scenes
                sub_scenes = self._split_into_scenes(content, title)
                for scene in sub_scenes:
                    scene.index = chunk_index
                    cinematic_chunks.append(scene)
                    chunk_index += 1
        
        # Step 3: Finalize - add context and counts
        total_chunks = len(cinematic_chunks)
        for i, chunk in enumerate(cinematic_chunks):
            chunk.total_chunks = total_chunks
            chunk.index = i
            
            # Add context for continuity
            if i > 0:
                prev_text = cinematic_chunks[i - 1].text
                chunk.previous_summary = prev_text[-200:] + "..." if len(prev_text) > 200 else prev_text
            
            if i < total_chunks - 1:
                next_text = cinematic_chunks[i + 1].text
                chunk.next_preview = next_text[:200] + "..." if len(next_text) > 200 else next_text
        
        logger.info(f"CinemaChunker produced {len(cinematic_chunks)} scene-optimized chunks")
        return cinematic_chunks
    
    def _split_into_scenes(self, text: str, chapter_title: Optional[str] = None) -> List[CinematicChunk]:
        """
        Split a large text block into scene-sized chunks.
        
        Tries to split at natural boundaries:
        1. Scene breaks (*** or ---)
        2. Double newlines (paragraphs)
        3. Sentence boundaries
        """
        scenes = []
        
        # Look for explicit scene breaks
        scene_break_pattern = r'\n\s*(?:\*{3,}|-{3,}|#{3,})\s*\n'
        explicit_scenes = re.split(scene_break_pattern, text)
        
        if len(explicit_scenes) > 1:
            # Has explicit scene breaks
            for i, scene_text in enumerate(explicit_scenes):
                scene_text = scene_text.strip()
                if not scene_text:
                    continue
                    
                # Check if scene needs further splitting
                if len(scene_text.split()) > self.SCENE_MAX_WORDS:
                    sub_scenes = self._split_by_paragraphs(scene_text, chapter_title)
                    scenes.extend(sub_scenes)
                else:
                    scenes.append(CinematicChunk(
                        chunk_id=f"scene_{uuid.uuid4().hex[:8]}",
                        text=scene_text,
                        chapter_title=chapter_title,
                        section_title=f"Scene {i + 1}" if len(explicit_scenes) > 1 else None,
                    ))
        else:
            # No explicit breaks, split by paragraphs
            scenes = self._split_by_paragraphs(text, chapter_title)
        
        return scenes
    
    def _split_by_paragraphs(self, text: str, chapter_title: Optional[str] = None) -> List[CinematicChunk]:
        """Split text by paragraphs, combining small ones."""
        paragraphs = re.split(r'\n\s*\n', text)
        scenes = []
        current_scene_parts = []
        current_word_count = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_word_count = len(para.split())
            
            # Check if adding this paragraph exceeds target
            if current_word_count + para_word_count > self.SCENE_TARGET_WORDS and current_scene_parts:
                # Save current scene
                scene_text = '\n\n'.join(current_scene_parts)
                scenes.append(CinematicChunk(
                    chunk_id=f"scene_{uuid.uuid4().hex[:8]}",
                    text=scene_text,
                    chapter_title=chapter_title,
                ))
                current_scene_parts = [para]
                current_word_count = para_word_count
            else:
                current_scene_parts.append(para)
                current_word_count += para_word_count
        
        # Add remaining content
        if current_scene_parts:
            scene_text = '\n\n'.join(current_scene_parts)
            scenes.append(CinematicChunk(
                chunk_id=f"scene_{uuid.uuid4().hex[:8]}",
                text=scene_text,
                chapter_title=chapter_title,
            ))
        
        return scenes
    
    def _simple_chunk(self, text: str) -> List:
        """Fallback chunking when SemanticChunker is not available."""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if current_size + para_size > self.SCENE_TARGET_CHARS and current_chunk:
                # Create chunk object mimicking SemanticChunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(type('SimpleChunk', (), {
                    'content': chunk_text,
                    'title': None,
                    'char_start': 0,
                    'char_end': len(chunk_text),
                })())
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(type('SimpleChunk', (), {
                'content': chunk_text,
                'title': None,
                'char_start': 0,
                'char_end': len(chunk_text),
            })())
        
        return chunks
    
    def estimate_video_duration(self, chunk: CinematicChunk) -> int:
        """
        Estimate video duration for a chunk in seconds.
        
        Heuristic: ~100 words = 30 seconds of video
        """
        words = chunk.word_count
        # Approximately 3-4 words per second of narration/action
        seconds = words // 3
        # Clamp to reasonable range
        return max(10, min(seconds, 180))  # 10s - 3 min
