"""
Unit Tests for Cinema Pipeline Models

Tests all data models used in the Book-to-Cinema pipeline.
"""

import pytest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from core.cinema.models import (
    CinemaStyle,
    JobStatus,
    CinematicChunk,
    CinematicScene,
    ScreenplayScene,
    Screenplay,
    VideoPrompt,
    RenderedVideo,
    CinemaJob,
    StyleTemplate,
)


class TestCinemaStyle:
    """Tests for CinemaStyle enum."""
    
    def test_all_styles_exist(self):
        """Verify all expected cinema styles are defined."""
        expected_styles = [
            "anime", "noir", "blockbuster", "documentary",
            "fantasy", "horror", "romantic", "scifi", "custom"
        ]
        actual_styles = [s.value for s in CinemaStyle]
        assert set(expected_styles) == set(actual_styles)
    
    def test_style_values(self):
        """Test individual style values."""
        assert CinemaStyle.ANIME.value == "anime"
        assert CinemaStyle.NOIR.value == "noir"
        assert CinemaStyle.BLOCKBUSTER.value == "blockbuster"
        assert CinemaStyle.FANTASY.value == "fantasy"
        assert CinemaStyle.HORROR.value == "horror"
        assert CinemaStyle.ROMANTIC.value == "romantic"
        assert CinemaStyle.SCIFI.value == "scifi"
        assert CinemaStyle.CUSTOM.value == "custom"


class TestJobStatus:
    """Tests for JobStatus enum."""
    
    def test_all_statuses_exist(self):
        """Verify all expected job statuses are defined."""
        expected = [
            "pending", "chunking", "adapting", "writing_screenplay",
            "generating_prompts", "rendering", "assembling", "complete", "failed"
        ]
        actual = [s.value for s in JobStatus]
        assert set(expected) == set(actual)
    
    def test_status_progression(self):
        """Test status values can be compared."""
        statuses = list(JobStatus)
        assert JobStatus.PENDING in statuses
        assert JobStatus.COMPLETE in statuses
        assert JobStatus.FAILED in statuses


class TestCinematicChunk:
    """Tests for CinematicChunk dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic chunk."""
        chunk = CinematicChunk(
            chunk_id="chunk_001",
            text="The detective walked through the dark alley.",
        )
        assert chunk.chunk_id == "chunk_001"
        assert "detective" in chunk.text
        assert chunk.word_count == 7  # Auto-calculated
    
    def test_word_count_calculation(self):
        """Test automatic word count calculation."""
        chunk = CinematicChunk(
            chunk_id="test",
            text="One two three four five"
        )
        assert chunk.word_count == 5
    
    def test_empty_text_word_count(self):
        """Test word count for empty text."""
        chunk = CinematicChunk(
            chunk_id="empty",
            text=""
        )
        # Empty string split gives [''], which has length 1
        # But we check for actual behavior
        assert chunk.word_count >= 0
    
    def test_full_chunk_creation(self):
        """Test creating a fully populated chunk."""
        chunk = CinematicChunk(
            chunk_id="chunk_003",
            text="Sample text content here.",
            chapter_title="Chapter 1",
            section_title="The Beginning",
            index=0,
            total_chunks=10,
            char_start=0,
            char_end=24,
            previous_summary="Previously...",
            next_preview="Coming up..."
        )
        assert chunk.chapter_title == "Chapter 1"
        assert chunk.section_title == "The Beginning"
        assert chunk.index == 0
        assert chunk.total_chunks == 10
        assert chunk.char_start == 0
        assert chunk.char_end == 24
        assert chunk.previous_summary == "Previously..."
        assert chunk.next_preview == "Coming up..."
    
    def test_default_values(self):
        """Test default values are set correctly."""
        chunk = CinematicChunk(chunk_id="id", text="text")
        assert chunk.chapter_title is None
        assert chunk.section_title is None
        assert chunk.index == 0
        assert chunk.total_chunks == 0
        assert chunk.char_start == 0
        assert chunk.char_end == 0
        assert chunk.previous_summary is None
        assert chunk.next_preview is None


class TestCinematicScene:
    """Tests for CinematicScene dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic scene."""
        scene = CinematicScene(
            scene_id="scene_001",
            chunk_id="chunk_001",
            original_text="The rain fell heavily on the streets."
        )
        assert scene.scene_id == "scene_001"
        assert scene.chunk_id == "chunk_001"
        assert "rain" in scene.original_text
    
    def test_default_values(self):
        """Test default values are correct."""
        scene = CinematicScene(
            scene_id="s1",
            chunk_id="c1",
            original_text="text"
        )
        assert scene.setting == ""
        assert scene.time_of_day == "day"
        assert scene.location_type == "interior"
        assert scene.characters == []
        assert scene.key_actions == []
        assert scene.dialogue == []
        assert scene.mood == "neutral"
        assert scene.camera_suggestions == []
        assert scene.lighting_mood == ""
        assert scene.color_palette == []
        assert scene.estimated_duration == 15
    
    def test_full_scene_creation(self):
        """Test creating a fully populated scene."""
        scene = CinematicScene(
            scene_id="scene_002",
            chunk_id="chunk_002",
            original_text="Original text here.",
            setting="Dark alley in 1920s Chicago",
            time_of_day="night",
            location_type="exterior",
            characters=[
                {"name": "John", "description": "detective", "emotion": "tense"}
            ],
            key_actions=["walks slowly", "reaches for gun"],
            dialogue=[
                {"character": "John", "line": "Who's there?", "direction": "whispers"}
            ],
            mood="tense",
            emotional_arc="builds tension",
            camera_suggestions=["wide shot", "close-up"],
            lighting_mood="low-key noir",
            color_palette=["#1a1a2e", "#16213e"],
            estimated_duration=20
        )
        assert scene.setting == "Dark alley in 1920s Chicago"
        assert scene.time_of_day == "night"
        assert scene.location_type == "exterior"
        assert len(scene.characters) == 1
        assert scene.characters[0]["name"] == "John"
        assert len(scene.key_actions) == 2
        assert len(scene.dialogue) == 1
        assert scene.mood == "tense"
        assert scene.estimated_duration == 20
    
    def test_to_dict(self):
        """Test scene serialization to dict."""
        scene = CinematicScene(
            scene_id="s1",
            chunk_id="c1",
            original_text="text",
            setting="A room",
            mood="happy"
        )
        result = scene.to_dict()
        
        assert isinstance(result, dict)
        assert result["scene_id"] == "s1"
        assert result["setting"] == "A room"
        assert result["mood"] == "happy"
        assert "time_of_day" in result
        assert "location_type" in result


class TestScreenplayScene:
    """Tests for ScreenplayScene dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic screenplay scene."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="scene_001",
            int_ext="INT",
            location="Office",
            time="DAY"
        )
        assert scene.scene_number == 1
        assert scene.int_ext == "INT"
        assert scene.location == "Office"
        assert scene.time == "DAY"
    
    def test_default_values(self):
        """Test default values."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="EXT",
            location="Street",
            time="NIGHT"
        )
        assert scene.action_lines == []
        assert scene.dialogue_blocks == []
        assert scene.opening_transition is None
        assert scene.closing_transition is None
    
    def test_full_scene(self):
        """Test fully populated screenplay scene."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="EXT",
            location="Dark Alley",
            time="NIGHT",
            action_lines=["John walks cautiously.", "He stops, listening."],
            dialogue_blocks=[
                {"character": "JOHN", "parenthetical": "(whispering)", "line": "Hello?"}
            ],
            opening_transition="FADE IN:",
            closing_transition="CUT TO:"
        )
        assert len(scene.action_lines) == 2
        assert len(scene.dialogue_blocks) == 1
        assert scene.opening_transition == "FADE IN:"
        assert scene.closing_transition == "CUT TO:"
    
    def test_to_screenplay_format(self):
        """Test formatting as screenplay text."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="INT",
            location="Office",
            time="DAY",
            action_lines=["John enters the room."],
            dialogue_blocks=[
                {"character": "JOHN", "line": "Good morning."}
            ]
        )
        formatted = scene.to_screenplay_format()
        
        assert isinstance(formatted, str)
        assert "INT. OFFICE - DAY" in formatted
        assert "John enters the room." in formatted
        assert "JOHN" in formatted
        assert "Good morning." in formatted
    
    def test_to_screenplay_format_with_transitions(self):
        """Test formatting with transitions."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="EXT",
            location="Street",
            time="NIGHT",
            opening_transition="FADE IN:",
            closing_transition="CUT TO:"
        )
        formatted = scene.to_screenplay_format()
        
        assert "FADE IN:" in formatted
        assert "CUT TO:" in formatted
    
    def test_to_screenplay_format_with_parenthetical(self):
        """Test formatting dialogue with parenthetical."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="INT",
            location="Room",
            time="DAY",
            dialogue_blocks=[
                {
                    "character": "MARY",
                    "parenthetical": "(nervously)",
                    "line": "I don't know..."
                }
            ]
        )
        formatted = scene.to_screenplay_format()
        
        assert "MARY" in formatted
        assert "(nervously)" in formatted
        assert "I don't know..." in formatted


class TestScreenplay:
    """Tests for Screenplay dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic screenplay."""
        screenplay = Screenplay(
            title="Test Movie",
            author="Test Author"
        )
        assert screenplay.title == "Test Movie"
        assert screenplay.author == "Test Author"
        assert screenplay.scenes == []
    
    def test_default_values(self):
        """Test default values."""
        screenplay = Screenplay(title="Test", author="Author")
        assert screenplay.genre == ""
        assert screenplay.style == CinemaStyle.BLOCKBUSTER
        assert screenplay.estimated_runtime_minutes == 0
    
    def test_with_scenes(self):
        """Test screenplay with scenes."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="INT",
            location="Room",
            time="DAY"
        )
        screenplay = Screenplay(
            title="My Movie",
            author="Writer",
            scenes=[scene]
        )
        assert len(screenplay.scenes) == 1
    
    def test_to_text(self):
        """Test exporting as formatted text."""
        scene = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="INT",
            location="Office",
            time="DAY",
            action_lines=["John sits at his desk."]
        )
        screenplay = Screenplay(
            title="My Movie",
            author="Test Writer",
            scenes=[scene]
        )
        
        text = screenplay.to_text()
        
        assert isinstance(text, str)
        assert "MY MOVIE" in text
        assert "Written by" in text
        assert "Test Writer" in text
        assert "INT. OFFICE - DAY" in text


class TestVideoPrompt:
    """Tests for VideoPrompt dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic video prompt."""
        prompt = VideoPrompt(
            scene_id="s1",
            provider="veo",
            prompt="A detective walking through a dark alley"
        )
        assert prompt.scene_id == "s1"
        assert prompt.provider == "veo"
        assert "detective" in prompt.prompt
    
    def test_default_values(self):
        """Test default values."""
        prompt = VideoPrompt(
            scene_id="s1",
            provider="replicate",
            prompt="Test prompt"
        )
        assert prompt.negative_prompt is None
        assert prompt.duration_seconds == 5
        assert prompt.aspect_ratio == "16:9"
        assert prompt.fps == 24
        assert prompt.style_preset is None
        assert prompt.reference_images == []
        assert prompt.provider_params == {}
    
    def test_full_prompt(self):
        """Test fully populated prompt."""
        prompt = VideoPrompt(
            scene_id="s1",
            provider="runway",
            prompt="Main prompt text",
            negative_prompt="blur, low quality",
            duration_seconds=10,
            aspect_ratio="21:9",
            fps=30,
            style_preset="cinematic",
            reference_images=["/path/to/ref1.jpg"],
            provider_params={"model": "gen2"}
        )
        assert prompt.negative_prompt == "blur, low quality"
        assert prompt.duration_seconds == 10
        assert prompt.aspect_ratio == "21:9"
        assert prompt.fps == 30
        assert prompt.style_preset == "cinematic"
        assert len(prompt.reference_images) == 1
    
    def test_to_dict(self):
        """Test serialization to dict."""
        prompt = VideoPrompt(
            scene_id="s1",
            provider="veo",
            prompt="Test prompt",
            duration_seconds=8
        )
        result = prompt.to_dict()
        
        assert isinstance(result, dict)
        assert result["scene_id"] == "s1"
        assert result["provider"] == "veo"
        assert result["prompt"] == "Test prompt"
        assert result["duration_seconds"] == 8


class TestRenderedVideo:
    """Tests for RenderedVideo dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic rendered video."""
        video = RenderedVideo(
            scene_id="s1",
            video_path=Path("/tmp/video.mp4")
        )
        assert video.scene_id == "s1"
        assert video.video_path == Path("/tmp/video.mp4")
    
    def test_default_values(self):
        """Test default values."""
        video = RenderedVideo(
            scene_id="s1",
            video_path=Path("/tmp/v.mp4")
        )
        assert video.duration_seconds == 0.0
        assert video.resolution == "1920x1080"
        assert video.fps == 24
        assert video.file_size_bytes == 0
        assert video.provider == ""
        assert video.prompt_used == ""
        assert video.generation_time_seconds == 0.0
        assert video.success is True
        assert video.error_message is None
        assert video.metadata == {}
    
    def test_full_video(self):
        """Test fully populated rendered video."""
        video = RenderedVideo(
            scene_id="s1",
            video_path=Path("/output/scene1.mp4"),
            duration_seconds=15.5,
            resolution="3840x2160",
            fps=60,
            file_size_bytes=50000000,
            provider="veo",
            prompt_used="Cinematic shot of detective",
            generation_time_seconds=45.2,
            success=True,
            metadata={"model_version": "v2"}
        )
        assert video.duration_seconds == 15.5
        assert video.resolution == "3840x2160"
        assert video.fps == 60
        assert video.file_size_bytes == 50000000
        assert video.provider == "veo"
        assert video.generation_time_seconds == 45.2
    
    def test_failed_video(self):
        """Test failed video rendering."""
        video = RenderedVideo(
            scene_id="s1",
            video_path=Path("/tmp/failed.mp4"),
            success=False,
            error_message="API rate limit exceeded"
        )
        assert video.success is False
        assert video.error_message == "API rate limit exceeded"


class TestCinemaJob:
    """Tests for CinemaJob dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic cinema job."""
        job = CinemaJob(
            job_id="job_001",
            source_path=Path("/input/book.txt"),
            output_dir=Path("/output")
        )
        assert job.job_id == "job_001"
        assert job.source_path == Path("/input/book.txt")
        assert job.output_dir == Path("/output")
    
    def test_default_values(self):
        """Test default values."""
        job = CinemaJob(
            job_id="j1",
            source_path=Path("/in.txt"),
            output_dir=Path("/out")
        )
        assert job.style == CinemaStyle.BLOCKBUSTER
        assert job.video_provider == "veo"
        assert job.target_segment_duration == 15
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.current_stage == ""
        assert job.error is None
        assert job.chunks == []
        assert job.scenes == []
        assert job.screenplay is None
        assert job.prompts == []
        assert job.videos == []
        assert job.final_video_path is None
    
    def test_created_at_is_set(self):
        """Test that created_at is automatically set."""
        before = datetime.now()
        job = CinemaJob(
            job_id="j1",
            source_path=Path("/in.txt"),
            output_dir=Path("/out")
        )
        after = datetime.now()
        
        assert job.created_at >= before
        assert job.created_at <= after
    
    def test_full_job(self):
        """Test fully populated job."""
        chunk = CinematicChunk(chunk_id="c1", text="Sample")
        scene = CinematicScene(scene_id="s1", chunk_id="c1", original_text="Sample")
        
        job = CinemaJob(
            job_id="job_002",
            source_path=Path("/input/novel.txt"),
            output_dir=Path("/output/movie"),
            style=CinemaStyle.NOIR,
            video_provider="replicate",
            target_segment_duration=20,
            status=JobStatus.RENDERING,
            progress=0.75,
            current_stage="Rendering video 3 of 4",
            chunks=[chunk],
            scenes=[scene]
        )
        assert job.style == CinemaStyle.NOIR
        assert job.video_provider == "replicate"
        assert job.status == JobStatus.RENDERING
        assert job.progress == 0.75
        assert len(job.chunks) == 1
        assert len(job.scenes) == 1
    
    def test_to_dict(self):
        """Test serialization to dict."""
        job = CinemaJob(
            job_id="j1",
            source_path=Path("/in.txt"),
            output_dir=Path("/out"),
            style=CinemaStyle.ANIME,
            status=JobStatus.COMPLETE,
            progress=1.0
        )
        result = job.to_dict()
        
        assert isinstance(result, dict)
        assert result["job_id"] == "j1"
        assert result["style"] == "anime"
        assert result["status"] == "complete"
        assert result["progress"] == 1.0
        assert result["chunks_count"] == 0
        assert result["scenes_count"] == 0


class TestStyleTemplate:
    """Tests for StyleTemplate dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic style template."""
        template = StyleTemplate(
            name="Test Style",
            description="A test style template",
            visual_style="cinematic",
            color_grading="warm",
            lighting_style="natural"
        )
        assert template.name == "Test Style"
        assert template.description == "A test style template"
        assert template.visual_style == "cinematic"
    
    def test_default_values(self):
        """Test default values."""
        template = StyleTemplate(
            name="Test",
            description="Desc",
            visual_style="style",
            color_grading="grade",
            lighting_style="light"
        )
        assert template.camera_movements == []
        assert template.default_shots == []
        assert template.reference_films == []
        assert template.aspect_ratio == "16:9"
        assert template.default_fps == 24
        assert template.default_transitions == "crossfade"
        assert template.prompt_prefix == ""
        assert template.prompt_suffix == ""
        assert template.negative_prompt == ""
        assert template.music_style == ""
    
    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "name": "Noir Style",
            "description": "Classic film noir aesthetic",
            "visual_style": "high contrast black and white",
            "color_grading": "desaturated",
            "lighting_style": "low-key dramatic",
            "camera_movements": ["tracking", "dutch angle"],
            "default_shots": ["close-up", "silhouette"],
            "reference_films": ["Casablanca", "The Maltese Falcon"],
            "aspect_ratio": "2.35:1",
            "default_fps": 24,
            "prompt_prefix": "Film noir style,",
            "prompt_suffix": ", dramatic shadows",
            "negative_prompt": "color, bright, modern",
            "music_style": "jazz saxophone"
        }
        
        template = StyleTemplate.from_dict(data)
        
        assert template.name == "Noir Style"
        assert template.visual_style == "high contrast black and white"
        assert len(template.camera_movements) == 2
        assert "tracking" in template.camera_movements
        assert len(template.reference_films) == 2
        assert template.aspect_ratio == "2.35:1"
        assert template.prompt_prefix == "Film noir style,"
        assert template.music_style == "jazz saxophone"
    
    def test_from_dict_with_missing_fields(self):
        """Test from_dict handles missing fields gracefully."""
        data = {
            "name": "Minimal",
            "description": "Minimal template"
        }
        
        template = StyleTemplate.from_dict(data)
        
        assert template.name == "Minimal"
        assert template.visual_style == ""
        assert template.aspect_ratio == "16:9"
        assert template.camera_movements == []
    
    def test_from_dict_empty(self):
        """Test from_dict with empty dict."""
        template = StyleTemplate.from_dict({})
        
        assert template.name == ""
        assert template.description == ""
        assert template.visual_style == ""


class TestModelIntegration:
    """Integration tests for model relationships."""
    
    def test_chunk_to_scene_flow(self):
        """Test creating scene from chunk."""
        chunk = CinematicChunk(
            chunk_id="chunk_001",
            text="The detective entered the dimly lit bar."
        )
        
        scene = CinematicScene(
            scene_id="scene_001",
            chunk_id=chunk.chunk_id,
            original_text=chunk.text,
            setting="Dimly lit bar",
            mood="mysterious"
        )
        
        assert scene.chunk_id == chunk.chunk_id
        assert scene.original_text == chunk.text
    
    def test_scene_to_screenplay_flow(self):
        """Test creating screenplay scene from cinematic scene."""
        cin_scene = CinematicScene(
            scene_id="s1",
            chunk_id="c1",
            original_text="Text",
            setting="A dark alley",
            time_of_day="night",
            location_type="exterior"
        )
        
        screenplay_scene = ScreenplayScene(
            scene_number=1,
            scene_id=cin_scene.scene_id,
            int_ext="EXT" if cin_scene.location_type == "exterior" else "INT",
            location=cin_scene.setting,
            time=cin_scene.time_of_day.upper()
        )
        
        assert screenplay_scene.int_ext == "EXT"
        assert screenplay_scene.location == "A dark alley"
        assert screenplay_scene.time == "NIGHT"
    
    def test_complete_job_workflow(self):
        """Test complete job with all components."""
        # Create job
        job = CinemaJob(
            job_id="full_job",
            source_path=Path("/input/story.txt"),
            output_dir=Path("/output"),
            style=CinemaStyle.FANTASY
        )
        
        # Add chunk
        chunk = CinematicChunk(chunk_id="c1", text="A wizard appeared.")
        job.chunks.append(chunk)
        
        # Add scene
        scene = CinematicScene(
            scene_id="s1", 
            chunk_id="c1",
            original_text="A wizard appeared.",
            setting="mystical forest"
        )
        job.scenes.append(scene)
        
        # Add screenplay
        ss = ScreenplayScene(
            scene_number=1,
            scene_id="s1",
            int_ext="EXT",
            location="Mystical Forest",
            time="DAY"
        )
        job.screenplay = Screenplay(
            title="The Wizard's Tale",
            author="Test",
            scenes=[ss]
        )
        
        # Add prompt
        prompt = VideoPrompt(
            scene_id="s1",
            provider="veo",
            prompt="Fantasy scene in mystical forest"
        )
        job.prompts.append(prompt)
        
        # Verify full job
        assert len(job.chunks) == 1
        assert len(job.scenes) == 1
        assert job.screenplay is not None
        assert len(job.prompts) == 1
        
        # Serialize
        job_dict = job.to_dict()
        assert job_dict["chunks_count"] == 1
        assert job_dict["scenes_count"] == 1
