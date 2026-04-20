"""
pptx_data_builder.py - Data preparation and pagination for PowerPoint slides.

Builds flat row data from summary_data, estimates row heights,
paginates blocks across slides, and builds Key Takeaways category results.
"""

import math

from services.pptx_constants import (
    COL_W, AVAIL_H, BLOCK_HDG_H, GAP_HDG_TABLE, HDR_H,
    ROW_BASE_H, ROW_PAD_H, CHAR_W_IN
)

CATEGORY_ORDER = [
    "Intervention",
    "Soft Error",
    "Skew",
    "Other Defects",
    "Other Issue",
    "Image Quality",
    "PQ",
]

def _cat_sort_key(cat_name):
    try:
        return CATEGORY_ORDER.index(cat_name)
    except ValueError:
        return len(CATEGORY_ORDER)


# ── Block building ────────────────────────────────────────────────────────────

def build_all_blocks(summary_data):
    """
    Build one block per (test_condition, category, tray) combination.
    Heading: Test Condition first, then Category, then Input Tray.
    """
    combos = []
    seen   = set()
    for cat in summary_data["categories"]:
        cat_name = cat["category"]
        for m in cat["media_summaries"]:
            tc  = m.get("test_condition", "")
            key = (tc, cat_name, m["tray"])
            if key not in seen:
                seen.add(key)
                combos.append(key)

    combos.sort(key=lambda x: (str(x[0]), _cat_sort_key(x[1]), str(x[2])))

    blocks = []
    for (tc, cat_name, tray) in combos:
        parts = [f"Test Condition: {tc}", f"Category: {cat_name}"]
        if tray:
            parts.append(f"Input Tray: {tray}")
        heading = "   |   ".join(parts)
        flat_rows = build_flat_rows(summary_data, tray, cat_name, tc)
        if flat_rows:
            blocks.append({"heading": heading, "rows": flat_rows, "cont": False})

    return blocks


def build_flat_rows(summary_data, tray, cat_name, test_condition=""):
    """
    Build flat rows for one (test_condition, category, tray) block.
    Plain media always first; rows grouped by media type then print mode.
    """
    raw = []
    for cat in summary_data["categories"]:
        if cat["category"] != cat_name:
            continue
        for m in cat["media_summaries"]:
            if m["tray"] == tray and m.get("test_condition", "") == test_condition:
                raw.append(m)

    if not raw:
        return []

    # Group by (media_type, media_cat) to keep qual/eval separate
    media_order  = []
    media_groups = {}
    for m in raw:
        mc  = m.get("media_cat", "") or ""
        key = (m["media_type"], mc)
        if key not in media_groups:
            media_order.append(key)
            media_groups[key] = []
        media_groups[key].append(m)

    # Plain first (case-insensitive), then alphabetical
    plain_keys = [k for k in media_order if k[0].strip().lower().startswith("plain")]
    other_keys = [k for k in media_order if not k[0].strip().lower().startswith("plain")]
    media_order = plain_keys + other_keys

    rows = []
    shown_media_types = set()  # track media types already displayed (for MT column)

    for (mt, mc) in media_order:
        first_media_row = mt not in shown_media_types  # controls Media Type column
        first_mc_row    = True                          # controls Media Cat column (always show per group)
        shown_media_types.add(mt)

        for media in media_groups[(mt, mc)]:
            mode     = str(media["mode"]) if media["mode"] else ""
            result   = media["overall_result"]
            errors   = media.get("errors", [])
            spec_val = media.get("spec", None)
            spec_str = f"{spec_val:.2f}/K" if spec_val is not None else ""

            if result not in ("FAIL", "NO SPEC", "PASS") or not errors:
                rows.append(_flat(
                    mt if first_media_row else "",
                    mc if first_mc_row    else "",
                    mode,
                    spec_str,
                    result, "", "", ""
                ))
                first_media_row = False
                first_mc_row    = False
                continue

            first_mode_row = True

            for err in errors:
                label = f"{err['error']}: {err['rate']:.2f}/K"

                if result == "NO SPEC":
                    rows.append(_flat(
                        mt       if first_media_row else "",
                        mc       if first_mc_row    else "",
                        mode     if first_mode_row  else "",
                        spec_str if first_mode_row  else "",
                        result   if first_mode_row  else "",
                        label, "", ""
                    ))
                    first_media_row = False
                    first_mc_row    = False
                    first_mode_row  = False
                else:
                    first_err_row = True
                    for entry in err["failed_media"]:
                        units       = ", ".join(entry["units"]) if entry["units"] else ""
                        media_rate  = entry.get("rate", None)
                        media_label = entry["media_name"]
                        if media_rate is not None:
                            media_label = f"{entry['media_name']} ({media_rate:.2f}/K)"
                        rows.append(_flat(
                            mt       if first_media_row else "",
                            mc       if first_mc_row    else "",
                            mode     if first_mode_row  else "",
                            spec_str if first_mode_row  else "",
                            result   if first_mode_row  else "",
                            label    if first_err_row   else "",
                            media_label, units
                        ))
                        first_media_row = False
                        first_mc_row    = False
                        first_mode_row  = False
                        first_err_row   = False

    return rows


def _flat(media, media_cat, mode, spec, result, error, media_name, units):
    return {"media": media, "media_cat": media_cat, "mode": mode, "spec": spec,
            "result": result, "error": error, "media_name": media_name, "units": units,
            "cols": [media, media_cat, mode, spec, result, error, media_name, units]}


# ── Height estimation ─────────────────────────────────────────────────────────

def estimate_row_h(row):
    max_lines = 1
    # Only estimate wrapping for variable-length columns (error, media name, units)
    # Fixed-short columns (media type, media cat, mode, spec, result) never wrap
    WRAP_COLS = {5, 6, 7}  # Error Type, Media Name, Unit
    for ci, text in enumerate(row["cols"]):
        if not text or ci not in WRAP_COLS:
            continue
        # Use tighter usable width (0.25" margin) and smaller char width for 8pt
        usable = max(0.1, COL_W[ci] - 0.25)
        cpl    = max(1, int(usable / CHAR_W_IN))
        lines  = max(1, math.ceil(len(str(text)) / cpl))
        max_lines = max(max_lines, lines)
    return ROW_BASE_H * max_lines + ROW_PAD_H


# ── Pagination ────────────────────────────────────────────────────────────────

def paginate_blocks(all_blocks):
    """
    One block per slide. Splits rows across slides when a block is too tall,
    repeating the heading as "(cont.)".
    Splits at individual row boundaries (including mid-media-name level).
    """
    slides = []

    for block in all_blocks:
        remaining_rows = list(block["rows"])
        first_chunk    = True

        while remaining_rows:
            chunk   = []
            # Conservative budget: subtract heading, gap, header, plus 0.20" margin
            # to ensure estimation error never causes overflow.
            avail   = AVAIL_H - BLOCK_HDG_H - GAP_HDG_TABLE - HDR_H - 0.20
            chunk_h = 0.0

            for row in remaining_rows:
                rh = estimate_row_h(row)
                if chunk and chunk_h + rh > avail:
                    break
                chunk.append(row)
                chunk_h += rh

            if not chunk:
                chunk = [remaining_rows[0]]   # force at least one row to avoid infinite loop

            heading = block["heading"] if first_chunk \
                      else block["heading"] + "  (cont.)"

            slides.append([{"heading": heading,
                             "rows":    chunk,
                             "cont":    not first_chunk}])
            remaining_rows = remaining_rows[len(chunk):]
            first_chunk    = False

    return slides


# ── Key Takeaways data ────────────────────────────────────────────────────────

def build_category_results(summary_data):
    """
    Build category-level pass/fail summary for the Key Takeaways table.

    Returns a list of (test_condition, rows) tuples — one entry per unique
    test condition found in the data. For Ambient there will be one entry;
    for Climatic there will be one entry per climatic condition value.

    Categories are treated as "has spec" only if at least one media summary
    for that (tc, category) returned a result other than NO SPEC / NO SPEC
    PROVIDED.  This is determined by a pre-scan so the logic is product-
    agnostic — no hardcoded category names needed.
    """
    NO_SPEC_RESULTS = {"NO SPEC", "NO SPEC PROVIDED"}

    # ── Pre-scan: determine which (tc, category) pairs have a spec ────────────
    has_spec = {}   # (tc, cat_name) → True/False
    for cat in summary_data["categories"]:
        cat_name = cat["category"]
        for m in cat["media_summaries"]:
            tc     = m.get("test_condition", "")
            result = m.get("overall_result", "")
            key    = (tc, cat_name)
            if result not in NO_SPEC_RESULTS:
                has_spec[key] = True
            elif key not in has_spec:
                has_spec[key] = False

    # tc_map: {test_condition: {category: {result, remarks}}}
    tc_map = {}

    for cat in summary_data["categories"]:
        cat_name = cat["category"]

        for m in cat["media_summaries"]:
            tc         = m.get("test_condition", "")
            tray       = str(m.get("tray", ""))
            mode       = str(m.get("mode", ""))
            media_type = m.get("media_type", "")
            media_cat  = m.get("media_cat", "")
            result     = m.get("overall_result", "")
            spec_val   = m.get("spec", None)
            spec_str   = f"{spec_val:.2f}" if spec_val is not None else "N/A"
            errors     = m.get("errors", [])

            cat_has_spec = has_spec.get((tc, cat_name), False)

            if tc not in tc_map:
                tc_map[tc] = {}
            if cat_name not in tc_map[tc]:
                default_result = "PASS" if cat_has_spec else "No issue"
                tc_map[tc][cat_name] = {"result": default_result, "remarks": []}

            mt_label = f"{media_type}_{media_cat}" if media_cat else media_type

            if cat_has_spec:
                # Spec-based category: PASS / FAIL
                if result == "FAIL":
                    tc_map[tc][cat_name]["result"] = "FAIL"
                    for err in errors:
                        error  = err.get("error", "")
                        rate   = err.get("rate", 0)
                        remark = (
                            f"{mt_label}_{tray}_{mode}_"
                            f"{error} error rate of {rate:.2f}/K "
                            f"(Spec: {spec_str}/K)"
                        )
                        if remark not in tc_map[tc][cat_name]["remarks"]:
                            tc_map[tc][cat_name]["remarks"].append(remark)
            else:
                # No-spec category: No issue / With observation
                if result not in NO_SPEC_RESULTS:
                    # Unexpected spec result in a no-spec category — treat conservatively
                    pass
                if errors:
                    if tc_map[tc][cat_name]["result"] != "With observation":
                        tc_map[tc][cat_name]["result"] = "With observation"
                    for err in errors:
                        error = err.get("error", "")
                        rate  = err.get("rate", 0)
                        remark = (
                            f"{mt_label}_{tray}_{mode}_"
                            f"{error} error rate of {rate:.2f}/K"
                        )
                        if remark not in tc_map[tc][cat_name]["remarks"]:
                            tc_map[tc][cat_name]["remarks"].append(remark)

    result_groups = []
    for tc in sorted(tc_map.keys()):
        cat_map = tc_map[tc]
        rows = [
            {"category": k, "result": v["result"], "remarks": v["remarks"]}
            for k, v in sorted(cat_map.items(), key=lambda x: _cat_sort_key(x[0]))
        ]
        result_groups.append({"test_condition": tc, "rows": rows})

    return result_groups
