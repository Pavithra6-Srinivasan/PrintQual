"""
pptx_constants.py - Shared constants for PowerPoint generation.
Colours, slide geometry, column layout, and typography.
"""

from pptx.dml.color import RGBColor
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

# ── Slide geometry (16:9 widescreen, inches) ──────────────────────────────────
SLIDE_W      = 10.0
SLIDE_H      = 5.625
MARGIN       = 0.25
TABLE_X      = MARGIN
TABLE_W      = SLIDE_W - 2 * MARGIN   # 9.5"
SLIDE_TOP    = 0.20                    # where content starts
SLIDE_BOTTOM = 5.25                    # hard lower limit
AVAIL_H      = SLIDE_BOTTOM - SLIDE_TOP

# ── Content table column widths (must sum to TABLE_W = 9.5") ─────────────────
# MediaType | MediaCat | PrintMode | Spec | Result | Error | MediaName | Units
COL_W   = [0.85, 0.65, 0.85, 0.60, 0.85, 1.40, 2.70, 1.60]
HEADERS = ["Media Type", "Media Cat", "Print Mode", "Spec", "Overall Result",
           "Error Type", "Media Name", "Unit"]
N_COLS  = len(HEADERS)

# ── Typography ────────────────────────────────────────────────────────────────
FONT            = "Calibri"
PT_TITLE        = 18
PT_HDG          = 15
PT_HEADER       = 9
PT_BODY         = 9
PT_CONTENT_BODY = 8

# ── Row geometry ──────────────────────────────────────────────────────────────
HDR_H         = 0.17   # header row height
ROW_BASE_H    = 0.15   # base height per data row (matches actual 8pt Calibri rendered height)
ROW_PAD_H     = 0.02   # cell padding allowance
CHAR_W_IN     = 0.055  # conservative Calibri-8 char width (intentionally tight)

# ── Block layout ──────────────────────────────────────────────────────────────
BLOCK_HDG_H   = 0.25   # heading text box height
GAP_HDG_TABLE = 0.06   # gap between heading and table
BLOCK_GAP     = 0.20   # gap between blocks on same slide

# ── XML namespace ─────────────────────────────────────────────────────────────
NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
