"""
pptx_service.py - Summary PowerPoint Generator

Layout:
  Slide 1 : Title slide
  Slide N+: Content slides

  Each content slide can contain multiple (heading + table) blocks stacked
  vertically. Each block corresponds to one (Input Tray + Test Category)
  combination.

  Heading: bold text box — "Input Tray: X  |  Category: Y"
  Table columns: Print Mode | Media Type | Overall Result |
                 Error Type & Rate | Failed Media Name | Failed Units

  Pagination:
  - Fit as many blocks as possible per slide
  - If a block (heading + table) does not fit, move entire block to next slide
  - If a single table is too tall on its own, split it across slides
    with heading repeated as "(cont.)"

Font: 11pt throughout table
"""

import copy
import math
from datetime import datetime

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ── Colours ───────────────────────────────────────────────────────────────────
COL_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
COL_BLACK   = RGBColor(0x00, 0x00, 0x00)
COL_BLUE    = RGBColor(0x44, 0x72, 0xC4)
COL_PASS_BG = RGBColor(0xC6, 0xEF, 0xCE)
COL_PASS_FG = RGBColor(0x00, 0x61, 0x00)
COL_FAIL_BG = RGBColor(0xFF, 0xC7, 0xCE)
COL_FAIL_FG = RGBColor(0xC0, 0x00, 0x00)
COL_NAVY    = RGBColor(0x1E, 0x27, 0x61)

# ── Slide geometry (16:9 widescreen, inches) ─────────────────────────────────
SLIDE_W       = 10.0
SLIDE_H       = 5.625
MARGIN        = 0.25
TABLE_X       = MARGIN
TABLE_W       = SLIDE_W - 2 * MARGIN   # 9.5"
SLIDE_TOP     = 0.20                    # where content starts
SLIDE_BOTTOM  = 5.50                    # furthest content can reach
AVAIL_H       = SLIDE_BOTTOM - SLIDE_TOP  # 5.30" total per slide

# Column widths — must sum to TABLE_W = 9.5"
# MediaType | PrintMode | Spec | Result | Error | MediaName | Units
COL_W   = [1.10, 1.00, 0.75, 1.00, 1.55, 2.60, 1.50]
HEADERS = ["Media Type", "Print Mode", "Spec", "Overall Result",
           "Error Type", "Media Name", "Unit"]
N_COLS  = len(HEADERS)

# Typography
FONT      = "Calibri"
PT_TITLE  = 18     # title slide / slide title
PT_HDG    = 10     # block heading text
PT_HEADER = 9      # table column header
PT_BODY   = 9      # table body

# Row geometry (sized for pt9, compact)
HDR_H      = 0.19   # table header row height (inches)
ROW_BASE_H = 0.15   # base height per data row (one line)
ROW_PAD_H  = 0.01   # top+bottom cell padding
CHAR_W_IN  = 0.064  # approximate Calibri-9 char width in inches

# Block heading height (text box above each table)
BLOCK_HDG_H  = 0.25   # inches
BLOCK_GAP    = 0.15   # gap between bottom of one block and top of next

# XML namespace
NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC
# ═══════════════════════════════════════════════════════════════════════════════

def generate_summary_pptx(output_path, summary_data, printer, variant,
                           sub_assembly, year, quarter, overview=None):
    prs = Presentation()
    prs.slide_width  = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)

    # Slide 1: Title slide
    if overview:
        _add_title_slide_new(prs, overview, printer, variant, year, quarter)

    # Slide 2: Overview slide
    if overview:
        _add_overview_slide(prs, overview, summary_data,
                            printer, variant, year, quarter)

    # Slides 3+: Content slides (one per tray+category block)
    all_blocks = _build_all_blocks(summary_data)
    slides     = _paginate_blocks(all_blocks)

    for slide_blocks in slides:
        _add_content_slide(prs, slide_blocks)

    # Post-process: wire up hyperlinks from overview remarks to content slides
    _apply_overview_hyperlinks(prs)

    prs.save(output_path)
    print(f"✓ Summary PowerPoint saved: {output_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# HYPERLINK POST-PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_overview_hyperlinks(prs):
    """
    After all slides are created, wire up hyperlinks in the overview remarks
    cells. Each remark cell links to the first content slide matching that
    (tray, category) combination.
    """
    if not hasattr(prs, '_overview_hyperlinks'):
        return

    # Build a map: heading_str → slide index
    slide_map = {}
    for idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame:
                txt = shape.text_frame.text.strip()
                if txt and "Input Tray:" in txt and "Category:" in txt:
                    slide_map[txt] = idx

    for link_info in prs._overview_hyperlinks:
        cat_name = link_info["cat_name"]
        tray     = link_info["tray"]
        table    = link_info["table"]
        row      = link_info["row"]
        col      = link_info["col"]

        # Find matching slide
        target_idx = None
        for heading, idx in slide_map.items():
            if f"Category: {cat_name}" in heading:
                target_idx = idx
                break

        if target_idx is None:
            continue

        # Apply hyperlink to the remarks cell using slide reference
        cell       = table.cell(row, col)
        tc         = cell._tc
        tf_el      = tc.find(
            f"{{{NS}}}txBody"
        )
        if tf_el is None:
            continue

        # Add hyperlink via relationship on the slide
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        target_slide = prs.slides[target_idx]
        rId = link_info["slide_obj"].part.relate_to(
            target_slide.part,
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
        )

        # Wrap all runs in the cell's first paragraph with a hyperlink
        NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
        for para in tf_el.findall(f"{{{NS_A}}}p"):
            runs = para.findall(f"{{{NS_A}}}r")
            if not runs:
                continue
            # Create hlinkClick on first run's rPr
            for run_el in runs:
                rPr = run_el.find(f"{{{NS_A}}}rPr")
                if rPr is None:
                    rPr = etree.SubElement(run_el, f"{{{NS_A}}}rPr")
                    run_el.insert(0, rPr)
                # Remove existing hlinkClick if any
                for hl in rPr.findall(
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}hlinkClick"
                ):
                    rPr.remove(hl)
                hl = etree.SubElement(
                    rPr,
                    "{http://schemas.openxmlformats.org/drawingml/2006/main}hlinkClick",
                    attrib={
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id": rId,
                        "action": "ppaction://hlinksldjump"
                    }
                )
                # Style the hyperlink text in blue underline
                rPr.set("u", "sng")
                clr_el = etree.SubElement(rPr, f"{{{NS_A}}}solidFill")
                etree.SubElement(clr_el, f"{{{NS_A}}}srgbClr",
                                 attrib={"val": "1F4E79"})


# ═══════════════════════════════════════════════════════════════════════════════
# BUILD BLOCKS
# Each block: {"heading": str, "rows": [flat_row, ...], "cont": bool}
# ═══════════════════════════════════════════════════════════════════════════════

def _build_all_blocks(summary_data):
    """
    Build one block per (tray, category) combination.
    Each block contains flat rows for that combination.
    Columns: print_mode | media_type | result | error | media_name | units
    """
    # Collect unique (tray, category) combos in order
    combos = []
    seen   = set()
    for cat in summary_data["categories"]:
        cat_name = cat["category"]
        for m in cat["media_summaries"]:
            key = (m["tray"], cat_name)
            if key not in seen:
                seen.add(key)
                combos.append(key)

    blocks = []
    for (tray, cat_name) in combos:
        heading  = f"Input Tray: {tray}   |   Category: {cat_name}"
        flat_rows = _build_flat_rows(summary_data, tray, cat_name)
        if flat_rows:
            blocks.append({"heading": heading, "rows": flat_rows, "cont": False})

    return blocks


def _build_flat_rows(summary_data, tray, cat_name):
    """
    Build flat rows grouped by media type first (Plain always first),
    then print mode within each media type.
    - Rates shown to 2 decimal places
    - Media name includes its own fail rate
    - Spec column added from media summary
    - NO SPEC rows show error type only
    """
    raw = []
    for cat in summary_data["categories"]:
        if cat["category"] != cat_name:
            continue
        for m in cat["media_summaries"]:
            if m["tray"] == tray:
                raw.append(m)

    if not raw:
        return []

    # Group by media_type
    media_order  = []
    media_groups = {}
    for m in raw:
        mt = m["media_type"]
        if mt not in media_groups:
            media_order.append(mt)
            media_groups[mt] = []
        media_groups[mt].append(m)

    # Change 1: Plain always first
    if "Plain" in media_order:
        media_order.remove("Plain")
        media_order.insert(0, "Plain")

    rows = []

    for mt in media_order:
        first_media_row = True

        for media in media_groups[mt]:
            mode   = str(media["mode"]) if media["mode"] else ""
            result = media["overall_result"]
            errors = media.get("errors", [])
            # Change 4: spec value
            spec_val = media.get("spec", None)
            spec_str = f"{spec_val:.2f}" if spec_val is not None else ""

            if result not in ("FAIL", "NO SPEC", "PASS") or not errors:
                rows.append(_flat(
                    mt if first_media_row else "",
                    mode,
                    spec_str if first_media_row else "",
                    result, "", "", ""
                ))
                first_media_row = False
                continue

            first_mode_row = True

            for err in errors:
                # Change 2: 2dp rates
                label = f"{err['error']}: {err['rate']:.2f}/K"

                if result == "NO SPEC":
                    rows.append(_flat(
                        mt       if first_media_row else "",
                        mode     if first_mode_row  else "",
                        spec_str if first_mode_row  else "",
                        result   if first_mode_row  else "",
                        label, "", ""
                    ))
                    first_media_row = False
                    first_mode_row  = False
                else:
                    first_err_row = True
                    for entry in err["failed_media"]:
                        units = ", ".join(entry["units"]) if entry["units"] else ""
                        # Change 3: include media name rate
                        media_rate = entry.get("rate", None)
                        media_label = entry["media_name"]
                        if media_rate is not None:
                            media_label = f"{entry['media_name']} ({media_rate:.2f}/K)"
                        rows.append(_flat(
                            mt       if first_media_row else "",
                            mode     if first_mode_row  else "",
                            spec_str if first_mode_row  else "",
                            result   if first_mode_row  else "",
                            label    if first_err_row   else "",
                            media_label, units
                        ))
                        first_media_row = False
                        first_mode_row  = False
                        first_err_row   = False

    return rows


def _flat(media, mode, spec, result, error, media_name, units):
    return {"media": media, "mode": mode, "spec": spec, "result": result,
            "error": error, "media_name": media_name, "units": units,
            "cols": [media, mode, spec, result, error, media_name, units]}


# ═══════════════════════════════════════════════════════════════════════════════
# HEIGHT ESTIMATION
# ═══════════════════════════════════════════════════════════════════════════════

def _estimate_row_h(row):
    max_lines = 1
    for ci, text in enumerate(row["cols"]):
        if not text:
            continue
        usable = max(0.1, COL_W[ci] - 0.10)
        cpl    = max(1, int(usable / CHAR_W_IN))
        lines  = max(1, math.ceil(len(str(text)) / cpl))
        max_lines = max(max_lines, lines)
    return ROW_BASE_H * max_lines + ROW_PAD_H


def _block_height(block):
    """Total height of heading + table for a block."""
    rows_h = HDR_H + sum(_estimate_row_h(r) for r in block["rows"])
    return BLOCK_HDG_H + rows_h


# ═══════════════════════════════════════════════════════════════════════════════
# PAGINATION
# Fit as many blocks as possible per slide.
# If a block is too tall for a slide on its own, split its rows.
# ═══════════════════════════════════════════════════════════════════════════════

def _paginate_blocks(all_blocks):
    """
    One block per slide. If a block's rows are too tall for one slide,
    split rows across slides with heading repeated as "(cont.)".
    This guarantees headings never overlap tables.
    """
    slides = []

    for block in all_blocks:
        remaining_rows = list(block["rows"])
        first_chunk    = True

        while remaining_rows:
            chunk   = []
            avail   = AVAIL_H - BLOCK_HDG_H - HDR_H
            chunk_h = 0.0

            for row in remaining_rows:
                rh = _estimate_row_h(row)
                if chunk and chunk_h + rh > avail:
                    break
                chunk.append(row)
                chunk_h += rh

            if not chunk:
                # Single row too tall — force it to avoid infinite loop
                chunk = [remaining_rows[0]]

            heading = block["heading"] if first_chunk \
                      else block["heading"] + "  (cont.)"

            slides.append([{"heading": heading,
                             "rows":    chunk,
                             "cont":    not first_chunk}])
            remaining_rows = remaining_rows[len(chunk):]
            first_chunk    = False

    return slides



# ═══════════════════════════════════════════════════════════════════════════════
# OVERVIEW SLIDE
# ═══════════════════════════════════════════════════════════════════════════════

def _add_title_slide_new(prs, overview, printer, variant, year, quarter):
    """
    Slide 1: Clean title slide.
    Line 1+2: "{printer} {variant}" — large black, centred
    Line 3:   test name — large black, centred
    Line 4:   "Q{q}FY{year}" — navy blue, centred
    Line 5:   "Date : {today}" — navy blue, centred
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    def add_text(text, y, h, size, color=COL_BLACK):
        txb = slide.shapes.add_textbox(
            Inches(MARGIN), Inches(y), Inches(TABLE_W), Inches(h))
        tf = txb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text           = text
        run.font.size      = Pt(size)
        run.font.color.rgb = color
        run.font.name      = FONT

    test_name = overview.get("objective", "")

    add_text(f"{printer} {variant}",   0.50, 0.65, 30)
    add_text(test_name,                1.25, 0.65, 30)
    add_text(f"Q{quarter}FY{year}",    2.15, 0.40, 16, color=COL_NAVY)
    add_text(
        f"Date : {datetime.now().strftime('%d %b %Y')}",
        2.65, 0.35, 14, color=COL_NAVY
    )


def _add_overview_slide(prs, overview, summary_data, printer, variant, year, quarter):
    """
    Slide 2: overview slide.
    Title: "{printer} {variant} Q{q}FY{year} {test_name}"
    Left side:
      Top table  — Unit | Actual Test Life Per Unit | Test Start | Test End
      Bot table  — Unit Number | Serial Number | FW Version (blank rows)
    Right side:
      Table — Category | Result | Remarks
              Remarks = "{media_type}_{tray}_{mode}_{error}({rate})" per line
              Each remark hyperlinks to its content slide
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    test_name = overview.get("objective", "")
    title_str = f"{printer} {variant} Q{quarter}FY{year} {test_name}"
    txb = slide.shapes.add_textbox(
        Inches(MARGIN), Inches(0.05), Inches(TABLE_W), Inches(0.26))
    tf  = txb.text_frame
    p   = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text           = title_str
    run.font.size      = Pt(PT_HDG)
    run.font.bold      = True
    run.font.color.rgb = COL_BLACK
    run.font.name      = FONT

    left_w  = 3.50
    right_x = MARGIN + left_w + 0.15
    right_w = TABLE_W - left_w - 0.15
    tbl_y   = 0.34

    # ── Left top table: unit info ─────────────────────────────────────────────
    unit_count  = overview.get("unit_count", 0) or 0
    actual_life = overview.get("actual_life", "")
    lh_hdrs = ["Unit", "Actual Test Life Per Unit", "Test Start", "Test End"]
    lh_vals = [
        str(unit_count),
        f"{int(actual_life):,}" if actual_life else "",
        overview.get("test_start", ""),
        overview.get("test_end", ""),
    ]
    lh_w  = [0.50, 1.20, 0.90, 0.90]
    lt_h  = 0.19 + 0.22   # header + 1 data row

    tbl_lt = slide.shapes.add_table(
        2, 4, Inches(TABLE_X), Inches(tbl_y),
        Inches(left_w), Inches(lt_h)
    ).table
    _clear_table_style(tbl_lt)
    for ci, cw in enumerate(lh_w):
        tbl_lt.columns[ci].width = Inches(cw)
    for ci, hdr in enumerate(lh_hdrs):
        cell = tbl_lt.cell(0, ci)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_BLUE
        _set_text(cell, hdr, bold=True, fg=COL_WHITE,
                  size=PT_HEADER, align=PP_ALIGN.CENTER)
        _set_border(cell)
    for ci, val in enumerate(lh_vals):
        cell = tbl_lt.cell(1, ci)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_WHITE
        _set_text(cell, val, size=PT_BODY, align=PP_ALIGN.CENTER)
        _set_border(cell)
    tbl_lt.rows[0].height = Inches(0.19)
    tbl_lt.rows[1].height = Inches(0.22)

    # ── Left bottom table: unit details (blank) ───────────────────────────────
    n_unit = max(1, min(int(unit_count), 10))
    ub_w   = [1.10, 1.20, 1.20]
    bot_y  = tbl_y + lt_h + 0.07
    bot_h  = min(0.19 + n_unit * 0.19, SLIDE_BOTTOM - bot_y)

    tbl_lb = slide.shapes.add_table(
        1 + n_unit, 3,
        Inches(TABLE_X), Inches(bot_y),
        Inches(sum(ub_w)), Inches(bot_h)
    ).table
    _clear_table_style(tbl_lb)
    for ci, cw in enumerate(ub_w):
        tbl_lb.columns[ci].width = Inches(cw)
    for ci, hdr in enumerate(["Unit Number", "Serial Number", "FW Version"]):
        cell = tbl_lb.cell(0, ci)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_BLUE
        _set_text(cell, hdr, bold=True, fg=COL_WHITE,
                  size=PT_HEADER, align=PP_ALIGN.CENTER)
        _set_border(cell)
    tbl_lb.rows[0].height = Inches(0.19)
    for ri in range(n_unit):
        for ci in range(3):
            cell = tbl_lb.cell(ri + 1, ci)
            cell.fill.solid(); cell.fill.fore_color.rgb = COL_WHITE
            _set_text(cell, "", size=PT_BODY)
            _set_border(cell)
        tbl_lb.rows[ri + 1].height = Inches(0.19)

    # ── Right table: Category | Result | Remarks ──────────────────────────────
    cat_results = _build_category_results(summary_data)
    rem_w       = right_w - 0.90 - 0.55
    rh_w        = [0.90, 0.55, rem_w]
    right_h     = min(0.19 + len(cat_results) * 0.22, SLIDE_BOTTOM - tbl_y)

    tbl_r = slide.shapes.add_table(
        1 + len(cat_results), 3,
        Inches(right_x), Inches(tbl_y),
        Inches(right_w), Inches(right_h)
    ).table
    _clear_table_style(tbl_r)
    for ci, cw in enumerate(rh_w):
        tbl_r.columns[ci].width = Inches(cw)
    for ci, hdr in enumerate(["Category", "Result", "Remarks"]):
        cell = tbl_r.cell(0, ci)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_BLUE
        _set_text(cell, hdr, bold=True, fg=COL_WHITE,
                  size=PT_HEADER, align=PP_ALIGN.CENTER)
        _set_border(cell)
    tbl_r.rows[0].height = Inches(0.19)

    if not hasattr(prs, '_overview_hyperlinks'):
        prs._overview_hyperlinks = []

    for ri, row_info in enumerate(cat_results):
        tr       = ri + 1
        cat_name = row_info["category"]
        result   = row_info["result"]
        remarks  = row_info["remarks"]   # list of strings

        # Category cell
        cell = tbl_r.cell(tr, 0)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_WHITE
        _set_text(cell, cat_name, size=PT_BODY)
        _set_border(cell)

        # Result cell — coloured
        cell = tbl_r.cell(tr, 1)
        cell.fill.solid()
        if result == "PASS":
            cell.fill.fore_color.rgb = COL_PASS_BG
            _set_text(cell, result, bold=True, fg=COL_PASS_FG,
                      size=PT_BODY, align=PP_ALIGN.CENTER)
        elif result == "FAIL":
            cell.fill.fore_color.rgb = COL_FAIL_BG
            _set_text(cell, result, bold=True, fg=COL_FAIL_FG,
                      size=PT_BODY, align=PP_ALIGN.CENTER)
        else:
            cell.fill.fore_color.rgb = RGBColor(0xD9, 0xD9, 0xD9)
            _set_text(cell, result, bold=True,
                      fg=RGBColor(0x40, 0x40, 0x40),
                      size=PT_BODY, align=PP_ALIGN.CENTER)
        _set_border(cell)

        # Remarks cell — one remark per line, hyperlink if FAIL
        cell = tbl_r.cell(tr, 2)
        cell.fill.solid(); cell.fill.fore_color.rgb = COL_WHITE
        remarks_text = "\n".join(remarks) if remarks else ""
        _set_text(cell, remarks_text, size=PT_BODY)
        _set_border(cell)

        if remarks:
            prs._overview_hyperlinks.append({
                "slide_obj": slide,
                "table":     tbl_r,
                "row":       tr,
                "col":       2,
                "cat_name":  cat_name,
                "tray":      row_info.get("tray", ""),
            })

        # Compact row height based on number of remark lines
        n_lines = max(1, len(remarks))
        tbl_r.rows[tr].height = Inches(max(0.19, n_lines * 0.16))


def _build_category_results(summary_data):
    """
    One summary row per unique category across all trays/modes.
    Result = FAIL if any combination fails, else PASS.
    Remarks = list of '{media_type}_{tray}_{mode}_{error}({rate})'
              only for FAIL combinations.
    """
    cat_map = {}

    for cat in summary_data["categories"]:
        cat_name = cat["category"]
        if cat_name not in cat_map:
            cat_map[cat_name] = {"result": "PASS", "remarks": [], "tray": ""}

        for m in cat["media_summaries"]:
            tray   = str(m.get("tray", ""))
            mode   = str(m.get("mode", ""))
            mt     = m.get("media_type", "")
            result = m.get("overall_result", "")
            errors = m.get("errors", [])

            if not cat_map[cat_name]["tray"]:
                cat_map[cat_name]["tray"] = tray

            if result == "FAIL":
                cat_map[cat_name]["result"] = "FAIL"
                for err in errors:
                    remark = (f"{mt}_{tray}_{mode}_"
                              f"{err['error']}({err['rate']:.2f}/K)")
                    if remark not in cat_map[cat_name]["remarks"]:
                        cat_map[cat_name]["remarks"].append(remark)

    return [
        {"category": k, "result": v["result"],
         "remarks": v["remarks"], "tray": v["tray"]}
        for k, v in cat_map.items()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# TITLE SLIDE
# ═══════════════════════════════════════════════════════════════════════════════

def _add_title_slide(prs, printer, variant, sub_assembly, year, quarter):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    bar = slide.shapes.add_shape(
        1, Inches(0), Inches(0), Inches(SLIDE_W), Inches(2.0))
    bar.fill.solid()
    bar.fill.fore_color.rgb = COL_NAVY
    bar.line.fill.background()

    def add_text(text, y, h, size, bold=False,
                 color=COL_WHITE, align=PP_ALIGN.CENTER):
        txb = slide.shapes.add_textbox(
            Inches(0.5), Inches(y), Inches(SLIDE_W - 1.0), Inches(h))
        tf = txb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text           = text
        run.font.size      = Pt(size)
        run.font.bold      = bold
        run.font.color.rgb = color
        run.font.name      = FONT

    add_text("Life Test Data Analysis", 0.3, 0.6, 26, bold=True)
    add_text(f"{printer}  ·  {variant}  ·  {sub_assembly}", 1.0, 0.5, 16)
    add_text(f"Q{quarter}  FY{year}", 2.2, 0.5, 20,
             bold=True, color=COL_NAVY)
    add_text(f"Generated: {datetime.now().strftime('%d %b %Y   %H:%M')}",
             2.9, 0.4, 11, color=RGBColor(0x60, 0x60, 0x60))


# ═══════════════════════════════════════════════════════════════════════════════
# CONTENT SLIDE — renders multiple heading+table blocks
# ═══════════════════════════════════════════════════════════════════════════════

def _add_content_slide(prs, slide_blocks):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = COL_WHITE

    cursor_y = SLIDE_TOP   # current vertical position in inches

    for block_idx, block in enumerate(slide_blocks):
        if block_idx > 0:
            cursor_y += BLOCK_GAP

        heading   = block["heading"]
        flat_rows = block["rows"]

        # ── Block heading text box ────────────────────────────────────────────
        txb = slide.shapes.add_textbox(
            Inches(MARGIN), Inches(cursor_y),
            Inches(TABLE_W), Inches(BLOCK_HDG_H)
        )
        tf = txb.text_frame
        p  = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text           = heading
        run.font.size      = Pt(PT_HDG)
        run.font.bold      = True
        run.font.color.rgb = COL_BLACK
        run.font.name      = FONT

        cursor_y += BLOCK_HDG_H

        if not flat_rows:
            continue

        # ── Table ─────────────────────────────────────────────────────────────
        row_heights = [_estimate_row_h(r) for r in flat_rows]
        table_h     = min(HDR_H + sum(row_heights),
                          SLIDE_BOTTOM - cursor_y)
        n_total     = 1 + len(flat_rows)

        tbl_shape = slide.shapes.add_table(
            n_total, N_COLS,
            Inches(TABLE_X), Inches(cursor_y),
            Inches(TABLE_W), Inches(table_h)
        )
        tbl = tbl_shape.table

        _clear_table_style(tbl)

        for ci, cw in enumerate(COL_W):
            tbl.columns[ci].width = Inches(cw)

        # Header row
        for ci, hdr in enumerate(HEADERS):
            cell = tbl.cell(0, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COL_BLUE
            _set_text(cell, hdr, bold=True, fg=COL_WHITE,
                      size=PT_HEADER, align=PP_ALIGN.CENTER)
            _set_border(cell)

        # Data rows
        for ri, row in enumerate(flat_rows):
            tr   = ri + 1
            cols = row["cols"]

            for ci, val in enumerate(cols):
                cell = tbl.cell(tr, ci)
                cell.fill.solid()
                cell.fill.fore_color.rgb = COL_WHITE

                if ci == 3 and val in ("PASS", "FAIL", "NO SPEC"):
                    if val == "PASS":
                        cell.fill.fore_color.rgb = COL_PASS_BG
                        _set_text(cell, val, bold=True, fg=COL_PASS_FG,
                                  size=PT_BODY, align=PP_ALIGN.CENTER)
                    elif val == "FAIL":
                        cell.fill.fore_color.rgb = COL_FAIL_BG
                        _set_text(cell, val, bold=True, fg=COL_FAIL_FG,
                                  size=PT_BODY, align=PP_ALIGN.CENTER)
                    else:
                        cell.fill.fore_color.rgb = RGBColor(0xD9, 0xD9, 0xD9)
                        _set_text(cell, val, bold=True,
                                  fg=RGBColor(0x40, 0x40, 0x40),
                                  size=PT_BODY, align=PP_ALIGN.CENTER)
                    _set_border(cell)
                    continue

                _set_text(cell, str(val) if val else "",
                          size=PT_BODY, align=PP_ALIGN.LEFT)
                _set_border(cell)

        # Row heights
        tbl.rows[0].height = Inches(HDR_H)
        for ri, h in enumerate(row_heights):
            tbl.rows[ri + 1].height = Inches(h)

        # Vertical merges on cols 0-3
        _apply_vertical_merges(tbl, flat_rows)

        cursor_y += table_h


# ═══════════════════════════════════════════════════════════════════════════════
# VERTICAL MERGE
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_vertical_merges(tbl, flat_rows):
    """
    Apply vertical cell merges on columns 0-3 based on blank-cell pattern.
    Blank value = consumed by merge above.
    """
    for ci in range(5):   # cols 0,1,2,3,4  (media, mode, spec, result, error)
        ri = 0
        n  = len(flat_rows)
        while ri < n:
            val = flat_rows[ri]["cols"][ci]
            if val != "":
                span = 1
                while ri + span < n and flat_rows[ri + span]["cols"][ci] == "":
                    span += 1
                if span > 1:
                    _set_rowspan(tbl.cell(ri + 1, ci), span)
                    for k in range(1, span):
                        _mark_vmerge(tbl.cell(ri + 1 + k, ci))
                ri += span
            else:
                ri += 1


def _set_rowspan(cell, span):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcPr.set("rowSpan", str(span))


def _mark_vmerge(cell):
    tc = cell._tc
    for tb in tc.findall(f"{{{NS}}}txBody"):
        tc.remove(tb)
    tcPr = tc.get_or_add_tcPr()
    tcPr.set("vMerge", "1")


# ═══════════════════════════════════════════════════════════════════════════════
# XML / CELL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _clear_table_style(tbl):
    tblPr = tbl._tbl.find(f"{{{NS}}}tblPr")
    if tblPr is None:
        return
    sid = tblPr.find(f"{{{NS}}}tableStyleId")
    if sid is not None:
        sid.text = "{00000000-0000-0000-0000-000000000000}"
    for attr in ("bandRow", "bandCol", "firstRow",
                 "firstCol", "lastRow", "lastCol"):
        tblPr.set(attr, "0")


def _set_border(cell):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for tag in ("lnL", "lnR", "lnT", "lnB"):
        for el in tcPr.findall(f"{{{NS}}}{tag}"):
            tcPr.remove(el)
        ln = etree.SubElement(tcPr, f"{{{NS}}}{tag}", attrib={"w": "12700"})
        sf = etree.SubElement(ln, f"{{{NS}}}solidFill")
        etree.SubElement(sf, f"{{{NS}}}srgbClr", attrib={"val": "000000"})


def _set_text(cell, text, bold=False, fg=None,
              size=PT_BODY, align=PP_ALIGN.LEFT):
    tf = cell.text_frame
    tf.word_wrap    = True
    tf.margin_left  = Pt(2)
    tf.margin_right = Pt(2)
    tf.margin_top    = Pt(1)
    tf.margin_bottom = Pt(1)

    p = tf.paragraphs[0]
    p.alignment = align
    for run in p.runs:
        run.text = ""

    run = p.add_run()
    run.text           = text
    run.font.size      = Pt(size)
    run.font.bold      = bold
    run.font.name      = FONT
    run.font.color.rgb = fg if fg else COL_BLACK