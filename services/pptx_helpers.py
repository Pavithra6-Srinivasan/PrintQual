"""
pptx_helpers.py - XML/cell helpers and vertical merge utilities.
"""

from lxml import etree
from pptx.enum.text import PP_ALIGN
from pptx.util import Pt

from services.pptx_constants import (
    NS, FONT, COL_BLACK, PT_BODY
)


# ── Cell styling ──────────────────────────────────────────────────────────────

def clear_table_style(tbl):
    tblPr = tbl._tbl.find(f"{{{NS}}}tblPr")
    if tblPr is None:
        return
    sid = tblPr.find(f"{{{NS}}}tableStyleId")
    if sid is not None:
        sid.text = "{00000000-0000-0000-0000-000000000000}"
    for attr in ("bandRow", "bandCol", "firstRow",
                 "firstCol", "lastRow", "lastCol"):
        tblPr.set(attr, "0")


def set_border(cell):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for tag in ("lnL", "lnR", "lnT", "lnB"):
        for el in tcPr.findall(f"{{{NS}}}{tag}"):
            tcPr.remove(el)
        ln = etree.SubElement(tcPr, f"{{{NS}}}{tag}", attrib={"w": "12700"})
        sf = etree.SubElement(ln, f"{{{NS}}}solidFill")
        etree.SubElement(sf, f"{{{NS}}}srgbClr", attrib={"val": "000000"})


def set_text(cell, text, bold=False, fg=None,
             size=PT_BODY, align=PP_ALIGN.LEFT):
    tf = cell.text_frame
    tf.word_wrap     = True
    tf.margin_left   = Pt(2)
    tf.margin_right  = Pt(2)
    tf.margin_top    = Pt(0)
    tf.margin_bottom = Pt(0)

    from pptx.oxml.ns import qn
    from lxml import etree as _etree

    # Remove ALL existing paragraphs and lstStyle, replace with clean versions
    txBody = tf._txBody
    for old_p in txBody.findall(qn("a:p")):
        txBody.remove(old_p)
    for old_ls in txBody.findall(qn("a:lstStyle")):
        txBody.remove(old_ls)

    sz_val = str(int(size * 100))
    b_val  = "1" if bold else "0"

    # Configure bodyPr for tight vertical fit
    bodyPr = txBody.find(qn("a:bodyPr"))
    if bodyPr is None:
        bodyPr = _etree.SubElement(txBody, qn("a:bodyPr"))
    bodyPr.set("anchor", "t")        # top-align text
    bodyPr.set("anchorCtr", "0")     # don't centre vertically
    bodyPr.set("wrap", "square")

    # Prevent PowerPoint from auto-expanding the row to fit text
    for child in list(bodyPr):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("noAutofit", "normAutofit", "spAutoFit"):
            bodyPr.remove(child)
    _etree.SubElement(bodyPr, qn("a:noAutofit"))

    # lstStyle: override inherited table style to enforce our font size on all text levels
    lstStyle  = _etree.SubElement(txBody, qn("a:lstStyle"))
    defPPr    = _etree.SubElement(lstStyle, qn("a:defPPr"))
    ls_defRPr = _etree.SubElement(defPPr, qn("a:defRPr"))
    ls_defRPr.set("sz", sz_val)
    ls_defRPr.set("b", b_val)
    ls_latin  = _etree.SubElement(ls_defRPr, qn("a:latin"))
    ls_latin.set("typeface", FONT)

    new_p = _etree.SubElement(txBody, qn("a:p"))
    pPr   = _etree.SubElement(new_p, qn("a:pPr"))
    pPr.set("algn", {
        PP_ALIGN.LEFT:   "l",
        PP_ALIGN.CENTER: "ctr",
        PP_ALIGN.RIGHT:  "r",
    }.get(align, "l"))

    # Zero paragraph spacing (before and after)
    spcBef = _etree.SubElement(pPr, qn("a:spcBef"))
    _etree.SubElement(spcBef, qn("a:spcPts"), attrib={"val": "0"})
    spcAft = _etree.SubElement(pPr, qn("a:spcAft"))
    _etree.SubElement(spcAft, qn("a:spcPts"), attrib={"val": "0"})

    # Tight line spacing (80% = tighter than single)
    lnSpc = _etree.SubElement(pPr, qn("a:lnSpc"))
    _etree.SubElement(lnSpc, qn("a:spcPct"), attrib={"val": "80000"})

    # defRPr sets font size for empty paragraphs / cells
    defRPr = _etree.SubElement(pPr, qn("a:defRPr"))
    defRPr.set("sz", sz_val)
    defRPr.set("b", b_val)
    def_latin = _etree.SubElement(defRPr, qn("a:latin"))
    def_latin.set("typeface", FONT)

    r    = _etree.SubElement(new_p, qn("a:r"))
    rPr  = _etree.SubElement(r, qn("a:rPr"), attrib={"lang": "en-US", "dirty": "0"})
    rPr.set("sz", sz_val)
    rPr.set("b", b_val)
    rPr.set("u", "none")

    colour = fg if fg else COL_BLACK
    solidFill = _etree.SubElement(rPr, qn("a:solidFill"))
    srgbClr   = _etree.SubElement(solidFill, qn("a:srgbClr"))
    srgbClr.set("val", str(colour))

    latin = _etree.SubElement(rPr, qn("a:latin"))
    latin.set("typeface", FONT)

    t = _etree.SubElement(r, qn("a:t"))
    t.text = text


# ── Vertical merge ────────────────────────────────────────────────────────────

def apply_vertical_merges(tbl, flat_rows):
    """Merge blank cells vertically on cols 0-5 (media, media_cat, mode, spec, result, error)."""
    for ci in range(6):
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
    """Mark cell as a vertical merge continuation.
    txBody MUST come before tcPr in the <a:tc> element (OOXML spec).
    We rebuild txBody in place (not remove+append) to preserve element order,
    then enforce 8pt so PowerPoint doesn't fall back to the 18pt table default."""
    from pptx.oxml.ns import qn as _qn
    from lxml import etree as _etree

    tc  = cell._tc
    SZ  = "800"   # 8pt in hundredths of a point

    # ── Rebuild txBody in-place to keep it BEFORE tcPr ───────────────────
    txBody = tc.find(f"{{{NS}}}txBody")
    if txBody is not None:
        # Clear all children and reuse the element (preserves position)
        for child in list(txBody):
            txBody.remove(child)
    else:
        # No txBody yet — insert at position 0 (before tcPr)
        txBody = _etree.Element(f"{{{NS}}}txBody")
        tc.insert(0, txBody)

    bodyPr = _etree.SubElement(txBody, _qn("a:bodyPr"))
    bodyPr.set("anchor", "t")
    bodyPr.set("anchorCtr", "0")
    _etree.SubElement(bodyPr, _qn("a:noAutofit"))

    lstStyle  = _etree.SubElement(txBody, _qn("a:lstStyle"))
    defPPr    = _etree.SubElement(lstStyle, _qn("a:defPPr"))
    ls_defRPr = _etree.SubElement(defPPr, _qn("a:defRPr"))
    ls_defRPr.set("sz", SZ)
    ls_latin  = _etree.SubElement(ls_defRPr, _qn("a:latin"))
    ls_latin.set("typeface", "Calibri")

    p   = _etree.SubElement(txBody, _qn("a:p"))
    pPr = _etree.SubElement(p, _qn("a:pPr"))
    spcBef = _etree.SubElement(pPr, _qn("a:spcBef"))
    _etree.SubElement(spcBef, _qn("a:spcPts"), attrib={"val": "0"})
    spcAft = _etree.SubElement(pPr, _qn("a:spcAft"))
    _etree.SubElement(spcAft, _qn("a:spcPts"), attrib={"val": "0"})
    defRPr = _etree.SubElement(pPr, _qn("a:defRPr"))
    defRPr.set("sz", SZ)
    dr_latin = _etree.SubElement(defRPr, _qn("a:latin"))
    dr_latin.set("typeface", "Calibri")

    # ── Set vMerge on tcPr AFTER txBody is in place ───────────────────────
    tcPr = tc.get_or_add_tcPr()
    tcPr.set("vMerge", "1")
