# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.

"""Part 2: browse the extracted catalog and build a printable selection.

You can either:
1) Run extract_catalog.py manually, or
2) Upload a PDF in this app and extract in one step.
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile

from catalog_common import code_sort_key, prefix_for_code
from extract_catalog import build_catalog_from_pdf_bytes, write_catalog

DATA_DIR = Path(__file__).resolve().parent / "data"
ELITE_AERIAL_DEADLIFT_MIN_VALUE = 0.4


PROFILE_RULES: dict[str, dict[str, Any]] = {
    "Senior Singles": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning pole spin",
            "1 static pole spin",
            "1 dead lift",
        ],
        "divisions": {
            "Intro": {"element_range": (0.1, 0.3), "total_range": (0.9, 2.7)},
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Professional": {"element_range": (0.3, 0.8), "total_range": (5.5, 8.8)},
            "Elite": {"element_range": (0.5, 1.0), "total_range": (7.7, 11.0)},
        },
        "notes": [
            "Elite seniors must choose an aerial dead lift with a fourth or higher point value.",
        ],
    },
    "Masters Singles": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning pole spin",
            "1 static pole spin",
            "1 dead lift",
        ],
        "divisions": {
            "Intro": {"element_range": (0.1, 0.3), "total_range": (0.9, 2.7)},
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Professional": {"element_range": (0.3, 0.8), "total_range": (5.5, 8.8)},
            "Elite": {"element_range": (0.5, 1.0), "total_range": (6.6, 11.0)},
        },
        "notes": [
            "Elite masters must choose an aerial dead lift with a fourth or higher point value.",
        ],
    },
    "Junior Singles": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning pole spin",
            "1 static pole spin",
            "1 dead lift",
        ],
        "divisions": {
            "Intro": {"element_range": (0.1, 0.3), "total_range": (0.9, 2.7)},
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Elite": {"element_range": (0.3, 0.8), "total_range": (5.5, 8.8)},
        },
    },
    "Novice Singles": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning pole spin",
            "1 static pole spin",
            "1 dead lift",
        ],
        "divisions": {
            "Intro": {"element_range": (0.1, 0.3), "total_range": (0.9, 2.7)},
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Elite": {"element_range": (0.3, 0.8), "total_range": (4.4, 7.2)},
        },
    },
    "Pre-Novice Singles": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning/static pole spin",
            "1 additional spin of choice",
            "1 dead lift",
        ],
        "divisions": {
            "Intro": {"element_range": (0.1, 0.3), "total_range": (0.9, 2.7)},
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
        },
        "notes": [
            "Pre-Novice does not have Professional or Elite divisions.",
        ],
    },
    "Para Pole": {
        "track": "Singles",
        "required_elements": 9,
        "requirements": [
            "3 flexibility elements",
            "3 strength elements",
            "1 spinning pole spin",
            "1 static pole spin",
            "1 dead lift",
        ],
        "divisions": {
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Elite": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
        },
        "notes": [
            (
                "Para Pole follows amateur compulsory value ranges with additional "
                "tolerance rules not yet enforced in this app."
            )
        ],
    },
    "Senior Doubles": {
        "track": "Doubles",
        "required_elements": 9,
        "requirements": [
            "3 synchronised partner elements: parallel, interlocking, balance-based",
            "1 balance partner element",
            "2 flying partner elements",
            "1 partner supported element",
            "1 pole-based floor element",
            "1 synchronised dead lift",
        ],
        "divisions": {
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Professional": {"element_range": (0.3, 0.8), "total_range": (5.5, 8.8)},
            "Elite": {"element_range": (0.5, 1.0), "total_range": (7.7, 11.0)},
        },
        "notes": [
            "Elite senior doubles must use an aerial dead lift with a fourth or higher point value."
        ],
    },
    "Junior Doubles": {
        "track": "Doubles",
        "required_elements": 9,
        "requirements": [
            "3 synchronised partner elements: parallel, interlocking, balance-based",
            "1 balance partner element",
            "2 flying partner elements",
            "1 partner supported element",
            "1 pole-based floor element",
            "1 synchronised dead lift",
        ],
        "divisions": {
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Elite": {"element_range": (0.3, 0.8), "total_range": (5.5, 8.8)},
        },
        "notes": [
            "Junior doubles does not have Intro or Professional divisions.",
        ],
    },
    "Novice/Youth Doubles": {
        "track": "Doubles",
        "required_elements": 9,
        "requirements": [
            "3 synchronised partner elements: parallel, interlocking, balance-based",
            "1 balance partner element",
            "2 flying partner elements",
            "1 partner supported element",
            "1 pole-based floor element",
            "1 synchronised dead lift",
        ],
        "divisions": {
            "Amateur": {"element_range": (0.1, 0.5), "total_range": (1.1, 4.5)},
            "Elite": {"element_range": (0.3, 0.8), "total_range": (4.4, 7.2)},
        },
        "notes": [
            "Novice and Youth doubles do not have Intro or Professional divisions.",
        ],
    },
}


def catalog_path() -> Path:
    return DATA_DIR / "catalog.json"


@st.cache_data(show_spinner=False)
def parse_catalog_json(catalog_json_text: str) -> tuple[list[dict[str, Any]], str]:
    payload = json.loads(catalog_json_text)
    return payload["elements"], payload.get("source_pdf", "unknown.pdf")


def load_catalog() -> tuple[list[dict[str, Any]], str] | None:
    path = catalog_path()
    if not path.exists():
        return None
    return parse_catalog_json(path.read_text(encoding="utf-8"))


def image_bytes_for(record: dict[str, Any]) -> bytes | None:
    image_path = record.get("image_path")
    if not image_path:
        return None
    full_path = DATA_DIR / image_path
    if not full_path.exists():
        return None
    return full_path.read_bytes()


def profile_details(category: str, division: str) -> dict[str, Any]:
    profile = PROFILE_RULES[category]
    division_details = profile["divisions"][division]
    return {
        **profile,
        "category": category,
        "division": division,
        "element_range": division_details["element_range"],
        "total_range": division_details["total_range"],
    }


def filter_records(
    records: list[dict[str, Any]], profile: dict[str, Any], query: str, sections: list[str]
) -> list[dict[str, Any]]:
    min_value, max_value = profile["element_range"]
    track = profile["track"]
    filtered: list[dict[str, Any]] = []

    for record in records:
        if track not in record["tracks"]:
            continue
        if sections and record["section"] not in sections:
            continue
        if record["value_max"] < min_value or record["value_min"] > max_value:
            continue

        if (
            profile["division"] == "Intro"
            and track == "Singles"
            and prefix_for_code(record["code_number"]) in {"DL", "ADL"}
            and not (
                record["code_number"].startswith("DL1") or record["code_number"].startswith("ADL9")
            )
        ):
            continue

        if (
            profile["division"] == "Elite"
            and profile["category"] in {"Senior Singles", "Masters Singles", "Senior Doubles"}
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
        if query and query.lower() not in haystack:
            continue

        filtered.append(record)

    return filtered


def selection_key(code_number: str) -> str:
    return f"selected::{code_number}"


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
    records: list[dict[str, Any]], profile: dict[str, Any], source_name: str
) -> str:
    total_min = sum(record["value_min"] for record in records)
    total_max = sum(record["value_max"] for record in records)
    cards = []
    for record in records:
        image_html = ""
        image_data = image_bytes_for(record)
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

    requirements_html = "".join(f"<li>{html.escape(item)}</li>" for item in profile["requirements"])
    notes_html = "".join(f"<li>{html.escape(item)}</li>" for item in profile.get("notes", []))

    return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>Compulsory Selection</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #52606d;
      --line: #d9e2ec;
      --paper: #fffdf8;
      --accent: #8d5524;
      --panel: #f8f5ef;
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: Georgia, serif; margin: 0; color: var(--ink); background: var(--paper); }}
    header {{ padding: 28px 40px 12px; border-bottom: 2px solid var(--accent); }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ margin: 4px 0; line-height: 1.45; }}
    main {{ padding: 24px 40px 40px; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
      margin-bottom: 20px; }}
    .summary div {{ background: var(--panel); border: 1px solid var(--line); padding: 12px 14px;
      border-radius: 8px; }}
        .requirements {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
            margin-bottom: 28px; }}
        .requirements section {{ border: 1px solid var(--line); border-radius: 8px;
            padding: 14px 16px; background: white; }}
        .cards {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; }}
        .card {{ break-inside: avoid; border: 1px solid var(--line); border-radius: 10px;
            padding: 16px; background: white; }}
        .card-header {{ display: flex; justify-content: space-between; gap: 12px;
            align-items: start; }}
        .code {{ font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: 0.08em; }}
        .value {{ font-size: 14px; white-space: pre-line; text-align: right; }}
        h2 {{ font-size: 20px; margin: 2px 0 0; }}
        .meta {{ margin-top: 10px; color: var(--muted); font-size: 13px; }}
        .element-image {{ width: 100%; max-height: 280px; object-fit: contain; margin-top: 12px;
            border-radius: 8px; background: var(--panel); }}
        ul {{ padding-left: 20px; line-height: 1.45; }}
        .criteria {{ margin-top: 12px; line-height: 1.45; }}
        .criteria-line {{ margin: 0 0 8px; padding-left: 0.2em; }}
        @page {{ size: A4 portrait; margin: 14mm; }}
        @media print {{
            .cards {{ grid-template-columns: 1fr; }}
            .card {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Compulsory Selection</h1>
        <p>Source PDF: {html.escape(source_name)}</p>
        <p>{html.escape(profile["category"])} | {html.escape(profile["division"])} |
            {html.escape(profile["track"])}</p>
    </header>
  <main>
    <div class=\"summary\">
      <div><strong>Selected elements</strong><br>{len(records)} /
        {profile["required_elements"]}</div>
      <div><strong>Allowed element range</strong><br>{profile["element_range"][0]:.1f} -
        {profile["element_range"][1]:.1f}</div>
      <div><strong>Total selected range</strong><br>{total_min:.1f} - {total_max:.1f}</div>
    </div>
    <div class=\"requirements\">
      <section>
        <h3>Requirements</h3>
        <ul>{requirements_html}</ul>
      </section>
      <section>
        <h3>Notes</h3>
        <ul>{notes_html or "<li>No extra notes for this profile.</li>"}</ul>
      </section>
    </div>
    <section class=\"cards\">{"".join(cards)}</section>
  </main>
</body>
</html>
"""


def _clear_selected_records() -> None:
    for key in list(st.session_state):
        if isinstance(key, str) and key.startswith("selected::"):
            del st.session_state[key]


def _handle_uploaded_pdf(uploaded_pdf: UploadedFile | None) -> None:
    if uploaded_pdf is None:
        st.sidebar.warning("Choose a PDF file first.")
        return
    pdf_bytes = uploaded_pdf.getvalue()
    if not pdf_bytes:
        st.sidebar.error("The uploaded PDF appears to be empty.")
        return
    with st.spinner("Extracting catalog from uploaded PDF..."):
        try:
            records = build_catalog_from_pdf_bytes(pdf_bytes, DATA_DIR, clean_output=True)
        except Exception as exc:  # noqa: BLE001
            st.sidebar.error(f"Extraction failed: {exc}")
            return
    if not records:
        st.sidebar.error("No compulsory catalog pages were detected in the uploaded PDF.")
        return
    source_name = uploaded_pdf.name or "uploaded.pdf"
    write_catalog(records, source_name, DATA_DIR)
    _clear_selected_records()
    st.cache_data.clear()
    st.sidebar.success(f"Extracted {len(records)} elements from {source_name}.")
    st.rerun()


def _render_rules(profile: dict[str, Any]) -> None:
    st.markdown(
        f"""
**Rules in use**

- Track: {profile["track"]}
- Required elements: {profile["required_elements"]}
- Allowed technical value per element: {profile["element_range"][0]:.1f} to
    {profile["element_range"][1]:.1f}
- Required total technical value: {profile["total_range"][0]:.1f} to {profile["total_range"][1]:.1f}
"""
    )
    if profile.get("requirements"):
        st.write("Required composition:")
        for item in profile["requirements"]:
            st.write(f"- {item}")
    if profile.get("notes"):
        st.write("Notes:")
        for item in profile["notes"]:
            st.write(f"- {item}")


def _render_element_browser(records: list[dict[str, Any]], max_results: int) -> None:
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
            st.checkbox(
                "Select",
                key=selection_key(record["code_number"]),
                value=st.session_state.get(selection_key(record["code_number"]), False),
            )
            st.caption(f"Section: {record['section']}")
            st.caption(f"Page: {record['page_number']}")
        with image_col:
            image_data = image_bytes_for(record)
            if image_data:
                st.image(image_data, use_container_width=True)
            else:
                st.info("No image extracted")
        with text_col:
            st.markdown(f"**Code**: {record['code_number']}")
            st.markdown(f"**Name**: {record['name']}")
            st.markdown(f"**Technical value**: {record['technical_value'].replace(chr(10), ' / ')}")
            st.markdown("**Criteria**")
            for line in record["criteria_lines"]:
                st.markdown(f"- {line}")
        st.divider()


def _render_printable_selection(
    records: list[dict[str, Any]], profile: dict[str, Any], source_name: str
) -> None:
    chosen_records = selected_records(records)
    st.subheader("Printable Selection")
    if not chosen_records:
        st.info("Select one or more elements to build the printable output.")
        return
    chosen_records.sort(key=lambda item: code_sort_key(item["code_number"]))
    selected_min = sum(record["value_min"] for record in chosen_records)
    selected_max = sum(record["value_max"] for record in chosen_records)
    summary_left, summary_mid, summary_right = st.columns(3)
    summary_left.metric("Selected count", len(chosen_records))
    summary_mid.metric("Selected total min", f"{selected_min:.1f}")
    summary_right.metric("Selected total max", f"{selected_max:.1f}")
    if len(chosen_records) != profile["required_elements"]:
        st.warning(
            f"This profile expects {profile['required_elements']} elements, but "
            f"{len(chosen_records)} are currently selected."
        )
    total_low, total_high = profile["total_range"]
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
    preview_data = [
        {
            "Code": record["code_number"],
            "Name": record["name"],
            "Section": record["section"],
            "Technical Value": record["technical_value"].replace("\n", " / "),
        }
        for record in chosen_records
    ]
    st.dataframe(preview_data, use_container_width=True, hide_index=True)
    export_html = render_export_html(chosen_records, profile, source_name)
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
        _handle_uploaded_pdf(uploaded_pdf)

    catalog = load_catalog()
    if catalog is None:
        st.error(
            f"No extracted catalog found at `{catalog_path()}`. "
            "Upload a PDF in the sidebar and click 'Extract Uploaded PDF', or run "
            "`python extract_catalog.py`."
        )
        return

    records, source_name = catalog
    st.sidebar.info(f"Loaded catalog extracted from: {source_name}")

    if not records:
        st.error("The extracted catalog is empty. Re-run extract_catalog.py to regenerate it.")
        return

    st.sidebar.header("Compulsory Profile")
    category = st.sidebar.selectbox("Category", list(PROFILE_RULES))
    division = st.sidebar.selectbox(
        "Division",
        list(PROFILE_RULES[category]["divisions"]),
    )
    profile = profile_details(category, division)

    section_options = sorted(
        {record["section"] for record in records if profile["track"] in record["tracks"]}
    )
    selected_sections = st.sidebar.multiselect("Sections", section_options)
    query = st.sidebar.text_input("Search", placeholder="Code, name, criteria...")
    max_results = st.sidebar.slider(
        "Visible results", min_value=10, max_value=200, value=40, step=10
    )

    filtered = filter_records(records, profile, query, selected_sections)
    chosen_records = selected_records(records)
    top_left, top_mid, top_right = st.columns(3)
    top_left.metric("Parsed elements", len(records))
    top_mid.metric("Matching this profile", len(filtered))
    top_right.metric("Currently selected", len(chosen_records))

    _render_rules(profile)
    st.divider()
    st.subheader("Element Browser")
    st.caption(
        "Use the search and section filters to narrow the list, then tick the "
        "elements you want in the printable export."
    )
    _render_element_browser(filtered, max_results)
    st.divider()
    _render_printable_selection(records, profile, source_name)


if __name__ == "__main__":
    main()
