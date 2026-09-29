"""Tests for selection state in the Streamlit app."""

from src import app
from src.catalog_filter import FilterCriteria, filter_records
from src.models.profiles import PROFILE_RULES, Division, Profile, Track


def test_filter_changes_keep_selected_records(monkeypatch):
    records = [
        {
            "code_number": "S1",
            "name": "Spin",
            "section": "Skating",
            "tracks": [Track.SINGLES],
            "value_min": 0.5,
            "value_max": 0.5,
            "criteria_lines": [],
        }
    ]
    session_state = {
        app.selection_key("S1"): True,
        app.selection_widget_key("S1"): True,
    }
    monkeypatch.setattr(app.st, "session_state", session_state)
    profile = PROFILE_RULES[Profile.SENIOR_SINGLES]
    criteria = FilterCriteria(
        Profile.SENIOR_SINGLES,
        profile,
        Division.ELITE,
        "no matching text",
        [],
    )

    assert filter_records(records, criteria) == []
    session_state.pop(app.selection_widget_key("S1"))
    assert app.selected_records(records) == records


def test_deselect_record_removes_only_that_record(monkeypatch):
    session_state = {
        app.selection_key("S1"): True,
        app.selection_widget_key("S1"): True,
        app.selection_key("S2"): True,
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    app.deselect_record("S1")

    assert app.selection_key("S1") not in session_state
    assert app.selection_widget_key("S1") not in session_state
    assert session_state[app.selection_key("S2")] is True


def test_clear_selected_records_removes_all_selections(monkeypatch):
    session_state = {
        app.selection_key("S1"): True,
        app.selection_widget_key("S1"): True,
        app.selection_key("S2"): True,
        app.selection_widget_key("S2"): True,
        "unrelated-state": "preserved",
    }
    monkeypatch.setattr(app.st, "session_state", session_state)

    app.clear_selected_records()

    assert not any(key.startswith(("selected::", "selection-widget::")) for key in session_state)
    assert session_state["unrelated-state"] == "preserved"
