# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.

from __future__ import annotations

import base64
import html
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile

try:
    from src.catalog_common import code_sort_key
    from src.catalog_filter import FilterCriteria, filter_records
    from src.extract_catalog import build_catalog_from_pdf_bytes
    from src.models import (
        PROFILE_RULES,
        Division,
        DivisionRules,
        Profile,
        ProfileRules,
        SelectionContext,
    )
except ImportError:  # pragma: no cover
    from catalog_common import code_sort_key
    from catalog_filter import FilterCriteria, filter_records
    from extract_catalog import build_catalog_from_pdf_bytes
    from models import (
        PROFILE_RULES,
        Division,
        DivisionRules,
        Profile,
        ProfileRules,
        SelectionContext,
    )

CATALOG_STATE_KEY = "catalog_records"
SOURCE_STATE_KEY = "catalog_source"
EXPORT_TEMPLATE_PATH = Path(__file__).with_name("compulsory-selection.html")


def extract_catalog_from_pdf(pdf_bytes: bytes) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        records = build_catalog_from_pdf_bytes(pdf_bytes, output_dir)
        for record in records:
            image_path = record.pop("image_path", None)
            record["image_bytes"] = (output_dir / image_path).read_bytes() if image_path else None
    return records


def selection_key(code_number: str) -> str:
    return f"selected::{code_number}"


def selection_widget_key(code_number: str) -> str:
    return f"selection-widget::{code_number}"


def selected_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if st.session_state.get(selection_key(record["code_number"]), False)
    ]


def format_value_range(value_min: float, value_max: float) -> str:
    if value_min == value_max:
        return f"{value_min:.1f}"
    return f"{value_min:.1f} - {value_max:.1f}"


def render_export_html(
    records: list[dict[str, Any]],
    category: Profile,
    profile: ProfileRules,
    division: Division,
    source_name: str,
) -> str:
    total_min = sum(record["value_min"] for record in records)
    total_max = sum(record["value_max"] for record in records)
    cards = []
    for record in records:
        image_html = ""
        image_data = record.get("image_bytes")
        if image_data:
            image_b64 = base64.b64encode(image_data).decode("ascii")
            image_html = (
                f'<img src="data:image/png;base64,{image_b64}" '
                f'alt="{html.escape(record["name"])}" class="element-image">'
            )

        criteria_items = "".join(
            f'<div class="criteria-line">{html.escape(line)}</div>'
            for line in record["criteria_lines"]
        )
        cards.append(
            "".join(
                [
                    '<article class="card">',
                    '<div class="card-header">',
                    f'<div><div class="code">{html.escape(record["code_number"])}</div>',
                    f"<h2>{html.escape(record['name'])}</h2></div>",
                    (
                        '<div class="value">TV '
                        f"{html.escape(record['technical_value'].replace(chr(10), ' / '))}</div>"
                    ),
                    "</div>",
                    image_html,
                    (
                        f'<div class="meta">{html.escape(record["section"])} | '
                        f"Page {record['page_number']}</div>"
                    ),
                    f'<div class="criteria">{criteria_items}</div>',
                    "</article>",
                ]
            )
        )

    requirements_html = "".join(f"<li>{html.escape(item)}</li>" for item in profile.requirements)
    notes_html = "".join(f"<li>{html.escape(item)}</li>" for item in profile.notes)

    template = EXPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    substitutions = {
        "{{SOURCE_NAME}}": html.escape(source_name),
        "{{PROFILE_CATEGORY}}": html.escape(category),
        "{{PROFILE_DIVISION}}": html.escape(division),
        "{{PROFILE_TRACK}}": html.escape(profile.track),
        "{{SELECTED_COUNT}}": str(len(records)),
        "{{REQUIRED_ELEMENTS}}": str(profile.required_elements),
        "{{ELEMENT_MIN}}": f"{profile.divisions[division].element_range[0]:.1f}",
        "{{ELEMENT_MAX}}": f"{profile.divisions[division].element_range[1]:.1f}",
        "{{TOTAL_MIN}}": f"{total_min:.1f}",
        "{{TOTAL_MAX}}": f"{total_max:.1f}",
        "{{REQUIREMENTS}}": requirements_html,
        "{{NOTES}}": notes_html or "<li>No extra notes for this profile.</li>",
        "{{CARDS}}": "".join(cards),
    }
    for placeholder, value in substitutions.items():
        template = template.replace(placeholder, value)
    return template


def clear_selected_records() -> None:
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith(("selected::", "selection-widget::")):
            del st.session_state[key]


def deselect_record(code_number: str) -> None:
    st.session_state.pop(selection_key(code_number), None)
    st.session_state.pop(selection_widget_key(code_number), None)


def sync_record_selection(code_number: str) -> None:
    if st.session_state.get(selection_widget_key(code_number), False):
        st.session_state[selection_key(code_number)] = True
    else:
        st.session_state.pop(selection_key(code_number), None)


def handle_uploaded_pdf(uploaded_pdf: UploadedFile | None) -> None:
    if uploaded_pdf is None:
        st.sidebar.warning("Choose a PDF file first.")
        return
    pdf_bytes = uploaded_pdf.getvalue()
    if not pdf_bytes:
        st.sidebar.error("The uploaded PDF appears to be empty.")
        return
    with st.spinner("Extracting catalog from uploaded PDF..."):
        try:
            records = extract_catalog_from_pdf(pdf_bytes)
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Extraction failed: {exc}")
            return
    if not records:
        st.sidebar.error("No compulsory catalog pages were detected in the uploaded PDF.")
        return
    source_name = uploaded_pdf.name or "uploaded.pdf"
    st.session_state[CATALOG_STATE_KEY] = records
    st.session_state[SOURCE_STATE_KEY] = source_name
    clear_selected_records()
    st.sidebar.success(f"Extracted {len(records)} elements from {source_name}.")
    st.rerun()


def render_rules(profile: ProfileRules, division_rules: DivisionRules) -> None:
    rules_col, composition_col = st.columns(2)
    with rules_col:
        st.markdown(
            f"""
**Rules in use**

- Track: {profile.track}
- Required elements: {profile.required_elements}
- Allowed technical value per element: {division_rules.element_range[0]:.1f} to
    {division_rules.element_range[1]:.1f}
- Required total technical value: {division_rules.total_range[0]:.1f} to
    {division_rules.total_range[1]:.1f}
"""
        )
    with composition_col:
        composition = "\n".join(f"- {item}" for item in profile.requirements)
        notes = "\n".join(f"- {item}" for item in profile.notes)
        composition_markdown = "**Required composition**\n\n"
        composition_markdown += composition or "- No specific composition listed."
        if notes:
            composition_markdown += f"\n\n**Notes**\n\n{notes}"
        st.markdown(composition_markdown)


def render_element_browser(records: list[dict[str, Any]], max_results: int) -> None:
    visible_records = records[:max_results]
    if not visible_records:
        st.warning("No elements match the current filters.")
        return
    for record in visible_records:
        st.markdown(
            f"### {record['code_number']} | {record['name']} | TV "
            f"{format_value_range(record['value_min'], record['value_max'])}"
        )
        select_col, image_col, text_col = st.columns([0.8, 1.2, 2.3])
        with select_col:
            widget_key = selection_widget_key(record["code_number"])
            if widget_key not in st.session_state:
                st.session_state[widget_key] = st.session_state.get(
                    selection_key(record["code_number"]), False
                )
            st.checkbox(
                "Select",
                key=widget_key,
                on_change=sync_record_selection,
                args=(record["code_number"],),
            )
            st.caption(f"Section: {record['section']}")
            st.caption(f"Page: {record['page_number']}")
        with image_col:
            image_data = record.get("image_bytes")
            if image_data:
                st.image(image_data, use_container_width=True)
            else:
                st.info("No image extracted")
        with text_col:
            st.markdown(f"**Code**: {record['code_number']}")
            st.markdown(f"**Name**: {record['name']}")
            technical_value = record["technical_value"].replace(chr(10), " / ")
            st.markdown(f"**Technical value**: {technical_value}")
            st.markdown("**Criteria**")
            for line in record["criteria_lines"]:
                st.markdown(f"- {line}")
        st.divider()


def render_printable_selection(
    records: list[dict[str, Any]],
    context: SelectionContext,
    *,
    show_division_rules: bool,
) -> None:
    profile = context.profile
    division_rules = profile.divisions[context.division]
    chosen_records = selected_records(records)
    st.subheader("Printable Selection")
    if not chosen_records:
        st.info("Select one or more elements to build the printable output.")
        return
    chosen_records.sort(key=lambda item: code_sort_key(item["code_number"]))
    selected_min = sum(record["value_min"] for record in chosen_records)
    selected_max = sum(record["value_max"] for record in chosen_records)
    summary_left, summary_mid = st.columns(2)
    summary_left.metric("Selected count", len(chosen_records))
    summary_mid.metric("Selected total", f"{selected_min:.1f}")
    if show_division_rules:
        if len(chosen_records) != profile.required_elements:
            st.warning(
                f"This profile expects {profile.required_elements} elements, but "
                f"{len(chosen_records)} are currently selected."
            )
        total_low, total_high = division_rules.total_range
        if selected_max < total_low or selected_min > total_high:
            st.warning(
                f"The current selection falls outside the required total range of "
                f"{total_low:.1f} to {total_high:.1f}."
            )
        else:
            st.success(
                f"The selected total range overlaps the required total range of "
                f"{total_low:.1f} to {total_high:.1f}."
            )
    if st.button("Deselect all", key="deselect-all-selected-records"):
        clear_selected_records()
        st.rerun()
    for record in chosen_records:
        code_col, name_col, section_col, value_col, action_col = st.columns(
            [0.8, 2.4, 1.2, 1.2, 0.8]
        )
        code_col.markdown(f"**{record['code_number']}**")
        name_col.write(record["name"])
        section_col.write(record["section"])
        value_col.write(record["technical_value"].replace("\n", " / "))
        if action_col.button(
            "Deselect",
            key=f"deselect::{record['code_number']}",
        ):
            deselect_record(record["code_number"])
            st.rerun()
    export_html = render_export_html(
        chosen_records, context.category, profile, context.division, context.source_name
    )
    st.download_button(
        "Download printable HTML",
        data=export_html,
        file_name="compulsory-selection.html",
        mime="text/html",
        use_container_width=True,
    )
    st.caption("Open the downloaded HTML file in a browser and print to PDF or paper.")


def main() -> None:
    st.set_page_config(page_title="Code of Points Helper", layout="wide")
    st.title("Code of Points Helper")
    st.caption(
        "Upload/extract a Code of Points PDF, shortlist compulsory elements, and "
        "export a printable selection."
    )

    st.sidebar.header("Catalog Source")
    uploaded_pdf = st.sidebar.file_uploader("Upload Code of Points PDF", type=["pdf"])
    if st.sidebar.button("Extract Uploaded PDF", use_container_width=True):
        handle_uploaded_pdf(uploaded_pdf)

    records = st.session_state.get(CATALOG_STATE_KEY)
    source_name = st.session_state.get(SOURCE_STATE_KEY)
    if not isinstance(source_name, str):
        source_name = "Unknown source"
    if not records:
        st.info(
            "Upload a Code of Points PDF in the sidebar and click 'Extract Uploaded PDF' "
            "to get started."
        )
        return

    st.sidebar.info(f"Loaded catalog extracted from: {source_name}")

    st.sidebar.header("Compulsory Profile")
    category = st.sidebar.selectbox("Category", list(PROFILE_RULES))
    division = st.sidebar.selectbox(
        "Division",
        list(PROFILE_RULES[category].divisions),
    )
    profile = PROFILE_RULES[category]
    division_rules = profile.divisions[division]

    section_options = sorted(
        {record["section"] for record in records if profile.track in record["tracks"]}
    )
    selected_sections = st.sidebar.multiselect("Sections", section_options)
    query = st.sidebar.text_input("Search", placeholder="Code, name, criteria...")
    max_results = st.sidebar.slider(
        "Visible results", min_value=10, max_value=200, value=40, step=10
    )

    st.sidebar.header("Division Rules Display")
    show_division_rules = (
        st.sidebar.selectbox(
            "Show division rules information",
            ["Hide", "Show"],
            index=0,
        )
        == "Show"
    )

    filtered = filter_records(
        records,
        FilterCriteria(category, profile, division, query, selected_sections),
    )
    chosen_records = selected_records(records)
    top_left, top_mid, top_right = st.columns(3)
    top_left.metric("Parsed elements", len(records))
    top_mid.metric("Matching this profile", len(filtered))
    top_right.metric("Currently selected", len(chosen_records))

    context = SelectionContext(category, profile, division, source_name)
    render_printable_selection(records, context, show_division_rules=show_division_rules)
    if show_division_rules:
        render_rules(profile, division_rules)
    st.divider()
    st.subheader("Element Browser")
    st.caption(
        "Use the search and section filters to narrow the list, then tick the "
        "elements you want in the printable export."
    )
    render_element_browser(filtered, max_results)


if __name__ == "__main__":
    main()
