"""Copyright (c) 2026 norangecarrot.

All Rights Reserved.
Licensed under the MIT.
"""

import json
from pathlib import Path

import pytest

from src.catalog_common import find_code_gaps

CATALOG_JSON_PATH = Path(__file__).resolve().parents[2] / "src" / "data" / "catalog.json"


def test_find_code_gaps_detects_missing_number():
    codes = ["F79", "F80", "F82", "F83"]
    assert find_code_gaps(codes) == {"F": [81]}


def test_find_code_gaps_no_gaps_for_consecutive_numbers():
    codes = ["F1", "F2", "F3", "S1", "S2"]
    assert find_code_gaps(codes) == {}


def test_find_code_gaps_ignores_variant_suffixes_and_combined_codes():
    codes = ["DL1/ADL1", "DL1a", "DL1b", "DL1c", "ADL1a", "ADL1b", "ADL1c", "DL2/ADL2"]
    assert find_code_gaps(codes) == {}


@pytest.mark.skipif(
    not CATALOG_JSON_PATH.exists(),
    reason="catalog.json is a generated artifact and requires the source PDF",
)
def test_generated_catalog_has_no_code_gaps():
    payload = json.loads(CATALOG_JSON_PATH.read_text(encoding="utf-8"))
    codes = [element["code_number"] for element in payload["elements"]]
    assert find_code_gaps(codes) == {}
