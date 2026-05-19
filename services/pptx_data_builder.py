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
                result_display = result if (result != "NO SPEC" or not spec_str) else "PASS"
                rows.append(_flat(
                    mt if first_media_row else "",
                    mc if first_mc_row    else "",
                    mode,
                    spec_str,
                    result_display, "", "", ""
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
                    if not err["failed_media"]:
                        # No per-media breakdown — just show the error rate line
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


def _build_remark(tray, media_type, media_cat, mode, error, rate, spec_str=None):
    """Build a Key Takeaways remark: tray_mediatype_mediacat_mode_error_rate_(Spec: x/K)"""
    parts = [p for p in [tray, media_type, media_cat, mode, error, f"{rate:.2f}/K"] if p]
    if spec_str and spec_str != "N/A":
        parts.append(f"(Spec: {spec_str}/K)")
    return "_".join(parts)


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

    # Context column indices: media(0), media_cat(1), mode(2), spec(3), result(4)
    _CTX_KEYS = ["media", "media_cat", "mode", "spec", "result"]

    for block in all_blocks:
        remaining_rows = list(block["rows"])
        first_chunk    = True
        last_ctx       = [""] * 5   # last seen non-blank value per context col

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

            # On continuation slides, restore context to the first row so readers
            # can see which Media Type / Media Cat / Print Mode / Spec / Result
            # the remaining rows belong to.
            if not first_chunk:
                fr   = chunk[0]
                cols = list(fr["cols"])
                need_update = any(not cols[ci] and last_ctx[ci] for ci in range(5))
                if need_update:
                    new_fr = dict(fr)
                    new_fr["cols"] = cols
                    for ci, key in enumerate(_CTX_KEYS):
                        if not cols[ci] and last_ctx[ci]:
                            cols[ci]       = last_ctx[ci]
                            new_fr[key]    = last_ctx[ci]
                    new_fr["cols"] = cols
                    chunk = [new_fr] + chunk[1:]

            heading = block["heading"] if first_chunk \
                      else block["heading"] + "  (cont.)"

            slides.append([{"heading": heading,
                             "rows":    chunk,
                             "cont":    not first_chunk}])

            # Update last_ctx from all rows in this chunk
            for row in chunk:
                for ci in range(5):
                    if row["cols"][ci]:
                        last_ctx[ci] = row["cols"][ci]

            remaining_rows = remaining_rows[len(chunk):]
            first_chunk    = False

    return slides


# ── Key Takeaways data ────────────────────────────────────────────────────────

def build_category_results(summary_data):
    """
    Build category-level pass/fail summary for the Key Takeaways table.

    Returns one entry per unique test condition. Each entry's rows are split
    by (category, media_type, media_cat) so the table shows one row per
    media type / media cat combination within each category.
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

    # tc_map: {tc: {cat_name: {result, remarks}}} — one entry per category
    _RESULT_RANK = {"FAIL": 2, "With observation": 1, "Observation": 1, "PASS": 0, "No issue": 0}
    tc_map = {}

    for cat in summary_data["categories"]:
        cat_name = cat["category"]

        for m in cat["media_summaries"]:
            tc         = m.get("test_condition", "")
            tray       = str(m.get("tray", ""))
            mode       = str(m.get("mode", ""))
            result     = m.get("overall_result", "")
            spec_val   = m.get("spec", None)
            spec_str   = f"{spec_val:.2f}" if spec_val is not None else "N/A"
            errors     = m.get("errors", [])
            media_type = m.get("media_type", "")
            media_cat  = m.get("media_cat", "")

            cat_has_spec = has_spec.get((tc, cat_name), False)

            mc_key = (media_type, media_cat)

            if tc not in tc_map:
                tc_map[tc] = {}
            if cat_name not in tc_map[tc]:
                default_result = "PASS" if cat_has_spec else "No issue"
                tc_map[tc][cat_name] = {"result": default_result, "remarks": [], "combo_pass": {}}

            entry  = tc_map[tc][cat_name]
            combos = entry["combo_pass"]

            # Track per-combo pass status (False once any FAIL seen)
            if mc_key not in combos:
                combos[mc_key] = True
            if result == "FAIL":
                combos[mc_key] = False

            # Promote overall result to worst seen
            if _RESULT_RANK.get(result, 0) > _RESULT_RANK.get(entry["result"], 0):
                entry["result"] = result

            if cat_has_spec:
                if result == "FAIL" and errors:
                    # errors[0] = total; errors[1:] = individual types.
                    # Individual errors that exceeded spec have failed_media populated.
                    spec_breaching = [e for e in errors[1:] if e.get("failed_media")]
                    if spec_breaching:
                        for err in spec_breaching:
                            remark = _build_remark(
                                tray, media_type, media_cat, mode,
                                err.get("error", ""), err.get("rate", 0), spec_str
                            )
                            if remark not in entry["remarks"]:
                                entry["remarks"].append(remark)
                    else:
                        # Total failed but no individual type breached — show the total
                        err    = errors[0]
                        remark = _build_remark(
                            tray, media_type, media_cat, mode,
                            err.get("error", ""), err.get("rate", 0), spec_str
                        )
                        if remark not in entry["remarks"]:
                            entry["remarks"].append(remark)
            else:
                if errors:
                    err    = errors[0]
                    remark = _build_remark(
                        tray, media_type, media_cat, mode,
                        err.get("error", ""), err.get("rate", 0)
                    )
                    if remark not in entry["remarks"]:
                        entry["remarks"].append(remark)

    result_groups = []
    for tc in sorted(tc_map.keys()):
        cat_map = tc_map[tc]
        rows    = []
        for cat_name in sorted(cat_map.keys(), key=_cat_sort_key):
            v       = cat_map[cat_name]
            overall = v["result"]

            if overall == "FAIL" or v["remarks"]:
                display_result = "With observation"
            else:
                display_result = "No issue"

            rows.append({
                "category":     cat_name,
                "result":       display_result,
                "result_style": display_result,
                "remarks":      v["remarks"],
            })
        result_groups.append({"test_condition": tc, "rows": rows})

    return result_groups
