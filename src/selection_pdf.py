# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.
"""PDF rendering for a printable element selection."""

from __future__ import annotations

import base64
import html
import io
from itertools import groupby
from typing import TYPE_CHECKING

import fitz

if TYPE_CHECKING:
    from src.models.catalog import CatalogRecord
    from src.models.frontend import SelectionContext

try:
    from src.catalog_common import code_sort_key
except ImportError:  # pragma: no cover
    from catalog_common import code_sort_key

ALL_CATEGORIES_OPTION = "All categories"
ALL_DIVISIONS_OPTION = "All divisions"
DEFAULT_PDF_TITLE = "My Compulsory Selection"


def format_value_range(value_min: float, value_max: float) -> str:
    if value_min == value_max:
        return f"{value_min:.1f}"
    return f"{value_min:.1f} - {value_max:.1f}"


PDF_PAGE_STYLE = """
<style>
body { font-family: Georgia, serif; color: #1f2933; }
h1 { font-size: 17px; margin: 0 0 6px; }
p.meta { margin: 2px 0; color: #52606d; font-size: 9px; }
h2.section-title {
    font-size: 12px; color: #8d5524; margin: 18px 0 6px;
    border-bottom: 1px solid #d9e2ec; padding-bottom: 2px;
}
table { border-collapse: collapse; width: 100%; margin-top: 6px; }
th, td {
    border: 1px solid #d9e2ec; padding: 4px 6px; font-size: 8px;
    text-align: left; vertical-align: top;
}
th { font-weight: bold; }
th.notes, td.notes { width: 200px; }
td.image-cell { width: 50px; text-align: center; }
.thumb { width: 44px; height: 44px; object-fit: contain; display: block; margin: 0 auto; }
ul.criteria { margin: 0; padding-left: 14px; }
ul.criteria li { margin-bottom: 4px; }
</style>
"""


def _record_thumbnail_html(record: CatalogRecord) -> str:
    image_data = record.image_bytes
    if not image_data:
        return ""
    image_b64 = base64.b64encode(image_data).decode("ascii")
    return (
        f'<img class="thumb" src="data:image/png;base64,{image_b64}" '
        f'alt="{html.escape(record.name)}">'
    )


def _record_criteria_html(record: CatalogRecord) -> str:
    criteria_items = "".join(f"<li>{html.escape(line)}</li>" for line in record.criteria_lines)
    return f'<ul class="criteria">{criteria_items}</ul>'


def _record_label_html(record: CatalogRecord) -> str:
    variant_description = record.variant_description
    variant_html = f"<br><em>{html.escape(variant_description)}</em>" if variant_description else ""
    return (
        f"<strong>{html.escape(record.code_number)}</strong><br>"
        f"{html.escape(record.name)}{variant_html}"
    )


def _section_table_html(
    section: str, section_records: list[CatalogRecord], *, notes_column: bool = False
) -> str:
    notes_cell = "<td class='notes'></td>" if notes_column else ""
    notes_header = "<th class='notes'>Notes</th>" if notes_column else ""
    rows_html = "".join(
        "".join(
            [
                "<tr>",
                f"<td>{_record_label_html(record)}</td>",
                f"<td class='image-cell'>{_record_thumbnail_html(record)}</td>",
                f"<td>{html.escape(record.technical_value.replace(chr(10), ' / '))}</td>",
                f"<td>{_record_criteria_html(record)}</td>",
                notes_cell,
                "</tr>",
            ]
        )
        for record in section_records
    )
    return "".join(
        [
            f"<h2 class='section-title'>{html.escape(section)}</h2>",
            "<table>",
            f"<tr><th>Element</th><th>Image</th><th>TV</th><th>Criteria</th>{notes_header}</tr>",
            rows_html,
            "</table>",
        ]
    )


def render_selection_pdf(
    records: list[CatalogRecord],
    context: SelectionContext,
    *,
    title: str = DEFAULT_PDF_TITLE,
    landscape: bool = False,
    notes_column: bool = False,
) -> bytes:
    """Render the selected elements as a PDF, grouped into one table per section."""
    total_min = sum(record.value_min for record in records)
    total_max = sum(record.value_max for record in records)
    grouped_records = sorted(
        records, key=lambda item: (item.section, code_sort_key(item.code_number))
    )
    sections_html = "".join(
        _section_table_html(section, list(section_records), notes_column=notes_column)
        for section, section_records in groupby(grouped_records, key=lambda item: item.section)
    )
    track = context.profile.track if context.profile else "All tracks"
    body_html = f"""
<html>
<head>{PDF_PAGE_STYLE}</head>
<body>
<h1>{html.escape(title.strip() or DEFAULT_PDF_TITLE)}</h1>
<p class="meta">Source PDF: {html.escape(context.source_name)}</p>
<p class="meta">
    {html.escape(context.category or ALL_CATEGORIES_OPTION)} |
    {html.escape(context.division or ALL_DIVISIONS_OPTION)} |
    {html.escape(track)}
</p>
<p class="meta">
    Selected count: {len(records)} |
    Selected total: {format_value_range(total_min, total_max)}
</p>
{sections_html}
</body>
</html>
"""
    mediabox = fitz.paper_rect("a4-l" if landscape else "a4")
    printable_area = mediabox + (36, 36, -36, -36)  # noqa: RUF005 -- fitz.Rect addition, not tuple concat

    def rect_function(
        rect_num: int,  # noqa: ARG001 -- fixed page layout, every call reuses the same rects
        filled: fitz.Rect,  # noqa: ARG001
    ) -> tuple[fitz.Rect, fitz.Rect, fitz.Matrix]:
        return mediabox, printable_area, fitz.Identity

    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    story = fitz.Story(html=body_html)
    story.write(writer, rect_function)
    writer.close()
    return buffer.getvalue()
