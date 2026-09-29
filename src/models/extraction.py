# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""Context models used while extracting catalog rows from a PDF page."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from pathlib import Path

    import fitz


@dataclass
class PageExtractionContext:
    document: fitz.Document
    page: fitz.Page
    page_index: int
    images_dir: Path
    image_placements: list[dict[str, Any]]
    blocks: list[dict[str, Any]]
    starts: list[dict[str, Any]]
    criteria_anchor_tops: list[float | None]


class RowBounds(NamedTuple):
    region_top: float
    region_bottom: float
    criteria_top: float
    criteria_bottom: float
