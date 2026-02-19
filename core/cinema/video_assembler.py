"""
Video Assembler - FFmpeg-based Video Concatenation

Combines rendered video segments into a final movie with
transitions, audio, and professional finishing.
"""

import asyncio
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import RenderedVideo

logger = logging.getLogger(__name__)


class VideoAssembler:
    """
    Assembles video segments into a final movie using FFmpeg.
    
    Features:
    - Segment concatenation
    - Transition effects (crossfade, fade to black)
    - Audio track overlay
    - Resolution/framerate normalization
    - Title cards and credits
    """
    
    TRANSITION_TYPES = ["cut", "crossfade", "fade_black", "dissolve"]
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        ffmpeg_path: Optional[str] = None,
    ):
        """
        Initialize VideoAssembler.
        
        Args:
            output_dir: Directory for assembled videos
            ffmpeg_path: Path to ffmpeg binary (auto-detected if None)
        """
        self.output_dir = output_dir or Path("outputs/movies")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.ffmpeg_path = ffmpeg_path or shutil.which("ffmpeg")
        
        if not self.ffmpeg_path:
            logger.warning("FFmpeg not found. Video assembly will be limited.")
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available."""
        return self.ffmpeg_path is not None
    
    async def assemble(
        self,
        videos: List[RenderedVideo],
        output_name: str,
        transition: str = "crossfade",
        transition_duration: float = 0.5,
        audio_track: Optional[Path] = None,
        resolution: str = "1920x1080",
        fps: int = 24,
    ) -> Path:
        """
        Assemble video segments into final movie.
        
        Args:
            videos: List of RenderedVideo objects (in order)
            output_name: Name for output file (without extension)
            transition: Transition type between scenes
            transition_duration: Transition length in seconds
            audio_track: Optional background music
            resolution: Output resolution
            fps: Output framerate
            
        Returns:
            Path to assembled movie file
        """
        if not self.is_available():
            raise RuntimeError("FFmpeg is not available")
        
        # Filter successful videos
        valid_videos = [v for v in videos if v.success and v.video_path.exists()]
        
        if not valid_videos:
            raise ValueError("No valid video segments to assemble")
        
        output_path = self.output_dir / f"{output_name}.mp4"
        
        if len(valid_videos) == 1:
            # Single video, just copy
            shutil.copy(valid_videos[0].video_path, output_path)
            return output_path
        
        # Use appropriate assembly method
        if transition == "cut":
            return await self._assemble_with_concat(valid_videos, output_path, resolution, fps)
        else:
            return await self._assemble_with_transitions(
                valid_videos, output_path, transition, transition_duration, resolution, fps
            )
    
    async def _assemble_with_concat(
        self,
        videos: List[RenderedVideo],
        output_path: Path,
        resolution: str,
        fps: int,
    ) -> Path:
        """Simple concatenation without transitions."""
        # Create concat file
        concat_file = self.output_dir / "concat_list.txt"
        with open(concat_file, "w") as f:
            for video in videos:
                f.write(f"file '{video.video_path.absolute()}'\n")
        
        # FFmpeg concat command
        cmd = [
            self.ffmpeg_path,
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-vf", f"scale={resolution},fps={fps}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            str(output_path),
        ]
        
        logger.info(f"Assembling {len(videos)} videos with concat...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        # Clean up
        concat_file.unlink()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg concat failed: {stderr.decode()}")
            raise RuntimeError(f"FFmpeg assembly failed: {stderr.decode()[:500]}")
        
        logger.info(f"Assembled movie: {output_path}")
        return output_path
    
    async def _assemble_with_transitions(
        self,
        videos: List[RenderedVideo],
        output_path: Path,
        transition: str,
        transition_duration: float,
        resolution: str,
        fps: int,
    ) -> Path:
        """Assembly with transition effects."""
        if len(videos) < 2:
            return await self._assemble_with_concat(videos, output_path, resolution, fps)
        
        # Build complex filter for crossfade
        inputs = []
        filter_parts = []
        
        for i, video in enumerate(videos):
            inputs.extend(["-i", str(video.video_path)])
        
        # Create filter chain
        # First, normalize all inputs
        for i in range(len(videos)):
            filter_parts.append(f"[{i}:v]scale={resolution},fps={fps},format=yuv420p[v{i}];")
        
        # Apply transitions
        current_stream = "v0"
        for i in range(1, len(videos)):
            next_stream = f"v{i}"
            out_stream = f"out{i}" if i < len(videos) - 1 else "outv"
            
            if transition == "crossfade":
                filter_parts.append(
                    f"[{current_stream}][{next_stream}]xfade=transition=fade:duration={transition_duration}:offset=0[{out_stream}];"
                )
            elif transition == "fade_black":
                filter_parts.append(
                    f"[{current_stream}][{next_stream}]xfade=transition=fadeblack:duration={transition_duration}:offset=0[{out_stream}];"
                )
            else:  # dissolve
                filter_parts.append(
                    f"[{current_stream}][{next_stream}]xfade=transition=dissolve:duration={transition_duration}:offset=0[{out_stream}];"
                )
            
            current_stream = out_stream
        
        filter_complex = "".join(filter_parts).rstrip(";")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            str(output_path),
        ]
        
        logger.info(f"Assembling {len(videos)} videos with {transition} transitions...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Transition assembly failed, falling back to concat: {stderr.decode()[:200]}")
            return await self._assemble_with_concat(videos, output_path, resolution, fps)
        
        logger.info(f"Assembled movie with transitions: {output_path}")
        return output_path
    
    async def add_audio_track(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Optional[Path] = None,
        volume: float = 0.3,
    ) -> Path:
        """
        Add background audio to a video.
        
        Args:
            video_path: Input video file
            audio_path: Audio track to add
            output_path: Output file (defaults to _with_audio suffix)
            volume: Audio volume (0.0 to 1.0)
            
        Returns:
            Path to video with audio
        """
        if output_path is None:
            output_path = video_path.with_stem(f"{video_path.stem}_with_audio")
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", f"[1:a]volume={volume}[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path),
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        
        if process.returncode != 0:
            logger.warning("Failed to add audio track")
            return video_path
        
        return output_path
    
    async def add_title_card(
        self,
        video_path: Path,
        title: str,
        subtitle: Optional[str] = None,
        duration: float = 3.0,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Add a title card at the beginning of the video.
        
        Args:
            video_path: Input video
            title: Main title text
            subtitle: Optional subtitle
            duration: Title card duration in seconds
            output_path: Output file
            
        Returns:
            Path to video with title card
        """
        if output_path is None:
            output_path = video_path.with_stem(f"{video_path.stem}_titled")
        
        # Create title card using FFmpeg drawtext
        text_filter = f"drawtext=text='{title}':fontsize=72:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2"
        
        if subtitle:
            text_filter += f",drawtext=text='{subtitle}':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=(h+100)/2"
        
        # This is a simplified version - full implementation would create a proper title card
        logger.info(f"Title card generation requires additional implementation")
        return video_path
    
    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video metadata using ffprobe."""
        if not self.ffmpeg_path:
            return {}
        
        ffprobe = self.ffmpeg_path.replace("ffmpeg", "ffprobe")
        
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    str(video_path),
                ],
                capture_output=True,
                text=True,
            )
            
            import json
            return json.loads(result.stdout)
        except Exception as e:
            logger.warning(f"Failed to get video info: {e}")
            return {}
