# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""Validated representation of a single extracted catalog element."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .profiles import Track  # noqa: TC001 -- pydantic needs this at runtime to build the schema


class CatalogRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    code_number: str
    name: str
    technical_value: str
    criteria: str
    criteria_lines: tuple[str, ...]
    section: str
    tracks: tuple[Track, ...]
    page_number: int
    value_min: float
    value_max: float
    image_path: str | None = None
    image_bytes: bytes | None = None
    variant_description: str | None = None
