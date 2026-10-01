# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.

"""Shared, PDF-library-free helpers used by both the extraction script and the Streamlit app."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SECTION_LABELS = {
    "SYN": "Synchronised Parallel",
    "BLN": "Balance Partner",
    "FLY": "Flying Partner",
    "PSE": "Partner Supported",
    "FLR": "Pole-Based Floor",
    "ADL": "Aerial Dead Lift",
    "DL": "Dead Lift",
    "ST": "Static Pole Spin",
    "SP": "Spinning Pole Spin",
    "F": "Flexibility",
    "S": "Strength",
}

SINGLES_PREFIXES = ("F", "S", "ST", "SP")
DOUBLES_PREFIXES = ("SYN", "BLN", "FLY", "PSE", "FLR")
CODE_FRAGMENT_RE = re.compile(r"^[A-Z]{1,4}[0-9]+[A-Z0-9/]*[a-z]?$")
VALUE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")
DEADLIFT_VARIANT_RE = re.compile(r"([abc])\s*-\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
CODE_NUMBER_RE = re.compile(r"^([A-Za-z]+)(\d+)[a-z]?$")

# Per the rules (dead lift page), the a/b/c code suffix denotes a leg position variant.
DEADLIFT_VARIANT_DESCRIPTIONS = {
    "a": "With bent legs",
    "b": "With both legs fully extended and open",
    "c": "With both legs fully extended and closed",
}


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def is_code_fragment(line: str) -> bool:
    compact = re.sub(r"\s+", "", line)
    return bool(CODE_FRAGMENT_RE.fullmatch(compact))


def prefix_for_code(code_number: str) -> str:
    for prefix in sorted(SECTION_LABELS, key=len, reverse=True):
        if code_number.startswith(prefix):
            return prefix
    match = re.match(r"[A-Z]+", code_number)
    return match.group(0) if match else "OTHER"


def section_for_code(code_number: str) -> str:
    return SECTION_LABELS.get(prefix_for_code(code_number), "Other")


def code_sort_key(code_number: str) -> tuple[str, int, str]:
    match = re.match(r"([A-Z]+)(\d+)(.*)", code_number)
    if not match:
        return (code_number, -1, "")
    prefix, number, suffix = match.groups()
    return (prefix, int(number), suffix)


def tracks_for_code(code_number: str) -> set[str]:
    prefix = prefix_for_code(code_number)
    if prefix in {"DL", "ADL"}:
        return {"Singles", "Doubles"}
    if prefix in SINGLES_PREFIXES:
        return {"Singles"}
    if prefix in DOUBLES_PREFIXES:
        return {"Doubles"}
    return {"Singles", "Doubles"}


def find_code_gaps(code_numbers: Iterable[str]) -> dict[str, list[int]]:
    """Find missing numbers within each code prefix's observed range.

    Element numbering (e.g. F1, F2, F3...) should be consecutive within a
    prefix; a hole here almost always means extraction dropped a row.
    Combined codes ("DL1/ADL1") and deadlift-style letter variants ("DL1a")
    are decomposed to their base prefix/number first.
    """
    numbers_by_prefix: dict[str, set[int]] = {}
    for code_number in code_numbers:
        for part in code_number.split("/"):
            match = CODE_NUMBER_RE.match(part)
            if not match:
                continue
            prefix, number = match.groups()
            numbers_by_prefix.setdefault(prefix, set()).add(int(number))

    gaps: dict[str, list[int]] = {}
    for prefix, numbers in numbers_by_prefix.items():
        missing = [n for n in range(min(numbers), max(numbers) + 1) if n not in numbers]
        if missing:
            gaps[prefix] = missing
    return gaps
