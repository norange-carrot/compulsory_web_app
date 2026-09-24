# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.catalog_common import prefix_for_code
from src.profile_rules import Division, Profile, ProfileRules, Track

ELITE_AERIAL_DEADLIFT_MIN_VALUE = 0.4


@dataclass(frozen=True)
class FilterCriteria:
    category: Profile
    profile: ProfileRules
    division: Division
    query: str
    sections: list[str]


def filter_records(
    records: list[dict[str, Any]],
    criteria: FilterCriteria,
) -> list[dict[str, Any]]:
    min_value, max_value = criteria.profile.divisions[criteria.division].element_range
    track = criteria.profile.track
    filtered: list[dict[str, Any]] = []

    for record in records:
        if track not in record["tracks"]:
            continue
        if criteria.sections and record["section"] not in criteria.sections:
            continue
        if record["value_max"] < min_value or record["value_min"] > max_value:
            continue

        if (
            criteria.division is Division.INTRO
            and track is Track.SINGLES
            and prefix_for_code(record["code_number"]) in {"DL", "ADL"}
            and not (
                record["code_number"].startswith("DL1") or record["code_number"].startswith("ADL9")
            )
        ):
            continue

        if (
            criteria.division is Division.ELITE
            and criteria.category
            in {Profile.SENIOR_SINGLES, Profile.MASTERS_SINGLES, Profile.SENIOR_DOUBLES}
            and prefix_for_code(record["code_number"]) in {"DL", "ADL"}
            and (
                not record["code_number"].startswith("ADL")
                or record["value_min"] < ELITE_AERIAL_DEADLIFT_MIN_VALUE
            )
        ):
            continue

        haystack = " ".join(
            [
                record["code_number"],
                record["name"],
                record["section"],
                " ".join(record["criteria_lines"]),
            ]
        ).lower()
        if criteria.query and criteria.query.lower() not in haystack:
            continue

        filtered.append(record)

    return filtered
