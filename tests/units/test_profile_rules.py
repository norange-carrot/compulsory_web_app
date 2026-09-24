"""Tests for validated competition profile configuration."""

import pytest
from pydantic import ValidationError

from src.profile_rules import PROFILE_RULES, Division, DivisionRules, Profile, Track


def test_profile_rules_are_pydantic_models():
    profile = PROFILE_RULES[Profile.SENIOR_SINGLES]

    assert profile.track is Track.SINGLES
    assert profile.divisions[Division.ELITE].element_range == (0.5, 1.0)
    assert profile.divisions[Division.ELITE].total_range == (7.7, 11.0)


def test_division_rules_reject_invalid_range_shape():
    with pytest.raises(ValidationError):
        DivisionRules(element_range=(0.1,), total_range=(0.9, 2.7))
