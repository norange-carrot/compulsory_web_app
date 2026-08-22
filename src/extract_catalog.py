# Copyright (c) 2026 norangecarrot.
# All Rights Reserved.
# Licensed under the MIT.

"""Part 1: read the IPSF Code of Points PDF and save its content to disk.

Run this once (or whenever the source PDF changes) to produce:
  - data/catalog.json  -- text fields for every parsed compulsory element
  - data/images/*       -- the illustration for each element, extracted at its
                           exact embedded-image position (native quality where
                           a single image matches, a tight rendered crop otherwise)

These helpers can also be imported by the Streamlit app to extract directly from
an uploaded PDF (no separate extraction script step required).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz

from src.catalog_common import (
    DEADLIFT_VARIANT_RE,
    VALUE_RE,
    code_sort_key,
    compact_whitespace,
    is_code_fragment,
    prefix_for_code,
    section_for_code,
    tracks_for_code,
)

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "data"
MAX_IMAGE_SIZE = 8
MIN_CLIP_HEIGHT = 10
MIN_PAGE_TEXT_Y = 70
CODE_COLUMN_X_MIN = 40
CODE_COLUMN_X_MAX = 180
NAME_BLOCK_MAX_Y_OFFSET = 50
TECHNICAL_VALUE_COLUMN_X_MIN = 310
TECHNICAL_VALUE_COLUMN_X_MAX = 345
DOUBLE_CODE_COUNT = 2
MIN_DOUBLE_VARIANT_COUNT = 6
MIN_IMAGE_CLIP_DIMENSION = 2


@dataclass
class _PageExtractionContext:
    document: fitz.Document
    page: fitz.Page
    page_index: int
    images_dir: Path
    image_placements: list[dict[str, Any]]
    blocks: list[dict[str, Any]]
    starts: list[dict[str, Any]]


def prepare_output_dirs(output_dir: Path, *, clean_output: bool = False) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    if clean_output and images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def default_pdf_path() -> Path | None:
    workspace = Path(__file__).resolve().parent
    candidates = sorted(workspace.glob("*.pdf"))
    return candidates[0] if candidates else None


def page_is_catalog(page: fitz.Page) -> bool:
    text = page.get_text("text").lower()
    return (
        "code" in text
        and "criteria" in text
        and "tech." in text
        and len(page.get_images(full=True)) > 0
    )


def parse_code_and_name(text: str) -> tuple[str, str] | None:
    lines = [compact_whitespace(line) for line in text.splitlines() if compact_whitespace(line)]
    if not lines or not is_code_fragment(lines[0]):
        return None

    code_lines: list[str] = []
    index = 0
    while index < len(lines) and is_code_fragment(lines[index]):
        code_lines.append(re.sub(r"\s+", "", lines[index]))
        index += 1

    if not code_lines:
        return None

    code_number = "".join(code_lines)
    name = compact_whitespace(" ".join(lines[index:]))
    if not name:
        return None
    return code_number, name


def parse_code_only(text: str) -> str | None:
    lines = [compact_whitespace(line) for line in text.splitlines() if compact_whitespace(line)]
    if not lines or not is_code_fragment(lines[0]):
        return None

    code_lines: list[str] = []
    index = 0
    while index < len(lines) and is_code_fragment(lines[index]):
        code_lines.append(re.sub(r"\s+", "", lines[index]))
        index += 1

    if index != len(lines):
        return None
    return "".join(code_lines) if code_lines else None


def looks_like_criteria_text(text: str) -> bool:
    text = compact_whitespace(text).lower()
    if not text:
        return False
    return bool(
        re.search(
            r"(?:^|\b)(hold the position|points of contact|arm position|grip|"
            r"leg position|body position|rotation|criteria|refer to|apply|"
            r"angle away|minimum)(?:\b|:)",
            text,
        )
    )


def looks_like_criteria_field(text: str) -> bool:
    text = compact_whitespace(text).lower()
    if not text:
        return False
    return bool(
        re.match(
            r"^(hold the position|points of contact|arm position|grip|leg position|"
            r"body position|rotation|criteria)(:|$)",
            text,
        )
    )


def normalize_criteria_lines(text: str) -> list[str]:
    lines = [compact_whitespace(line) for line in text.splitlines() if compact_whitespace(line)]
    if not lines:
        return []

    normalized: list[str] = []
    for line in lines:
        formatted_line = re.sub(r"^[\-•]\s*", "", line)
        if not formatted_line:
            continue
        if not normalized:
            normalized.append(formatted_line)
            continue
        if looks_like_criteria_field(formatted_line) or looks_like_criteria_field(normalized[-1]):
            normalized.append(formatted_line)
        else:
            normalized[-1] = f"{normalized[-1]} {formatted_line}"

    return [compact_whitespace(line) for line in normalized]


def sanitize_filename(code_number: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", code_number)


def page_image_placements(page: fitz.Page) -> list[dict[str, Any]]:
    """Real embedded-image bounding boxes on this page, sorted top-to-bottom.

    Using the PDF's own image placement rectangles (instead of a guessed crop
    window derived from text positions) is what lets us match each row to its
    exact illustration, with no bleed from neighboring rows or text columns.
    """
    placements: list[dict[str, Any]] = []
    for xref, *_ in page.get_images(full=True):
        for rect in page.get_image_rects(xref):
            if rect.width < MAX_IMAGE_SIZE or rect.height < MAX_IMAGE_SIZE:
                continue
            placements.append({"xref": xref, "rect": rect})
    placements.sort(key=lambda item: (item["rect"].y0, item["rect"].x0))
    return placements


def match_row_images(
    placements: list[dict[str, Any]], row_top: float, row_bottom: float
) -> list[dict[str, Any]]:
    matches = []
    for placement in placements:
        rect = placement["rect"]
        overlap = min(rect.y1, row_bottom) - max(rect.y0, row_top)
        if overlap > 0.3 * rect.height:
            matches.append(placement)
    return matches


def render_crop_png_bytes(page: fitz.Page, start_y: float, end_y: float) -> bytes | None:
    clip = fitz.Rect(170, max(start_y - 10, 70), 320, min(end_y - 8, page.rect.height - 20))
    if clip.height <= MIN_CLIP_HEIGHT:
        return None
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.7, 1.7), clip=clip, alpha=False)
    return pixmap.tobytes("png")


def extract_row_image(
    document: fitz.Document,
    page: fitz.Page,
    matches: list[dict[str, Any]],
    region_top: float,
    region_bottom: float,
) -> tuple[bytes, str] | None:
    """Return (image_bytes, file_extension) for a row, preferring lossless extraction.

    A single matched placement is pulled straight out of the PDF via extract_image,
    which returns the original embedded bytes untouched (no re-rasterization or
    scaling artifacts). Multiple placements (e.g. an entry/exit pose pair) are
    combined by rendering a tight pixmap clip of their exact union rectangle.
    """
    if len(matches) == 1:
        xref = matches[0]["xref"]
        info = document.extract_image(xref)
        if info and info.get("image"):
            return info["image"], info.get("ext", "png")

    if matches:
        union = matches[0]["rect"]
        for placement in matches[1:]:
            union |= placement["rect"]
        pad = 3
        clip = fitz.Rect(union.x0 - pad, union.y0 - pad, union.x1 + pad, union.y1 + pad) & page.rect
        if clip.width > MIN_IMAGE_CLIP_DIMENSION and clip.height > MIN_IMAGE_CLIP_DIMENSION:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip, alpha=False)
            return pixmap.tobytes("png"), "png"

    fallback = render_crop_png_bytes(page, region_top, region_bottom)
    if fallback:
        return fallback, "png"
    return None


def expand_deadlift_variants(record: dict[str, Any]) -> list[dict[str, Any]]:
    if prefix_for_code(record["code_number"]) not in {"DL", "ADL"}:
        return [record]

    variants = DEADLIFT_VARIANT_RE.findall(record["technical_value"])
    if not variants:
        return [record]

    base_codes = [part for part in record["code_number"].split("/") if part]
    expanded: list[dict[str, Any]] = []

    if len(base_codes) == 1:
        grouped = [(base_codes[0], variants)]
    elif len(base_codes) == DOUBLE_CODE_COUNT and len(variants) >= MIN_DOUBLE_VARIANT_COUNT:
        grouped = [
            (base_codes[0], variants[:3]),
            (base_codes[1], variants[3:6]),
        ]
    else:
        return [record]

    for base_code, group in grouped:
        for letter, value in group:
            variant = dict(record)
            variant["code_number"] = f"{base_code}{letter.lower()}"
            variant["technical_value"] = value
            variant["value_min"] = float(value)
            variant["value_max"] = float(value)
            variant["section"] = section_for_code(base_code)
            expanded.append(variant)

    return expanded or [record]


def _page_text_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    blocks = []
    for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
        cleaned = text.strip()
        if not cleaned or y0 < MIN_PAGE_TEXT_Y or y1 > page.rect.height - 40:
            continue
        blocks.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "text": cleaned})

    blocks.sort(key=lambda block: (block["y0"], block["x0"]))
    return blocks


def _catalog_start_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        block
        for block in blocks
        if block["x0"] < CODE_COLUMN_X_MAX
        and (parse_code_and_name(block["text"]) or parse_code_only(block["text"]))
    ]


def _row_region(
    starts: list[dict[str, Any]], index: int, page_height: float
) -> tuple[float, float, float]:
    start_block = starts[index]
    previous_start_y = starts[index - 1]["y0"] if index > 0 else 84
    next_start_y = starts[index + 1]["y0"] if index + 1 < len(starts) else page_height - 24
    midpoint_top = (previous_start_y + start_block["y0"]) / 2 if index > 0 else 84
    region_top = max(84, min(midpoint_top, start_block["y0"] - 90))
    region_bottom = (
        (start_block["y0"] + next_start_y) / 2 if index + 1 < len(starts) else page_height - 24
    )
    return midpoint_top, region_top, region_bottom


def _parse_start_block(start_block: dict[str, Any]) -> tuple[str, str] | None:
    parsed = parse_code_and_name(start_block["text"])
    if parsed:
        return parsed
    code_only = parse_code_only(start_block["text"])
    return (code_only, "") if code_only else None


def _name_blocks_for_row(
    blocks: list[dict[str, Any]], start_block: dict[str, Any], region_bottom: float
) -> list[dict[str, Any]]:
    left_blocks = [
        block
        for block in blocks
        if start_block["y0"] <= block["y0"] < region_bottom
        and CODE_COLUMN_X_MIN <= block["x0"] < CODE_COLUMN_X_MAX
        and block is not start_block
    ]
    name_blocks = []
    for left_block in left_blocks:
        if parse_code_and_name(left_block["text"]) or parse_code_only(left_block["text"]):
            continue
        if looks_like_criteria_text(left_block["text"]):
            continue
        if left_block["y0"] - start_block["y0"] > NAME_BLOCK_MAX_Y_OFFSET:
            continue
        name_blocks.append(left_block)
    return name_blocks


def _row_name(name: str, name_blocks: list[dict[str, Any]]) -> str:
    if not name_blocks:
        return name
    name_parts = [
        name,
        *[block["text"] for block in sorted(name_blocks, key=lambda item: item["y0"])],
    ]
    return compact_whitespace(" ".join(name_parts))


def _row_content(
    blocks: list[dict[str, Any]],
    start_block: dict[str, Any],
    region_top: float,
    region_bottom: float,
    name_blocks: list[dict[str, Any]],
) -> tuple[str, str, list[str], list[float]]:
    tech_blocks = [
        block
        for block in blocks
        if region_top <= block["y0"] < region_bottom
        and TECHNICAL_VALUE_COLUMN_X_MIN <= block["x0"] <= TECHNICAL_VALUE_COLUMN_X_MAX
        and VALUE_RE.search(block["text"])
    ]
    criteria_blocks = [
        block
        for block in blocks
        if region_top <= block["y0"] < region_bottom
        and (block["x0"] >= TECHNICAL_VALUE_COLUMN_X_MAX or looks_like_criteria_text(block["text"]))
    ]
    criteria_blocks = [
        block
        for block in criteria_blocks
        if block is not start_block
        and block not in name_blocks
        and compact_whitespace(block["text"])
    ]
    criteria_blocks.sort(key=lambda block: (block["y0"], block["x0"]))

    technical_value = "\n".join(block["text"].strip() for block in tech_blocks)
    criteria_text = "\n".join(block["text"].strip() for block in criteria_blocks)
    criteria_lines = normalize_criteria_lines(criteria_text)
    numeric_values = [float(value) for value in VALUE_RE.findall(technical_value)]
    return technical_value, criteria_text, criteria_lines, numeric_values


def _save_row_image(
    context: _PageExtractionContext,
    midpoint_top: float,
    region_top: float,
    region_bottom: float,
    code_number: str,
) -> str | None:
    row_matches = match_row_images(context.image_placements, midpoint_top, region_bottom)
    extracted = extract_row_image(
        context.document, context.page, row_matches, region_top, region_bottom
    )
    if not extracted:
        return None
    image_bytes, extension = extracted
    filename = f"{sanitize_filename(code_number)}_{context.page_index + 1}.{extension}"
    (context.images_dir / filename).write_bytes(image_bytes)
    return f"images/{filename}"


def _extract_row_record(
    context: _PageExtractionContext,
    index: int,
) -> dict[str, Any] | None:
    start_block = context.starts[index]
    parsed_start = _parse_start_block(start_block)
    if not parsed_start:
        return None
    code_number, name = parsed_start
    midpoint_top, region_top, region_bottom = _row_region(
        context.starts, index, context.page.rect.height
    )
    name_blocks = _name_blocks_for_row(context.blocks, start_block, region_bottom)
    name = _row_name(name, name_blocks)
    if not name:
        return None

    technical_value, criteria_text, criteria_lines, numeric_values = _row_content(
        context.blocks, start_block, region_top, region_bottom, name_blocks
    )
    if not numeric_values or not criteria_lines:
        return None

    image_path = _save_row_image(
        context,
        midpoint_top,
        region_top,
        region_bottom,
        code_number,
    )
    return {
        "code_number": code_number,
        "name": name,
        "technical_value": technical_value,
        "criteria": criteria_text,
        "criteria_lines": criteria_lines,
        "section": section_for_code(code_number),
        "tracks": sorted(tracks_for_code(code_number)),
        "page_number": context.page_index + 1,
        "value_min": min(numeric_values),
        "value_max": max(numeric_values),
        "image_path": image_path,
    }


def extract_page_records(
    document: fitz.Document, page_index: int, images_dir: Path
) -> list[dict[str, Any]]:
    page = document[page_index]
    blocks = _page_text_blocks(page)
    starts = _catalog_start_blocks(blocks)
    context = _PageExtractionContext(
        document, page, page_index, images_dir, page_image_placements(page), blocks, starts
    )

    records: list[dict[str, Any]] = []
    for index in range(len(starts)):
        raw_record = _extract_row_record(context, index)
        if raw_record:
            records.extend(expand_deadlift_variants(raw_record))

    return records


def _build_catalog_from_document(document: fitz.Document, images_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for page_index in range(document.page_count):
        page = document[page_index]
        if not page_is_catalog(page):
            continue
        for record in extract_page_records(document, page_index, images_dir):
            if record["code_number"] in seen_codes:
                continue
            seen_codes.add(record["code_number"])
            records.append(record)

    records.sort(key=lambda item: (item["section"], code_sort_key(item["code_number"])))
    return records


def build_catalog(
    pdf_path: Path, output_dir: Path, *, clean_output: bool = False
) -> list[dict[str, Any]]:
    images_dir = prepare_output_dirs(output_dir, clean_output=clean_output)
    with fitz.open(pdf_path) as document:
        return _build_catalog_from_document(document, images_dir)


def build_catalog_from_pdf_bytes(
    pdf_bytes: bytes, output_dir: Path, *, clean_output: bool = False
) -> list[dict[str, Any]]:
    images_dir = prepare_output_dirs(output_dir, clean_output=clean_output)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        return _build_catalog_from_document(document, images_dir)


def write_catalog(records: list[dict[str, Any]], source_pdf_name: str, output_dir: Path) -> None:
    catalog_path = output_dir / "catalog.json"
    catalog_path.write_text(
        json.dumps({"source_pdf": source_pdf_name, "elements": records}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract the IPSF Code of Points catalog from a PDF into JSON + image files."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        default=None,
        help="Path to the source PDF (defaults to the bundled .pdf file in this folder).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write catalog.json and images/ into (default: ./data).",
    )
    args = parser.parse_args()

    pdf_path = args.pdf or default_pdf_path()
    if pdf_path is None or not pdf_path.exists():
        parser.error("No PDF found. Pass a path or place a .pdf file in this folder.")

    records = build_catalog(pdf_path, args.output_dir, clean_output=True)
    if not records:
        parser.error("No compulsory element catalog pages were detected in this PDF.")

    write_catalog(records, pdf_path.name, args.output_dir)


if __name__ == "__main__":
    main()
