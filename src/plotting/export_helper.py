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

PNG export robustness
---------------------
``fig.write_image`` (Kaleido) can *block indefinitely* on some setups - e.g. a
Plotly/Kaleido version mismatch, or Kaleido trying to launch Chrome and never
returning. Because that call holds the main thread, a hang would freeze the
whole CLI (the menu would stop accepting input). To prevent that, PNG rendering
runs on a worker thread guarded by a hard timeout: if Kaleido does not finish in
time, we report the problem and hand control straight back to the menu instead
of hanging.
"""

import os
import re
import sys
import datetime
import threading

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
PNG_TIMEOUT_SECONDS = 60        # hard cap so a stuck Kaleido never freezes the CLI


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


def _kaleido_available():
    """True if the Kaleido PNG backend can be imported."""
    try:
        import kaleido  # noqa: F401
        return True
    except Exception:
        return False


def _write_png(fig, path):
    """Render a PNG on a worker thread, bounded by ``PNG_TIMEOUT_SECONDS``.

    Returns (ok: bool, reason: str|None). ``reason`` is "timeout" when Kaleido
    did not finish in time, otherwise an error message; None on success.
    """
    box = {}

    def _work():
        try:
            fig.write_image(path, scale=3, width=1100, height=650)
            box["ok"] = True
        except Exception as exc:                       # pragma: no cover
            box["err"] = exc

    worker = threading.Thread(target=_work, daemon=True)
    worker.start()
    worker.join(PNG_TIMEOUT_SECONDS)

    if worker.is_alive():
        return False, "timeout"
    if box.get("ok"):
        return True, None
    return False, str(box.get("err", "unknown error"))


def _export_png(fig, png_path):
    """Attempt a PNG export with friendly, non-blocking failure handling."""
    if not _kaleido_available():
        print_error("PNG export needs the 'kaleido' package (it is not installed).")
        print_error("Install it with:  pip install kaleido==0.2.1")
        print_error("Meanwhile, choose 'Interactive HTML', or use the camera icon")
        print_error("in the diagram window to save a PNG directly.")
        return None

    print(colored("  Rendering PNG (this can take a few seconds)\u2026", 'cyan'))
    ok, reason = _write_png(fig, png_path)
    if ok:
        print_success(f"PNG image saved: {png_path}")
        return png_path

    if reason == "timeout":
        print_error(f"PNG export timed out after {PNG_TIMEOUT_SECONDS}s - the Kaleido")
        print_error("image engine is not responding (often a Plotly/Kaleido version")
        print_error("mismatch). Returning you to the menu.")
        print_error("Fix:  pip install -U plotly kaleido    (or pin kaleido==0.2.1)")
        print_error("Tip:  'Interactive HTML' always works, or use the camera icon")
        print_error("      in the diagram window to save a PNG.")
    else:
        print_error("PNG export failed in the Kaleido backend.")
        print_error("Fix:  pip install -U plotly kaleido    (or pin kaleido==0.2.1)")
        print_error(f"(details: {reason})")
    return None


def export_plotly(fig, default_name="diagram"):
    """Offer to export ``fig`` as interactive HTML and/or a PNG image.

    Returns a list of the file paths written (may be empty if the user skips).
    Never raises on a cancelled/declined prompt, and never blocks the CLI on a
    misbehaving PNG backend.
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
        result = _export_png(fig, png_path)
        if result:
            saved.append(result)

    return saved


def present_plotly(fig, default_name="diagram"):
    """Show ``fig`` interactively, then run the optional export workflow.

    This is the single entry-point the diagram functions should call instead of
    ``fig.show(...)`` so that interactive display and saving stay consistent.
    """
    fig.show(config=T.PLOTLY_CONFIG)
    return export_plotly(fig, default_name)
