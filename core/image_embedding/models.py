"""
Image Embedding Models - AI Publisher Pro

Data models for image extraction and embedding.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import base64


class ImageFormat(Enum):
    """Supported image formats"""
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    WEBP = "webp"
    GIF = "gif"
    TIFF = "tiff"
    BMP = "bmp"

    @classmethod
    def from_extension(cls, ext: str) -> "ImageFormat":
        """Get format from file extension"""
        ext = ext.lower().lstrip(".")
        if ext == "jpg":
            return cls.JPEG
        try:
            return cls(ext)
        except ValueError:
            return cls.PNG  # Default fallback


@dataclass
class ImagePosition:
    """Position of image in source document"""
    page: int  # 1-indexed page number
    x: float = 0.0  # X coordinate (points from left)
    y: float = 0.0  # Y coordinate (points from top)
    width: float = 0.0  # Original width in points
    height: float = 0.0  # Original height in points

    # Relative position for layout preservation
    x_ratio: float = 0.0  # 0-1, position relative to page width
    y_ratio: float = 0.0  # 0-1, position relative to page height

    def to_dict(self) -> Dict:
        return {
            "page": self.page,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "x_ratio": self.x_ratio,
            "y_ratio": self.y_ratio,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ImagePosition":
        return cls(
            page=data.get("page", 1),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 0.0),
            height=data.get("height", 0.0),
            x_ratio=data.get("x_ratio", 0.0),
            y_ratio=data.get("y_ratio", 0.0),
        )


@dataclass
class ImageBlock:
    """
    Represents an extracted image with metadata.

    This is the core data structure for image embedding.
    Contains the actual image data (bytes) plus metadata.
    """
    # Core data
    image_data: bytes  # Raw image bytes
    format: ImageFormat = ImageFormat.PNG

    # Dimensions (pixels)
    width_px: int = 0
    height_px: int = 0

    # Position in source document
    position: ImagePosition = field(default_factory=lambda: ImagePosition(page=1))

    # Metadata
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    image_id: Optional[str] = None  # Unique identifier

    # Source info
    source_page: int = 1
    source_index: int = 0  # Index within page (0-based)

    # Embedding options
    max_width_inches: float = 6.0  # Max width when embedded (80% of page)
    keep_aspect_ratio: bool = True

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_bytes(self) -> int:
        """Size of image data in bytes"""
        return len(self.image_data)

    @property
    def size_kb(self) -> float:
        """Size of image data in KB"""
        return self.size_bytes / 1024

    @property
    def aspect_ratio(self) -> float:
        """Width / Height ratio"""
        if self.height_px == 0:
            return 1.0
        return self.width_px / self.height_px

    @property
    def mime_type(self) -> str:
        """MIME type for the image"""
        mime_map = {
            ImageFormat.PNG: "image/png",
            ImageFormat.JPEG: "image/jpeg",
            ImageFormat.JPG: "image/jpeg",
            ImageFormat.WEBP: "image/webp",
            ImageFormat.GIF: "image/gif",
            ImageFormat.TIFF: "image/tiff",
            ImageFormat.BMP: "image/bmp",
        }
        return mime_map.get(self.format, "image/png")

    @property
    def file_extension(self) -> str:
        """File extension for the image"""
        if self.format == ImageFormat.JPEG:
            return "jpg"
        return self.format.value

    def to_base64(self) -> str:
        """Convert image data to base64 string"""
        return base64.b64encode(self.image_data).decode("utf-8")

    def to_data_uri(self) -> str:
        """Convert to data URI for HTML embedding"""
        return f"data:{self.mime_type};base64,{self.to_base64()}"

    def to_dict(self, include_data: bool = False) -> Dict:
        """
        Convert to dictionary.

        Args:
            include_data: If True, include base64 encoded image data
        """
        result = {
            "format": self.format.value,
            "width_px": self.width_px,
            "height_px": self.height_px,
            "position": self.position.to_dict(),
            "caption": self.caption,
            "alt_text": self.alt_text,
            "image_id": self.image_id,
            "source_page": self.source_page,
            "source_index": self.source_index,
            "size_bytes": self.size_bytes,
            "aspect_ratio": self.aspect_ratio,
            "metadata": self.metadata,
        }

        if include_data:
            result["image_data_base64"] = self.to_base64()

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> "ImageBlock":
        """Create ImageBlock from dictionary"""
        image_data = b""
        if "image_data_base64" in data:
            image_data = base64.b64decode(data["image_data_base64"])

        return cls(
            image_data=image_data,
            format=ImageFormat(data.get("format", "png")),
            width_px=data.get("width_px", 0),
            height_px=data.get("height_px", 0),
            position=ImagePosition.from_dict(data.get("position", {})),
            caption=data.get("caption"),
            alt_text=data.get("alt_text"),
            image_id=data.get("image_id"),
            source_page=data.get("source_page", 1),
            source_index=data.get("source_index", 0),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return (
            f"ImageBlock(id={self.image_id}, format={self.format.value}, "
            f"size={self.width_px}x{self.height_px}, page={self.source_page}, "
            f"data={self.size_kb:.1f}KB)"
        )
