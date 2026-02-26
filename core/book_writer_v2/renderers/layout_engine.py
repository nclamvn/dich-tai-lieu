"""
Layout Engine (Sprint K)

Orchestrator for multi-format rendering of illustrated books.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models import BookBlueprint
from ..illustration_models import BookGenre, IllustrationPlan, LayoutConfig

logger = logging.getLogger("BookWriter.LayoutEngine")


class LayoutEngine:
    """
    Orchestrates rendering across multiple output formats.

    Usage:
        engine = LayoutEngine()
        paths = engine.render(
            blueprint=blueprint,
            plan=illustration_plan,
            image_dir="data/uploads/books/{project_id}/images",
            formats=["docx", "html", "epub"],
            output_dir=Path("output/books/{project_id}"),
        )
    """

    def render(
        self,
        blueprint: BookBlueprint,
        plan: Optional[IllustrationPlan],
        image_dir: str,
        formats: List[str],
        output_dir: Path,
        genre: BookGenre = BookGenre.NON_FICTION,
    ) -> Dict[str, str]:
        """
        Render book in requested formats.

        Returns dict mapping format name to output file path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results = {}

        config = LayoutConfig.for_genre(genre)

        def _sanitize_filename(title: str) -> str:
            """Remove filesystem-unsafe characters and normalize."""
            s = re.sub(r'[\\/:*?"<>|]', '_', title)
            s = s.replace(" ", "_")
            return s[:80]

        for fmt in formats:
            try:
                if fmt == "docx":
                    from .docx_renderer import DocxIllustratedRenderer
                    renderer = DocxIllustratedRenderer(config, genre)
                    sanitized = _sanitize_filename(blueprint.title)
                    out_path = str(output_dir / f"{sanitized}.docx")
                    results["docx"] = renderer.render(
                        blueprint, plan, image_dir, out_path
                    )
                elif fmt == "epub":
                    from .epub_renderer import EpubRenderer
                    renderer = EpubRenderer(genre)
                    path = renderer.render(blueprint, output_dir, plan)
                    results["epub"] = str(path)
                elif fmt == "pdf":
                    from .pdf_renderer import PdfIllustratedRenderer
                    renderer = PdfIllustratedRenderer(config, genre)
                    sanitized = _sanitize_filename(blueprint.title)
                    out_path = str(output_dir / f"{sanitized}.pdf")
                    results["pdf"] = renderer.render(
                        blueprint, plan, image_dir, out_path
                    )
                else:
                    logger.info(
                        f"Format '{fmt}' handled by PublisherAgent directly"
                    )
            except Exception as e:
                logger.error(f"LayoutEngine: failed to render {fmt}: {e}")

        return results
