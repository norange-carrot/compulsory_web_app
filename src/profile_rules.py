# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""Competition profile rules and their validated representations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Track(StrEnum):
    SINGLES = "Singles"
    DOUBLES = "Doubles"


class Division(StrEnum):
    INTRO = "Intro"
    AMATEUR = "Amateur"
    PROFESSIONAL = "Professional"
    ELITE = "Elite"


class Profile(StrEnum):
    SENIOR_SINGLES = "Senior Singles"
    MASTERS_SINGLES = "Masters Singles"
    JUNIOR_SINGLES = "Junior Singles"
    NOVICE_SINGLES = "Novice Singles"
    PRE_NOVICE_SINGLES = "Pre-Novice Singles"
    PARA_POLE = "Para Pole"
    SENIOR_DOUBLES = "Senior Doubles"
    JUNIOR_DOUBLES = "Junior Doubles"
    NOVICE_YOUTH_DOUBLES = "Novice/Youth Doubles"


class DivisionRules(BaseModel):
    model_config = ConfigDict(frozen=True)

    element_range: tuple[float, float]
    total_range: tuple[float, float]


class ProfileRules(BaseModel):
    """Requirements shared by every division in a competition category."""

    model_config = ConfigDict(frozen=True)

    track: Track
    required_elements: int
    requirements: tuple[str, ...]
    divisions: dict[Division, DivisionRules]
    notes: tuple[str, ...] = ()


SINGLES_REQUIREMENTS = (
    "3 flexibility elements",
    "3 strength elements",
    "1 spinning pole spin",
    "1 static pole spin",
    "1 dead lift",
)

DOUBLES_REQUIREMENTS = (
    "3 synchronised partner elements: parallel, interlocking, balance-based",
    "1 balance partner element",
    "2 flying partner elements",
    "1 partner supported element",
    "1 pole-based floor element",
    "1 synchronised dead lift",
)

INTRO_DIVISION_RULES = DivisionRules(element_range=(0.1, 0.3), total_range=(0.9, 2.7))
AMATEUR_DIVISION_RULES = DivisionRules(element_range=(0.1, 0.5), total_range=(1.1, 4.5))
PROFESSIONAL_DIVISION_RULES = DivisionRules(element_range=(0.3, 0.8), total_range=(5.5, 8.8))


PROFILE_RULES: dict[Profile, ProfileRules] = {
    Profile.SENIOR_SINGLES: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=SINGLES_REQUIREMENTS,
        divisions={
            Division.INTRO: INTRO_DIVISION_RULES,
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.PROFESSIONAL: PROFESSIONAL_DIVISION_RULES,
            Division.ELITE: DivisionRules(element_range=(0.5, 1.0), total_range=(7.7, 11.0)),
        },
        notes=(
            "Elite seniors must choose an aerial dead lift with a fourth or higher point value.",
        ),
    ),
    Profile.MASTERS_SINGLES: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=SINGLES_REQUIREMENTS,
        divisions={
            Division.INTRO: INTRO_DIVISION_RULES,
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.PROFESSIONAL: PROFESSIONAL_DIVISION_RULES,
            Division.ELITE: DivisionRules(element_range=(0.5, 1.0), total_range=(6.6, 11.0)),
        },
        notes=(
            "Elite masters must choose an aerial dead lift with a fourth or higher point value.",
        ),
    ),
    Profile.JUNIOR_SINGLES: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=SINGLES_REQUIREMENTS,
        divisions={
            Division.INTRO: INTRO_DIVISION_RULES,
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.ELITE: PROFESSIONAL_DIVISION_RULES,
        },
    ),
    Profile.NOVICE_SINGLES: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=SINGLES_REQUIREMENTS,
        divisions={
            Division.INTRO: INTRO_DIVISION_RULES,
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.ELITE: DivisionRules(element_range=(0.3, 0.8), total_range=(4.4, 7.2)),
        },
    ),
    Profile.PRE_NOVICE_SINGLES: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=(
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning/static pole spin",
            "1 additional spin of choice",
            "1 dead lift",
        ),
        divisions={
            Division.INTRO: INTRO_DIVISION_RULES,
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
        },
        notes=("Pre-Novice does not have Professional or Elite divisions.",),
    ),
    Profile.PARA_POLE: ProfileRules(
        track=Track.SINGLES,
        required_elements=9,
        requirements=SINGLES_REQUIREMENTS,
        divisions={
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.ELITE: AMATEUR_DIVISION_RULES,
        },
        notes=(
            (
                "Para Pole follows amateur compulsory value ranges with additional tolerance rules "
                "not yet enforced in this app."
            ),
        ),
    ),
    Profile.SENIOR_DOUBLES: ProfileRules(
        track=Track.DOUBLES,
        required_elements=9,
        requirements=DOUBLES_REQUIREMENTS,
        divisions={
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.PROFESSIONAL: PROFESSIONAL_DIVISION_RULES,
            Division.ELITE: DivisionRules(element_range=(0.5, 1.0), total_range=(7.7, 11.0)),
        },
        notes=(
            "Elite senior doubles must use an aerial dead lift with a fourth or higher point value.",  # noqa: E501
        ),
    ),
    Profile.JUNIOR_DOUBLES: ProfileRules(
        track=Track.DOUBLES,
        required_elements=9,
        requirements=DOUBLES_REQUIREMENTS,
        divisions={
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.ELITE: PROFESSIONAL_DIVISION_RULES,
        },
        notes=("Junior doubles does not have Intro or Professional divisions.",),
    ),
    Profile.NOVICE_YOUTH_DOUBLES: ProfileRules(
        track=Track.DOUBLES,
        required_elements=9,
        requirements=DOUBLES_REQUIREMENTS,
        divisions={
            Division.AMATEUR: AMATEUR_DIVISION_RULES,
            Division.ELITE: DivisionRules(element_range=(0.3, 0.8), total_range=(4.4, 7.2)),
        },
        notes=("Novice and Youth doubles do not have Intro or Professional divisions.",),
    ),
}
