"""
export_helper.py
================
Centralised "present & export" workflow for every Plotly diagram in the suite.

``present_plotly`` renders a figure interactively (matching the existing
behaviour) and then offers the user a polished, optional export step:

    * Interactive HTML  -> self-contained .html (opens in any browser, retains
      hover / zoom / pan), Plotly.js pulled from CDN to keep files small.
    * PNG image         -> high-resolution raster (scale x3) via Kaleido.
    * Both              -> writes both files in one go.

All exports are written to  <project-root>/exports/diagrams/  with a unique
timestamped, filesystem-safe filename so nothing is ever overwritten. The
export prompt is fully skippable and degrades gracefully on non-interactive
terminals or when the optional ``kaleido`` PNG backend is not installed.
"""

import os
import re
import sys
import datetime

# --- PATH INJECTION (so this module works from flat or package imports) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ui.Menus import print_success, print_error
from ui.inputs import ask_yes_no, ask_choice
from termcolor import colored

try:
    from plotting import plot_theme as T
except Exception:                       # pragma: no cover (flat import for previews)
    import plot_theme as T


EXPORT_SUBDIR = os.path.join("exports", "diagrams")


def _export_dir():
    """Return (and lazily create) the diagrams export directory."""
    out = os.path.join(project_root, EXPORT_SUBDIR)
    os.makedirs(out, exist_ok=True)
    return out


def _safe_name(name):
    """Turn a human title into a filesystem-safe slug."""
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name).strip())
    slug = slug.strip("_") or "diagram"
    return slug[:60]


def _timestamp():
    return datetime.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")


def export_plotly(fig, default_name="diagram"):
    """Offer to export ``fig`` as interactive HTML and/or a PNG image.

    Returns a list of the file paths written (may be empty if the user skips).
    Never raises on a cancelled/declined prompt or a missing PNG backend.
    """
    saved = []
    try:
        if not ask_yes_no("Export this diagram to a file?", default=False):
            return saved
        print(colored("  1) Interactive HTML", 'yellow')
              + colored("    2) PNG image", 'yellow')
              + colored("    3) Both", 'yellow'))
        choice = ask_choice("Choose export format", ["1", "2", "3"], allow_cancel=True)
    except (EOFError, KeyboardInterrupt):
        return saved
    if choice is None:
        return saved

    base = _safe_name(default_name)
    stamp = _timestamp()
    out_dir = _export_dir()

    if choice in ("1", "3"):
        html_path = os.path.join(out_dir, f"{base}_{stamp}.html")
        try:
            fig.write_html(html_path, include_plotlyjs="cdn", config=T.PLOTLY_CONFIG)
            saved.append(html_path)
            print_success(f"Interactive HTML saved: {html_path}")
        except Exception as e:
            print_error(f"Could not write HTML: {e}")

    if choice in ("2", "3"):
        png_path = os.path.join(out_dir, f"{base}_{stamp}.png")
        try:
            fig.write_image(png_path, scale=3, width=1100, height=650)
            saved.append(png_path)
            print_success(f"PNG image saved: {png_path}")
        except Exception as e:
            print_error("PNG export requires the 'kaleido' package.")
            print_error("Install it with:  pip install kaleido")
            print_error(f"(details: {e})")

    return saved


def present_plotly(fig, default_name="diagram"):
    """Show ``fig`` interactively, then run the optional export workflow.

    This is the single entry-point the diagram functions should call instead of
    ``fig.show(...)`` so that interactive display and saving stay consistent.
    """
    fig.show(config=T.PLOTLY_CONFIG)
    return export_plotly(fig, default_name)
