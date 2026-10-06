"""Copyright (c) 2026 norangecarrot.

All Rights Reserved.
Licensed under the MIT.
"""

from src.extract_catalog import expand_deadlift_variants
from src.models.catalog import CatalogRecord


def _base_deadlift_record() -> CatalogRecord:
    return CatalogRecord(
        code_number="DL1",
        name="Dead Lift",
        technical_value="a - 0.1\nb - 0.2\nc - 0.3",
        criteria="- Points of contact: both hands",
        criteria_lines=("Points of contact: both hands",),
        section="Dead Lift",
        tracks=("Singles", "Doubles"),
        page_number=101,
        value_min=0.1,
        value_max=0.3,
        image_path=None,
    )


def test_expand_deadlift_variants_keeps_name_unchanged():
    variants = expand_deadlift_variants(_base_deadlift_record())

    assert [variant.code_number for variant in variants] == ["DL1a", "DL1b", "DL1c"]
    assert all(variant.name == "Dead Lift" for variant in variants)


def test_expand_deadlift_variants_adds_variant_description():
    variants = expand_deadlift_variants(_base_deadlift_record())

    assert [variant.variant_description for variant in variants] == [
        "With bent legs",
        "With both legs fully extended and open",
        "With both legs fully extended and closed",
    ]


def test_expand_deadlift_variants_prepends_description_to_criteria():
    variants = expand_deadlift_variants(_base_deadlift_record())

    for variant in variants:
        assert variant.criteria_lines[0] == variant.variant_description
        assert variant.criteria_lines[1:] == ("Points of contact: both hands",)
        assert variant.criteria.startswith(f"- {variant.variant_description}\n")
