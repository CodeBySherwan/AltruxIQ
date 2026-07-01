"""Centralized filesystem path resolution for AltruxIQ.

Single source of truth for every on-disk location the application touches.
Nothing outside this module should compute a project-relative path — import
the constant you need from here instead of re-deriving it from ``__file__``.

Layout (resolved from this file at ``src/common/paths.py``)::

    PROJECT_ROOT/
    ├── data/                        <- DATA_DIR
    │   ├── materials.json           <- MATERIALS_DB_FILE
    │   ├── custom_materials.json    <- CUSTOM_MATERIALS_FILE
    │   ├── standard_sections.json   <- STANDARD_SECTIONS_FILE
    │   └── custom_sections.json     <- CUSTOM_SECTIONS_FILE
    ├── exports/
    │   └── diagrams/                <- DIAGRAM_EXPORT_DIR
    ├── screenshots/                 <- SCREENSHOTS_DIR
    └── beam_projects.json           <- PROJECTS_FILE
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Anchor points
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
SRC_DIR: Path = _THIS_FILE.parent.parent          # .../src
PROJECT_ROOT: Path = SRC_DIR.parent                # repo root

# ---------------------------------------------------------------------------
# Directories the app reads from / writes to
# ---------------------------------------------------------------------------
DATA_DIR: Path = PROJECT_ROOT / "data"
EXPORTS_DIR: Path = PROJECT_ROOT / "exports"
DIAGRAM_EXPORT_DIR: Path = EXPORTS_DIR / "diagrams"
SCREENSHOTS_DIR: Path = PROJECT_ROOT / "screenshots"

# ---------------------------------------------------------------------------
# Individual data files
# ---------------------------------------------------------------------------
# NOTE: casing matches what cli.load_material_database() currently passes
# ("Materials.json") and what exists on disk ("materials.json"). Windows is
# case-insensitive so both resolve; kept verbatim to avoid a behavior change
# during the path-centralization step. Phase 2+ may normalize to lowercase.
MATERIALS_DB_FILE: Path = DATA_DIR / "materials.json"
CUSTOM_MATERIALS_FILE: Path = DATA_DIR / "custom_materials.json"
STANDARD_SECTIONS_FILE: Path = DATA_DIR / "standard_sections.json"
CUSTOM_SECTIONS_FILE: Path = DATA_DIR / "custom_sections.json"

PROJECTS_FILE: Path = PROJECT_ROOT / "beam_projects.json"


# ---------------------------------------------------------------------------
# sys.path bootstrap (retained for backward compatibility)
# ---------------------------------------------------------------------------
def ensure_src_in_path() -> None:
    """Idempotently add ``src/`` to ``sys.path``.

    Called from modules that need cross-package imports (e.g. ``from
    solver.stepped_solver import ...``) but that are themselves invoked before
    ``src/`` is on the path. Prefer running via a project-root entry point so
    this isn't needed at all.
    """
    src = str(SRC_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)


def ensure_writable_dirs() -> None:
    """Create every directory the app writes to. Call once at startup.

    Read-only directories (``DATA_DIR`` is shipped with the repo) are not
    created here; only the write targets that are auto-generated on first use.
    """
    for d in (EXPORTS_DIR, DIAGRAM_EXPORT_DIR, SCREENSHOTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
