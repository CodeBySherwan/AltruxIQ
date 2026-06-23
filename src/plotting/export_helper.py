"""
export_helper.py
================
Centralised "present & export" workflow for every Plotly diagram in the suite.

``present_plotly`` renders a figure interactively (matching the existing
behaviour) and then offers the user a polished, optional export step:

    * Interactive HTML  -> self-contained .html (opens in any browser, retains
      hover / zoom / pan), Plotly.js pulled from CDN to keep files small.
    * PNG image         -> uses Plotly's OWN built-in image export (the camera
      button) in the browser. No Kaleido / Orca / Chrome dependency.
    * Both              -> writes the HTML and triggers the PNG download.

Why the browser for PNG?
------------------------
Plotly.js renders a PNG client-side via ``Plotly.downloadImage`` - exactly what
the modebar camera icon does. That path is dependency-free and never blocks the
CLI, unlike the server-side ``fig.write_image`` (Kaleido) route, which can hang
on a version mismatch. We write a tiny self-contained HTML that opens the figure
and immediately fires the built-in PNG download into the browser's Downloads
folder, then open it with the default browser.

Interactive HTML files are saved to  <project-root>/exports/diagrams/  with a
unique timestamped, filesystem-safe filename so nothing is ever overwritten.
"""

import os
import re
import sys
import datetime
import webbrowser

# --- PATH INJECTION (so this module works from flat or package imports) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import plotly.io as pio

from ui.Menus import print_success, print_error
from ui.inputs import ask_yes_no, ask_choice
from termcolor import colored

try:
    from plotting import plot_theme as T
except Exception:                       # pragma: no cover (flat import for previews)
    import plot_theme as T


EXPORT_SUBDIR = os.path.join("exports", "diagrams")
# Built-in PNG export resolution (matches the modebar camera button settings).
_PNG_W, _PNG_H, _PNG_SCALE = 1100, 650, 3


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


def _write_interactive_html(fig, path):
    """Write a self-contained interactive HTML diagram."""
    fig.write_html(path, include_plotlyjs="cdn", config=T.PLOTLY_CONFIG)


def _export_png_via_browser(fig, base, stamp):
    """Trigger Plotly's built-in PNG export (the camera button) in the browser.

    Writes a tiny HTML that renders the figure and immediately calls
    ``Plotly.downloadImage`` - the exact engine behind the modebar camera icon -
    then opens it in the default browser. No Kaleido / Chrome dependency, and it
    never blocks the CLI. The PNG lands in the browser's Downloads folder.
    """
    # post_script runs after the plot is created; grab the graph div and ask
    # Plotly.js itself to render + download a PNG. A short delay lets layout settle.
    post_script = (
        "var __gd = document.querySelector('.plotly-graph-div');"
        "setTimeout(function(){"
        "  Plotly.downloadImage(__gd, {format:'png', scale:%d, width:%d, height:%d,"
        "    filename:'%s'});"
        "}, 800);"
    ) % (_PNG_SCALE, _PNG_W, _PNG_H, f"{base}_{stamp}")

    html = pio.to_html(fig, include_plotlyjs="cdn", config=T.PLOTLY_CONFIG,
                       full_html=True, post_script=post_script)
    helper = os.path.join(_export_dir(), f"{base}_{stamp}_png.html")
    with open(helper, "w", encoding="utf-8") as f:
        f.write(html)

    opened = webbrowser.open("file://" + os.path.abspath(helper))
    if opened:
        print_success("Opening your browser to save the PNG (Plotly built-in export)\u2026")
        print_success("The image will appear in your browser's Downloads folder as")
        print_success(f"  {base}_{stamp}.png")
        print(colored("  Tip: you can also click the \U0001f4f7 camera icon in any diagram "
                      "window to save a PNG at any time.", 'cyan'))
    else:
        print_error("Could not open a browser automatically.")
        print_error(f"Open this file manually to download the PNG:  {helper}")
    return helper


def export_plotly(fig, default_name="diagram"):
    """Offer to export ``fig`` as interactive HTML and/or a PNG image.

    Returns a list of the file paths produced (may be empty if the user skips).
    Never raises on a cancelled/declined prompt and never blocks the CLI.
    """
    saved = []
    try:
        if not ask_yes_no("Export this diagram to a file?", default=False):
            return saved
        print(colored("  1) Interactive HTML", 'yellow')
              + colored("    2) PNG image (Plotly built-in)", 'yellow')
              + colored("    3) Both", 'yellow'))
        choice = ask_choice("Choose export format", ["1", "2", "3"], allow_cancel=True)
    except (EOFError, KeyboardInterrupt):
        return saved
    if choice is None:
        return saved

    base = _safe_name(default_name)
    stamp = _timestamp()

    if choice in ("1", "3"):
        html_path = os.path.join(_export_dir(), f"{base}_{stamp}.html")
        try:
            _write_interactive_html(fig, html_path)
            saved.append(html_path)
            print_success(f"Interactive HTML saved: {html_path}")
        except Exception as e:
            print_error(f"Could not write HTML: {e}")

    if choice in ("2", "3"):
        try:
            saved.append(_export_png_via_browser(fig, base, stamp))
        except Exception as e:
            print_error(f"PNG export failed: {e}")
            print_error("You can still use the \U0001f4f7 camera icon in the diagram window.")

    return saved


def present_plotly(fig, default_name="diagram"):
    """Show ``fig`` interactively, then run the optional export workflow.

    This is the single entry-point the diagram functions should call instead of
    ``fig.show(...)`` so that interactive display and saving stay consistent.
    """
    fig.show(config=T.PLOTLY_CONFIG)
    return export_plotly(fig, default_name)
