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

    from src.models.catalog import CatalogRecord

try:
    from src.catalog_common import code_sort_key
    from src.catalog_filter import FilterCriteria, filter_records
    from src.extract_catalog import build_catalog_from_pdf_bytes
    from src.models.frontend import SelectionContext
    from src.models.profiles import (
        PROFILE_RULES,
        Division,
        DivisionRules,
        Profile,
        ProfileRules,
    )
except ImportError:  # pragma: no cover
    from catalog_common import code_sort_key
    from catalog_filter import FilterCriteria, filter_records
    from extract_catalog import build_catalog_from_pdf_bytes
    from models.frontend import SelectionContext
    from models.profiles import (
        PROFILE_RULES,
        Division,
        DivisionRules,
        Profile,
        ProfileRules,
    )

CATALOG_STATE_KEY = "catalog_records"
SOURCE_STATE_KEY = "catalog_source"
EXPORT_TEMPLATE_PATH = Path(__file__).with_name("compulsory-selection.html")
ALL_CATEGORIES_OPTION = "All categories"
ALL_DIVISIONS_OPTION = "All divisions"
ELEMENTS_PER_PAGE = 60
BROWSER_PAGE_STATE_KEY = "element_browser_page"
BROWSER_FILTER_SIGNATURE_KEY = "element_browser_filter_signature"


def extract_catalog_from_pdf(pdf_bytes: bytes) -> list[CatalogRecord]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_dir = Path(tmp_dir)
        records = build_catalog_from_pdf_bytes(pdf_bytes, output_dir)
        return [
            record.model_copy(
                update={
                    "image_path": None,
                    "image_bytes": (
                        (output_dir / record.image_path).read_bytes() if record.image_path else None
                    ),
                }
            )
            for record in records
        ]


def selection_key(code_number: str) -> str:
    return f"selected::{code_number}"


def selection_widget_key(code_number: str) -> str:
    return f"selection-widget::{code_number}"


def selected_records(records: list[CatalogRecord]) -> list[CatalogRecord]:
    return [
        record
        for record in records
        if st.session_state.get(selection_key(record.code_number), False)
    ]


def format_value_range(value_min: float, value_max: float) -> str:
    if value_min == value_max:
        return f"{value_min:.1f}"
    return f"{value_min:.1f} - {value_max:.1f}"


def render_export_html(
    records: list[CatalogRecord],
    category: Profile | None,
    profile: ProfileRules | None,
    division: Division | None,
    source_name: str,
) -> str:
    total_min = sum(record.value_min for record in records)
    total_max = sum(record.value_max for record in records)
    cards = []
    for record in records:
        image_html = ""
        image_data = record.image_bytes
        if image_data:
            image_b64 = base64.b64encode(image_data).decode("ascii")
            image_html = (
                f'<img src="data:image/png;base64,{image_b64}" '
                f'alt="{html.escape(record.name)}" class="element-image">'
            )

        criteria_items = "".join(
            f'<div class="criteria-line">{html.escape(line)}</div>'
            for line in record.criteria_lines
        )
        variant_description = record.variant_description
        variant_html = (
            f'<div class="variant">{html.escape(variant_description)}</div>'
            if variant_description
            else ""
        )
        cards.append(
            "".join(
                [
                    '<article class="card">',
                    '<div class="card-header">',
                    f'<div><div class="code">{html.escape(record.code_number)}</div>',
                    f"<h2>{html.escape(record.name)}</h2>",
                    variant_html,
                    "</div>",
                    (
                        '<div class="value">TV '
                        f"{html.escape(record.technical_value.replace(chr(10), ' / '))}</div>"
                    ),
                    "</div>",
                    image_html,
                    (
                        f'<div class="meta">{html.escape(record.section)} | '
                        f"Page {record.page_number}</div>"
                    ),
                    f'<div class="criteria">{criteria_items}</div>',
                    "</article>",
                ]
            )
        )

    requirements_html = (
        "".join(f"<li>{html.escape(item)}</li>" for item in profile.requirements)
        if profile is not None
        else "<li>No category selected.</li>"
    )
    notes_html = (
        "".join(f"<li>{html.escape(item)}</li>" for item in profile.notes) if profile else ""
    )
    element_range = profile.divisions[division].element_range if profile and division else None

    template = EXPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    substitutions = {
        "{{SOURCE_NAME}}": html.escape(source_name),
        "{{PROFILE_CATEGORY}}": html.escape(category or ALL_CATEGORIES_OPTION),
        "{{PROFILE_DIVISION}}": html.escape(division or ALL_DIVISIONS_OPTION),
        "{{PROFILE_TRACK}}": html.escape(profile.track if profile else "All tracks"),
        "{{SELECTED_COUNT}}": str(len(records)),
        "{{REQUIRED_ELEMENTS}}": str(profile.required_elements) if profile else "N/A",
        "{{ELEMENT_MIN}}": f"{element_range[0]:.1f}" if element_range else "N/A",
        "{{ELEMENT_MAX}}": f"{element_range[1]:.1f}" if element_range else "N/A",
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


CRITERIA_LIST_CSS = """
<style>
.criteria-list { margin: 0.2em 0 0; padding-left: 1.2em; line-height: 1.15; }
.criteria-list li { margin-bottom: 1px; }
.element-thumb {
    width: 180px;
    height: 180px;
    object-fit: contain;
    display: block;
}
</style>
"""


def paginate_records(
    records: list[CatalogRecord], filter_signature: tuple[Any, ...]
) -> list[CatalogRecord]:
    if st.session_state.get(BROWSER_FILTER_SIGNATURE_KEY) != filter_signature:
        st.session_state[BROWSER_FILTER_SIGNATURE_KEY] = filter_signature
        st.session_state[BROWSER_PAGE_STATE_KEY] = 1
    total_pages = max(1, -(-len(records) // ELEMENTS_PER_PAGE))
    current_page = st.session_state.get(BROWSER_PAGE_STATE_KEY, 1)
    current_page = min(max(current_page, 1), total_pages)
    st.session_state[BROWSER_PAGE_STATE_KEY] = current_page

    prev_col, label_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button("Previous", disabled=current_page <= 1, key="element-browser-prev"):
            st.session_state[BROWSER_PAGE_STATE_KEY] = current_page - 1
            st.rerun()
    with label_col:
        st.markdown(
            f"<div style='text-align:center'>Page {current_page} of {total_pages} "
            f"({len(records)} elements)</div>",
            unsafe_allow_html=True,
        )
    with next_col:
        if st.button("Next", disabled=current_page >= total_pages, key="element-browser-next"):
            st.session_state[BROWSER_PAGE_STATE_KEY] = current_page + 1
            st.rerun()

    start = (current_page - 1) * ELEMENTS_PER_PAGE
    return records[start : start + ELEMENTS_PER_PAGE]


def render_record_card(record: CatalogRecord) -> None:
    variant_description = record.variant_description
    variant_part = f" | {variant_description}" if variant_description else ""
    st.markdown(
        f"### {record.code_number} | {record.name}{variant_part} | TV "
        f"{format_value_range(record.value_min, record.value_max)}"
    )
    select_col, image_col, info_col, criteria_col = st.columns([0.8, 1.2, 1.0, 1.5])
    with select_col:
        widget_key = selection_widget_key(record.code_number)
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state.get(
                selection_key(record.code_number), False
            )
        st.checkbox(
            "Select",
            key=widget_key,
            on_change=sync_record_selection,
            args=(record.code_number,),
        )
        st.caption(f"Section: {record.section}")
        st.caption(f"Page: {record.page_number}")
    with image_col:
        image_data = record.image_bytes
        if image_data:
            image_b64 = base64.b64encode(image_data).decode("ascii")
            st.markdown(
                f'<img src="data:image/png;base64,{image_b64}" '
                f'alt="{html.escape(record.name)}" class="element-thumb">',
                unsafe_allow_html=True,
            )
        else:
            st.info("No image extracted")
    with info_col:
        st.markdown(f"**Code**: {record.code_number}")
        st.markdown(f"**Name**: {record.name}")
        technical_value = record.technical_value.replace(chr(10), " / ")
        st.markdown(f"**Technical value**: {technical_value}")
    with criteria_col:
        st.markdown("**Criteria**")
        criteria_items = "".join(f"<li>{html.escape(line)}</li>" for line in record.criteria_lines)
        st.markdown(f'<ul class="criteria-list">{criteria_items}</ul>', unsafe_allow_html=True)
    st.divider()


def render_element_browser(records: list[CatalogRecord], filter_signature: tuple[Any, ...]) -> None:
    if not records:
        st.warning("No elements match the current filters.")
        return
    visible_records = paginate_records(records, filter_signature)
    st.markdown(CRITERIA_LIST_CSS, unsafe_allow_html=True)
    for record in visible_records:
        render_record_card(record)


def render_printable_selection(
    records: list[CatalogRecord],
    context: SelectionContext,
    *,
    show_division_rules: bool,
) -> None:
    profile = context.profile
    division_rules = (
        profile.divisions[context.division]
        if profile is not None and context.division is not None
        else None
    )
    chosen_records = selected_records(records)
    st.subheader("Printable Selection")
    if not chosen_records:
        st.info("Select one or more elements to build the printable output.")
        return
    chosen_records.sort(key=lambda item: code_sort_key(item.code_number))
    selected_min = sum(record.value_min for record in chosen_records)
    selected_max = sum(record.value_max for record in chosen_records)
    summary_left, summary_mid = st.columns(2)
    summary_left.metric("Selected count", len(chosen_records))
    summary_mid.metric("Selected total", f"{selected_min:.1f}")
    if show_division_rules and profile is not None and division_rules is not None:
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
        code_col.markdown(f"**{record.code_number}**")
        name_col.write(record.name)
        section_col.write(record.section)
        value_col.write(record.technical_value.replace("\n", " / "))
        if action_col.button(
            "Deselect",
            key=f"deselect::{record.code_number}",
        ):
            deselect_record(record.code_number)
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

    st.sidebar.header("Catalog Source")
    uploaded_pdf = st.sidebar.file_uploader(
        "Upload Code of Points PDF",
        type=["pdf"],
        label_visibility="collapsed",
        accept_multiple_files=False,
    )
    if st.sidebar.button("Extract Uploaded PDF", use_container_width=True):
        handle_uploaded_pdf(uploaded_pdf)

    records = st.session_state.get(CATALOG_STATE_KEY)
    source_name = st.session_state.get(SOURCE_STATE_KEY)
    if not isinstance(source_name, str):
        source_name = "Unknown source"
    if not records:
        st.caption(
            "Upload a Code of Points PDF, shortlist compulsory elements, and "
            "export a printable selection."
        )
        st.warning(
            "**Disclaimer:** This project is an unofficial, independent tool and is "
            "**not affiliated with, endorsed by, or sponsored by** the International "
            "Pole Sports Federation (IPSF) or any other rulebook publisher.\n\n"
            "The Code of Points PDF is copyrighted material owned by its publisher. "
            "This app does not include or distribute that PDF. You must supply your "
            "own legally obtained copy and upload it in the sidebar, then click "
            "'Extract Uploaded PDF' to get started.\n\n"
            "No responsibility is taken for the accuracy or completeness of the "
            "elements shown by this app. This tool must **not** be used when filling "
            "out the official Compulsory Score Form.\n\n"
            "Comments, wishes, or improvement suggestions are very welcome — feel "
            "free to reach out on Instagram "
            "[@norange7](https://www.instagram.com/norange7/)."
        )
        return

    st.sidebar.info(f"Loaded catalog extracted from: {source_name}")

    st.sidebar.header("Compulsory Profile")
    category_choice = st.sidebar.selectbox("Category", [ALL_CATEGORIES_OPTION, *PROFILE_RULES])
    category = None if category_choice == ALL_CATEGORIES_OPTION else Profile(category_choice)
    profile = PROFILE_RULES[category] if category is not None else None

    division_options = (
        [ALL_DIVISIONS_OPTION, *profile.divisions]
        if profile is not None
        else [ALL_DIVISIONS_OPTION]
    )
    division_choice = st.sidebar.selectbox("Division", division_options)
    division = None if division_choice == ALL_DIVISIONS_OPTION else Division(division_choice)
    division_rules = (
        profile.divisions[division] if profile is not None and division is not None else None
    )

    section_options = sorted(
        {record.section for record in records if profile is None or profile.track in record.tracks}
    )
    selected_sections = st.sidebar.multiselect("Sections", section_options)
    query = st.sidebar.text_input("Search", placeholder="Code, name, criteria...")

    st.sidebar.header("Division Rules Display")
    can_show_division_rules = division_rules is not None
    show_division_rules = (
        st.sidebar.selectbox(
            "Show division rules information",
            ["Hide", "Show"],
            index=0,
            disabled=not can_show_division_rules,
        )
        == "Show"
        and can_show_division_rules
    )

    filtered = filter_records(
        records,
        FilterCriteria(category, profile, division, query, selected_sections),
    )
    chosen_records = selected_records(records)
    top_left, top_right = st.columns(2)
    top_left.metric("Parsed elements", len(records))
    top_right.metric("Currently selected", len(chosen_records))

    context = SelectionContext(category, profile, division, source_name)
    render_printable_selection(records, context, show_division_rules=show_division_rules)
    if show_division_rules and profile is not None and division_rules is not None:
        render_rules(profile, division_rules)
    st.divider()
    st.subheader("Element Browser")
    filter_signature = (category, division, tuple(sorted(selected_sections)), query)
    render_element_browser(filtered, filter_signature)


if __name__ == "__main__":
    main()
