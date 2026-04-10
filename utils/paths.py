"""
utils/paths.py - Resolve file paths correctly whether running from
source or as a PyInstaller-packaged executable.

User-editable files (spec.xlsx, reports/) always live next to the .exe.
Bundled read-only assets live inside the package (_MEIPASS).
"""

import sys
from pathlib import Path


def app_dir() -> Path:
    """
    Directory where the .exe lives (packaged) or the project root (dev).
    Use this for user-editable files: spec.xlsx, output folders.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle — use folder containing the .exe
        return Path(sys.executable).parent
    else:
        # Running from source — use project root
        return Path(__file__).resolve().parent.parent


def default_spec_path() -> Path:
    """Path to spec.xlsx — always next to the .exe so users can edit it."""
    return app_dir() / "spec.xlsx"


def default_output_dir() -> Path:
    """Default output folder for reports — next to the .exe."""
    return app_dir() / "reports"
