# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""Frontend-facing models used by the Streamlit application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .profiles import Division, Profile, ProfileRules


@dataclass(frozen=True)
class SelectionContext:
    category: Profile
    profile: ProfileRules
    division: Division
    source_name: str
