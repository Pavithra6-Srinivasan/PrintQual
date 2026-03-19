"""
pptx_service.py - Summary PowerPoint Generator

Key fixes:
  1. Height-aware pagination: estimates each row's actual height based on
     text wrap, cuts to next slide before overflow occurs.
  2. Table formatting matches target: uniform black borders on every cell,
     consistent row heights, blue header, white body, PASS/FAIL colour only
     in Overall Result column.
"""

from datetime import datetime
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from lxml import etree
import math


# ── Palette ───────────────────────────────────────────────────────────────────
COL_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
COL_BLACK   = RGBColor(0x00, 0x00, 0x00)
COL_BLUE    = RGBColor(0x44, 0x72, 0xC4)
COL_PASS_BG = RGBColor(0xC6, 0xEF, 0xCE)
COL_PASS_FG = RGBColor(0x00, 0x61, 0x00)
COL_FAIL_BG = RGBColor(0xFF, 0xC7, 0xCE)
COL_FAIL_FG = RGBColor(0xC0, 0x00, 0x00)
COL_NAVY    = RGBColor(0x1E, 0x27, 0x61)

# ── Slide layout (4:3 standard, inches) ───────────────────────────────────────
SLIDE_W = 10.0
SLIDE_H = 7.5

MARGIN  = 0.25
TABLE_X = MARGIN
TABLE_W = SLIDE_W - 2 * MARGIN   # 9.5"
TABLE_Y = 0.80                    # top of table on slide
TABLE_MAX_BOTTOM = 7.35           # furthest the table bottom can reach

TABLE_AVAIL_H = TABLE_MAX_BOTTOM - TABLE_Y   # 6.55"

# Column widths (inches) — must sum to TABLE_W = 9.5
COL_WIDTHS = [1.30, 1.15, 1.10, 1.70, 2.75, 1.50]
HEADERS    = ["Category", "Media Type", "Overall Result",
              "Error Type & Rate", "Failed Media Name", "Failed Units"]

# Approximate characters per line for each column at pt12 Calibri
# Used for wrap estimation. Calibri 12pt ≈ 0.085" per char.
CHAR_WIDTH_INCHES = 0.085
CELL_PAD_H = 0.06   # top + bottom padding in inches per cell (Pt3 * 2 / 72)

# Row heights
HEADER_ROW_H_IN = 0.36
DATA_ROW_BASE_H = 0.32   # minimum height for one line of pt12

# Font
PT_TITLE  = 18
PT_HEADER = 12
PT_BODY   = 12
FONT      = "Calibri"

NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


# ── Public entry point ────────────────────────────────────────────────────────

def generate_summary_pptx(output_path, summary_data, printer, variant,
                           sub_assembly, year, quarter):
    prs = Presentation()
    prs.slide_width  = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)

    _add_title_slide(prs, printer, variant, sub_assembly, year, quarter)

    for (tray, mode) in _collect_tray_mode_combos(summary_data):
        slide_title = f"Input Tray: {tray}   |   Print Mode: {mode}"
        all_rows    = _build_table_rows(summary_data, tray, mode)
        pages       = _paginate_by_height(all_rows, TABLE_AVAIL_H)

        for page_idx, page_rows in enumerate(pages):
            title = slide_title if page_idx == 0 else f"{slide_title}  (cont.)"
            _add_content_slide(prs, title, page_rows)

    prs.save(output_path)
    print(f"✓ Summary PowerPoint saved: {output_path}")


# ── Height-aware pagination ───────────────────────────────────────────────────

def _estimate_row_height(row_cols):
    """
    Estimate the rendered height of a data row in inches.
    Checks every cell and takes the maximum line-wrap count across columns.
    Returns height in inches.
    """
    max_lines = 1

    for ci, text in enumerate(row_cols):
        if not text:
            continue
        col_w = COL_WIDTHS[ci]
        usable_w = col_w - 0.08   # subtract left+right padding
        chars_per_line = max(1, int(usable_w / CHAR_WIDTH_INCHES))
        lines = math.ceil(len(str(text)) / chars_per_line)
        lines = max(1, lines)
        max_lines = max(max_lines, lines)

    return DATA_ROW_BASE_H * max_lines + CELL_PAD_H


def _paginate_by_height(rows, avail_height_inches):
    """
    Split rows into pages such that no page's table exceeds avail_height_inches.
    Accounts for: header row height + sum of estimated data row heights.
    """
    if not rows:
        return [[]]

    pages = []
    current_page = []
    # Start with header row height already consumed
    used = HEADER_ROW_H_IN

    for row in rows:
        row_h = _estimate_row_height(row["cols"])
        if current_page and (used + row_h) > avail_height_inches:
            # This row won't fit — start a new page
            pages.append(current_page)
            current_page = [row]
            used = HEADER_ROW_H_IN + row_h
        else:
            current_page.append(row)
            used += row_h

    if current_page:
        pages.append(current_page)

    return pages


# ── Title slide ───────────────────────────────────────────────────────────────

def _add_title_slide(prs, printer, variant, sub_assembly, year, quarter):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    bar = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(SLIDE_W), Inches(2.8)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = COL_NAVY
    bar.line.fill.background()

    def add_text(text, y, h, size, bold=False, color=COL_WHITE,
                 align=PP_ALIGN.CENTER):
        txb = slide.shapes.add_textbox(
            Inches(0.5), Inches(y), Inches(SLIDE_W - 1.0), Inches(h)
        )
        tf = txb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = FONT

    add_text("Life Test Data Analysis", 0.5, 0.8, 28, bold=True)
    add_text(f"{printer}  ·  {variant}  ·  {sub_assembly}", 1.4, 0.6, 18)
    add_text(f"Q{quarter}  FY{year}", 3.1, 0.6, 22, bold=True, color=COL_NAVY)
    add_text(
        f"Generated: {datetime.now().strftime('%d %b %Y   %H:%M')}",
        3.9, 0.5, 11, color=RGBColor(0x60, 0x60, 0x60)
    )


# ── Content slide ─────────────────────────────────────────────────────────────

def _add_content_slide(prs, title_text, data_rows):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    # Slide title
    txb = slide.shapes.add_textbox(
        Inches(MARGIN), Inches(0.10),
        Inches(TABLE_W), Inches(0.62)
    )
    tf = txb.text_frame
    p  = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = title_text
    run.font.size = Pt(PT_TITLE)
    run.font.bold = True
    run.font.color.rgb = COL_BLACK
    run.font.name = FONT

    if not data_rows:
        return

    # Calculate actual row heights for this page
    row_heights_in = [_estimate_row_height(r["cols"]) for r in data_rows]
    total_h = HEADER_ROW_H_IN + sum(row_heights_in)
    # Cap at available height just in case
    total_h = min(total_h, TABLE_AVAIL_H)

    n_total   = 1 + len(data_rows)
    tbl_shape = slide.shapes.add_table(
        n_total, len(HEADERS),
        Inches(TABLE_X), Inches(TABLE_Y),
        Inches(TABLE_W), Inches(total_h)
    )
    tbl = tbl_shape.table

    # Strip table band style so cell-level borders are not overridden
    _clear_table_style(tbl)

    # Column widths
    for ci, cw in enumerate(COL_WIDTHS):
        tbl.columns[ci].width = Inches(cw)

    # ── Header row ────────────────────────────────────────────────────────────
    for ci, hdr in enumerate(HEADERS):
        cell = tbl.cell(0, ci)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COL_BLUE
        _set_cell_text(cell, hdr, bold=True, fg=COL_WHITE,
                       size=PT_HEADER, align=PP_ALIGN.CENTER)
        _apply_black_border(cell)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for ri, row_meta in enumerate(data_rows):
        tbl_row = ri + 1
        cols    = row_meta["cols"]

        for ci, val in enumerate(cols):
            cell = tbl.cell(tbl_row, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COL_WHITE

            if ci == 2 and val in ("PASS", "FAIL"):
                if val == "PASS":
                    cell.fill.fore_color.rgb = COL_PASS_BG
                    _set_cell_text(cell, val, bold=True, fg=COL_PASS_FG,
                                   size=PT_BODY, align=PP_ALIGN.CENTER)
                else:
                    cell.fill.fore_color.rgb = COL_FAIL_BG
                    _set_cell_text(cell, val, bold=True, fg=COL_FAIL_FG,
                                   size=PT_BODY, align=PP_ALIGN.CENTER)
                _apply_black_border(cell)
                continue

            _set_cell_text(cell, str(val) if val else "",
                           size=PT_BODY, align=PP_ALIGN.LEFT)
            _apply_black_border(cell)

    # ── Row heights ───────────────────────────────────────────────────────────
    tbl.rows[0].height = Inches(HEADER_ROW_H_IN)
    for ri, h in enumerate(row_heights_in):
        tbl.rows[ri + 1].height = Inches(h)


# ── Table row builder ─────────────────────────────────────────────────────────

def _build_table_rows(summary_data, tray, mode):
    rows = []

    for cat in summary_data["categories"]:
        category_name = cat["category"]

        media_list = [
            m for m in cat["media_summaries"]
            if m["tray"] == tray and m["mode"] == mode
        ]
        if not media_list:
            continue

        first_cat_row = True

        for media in media_list:
            media_type     = media["media_type"]
            overall_result = media["overall_result"]
            errors         = media.get("errors", [])

            if overall_result != "FAIL" or not errors:
                rows.append({
                    "cols": [
                        category_name if first_cat_row else "",
                        media_type,
                        overall_result,
                        "", "", ""
                    ],
                    "result": overall_result
                })
                first_cat_row = False
                continue

            first_media_row = True

            for err in errors:
                error_label   = f"{err['error']}: {err['rate']:.3f}/K"
                first_err_row = True

                for entry in err["failed_media"]:
                    media_name = entry["media_name"]
                    units_str  = ", ".join(entry["units"]) if entry["units"] else ""

                    rows.append({
                        "cols": [
                            category_name  if first_cat_row   else "",
                            media_type     if first_media_row else "",
                            overall_result if first_media_row else "",
                            error_label    if first_err_row   else "",
                            media_name,
                            units_str
                        ],
                        "result": overall_result
                    })

                    first_cat_row   = False
                    first_media_row = False
                    first_err_row   = False

    return rows


# ── XML helpers ───────────────────────────────────────────────────────────────

def _clear_table_style(tbl):
    """
    Remove PowerPoint's built-in table band/style so cell-level border
    and fill settings are not overridden by the theme.
    """
    tblPr = tbl._tbl.find(f"{{{NS}}}tblPr")
    if tblPr is None:
        return
    style_el = tblPr.find(f"{{{NS}}}tableStyleId")
    if style_el is not None:
        style_el.text = "{00000000-0000-0000-0000-000000000000}"
    for attr in ("bandRow", "bandCol", "firstRow", "firstCol", "lastRow", "lastCol"):
        tblPr.set(attr, "0")


def _apply_black_border(cell):
    """
    Write 1pt solid black border on all four sides of a table cell.
    Done via direct XML manipulation — python-pptx has no public API for this.
    """
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()

    for tag in ("lnL", "lnR", "lnT", "lnB"):
        for el in tcPr.findall(f"{{{NS}}}{tag}"):
            tcPr.remove(el)
        ln = etree.SubElement(tcPr, f"{{{NS}}}{tag}", attrib={"w": "12700"})
        sf = etree.SubElement(ln, f"{{{NS}}}solidFill")
        etree.SubElement(sf, f"{{{NS}}}srgbClr", attrib={"val": "000000"})


def _set_cell_text(cell, text, bold=False, fg=None,
                   size=PT_BODY, align=PP_ALIGN.LEFT):
    tf = cell.text_frame
    tf.word_wrap = True
    tf.margin_left   = Pt(3)
    tf.margin_right  = Pt(3)
    tf.margin_top    = Pt(2)
    tf.margin_bottom = Pt(2)

    p = tf.paragraphs[0]
    p.alignment = align

    for run in p.runs:
        run.text = ""

    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = FONT
    run.font.color.rgb = fg if fg else COL_BLACK


# ── Misc ──────────────────────────────────────────────────────────────────────

def _collect_tray_mode_combos(summary_data):
    combos = set()
    for cat in summary_data["categories"]:
        for m in cat["media_summaries"]:
            combos.add((m["tray"], m["mode"]))
    return sorted(combos, key=lambda x: (str(x[0]), str(x[1])))