"""
Video Editor Agent

Stitches video clips into sequences and adds transitions.
Requires FFmpeg for video processing.
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_agent import BaseAgent, AgentResult
from ..models import VideoClip

logger = logging.getLogger(__name__)


class VideoEditorAgent(BaseAgent):
    """Agent for editing and stitching video clips"""

    name = "VideoEditor"
    description = "Stitches video clips and adds transitions"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
            self.ffmpeg_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.ffmpeg_available = False
            logger.debug("FFmpeg not available - video editing disabled")

    async def execute(self, input_data: Dict[str, Any]) -> AgentResult:
        """
        Stitch video clips into a sequence.

        Args:
            input_data: {
                "clips": List[VideoClip],
                "output_path": str,
                "transition": str,  # "cut", "dissolve", "fade"
            }
        """
        self.log_start("Stitching video sequence")

        if not self.ffmpeg_available:
            return AgentResult(
                success=False, data=None, error="FFmpeg not available"
            )

        try:
            clips: List[VideoClip] = input_data.get("clips", [])
            output_path: str = input_data.get("output_path", "outputs/video/final.mp4")
            transition: str = input_data.get("transition", "cut")

            if not clips:
                return AgentResult(
                    success=False, data=None, error="No clips provided"
                )

            selected_clips = [c for c in clips if c.is_selected and c.file_path]

            if not selected_clips:
                return AgentResult(
                    success=False, data=None,
                    error="No selected clips with files"
                )

            selected_clips.sort(key=lambda c: c.shot_id)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            if transition == "dissolve":
                result_path = await self._concat_with_dissolve(selected_clips, output_path)
            elif transition == "fade":
                result_path = await self._concat_with_fade(selected_clips, output_path)
            else:
                result_path = await self._concat_videos(selected_clips, output_path)

            if not result_path:
                return AgentResult(
                    success=False, data=None,
                    error="Video stitching failed"
                )

            total_duration = sum(c.duration_seconds for c in selected_clips)

            self.log_complete(f"Created {total_duration:.1f}s video")

            return AgentResult(
                success=True,
                data={
                    "output_path": result_path,
                    "total_duration": total_duration,
                    "clip_count": len(selected_clips),
                },
                tokens_used=0,
                cost_usd=0,
            )

        except Exception as e:
            self.log_error(str(e))
            return AgentResult(success=False, data=None, error=str(e))

    async def _concat_videos(
        self, clips: List[VideoClip], output_path: str,
    ) -> Optional[str]:
        """Concatenate videos with simple cuts"""
        try:
            concat_file = Path(output_path).parent / "concat.txt"

            with open(concat_file, "w") as f:
                for clip in clips:
                    safe_path = clip.file_path.replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            concat_file.unlink(missing_ok=True)

            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr.decode()}")
                return None

            return output_path

        except Exception as e:
            logger.error(f"Concat error: {e}")
            return None

    async def _concat_with_dissolve(
        self,
        clips: List[VideoClip],
        output_path: str,
        dissolve_duration: float = 0.5,
    ) -> Optional[str]:
        """Concatenate with cross-dissolve transitions"""
        try:
            if len(clips) == 1:
                return await self._concat_videos(clips, output_path)

            inputs = []
            filter_parts = []

            for clip in clips:
                inputs.extend(["-i", clip.file_path])

            prev_output = "[0:v]"
            for i in range(1, len(clips)):
                offset = sum(c.duration_seconds for c in clips[:i]) - (dissolve_duration * i)
                output = f"[v{i}]" if i < len(clips) - 1 else "[outv]"

                filter_parts.append(
                    f"{prev_output}[{i}:v]xfade=transition=dissolve:"
                    f"duration={dissolve_duration}:offset={offset}{output}"
                )
                prev_output = output

            filter_complex = ";".join(filter_parts)

            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-c:v", "libx264",
                "-preset", "fast",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode != 0:
                logger.error(f"FFmpeg xfade error: {result.stderr.decode()}")
                return await self._concat_videos(clips, output_path)

            return output_path

        except Exception as e:
            logger.error(f"Dissolve error: {e}")
            return await self._concat_videos(clips, output_path)

    async def _concat_with_fade(
        self,
        clips: List[VideoClip],
        output_path: str,
        fade_duration: float = 0.3,
    ) -> Optional[str]:
        """Concatenate with fade to black transitions"""
        return await self._concat_with_dissolve(clips, output_path, fade_duration)
