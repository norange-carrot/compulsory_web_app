"""Tests for printable selection PDF generation."""

import fitz

from src.models.catalog import CatalogRecord
from src.models.frontend import SelectionContext
from src.selection_pdf import render_selection_pdf


def test_render_selection_pdf_contains_selection_details():
    record = CatalogRecord(
        code_number="S1",
        name="Spin",
        technical_value="0.5",
        criteria="",
        criteria_lines=("Entry & control",),
        section="Skating",
        tracks=(),
        page_number=1,
        value_min=0.5,
        value_max=0.5,
    )
    context = SelectionContext(None, None, None, "catalog.pdf")

    pdf_bytes = render_selection_pdf([record], context)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        text = "\n".join(page.get_text() for page in pdf)

    assert "Printable Selection" in text
    assert "catalog.pdf" in text
    assert "Selected count: 1" in text
    assert "S1" in text
    assert "Entry & control" in text
