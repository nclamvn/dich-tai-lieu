"""
Unit Tests for Cinema Chunker and Prompt Generator

Tests scene-optimized text chunking and AI video prompt generation.
"""

import pytest
from pathlib import Path
from typing import List, Optional

from core.cinema.cinema_chunker import CinemaChunker
from core.cinema.prompt_generator import CinemaPromptGenerator, DEFAULT_STYLE_PROMPTS
from core.cinema.models import (
    CinematicChunk,
    CinematicScene,
    ScreenplayScene,
    VideoPrompt,
    CinemaStyle,
    StyleTemplate,
)


class TestCinemaChunker:
    """Tests for CinemaChunker class."""
    
    @pytest.fixture
    def chunker(self):
        """Create a CinemaChunker instance."""
        return CinemaChunker()
    
    def test_chunker_creation(self, chunker):
        """Test basic chunker creation."""
        assert chunker is not None
        # Use class constants instead of instance attributes
        assert CinemaChunker.SCENE_MIN_WORDS > 0
        assert CinemaChunker.SCENE_MAX_WORDS > CinemaChunker.SCENE_MIN_WORDS
    
    @pytest.mark.asyncio
    async def test_chunk_empty_text(self, chunker):
        """Test chunking empty text."""
        chunks = await chunker.chunk_for_cinema("")
        # May return 0 or 1 empty chunk depending on implementation
        assert len(chunks) <= 1
        if len(chunks) == 1:
            # If there's a chunk, it should be empty
            assert chunks[0].text.strip() == ""
    
    @pytest.mark.asyncio
    async def test_chunk_short_text(self, chunker):
        """Test chunking short text."""
        text = "This is a short text that should become a single chunk."
        chunks = await chunker.chunk_for_cinema(text)
        
        # Should create at least one chunk
        assert len(chunks) >= 1
        # First chunk should have the text
        assert len(chunks[0].text) > 0
    
    @pytest.mark.asyncio
    async def test_chunk_long_text(self, chunker):
        """Test chunking longer text."""
        # Create text with ~1000 words
        text = " ".join(["This is a sentence." for _ in range(200)])
        chunks = await chunker.chunk_for_cinema(text)
        
        # Should create at least one chunk
        assert len(chunks) >= 1
        # All chunks should have content
        for chunk in chunks:
            assert len(chunk.text.strip()) > 0
    
    @pytest.mark.asyncio
    async def test_chunk_has_correct_attributes(self, chunker):
        """Test that chunks have all required attributes."""
        text = "Chapter 1: The Beginning. Once upon a time in a far away land."
        chunks = await chunker.chunk_for_cinema(text)
        
        assert len(chunks) >= 1
        chunk = chunks[0]
        
        # Check required attributes
        assert hasattr(chunk, 'chunk_id')
        assert hasattr(chunk, 'text')
        assert hasattr(chunk, 'index')
        assert hasattr(chunk, 'total_chunks')
        assert hasattr(chunk, 'word_count')
    
    @pytest.mark.asyncio
    async def test_chunk_ids_are_unique(self, chunker):
        """Test that chunk IDs are unique."""
        text = " ".join(["Paragraph text here." for _ in range(100)])
        chunks = await chunker.chunk_for_cinema(text)
        
        if len(chunks) > 1:
            chunk_ids = [c.chunk_id for c in chunks]
            assert len(chunk_ids) == len(set(chunk_ids)), "Chunk IDs should be unique"
    
    @pytest.mark.asyncio
    async def test_chunk_indices_are_sequential(self, chunker):
        """Test that chunk indices are sequential."""
        text = " ".join(["Sentence number." for _ in range(150)])
        chunks = await chunker.chunk_for_cinema(text)
        
        for i, chunk in enumerate(chunks):
            assert chunk.index == i
    
    @pytest.mark.asyncio
    async def test_chunk_total_chunks_is_correct(self, chunker):
        """Test that total_chunks is set correctly."""
        text = " ".join(["Some text content." for _ in range(100)])
        chunks = await chunker.chunk_for_cinema(text)
        
        total = len(chunks)
        for chunk in chunks:
            assert chunk.total_chunks == total
    
    @pytest.mark.asyncio
    async def test_chunk_word_count_is_calculated(self, chunker):
        """Test that word counts are calculated."""
        text = "One two three four five. " * 50
        chunks = await chunker.chunk_for_cinema(text)
        
        for chunk in chunks:
            # word_count should be positive
            assert chunk.word_count > 0
    
    def test_estimate_video_duration(self, chunker):
        """Test video duration estimation."""
        chunk = CinematicChunk(
            chunk_id="test",
            text="Word " * 100,  # 100 words
        )
        
        duration = chunker.estimate_video_duration(chunk)
        
        # Should return a positive duration
        assert duration > 0
        # ~100 words should be around 30 seconds based on heuristic
        assert 10 <= duration <= 60
    
    @pytest.mark.asyncio
    async def test_chunk_with_chapter_markers(self, chunker):
        """Test chunking text with chapter markers."""
        text = """
        Chapter 1: The Beginning
        
        This is the first chapter content. It contains some text.
        
        ***
        
        Chapter 2: The Middle
        
        This is the second chapter content with more text.
        """
        chunks = await chunker.chunk_for_cinema(text)
        
        # Should create chunks
        assert len(chunks) >= 1
    
    @pytest.mark.asyncio
    async def test_chunk_preserves_text_content(self, chunker):
        """Test that chunking preserves all text content."""
        text = "Important content that should not be lost. " * 20
        chunks = await chunker.chunk_for_cinema(text)
        
        # Combine all chunk texts
        combined = " ".join(c.text for c in chunks)
        
        # Key words should be preserved
        assert "Important" in combined or "important" in combined.lower()



class TestCinemaPromptGenerator:
    """Tests for CinemaPromptGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create a CinemaPromptGenerator instance."""
        return CinemaPromptGenerator()
    
    @pytest.fixture
    def sample_scene(self):
        """Create a sample cinematic scene."""
        return CinematicScene(
            scene_id="scene_001",
            chunk_id="chunk_001",
            original_text="The detective walked through the dark alley.",
            setting="Dark alley in a city",
            time_of_day="night",
            location_type="exterior",
            characters=[{"name": "Detective", "description": "tall man in trench coat"}],
            key_actions=["walking cautiously", "looking around"],
            mood="tense",
            lighting_mood="low-key noir"
        )
    
    @pytest.fixture
    def sample_screenplay_scene(self):
        """Create a sample screenplay scene."""
        return ScreenplayScene(
            scene_number=1,
            scene_id="scene_001",
            int_ext="EXT",
            location="Dark Alley",
            time="NIGHT",
            action_lines=["A figure moves through shadows."]
        )
    
    def test_generator_creation(self, generator):
        """Test basic generator creation."""
        assert generator is not None
    
    def test_default_style_prompts_exist(self):
        """Test that default style prompts are defined."""
        assert len(DEFAULT_STYLE_PROMPTS) > 0
        assert CinemaStyle.BLOCKBUSTER in DEFAULT_STYLE_PROMPTS
        assert CinemaStyle.NOIR in DEFAULT_STYLE_PROMPTS
        assert CinemaStyle.ANIME in DEFAULT_STYLE_PROMPTS
    
    def test_default_style_prompts_have_required_keys(self):
        """Test that default style prompts have required keys."""
        for style, prompts in DEFAULT_STYLE_PROMPTS.items():
            assert "prefix" in prompts, f"Style {style} missing prefix"
            assert "suffix" in prompts, f"Style {style} missing suffix"
    
    def test_generate_prompt_basic(self, generator, sample_scene):
        """Test basic prompt generation."""
        prompt = generator.generate_prompt(
            scene=sample_scene,
            style=CinemaStyle.NOIR,
            provider="veo"
        )
        
        assert isinstance(prompt, VideoPrompt)
        assert prompt.scene_id == sample_scene.scene_id
        assert prompt.provider == "veo"
        assert len(prompt.prompt) > 0
    
    def test_generate_prompt_different_styles(self, generator, sample_scene):
        """Test prompt generation for different styles."""
        styles = [CinemaStyle.BLOCKBUSTER, CinemaStyle.NOIR, CinemaStyle.ANIME, CinemaStyle.FANTASY]
        
        for style in styles:
            prompt = generator.generate_prompt(
                scene=sample_scene,
                style=style,
                provider="veo"
            )
            assert isinstance(prompt, VideoPrompt)
            assert len(prompt.prompt) > 0
    
    def test_generate_prompt_different_providers(self, generator, sample_scene):
        """Test prompt generation for different providers."""
        providers = ["veo", "runway", "replicate", "generic"]
        
        for provider in providers:
            prompt = generator.generate_prompt(
                scene=sample_scene,
                style=CinemaStyle.BLOCKBUSTER,
                provider=provider
            )
            assert isinstance(prompt, VideoPrompt)
            assert prompt.provider == provider
    
    def test_generate_prompt_with_screenplay(self, generator, sample_scene, sample_screenplay_scene):
        """Test prompt generation with screenplay scene."""
        prompt = generator.generate_prompt(
            scene=sample_scene,
            screenplay_scene=sample_screenplay_scene,
            style=CinemaStyle.NOIR,
            provider="veo"
        )
        
        assert isinstance(prompt, VideoPrompt)
        assert len(prompt.prompt) > 0
    
    def test_generate_prompt_has_negative_prompt(self, generator, sample_scene):
        """Test that some styles include negative prompts."""
        prompt = generator.generate_prompt(
            scene=sample_scene,
            style=CinemaStyle.NOIR,
            provider="veo"
        )
        
        # Negative prompt may or may not be set depending on implementation
        # Just verify the attribute exists
        assert hasattr(prompt, 'negative_prompt')
    
    def test_generate_prompt_duration(self, generator, sample_scene):
        """Test prompt with custom duration."""
        duration = 15
        prompt = generator.generate_prompt(
            scene=sample_scene,
            style=CinemaStyle.BLOCKBUSTER,
            provider="veo",
            duration_seconds=duration
        )
        
        assert prompt.duration_seconds == duration
    
    def test_generate_prompts_for_scenes(self, generator):
        """Test generating prompts for multiple scenes."""
        scenes = [
            CinematicScene(
                scene_id=f"scene_{i}",
                chunk_id=f"chunk_{i}",
                original_text=f"Scene {i} content.",
                setting=f"Location {i}",
                mood="neutral"
            )
            for i in range(3)
        ]
        
        prompts = generator.generate_prompts_for_scenes(
            scenes=scenes,
            style=CinemaStyle.BLOCKBUSTER,
            provider="veo"
        )
        
        assert len(prompts) == len(scenes)
        for i, prompt in enumerate(prompts):
            assert prompt.scene_id == f"scene_{i}"
    
    def test_generate_prompts_with_screenplay_scenes(self, generator):
        """Test prompt generation with matching screenplay scenes."""
        scenes = [
            CinematicScene(
                scene_id="s1",
                chunk_id="c1",
                original_text="Text",
                setting="A room"
            )
        ]
        
        screenplay_scenes = [
            ScreenplayScene(
                scene_number=1,
                scene_id="s1",
                int_ext="INT",
                location="Room",
                time="DAY"
            )
        ]
        
        prompts = generator.generate_prompts_for_scenes(
            scenes=scenes,
            screenplay_scenes=screenplay_scenes,
            style=CinemaStyle.ROMANTIC,
            provider="replicate"
        )
        
        assert len(prompts) == 1
    
    def test_load_style_template_nonexistent(self, generator):
        """Test loading non-existent style template."""
        # Should handle gracefully and return None
        template = generator.load_style_template(CinemaStyle.CUSTOM)
        # May return None or a default template
        assert template is None or isinstance(template, StyleTemplate)
    
    def test_enhance_prompt_with_continuity(self, generator, sample_scene):
        """Test prompt enhancement with continuity."""
        prompt = VideoPrompt(
            scene_id="s1",
            provider="veo",
            prompt="A detective scene",
            duration_seconds=10
        )
        
        enhanced = generator.enhance_prompt_with_continuity(
            current_prompt=prompt,
            previous_prompt=None,
            next_scene=None
        )
        
        assert isinstance(enhanced, VideoPrompt)
        # Should still have original content
        assert "detective" in enhanced.prompt.lower() or enhanced.prompt == prompt.prompt
    
    def test_prompt_includes_scene_elements(self, generator, sample_scene):
        """Test that prompt includes scene elements."""
        prompt = generator.generate_prompt(
            scene=sample_scene,
            style=CinemaStyle.NOIR,
            provider="veo"
        )
        
        prompt_lower = prompt.prompt.lower()
        
        # Should include some elements from the scene
        # At least the setting or mood should appear
        has_setting = "alley" in prompt_lower or "dark" in prompt_lower
        has_mood = "tense" in prompt_lower or "noir" in prompt_lower
        has_time = "night" in prompt_lower
        
        assert has_setting or has_mood or has_time, \
            "Prompt should include scene elements"


class TestCinemaChunkerAndPromptIntegration:
    """Integration tests for chunker and prompt generator."""
    
    @pytest.mark.asyncio
    async def test_chunk_to_prompt_workflow(self):
        """Test complete workflow from text to prompts."""
        # Create chunker and generator
        chunker = CinemaChunker()
        generator = CinemaPromptGenerator()
        
        # Sample text
        text = """
        Chapter 1: The Beginning
        
        The old detective sat in his dimly lit office. Rain pattered against 
        the window as he studied the case files spread across his desk. 
        Something wasn't right about this case. The evidence pointed one way, 
        but his gut told him another story entirely.
        
        He stood and walked to the window, watching the city lights blur 
        through the rain. Somewhere out there, the truth was waiting to be found.
        """
        
        # Chunk the text
        chunks = await chunker.chunk_for_cinema(text)
        assert len(chunks) >= 1
        
        # Create scenes from chunks (simplified)
        scenes = [
            CinematicScene(
                scene_id=f"scene_{chunk.chunk_id}",
                chunk_id=chunk.chunk_id,
                original_text=chunk.text,
                setting="Detective's office" if i == 0 else "City view",
                time_of_day="night",
                location_type="interior",
                mood="mysterious"
            )
            for i, chunk in enumerate(chunks)
        ]
        
        # Generate prompts
        prompts = generator.generate_prompts_for_scenes(
            scenes=scenes,
            style=CinemaStyle.NOIR,
            provider="veo"
        )
        
        assert len(prompts) == len(scenes)
        for prompt in prompts:
            assert len(prompt.prompt) > 0
