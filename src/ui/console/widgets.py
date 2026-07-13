"""Console UI toolkit: framed widgets, banners, utilisation bars and the
session clock.

Generic, domain-agnostic rendering primitives sharing one visual language.
Pure stdlib + termcolor; no project dependencies. Extracted verbatim from
``ui.Menus`` during the P3 ``console/`` decomposition.
"""
import os
import sys
import threading
import datetime
from termcolor import colored

# =============================================================================
#  SESSION CLOCK / RUNTIME TELEMETRY
# -----------------------------------------------------------------------------
#  A single monotonic session start-stamp drives the SESSION STATUS panel:
#  a live wall-clock, session uptime and (optionally) a real ticking clock
#  rendered in place via ANSI cursor save/restore while the menu waits for
#  input. Falls back gracefully on non-TTY / unsupported terminals.
# =============================================================================
SESSION_START = datetime.datetime.now().astimezone()


def session_uptime():
    """Seconds elapsed since the application session started."""
    return (datetime.datetime.now().astimezone() - SESSION_START).total_seconds()


def _live_clock_supported():
    """True only when stdout is an interactive TTY that can take ANSI codes."""
    try:
        return sys.stdout.isatty()
    except AttributeError:
        return False


def input_with_live_clock(prompt_text, render_clock_line):
    """Display a prompt while a one-line live clock ticks on the line directly
    above it. The clock line is rewritten once per second using ANSI cursor
    save/restore so the user's typing is never disturbed.

    ``render_clock_line`` is a zero-arg callable returning the (already
    coloured) clock string. Falls back to a static line on non-TTY terminals.
    """
    if not _live_clock_supported():
        print(render_clock_line())
        return input(prompt_text)

    print(render_clock_line())          # initial paint, one line above prompt
    stop = threading.Event()

    def _worker():
        while not stop.wait(1.0):
            try:
                sys.stdout.write("\0337")        # save cursor
                sys.stdout.write("\033[1A")      # up one line (to clock line)
                sys.stdout.write("\r\033[2K")    # col 0 + clear entire line
                sys.stdout.write(render_clock_line())
                sys.stdout.write("\0338")        # restore cursor
                sys.stdout.flush()
            except (OSError, ValueError):
                return

    ticker = threading.Thread(target=_worker, daemon=True)
    ticker.start()
    try:
        return input(prompt_text)
    finally:
        stop.set()
        ticker.join(timeout=1.2)

# =============================================================================
#  PROFESSIONAL CONSOLE UI TOOLKIT  (commercial-grade rendering primitives)
# -----------------------------------------------------------------------------
#  Centralised drawing helpers so every screen shares one consistent visual
#  language: framed banners, titled section rules, aligned key/value fields,
#  utilisation bars and pass/fail status badges. Used across all menus and
#  result/report screens. Pure stdlib + termcolor; no external dependencies.
# =============================================================================
UI_W = 64  # inner width (number of horizontal glyphs between frame corners)


def _strip_len(text):
    """Visible length of a string (helper for alignment)."""
    return len(text)


def ui_banner(title, subtitle=None, color='cyan'):
    """Render a centred, double-ruled title banner."""
    print("\n")
    print(colored("\u2554" + "\u2550" * UI_W + "\u2557", color, attrs=['bold']))
    print(colored("\u2551" + str(title).center(UI_W) + "\u2551", color, attrs=['bold']))
    if subtitle:
        print(colored("\u2551" + str(subtitle).center(UI_W) + "\u2551", color))
    print(colored("\u255a" + "\u2550" * UI_W + "\u255d", color, attrs=['bold']))


def ui_open(title, color='yellow'):
    """Open a titled section rule:  +- TITLE --------------------------"""
    title = str(title)
    pad = UI_W - (len(title) + 3)
    if pad < 1:
        pad = 1
    print(colored(f"\u250c\u2500 {title} " + "\u2500" * pad, color, attrs=['bold']))


def ui_close(color='yellow'):
    """Close a section rule."""
    print(colored("\u2514" + "\u2500" * UI_W, color, attrs=['bold']))


def ui_blank(color='yellow'):
    """Vertical spacer inside a section."""
    print(colored("\u2502", color))


def ui_text(text, color='white', frame_color=None):
    """Plain framed line of text."""
    fc = frame_color or color
    print(colored("\u2502 ", fc) + colored(str(text), color))


def ui_head(text, color='white', frame_color=None):
    """Bold sub-heading line inside a section."""
    fc = frame_color or color
    print(colored("\u2502 ", fc) + colored(str(text), color, attrs=['bold']))


def ui_field(label, value, frame_color='white', label_color=None,
             value_color='white', width=30, bullet=None):
    """Aligned key/value row with optional bullet and dotted leader feel."""
    lc = label_color or frame_color
    lead = f"  {bullet} " if bullet else " "
    label = str(label)
    line = f"{label}".ljust(width)
    print(colored("\u2502" + lead, frame_color)
          + colored(line, lc)
          + colored(str(value), value_color, attrs=['bold']))


def ui_bullet(text, color='white', frame_color=None, mark="\u2022"):
    """Bulleted list item."""
    fc = frame_color or color
    print(colored("\u2502   " + mark + " ", fc) + colored(str(text), color))


def ui_bar(frac, width=24):
    """Return (rendered_bar, color) for a 0..>1 utilisation fraction."""
    try:
        frac = float(frac)
    except (TypeError, ValueError):
        frac = 0.0
    if frac < 0:
        frac = 0.0
    filled = int(round(min(frac, 1.0) * width))
    filled = max(0, min(width, filled))
    if frac <= 0.75:
        col = 'green'
    elif frac <= 0.95:
        col = 'yellow'
    else:
        col = 'red'
    bar = "\u2588" * filled + "\u2591" * (width - filled)
    pct = f"{frac * 100:6.1f}%"
    return colored(bar, col) + colored(f" {pct}", col, attrs=['bold']), col


def ui_check_row(name, dc_ratio, status_text=None, width=22):
    """Render one limit-state check line: name | bar | D/C | verdict."""
    bar, col = ui_bar(dc_ratio)
    name = str(name).ljust(width)
    if status_text is None:
        if dc_ratio <= 0.95:
            status_text = "PASS \u2713"
        elif dc_ratio <= 1.0:
            status_text = "MARGINAL \u26a0"
        else:
            status_text = "FAIL \u2717"
    print(colored("\u2502 ", col) + colored(name, 'white')
          + bar + colored(f"  D/C={dc_ratio:5.2f}  ", 'white')
          + colored(status_text, col, attrs=['bold']))


def ui_verdict_badge(status):
    """Map a verdict keyword to (label, color)."""
    s = str(status).upper()
    table = {
        'PASS':     ("\u2713 PASS \u2014 DESIGN ACCEPTABLE", 'green'),
        'REVIEW':   ("\u26a0 REVIEW \u2014 MARGINAL / ENGINEER JUDGEMENT REQUIRED", 'yellow'),
        'FAIL':     ("\u2717 FAIL \u2014 DESIGN NOT ACCEPTABLE", 'red'),
        'INCOMPLETE': ("\u2139 INCOMPLETE \u2014 RUN STRESS & DEFLECTION CHECKS", 'cyan'),
    }
    return table.get(s, (s, 'white'))


def ui_footer(text="Press Enter to continue...", color='cyan'):
    """Standard interactive footer prompt."""
    print("\n")
    return input(colored(f"  {text}", color, attrs=['bold']))


def ui_menu_stage(stage_label, color='cyan'):
    """Print an FEA workflow stage divider used to group main-menu items."""
    label = f"  {stage_label}  "
    pad_total = UI_W - len(label)
    left = pad_total // 2
    right = pad_total - left
    print(colored("\u2502", 'yellow')
          + colored("\u00b7" * left + label + "\u00b7" * right, color, attrs=['bold']))


# =============================
# Utility & Helper Functions
# =============================
def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_title(title):
    """Print a formatted title for menus and sections."""
    print(colored(f"\n=== {title} ===\n", 'cyan', attrs=['bold']))


def print_option(option):
    """Print a formatted option."""
    print(colored(option, 'yellow'))


def print_error(error_msg):
    """Print an error message (in red)."""
    print(colored(error_msg, 'red', attrs=['bold']))


def print_success(msg):
    """Print a success message (in green)."""
    print(colored(msg, 'green'))
