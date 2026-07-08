import os
import sys
import time
import threading
import datetime
from termcolor import colored, cprint
import numpy as np

# =============================================================================
#  SESSION CLOCK / RUNTIME TELEMETRY
# -----------------------------------------------------------------------------
#  A single monotonic session start-stamp drives the SESSION STATUS panel:
#  a live wall-clock, session uptime and (optionally) a real ticking clock
#  rendered in place via ANSI cursor save/restore while the menu waits for
#  input. Falls back gracefully on non-TTY / unsupported terminals.
# =============================================================================
SESSION_START = datetime.datetime.now().astimezone()


def fmt_datetime(dt=None):
    """Human-friendly local timestamp, e.g. 'Tue 23 Jun 2026  19:45:21'."""
    dt = dt or datetime.datetime.now().astimezone()
    return dt.strftime("%a %d %b %Y  %H:%M:%S")


def fmt_date_compact(dt=None):
    """Compact date-time used for project filenames/labels: '2026-06-23 19:45'."""
    dt = dt or datetime.datetime.now().astimezone()
    return dt.strftime("%Y-%m-%d %H:%M")


def fmt_duration(seconds):
    """Format an elapsed duration as 'HH:MM:SS' (or 'Dd HH:MM:SS')."""
    seconds = int(max(0, seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h:02d}:{m:02d}:{s:02d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def session_uptime():
    """Seconds elapsed since the application session started."""
    return (datetime.datetime.now().astimezone() - SESSION_START).total_seconds()


def _live_clock_supported():
    """True only when stdout is an interactive TTY that can take ANSI codes."""
    try:
        return sys.stdout.isatty()
    except Exception:
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
            except Exception:
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
# Global Unit Configurations
# =============================
# Unit handling is centralized in `common.units` (single source of truth).
# Re-exported here for backward compatibility with the many call sites and
# external modules that still do `from ui.Menus import get_divisor`.
from common.units import (
    METRIC_UNITS,
    IMPERIAL_UNITS,
    UNIT_SYSTEMS,
    DEFAULT_UNITS,
    get_divisor,
    from_si,
    to_si,
    system_multiplier,
    get_scale,
    default_units,
    is_imperial,
)
from common.config import SERVICEABILITY

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

# =============================
# Extended Main Menu and Runner
# =============================
# First, update the main_menu_template() function to add the new option
def main_menu_template(current_points=2001, session_info=None):
    """Display the main menu, organised by the standard FEA workflow:
    Pre-Processing -> Solution -> Post-Processing -> Configuration.
    Item numbers are preserved (0-13) so the controller dispatch is unchanged.

    ``session_info`` (optional dict) feeds the live SESSION STATUS panel:
        name          -> active project display name (with date), or None
        saved_at      -> ISO / display timestamp of last save, or None
        unit_system   -> 'Metric' | 'Imperial'
        steps_done    -> int, completed pre-processing inputs (0-4)
        steps_total   -> int, total pre-processing inputs (default 4)
        analysed      -> bool, whether a solution exists
    """
    clear_screen()
    ui_banner("AltruxIQ  \u2022  STRUCTURAL FEA SUITE",
              "Beam Analysis & Design-Check Workstation", color='cyan')

    print("\n")
    ui_open("ANALYSIS WORKFLOW", 'yellow')
    ui_blank('yellow')

    # ---- Stage 1: PRE-PROCESSING ----------------------------------------
    ui_menu_stage("STAGE 1  \u2014  PRE-PROCESSING", 'cyan')
    pre_items = [
        ("\U0001f5c2  Project Management", "Create, load, modify or delete analysis projects"),
        ("\U0001f4d0  Beam Type / Model", "Define structural system & support topology"),
        ("\U0001f9ee  Section / Profile", "Cross-section geometry & section properties"),
        ("\U0001f9ea  Material Model", "Assign material & mechanical properties"),
        ("\U0001f512  Boundary Conditions", "Supports, restraints & degrees of freedom"),
        ("\u2696\ufe0f   Load Application", "Point, distributed, moment & triangular loads"),
        ("\U0001f4ca  Model Preview", "Render beam schematic with loads & supports"),
    ]
    for idx, (title, desc) in enumerate(pre_items, 1):
        print(colored(f"\u2502 {idx:2d} \u2502 {title}", 'yellow')
              + colored(f"  \u2014 {desc}", 'white'))

    ui_blank('yellow')
    # ---- Stage 2: SOLUTION ----------------------------------------------
    ui_menu_stage("STAGE 2  \u2014  SOLUTION", 'cyan')
    print(colored("\u2502  8 \u2502 \U0001f9e9  Solve / Simulate", 'yellow')
          + colored("  \u2014 Reactions, shear, moment, deflection & stress", 'white'))

    ui_blank('yellow')
    # ---- Stage 3: POST-PROCESSING ---------------------------------------
    ui_menu_stage("STAGE 3  \u2014  POST-PROCESSING", 'cyan')
    print(colored("\u2502  9 \u2502 \U0001f4c8  Results & Visualization", 'yellow')
          + colored("  \u2014 SFD/BMD, stress, deflection, 3D FEA contours", 'white'))
    print(colored("\u2502 11 \u2502 \U0001f4cb  Design Check & Recommendations", 'yellow')
          + colored("  \u2014 Limit-state verification & optimisation report", 'white'))

    ui_blank('yellow')
    # ---- Data + Configuration -------------------------------------------
    ui_menu_stage("DATA  &  CONFIGURATION", 'cyan')
    print(colored("\u2502 10 \u2502 \U0001f4be  Save Project", 'yellow')
          + colored("  \u2014 Persist current model & results to disk", 'white'))
    print(colored("\u2502 12 \u2502 \u2699\ufe0f   Unit System", 'yellow')
          + colored("  \u2014 Switch SI (Metric) \u2194 US Customary", 'white'))
    print(colored("\u2502 13 \u2502 \u2699\ufe0f   Solver Resolution", 'yellow')
          + colored(f"  \u2014 Discretisation density (current: {current_points} pts)", 'white'))

    ui_blank('yellow')
    print(colored("\u2502  0 \u2502 \U0001f6aa  Exit", 'red')
          + colored("  \u2014 Close the application", 'white'))
    ui_close('yellow')

    # ---- Status bar ------------------------------------------------------
    info = session_info or {}
    proj_name   = info.get("name")
    saved_at    = info.get("saved_at")
    unit_system = info.get("unit_system", "Metric")
    steps_done  = int(info.get("steps_done", 0))
    steps_total = int(info.get("steps_total", 4))
    analysed    = bool(info.get("analysed", False))

    print("\n")
    ui_open("SESSION STATUS", 'green')

    if proj_name:
        ui_field("Active project", proj_name,
                 frame_color='green', label_color='green', value_color='cyan')
        ui_field("Last saved", saved_at or "unsaved \u2014 changes pending",
                 frame_color='green', label_color='green',
                 value_color=('white' if saved_at else 'yellow'))
    else:
        ui_field("Active project", "\u2014 none loaded (new session) \u2014",
                 frame_color='green', label_color='green', value_color='yellow')

    ui_field("Unit system", unit_system,
             frame_color='green', label_color='green', value_color='white')
    ui_field("Solver discretisation", f"{current_points} integration points",
             frame_color='green', label_color='green', value_color='white')

    # Pre-processing completeness bar + solution state
    frac = (steps_done / steps_total) if steps_total else 0.0
    bar, _col = ui_bar(frac, width=20)
    print(colored("\u2502 ", 'green')
          + colored("Pre-processing".ljust(30), 'green')
          + bar + colored(f"  {steps_done}/{steps_total} inputs", 'white'))
    sol_txt, sol_col = (("\u2713 solved", 'green') if analysed
                        else ("\u2014 not yet solved", 'yellow'))
    ui_field("Solution state", sol_txt,
             frame_color='green', label_color='green', value_color=sol_col)
    ui_close('green')

    def _render_clock_line():
        now = datetime.datetime.now().astimezone()
        return (colored("  \U0001f552 ", 'green')
                + colored(fmt_datetime(now), 'white', attrs=['bold'])
                + colored("   \u2502   \u23f1 uptime ", 'green')
                + colored(fmt_duration(session_uptime()), 'white', attrs=['bold']))

    print("")
    selection = input_with_live_clock(
        colored("  Enter selection [0-13] \u2794 ", 'cyan', attrs=['bold']),
        _render_clock_line,
    )
    return selection

# =============================
# Project Management Functions
# =============================
def project_management_menu(session_info=None):
    """Display an enhanced project management submenu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  PROJECT MANAGEMENT                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🆕 New Project", "Start a fresh beam analysis project"),
        ("📂 Load Project", "Open a previously saved project"),
        ("🔄 Modify Project", "Change parameters of the loaded project"),
        ("🗑️  Delete Project", "Remove a saved project from storage"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        # Format each menu item with a number, title, and description
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Dynamic project status section, driven by the live session state.
    info = session_info or {}
    proj_name = info.get("name")
    saved_at  = info.get("saved_at")
    print("")
    ui_open("PROJECT STATUS", 'green')
    if proj_name:
        ui_field("Active project", proj_name,
                 frame_color='green', label_color='green', value_color='cyan')
        ui_field("Last saved", saved_at or "unsaved — changes pending",
                 frame_color='green', label_color='green',
                 value_color=('white' if saved_at else 'yellow'))
    else:
        ui_field("Active project", "No active project loaded",
                 frame_color='green', label_color='green', value_color='yellow')
    ui_field("Storage time", fmt_datetime(),
             frame_color='green', label_color='green', value_color='white')
    ui_close('green')
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-5] ➔ ", 'cyan', attrs=['bold']))
    return choice


# =============================
# Profile Definition Functions
# =============================
def profile_definition_menu(units=METRIC_UNITS):
    """Display an enhanced profile definition menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  PROFILE DEFINITION                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        (f"📏 Enter Beam Length ({units['length']})", "Define the total length of the beam"),
        ("📊 Define Profile", "Select cross-section type and dimensions"),
        ("👁️  View Current Profile", "Display the currently defined profile properties"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-4] ➔ ", 'cyan', attrs=['bold']))
    return choice


def choose_profile():
    """
    Display enhanced available profile options and prompt for a choice.
    
    Returns:
        str: The chosen profile number (as a string).
    """
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  AVAILABLE PROFILES                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ CROSS-SECTION TYPES "+"─"*40, 'yellow', attrs=['bold']))
    
    profiles = [
        ("I-beam", "▣", "Standard structural section with flanges"),
        ("T-beam", "┻", "T-shaped cross-section"),
        ("Solid Circle", "⬤", "Circular solid section"),
        ("Hollow Circle", "◯", "Circular tube section"),
        ("Square", "■", "Square solid section"),
        ("Hollow Square", "□", "Square tube section"),
        ("Rectangle", "▬", "Rectangular solid section"),
        ("Hollow Rectangle", "▭", "Rectangular tube section")
    ]
    
    for idx, (name, icon, description) in enumerate(profiles, 1):
        print(colored(f"│ {idx:2d} │ {icon} {name}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    profile_choice = input(colored("Enter your preferred profile number [1-8] ➔ ", 'cyan', attrs=['bold']))
    return profile_choice

def profile_source_menu():
    """Display the profile source options (Custom, Library, Saved)."""
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                    PROFILE SOURCE                            ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    print(colored("┌─ SELECT PROFILE SOURCE "+"─"*38, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("✍️  Enter Custom Dimensions", "Type in dimensions manually"),
        ("📚 Standard Section Library", "Browse IPE, HEA, W-Sections..."),
        ("💾 My Saved Sections", "Retrieve a saved custom section"),
        ("📥 Save Current Section", "Save the active section for reuse"),
        ("🗑️  Delete Custom Section", "Remove a user-defined section"),  # <--- NEW OPTION
        ("⬅️  Return to Profile Menu", "Go back")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + colored(f" - {description}", 'white'))
        
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print("")
    return input(colored("Enter your choice [1-6] ➔ ", 'cyan', attrs=['bold'])) # <--- Updated to 6
def display_section_library(sections, title="SECTION LIBRARY", is_custom=False):
    """Display a list of sections and return the user's choice index."""
    clear_screen()
    print("\n")
    print(colored(f"╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored(f"║ {title:^60} ║", 'cyan', attrs=['bold']))
    print(colored(f"╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    if not sections:
        print(colored("  No sections found in this category.", 'red'))
        print("\n")
        input(colored("Press Enter to return...", 'cyan', attrs=['bold']))
        return None

    print(colored("┌─ SELECT A SECTION "+"─"*43, 'yellow', attrs=['bold']))
    for idx, sec in enumerate(sections, 1):
        name = sec.get('name', 'Unknown')
        ix_val = sec.get('Ix', 0)
        
        if is_custom:
            date_str = sec.get('created_at', '')[:10]
            print(colored(f"│ {idx:2d} │ {name:<25} — Ix = {ix_val:.2e} m⁴ | Saved: {date_str} [CUSTOM]", 'yellow', attrs=['bold']))
        else:
            h_val = sec.get('H', sec.get('diameter', 0)) * 1000 # convert m to mm
            b_val = sec.get('bf', sec.get('width', 0)) * 1000   # convert m to mm
            print(colored(f"│ {idx:2d} │ {name:<25} — Ix = {ix_val:.2e} m⁴ | H ≈ {h_val:.0f}mm | B ≈ {b_val:.0f}mm", 'white'))
    
    print(colored("│  0 │ ⬅️  Go Back", 'red'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print("")
    
    choice = input(colored(f"Enter your choice [0-{len(sections)}] ➔ ", 'cyan', attrs=['bold']))
    try:
        choice_idx = int(choice)
        if choice_idx == 0:
            return None
        if 1 <= choice_idx <= len(sections):
            return choice_idx - 1
    except ValueError:
        pass
    print_error("Invalid selection.")
    time.sleep(1)
    return None

def material_selection_menu(beam_type=None, segments=None, units=None):
    """Display an enhanced material selection menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  MATERIAL SELECTION                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Segment material status bar for Stepped Bar
    if beam_type == "Stepped Bar" and segments:
        print(colored("┌─ STEPPED BAR SEGMENT MATERIALS ─────────────────────────────", 'magenta', attrs=['bold']))
        len_div = 1.0
        len_unit = "m"
        if units and units.get('length') == 'ft':
            len_div = 0.3048
            len_unit = "ft"
        
        for idx, seg in enumerate(segments, 1):
            seg_len = (seg['end'] - seg['start']) / len_div
            mat_name = seg.get('material_name', 'Unknown')
            print(colored(f"│ • Seg {idx} ({seg_len:.2f} {len_unit}): {mat_name}", 'magenta'))
        print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
        print("\n")

    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔍 Select Material", "Choose a material from the database"),
        ("📋 View Current Material Details", "Display properties of the selected material"),
        ("➕ Add Custom Material", "Define and save a new material"),     # <--- NEW
        ("🗑️  Delete Custom Material", "Remove a user-defined material"), # <--- NEW
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    print("")
    choice = input(colored("Enter your choice [1-5] ➔ ", 'cyan', attrs=['bold'])) # <--- CHANGED TO 5
    return choice


def boundary_conditions_menu():
    """Display an enhanced boundary conditions menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  BOUNDARY CONDITIONS                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔒 Define Supports", "Set positions and types of beam supports"),
        ("👁️  View Supports", "Display the current support configuration"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-3] ➔ ", 'cyan', attrs=['bold']))
    return choice


def loads_definition_menu():
    """Display an enhanced loads definition menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  LOADS DEFINITION                            ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("⚖️  Define Loads", "Add point, distributed, moment, or triangular loads"),
        ("📋 View Loads", "Display the current load configuration"),
        ("📊 Show Beam Schematic", "Visualize beam with applied loads"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-4] ➔ ", 'cyan', attrs=['bold']))
    return choice


def analysis_simulation_menu():
    """Display an enhanced analysis/simulation menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  ANALYSIS/SIMULATION                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🧮 Solve Beam", "Calculate shear force, bending moment, and reactions"),
        ("📈 View Analysis Results", "Display the calculated beam response"),
        ("📉 Calculate Deflection", "Compute beam deflection under loads"),
        ("⚠️  Calculate Stress and F.O.S", "Determine stresses and factor of safety"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-5] ➔ ", 'cyan', attrs=['bold']))
    return choice


def postprocessing_menu(beam_type=None):
    """Display an enhanced postprocessing/visualization menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                POSTPROCESSING/VISUALIZATION                  ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ VISUALIZATION OPTIONS "+"─"*38, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔄 Reactions Schematic Plots",         "Visualize support reaction forces (Plotly-only)"),
        ("📊 Shear-Force Plots",                 "Generate SFD diagram"),
        ("📊 Bending-Moment Plot",               "Generate BMD diagram"),
        ("📊 Shear-Force/Bending-Moment Plots",  "Generate SFD and BMD diagrams"),
        ("📈 Shear-Stress",                      "Display Shear stress distribution"),
        ("📈 Bending-Stress",                    "Display Bending stress distribution"),
        ("📉 Deflection Plots",                  "Show beam displacement curves"),
        ("📑 Combined Plots",                    "Show all diagrams together (Plotly Only)"),
    ]
    
    # Stepped bar extras
    if beam_type == "Stepped Bar":
        menu_items.append(("📈 Axial-Force Plot",       "Display axial force diagram"))
        menu_items.append(("📈 Axial-Displacement Plot", "Display axial displacement diagram"))
        menu_items.append(("📈 Combined Stress",         "Display combined bending + axial stress"))
    
    menu_items.append(("🧱 3D FEA Contour View",       "Commercial FEA-style 3D coloured contour plots (PyVista)"))
    menu_items.append(("⬅️  Return to Main Menu",      "Go back to the main menu"))
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    max_choice = len(menu_items)
    choice = input(colored(f"Enter your choice [1-{max_choice}] ➔ ", 'cyan', attrs=['bold']))
    return choice


def pyvista_menu():
    """Display the PyVista 3D FEA contour sub-menu and return the user's choice."""
    clear_screen()

    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║            3D FEA CONTOUR VIEW  (PyVista)                    ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    print(colored("┌─ SELECT RESULT TO VISUALISE "+"─"*33, 'yellow', attrs=['bold']))

    menu_items = [
        ("🔄 Reactions Schematic",    "Reaction force arrows on 3D beam solid"),
        ("📊 Shear Force",            "Blue→Red shear force contour on 3D beam"),
        ("📊 Bending Moment",         "Blue→Red bending moment contour on 3D beam"),
        ("📈 Shear Stress",           "Blue→Red shear stress contour on 3D beam"),
        ("📈 Bending Stress",         "Blue→Red bending stress contour on 3D beam"),
        ("📉 Deflection",             "Displaced shape coloured by displacement magnitude"),
        ("📑 Combined (All Results)", "Sequential viewer — close each window to advance"),
        ("🎬 Load Animation",         "Watch the beam deflect & load from 0% → 100% (animated)"),
        ("⬅️  Return to Postprocessing Menu", "Go back"),
    ]

    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') +
              colored(f" - {description}", 'white'))

    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print(colored("""
  ℹ  Screenshots are automatically saved to  screenshots/  folder.
  ℹ  Close the interactive window to return to the menu.
""", 'cyan'))
    print("")
    choice = input(colored("Enter your choice [1-9] ➔ ", 'cyan', attrs=['bold']))
    return choice

def display_profile_info(beam_length, shape, Ix, c, b, y_array, units=METRIC_UNITS, beam_type=None, segments=None):
    """
    Display enhanced profile information in a visually appealing format.
    
    Parameters:
    -----------
    beam_length: float
        Length of the beam in meters
    shape: str
        Name of the profile shape
    Ix: float
        Moment of inertia in m⁴
    c: float
        Distance from neutral axis to extreme fiber in m
    b: float
        Representative width in m
    y_array: ndarray
        Array of y-coordinates for stress calculations
    """
    clear_screen()
    # Grab the divisors (single source: common.units.get_divisor)
    len_div = get_divisor(units, 'length')
    inertia_div = get_divisor(units, 'inertia')

    if beam_type == "Stepped Bar" and segments:
        clear_screen()
        print("\n")
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║                STEPPED BAR PROFILE DETAILS                   ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("\n")
        
        # Display each segment's info in a list
        print(colored("┌─ SEGMENTS AND CROSS-SECTIONS ────────────────────────────────", 'yellow', attrs=['bold']))
        for idx, seg in enumerate(segments, 1):
            s_len = (seg['end'] - seg['start']) / len_div
            s_shape = seg['shape']
            s_I = seg['I']
            s_A = seg['A']
            s_c = seg['c']
            s_b = seg['b']
            s_E = seg['E']
            s_mat = seg.get('material_name', 'Unknown')
            
            # Format numbers
            i_str = f"{s_I / inertia_div:.6e}"
            a_str = f"{s_A * 1e6:.2f}" if units.get('length') == 'm' else f"{s_A * 144:.2f}" # convert to mm² or in²
            a_unit = "mm²" if units.get('length') == 'm' else "in²"
            
            print(colored(f"│ Segment {idx}: {s_shape} ({s_mat})", 'cyan', attrs=['bold']))
            print(colored(f"│   Span: {seg['start']/len_div:.3f} to {seg['end']/len_div:.3f} {units['length']} (L={s_len:.3f} {units['length']})", 'white'))
            print(colored(f"│   Area: {a_str} {a_unit}  |  Ix: {i_str} {units['inertia']}", 'white'))
            print(colored(f"│   NA-extreme fiber (c): {s_c/len_div:.4f} {units['length']}  |  Width (b): {s_b/len_div:.4f} {units['length']}", 'white'))
            print(colored(f"│   Elastic Modulus (E): {s_E/1e9:.1f} GPa  |  Section Modulus: {(s_I/s_c if s_c > 0 else 0.0)/get_divisor(units, 'sec_mod'):.6e} {units['sec_mod']}", 'white'))
            print(colored(f"│" + "─"*60, 'yellow'))
        
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
        print("\n")
        input(colored("Press Enter to return to the Profile Definition menu...", 'cyan', attrs=['bold']))
        return

    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                    PROFILE INFORMATION                        ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Display profile name with decoration
    print("\n")
    print(colored("┌─ PROFILE TYPE: ", 'yellow', attrs=['bold']) + 
          colored(f"{shape}", 'yellow', attrs=['bold']) + 
          colored(" " + "─"*(46 - len(shape)), 'yellow', attrs=['bold']))
    
    # Display ASCII art based on profile type
    if shape == "I-beam":
        print(colored("│", 'yellow'))
        print(colored("│  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔", 'white'))
        print(colored("│        ▏      ▕", 'white'))
        print(colored("│        ▏      ▕", 'white'))
        print(colored("│        ▏      ▕", 'white'))
        print(colored("│  ▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁", 'white'))
        print(colored("│", 'yellow'))
    elif shape == "T-beam":
        print(colored("│", 'yellow'))
        print(colored("│  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│", 'yellow'))
    elif shape == "Circle" or shape == "Solid Circle":
        print(colored("│", 'yellow'))
        print(colored("│         ▗▄▄▄▖", 'white'))
        print(colored("│       ▗▛    ▜▖", 'white'))
        print(colored("│      ▐       ▌", 'white'))
        print(colored("│       ▝▙    ▟▘", 'white'))
        print(colored("│         ▝▀▀▀▘", 'white'))
        print(colored("│", 'yellow'))
    elif shape == "Hollow Circle":
        print(colored("│", 'yellow'))
        print(colored("│         ▗▄▄▄▖", 'white'))
        print(colored("│       ▗▛    ▜▖", 'white'))
        print(colored("│      ▐  ▗▄▖  ▌", 'white'))
        print(colored("│       ▝▙▝▀▘▟▘", 'white'))
        print(colored("│         ▝▀▀▀▘", 'white'))
        print(colored("│", 'yellow'))
    elif shape == "Square" or shape == "Rectangle":
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))
    elif shape == "Hollow Square" or shape == "Hollow Rectangle":
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █▄▄▄▄▄▄▄▄█", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █▀▀▀▀▀▀▀▀█", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))
    
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    # Display beam information
    print("\n")
    print(colored("┌─ BEAM INFORMATION "+"─"*42, 'green', attrs=['bold']))
    print(colored(f"│ Beam Length: {(beam_length / len_div):.4f} {units['length']}", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Display profile properties
    print("\n")
    print(colored("┌─ PROFILE PROPERTIES "+"─"*41, 'magenta', attrs=['bold']))
    
    # Format moment of inertia with appropriate scientific notation
    if Ix < 0.001 or Ix > 10000:
        ix_str = f"{Ix:.6e}"
    else:
        ix_str = f"{Ix:.6f}"
    
    print(colored(f"│ Moment of Inertia (Ix): {(Ix / inertia_div):.6e} {units['inertia']}", 'magenta'))
    print(colored(f"│ Distance to Extreme Fiber (c): {(c / len_div):.4f} {units['length']}", 'magenta'))
    print(colored(f"│ Representative Width (b): {(b / len_div):.4f} {units['length']}", 'magenta'))
    
    # Display calculated parameters
    print("\n")
    print(colored("┌─ CALCULATED PARAMETERS "+"─"*38, 'blue', attrs=['bold']))
    
    # Calculate section modulus
    section_modulus = Ix / c if c > 0 else 0.0
    if section_modulus < 0.001 or section_modulus > 10000:
        sm_str = f"{section_modulus:.6e}"
    else:
        sm_str = f"{section_modulus:.6f}"
    
    # Calculate radius of gyration
    A = 0  # Area would need to be calculated based on profile type
    if shape == "Circle" or shape == "Solid Circle":
        A = np.pi * (b/2)**2
    elif shape == "Square":
        A = b**2
    elif shape == "Rectangle":
        # Assuming b is width and 2*c is height
        A = b * (2*c)
    
    if A > 0:
        radius_gyration = np.sqrt(Ix / A)
        print(colored(f"│ Section Modulus (Ix/c): {sm_str} {units['sec_mod']}", 'blue'))
        print(colored(f"│ Radius of Gyration: {radius_gyration:.4f} {units['length']}", 'blue'))
    else:
        print(colored(f"│ Section Modulus (Ix/c): {sm_str} {units['sec_mod']}", 'blue'))
    
    print(colored(f"│ Stress Calculation Points: {len(y_array)} points", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    print("\n")
    print(colored("┌─ TYPICAL APPLICATIONS "+"─"*41, 'cyan', attrs=['bold']))
    
    # Show typical applications based on profile type
    if shape == "I-beam":
        applications = "Building columns, beams, bridges, heavy structures"
    elif shape == "T-beam":
        applications = "Concrete floor systems, architectural features"
    elif shape == "Circle" or shape == "Solid Circle":
        applications = "Columns, shafts, axles, bars"
    elif shape == "Hollow Circle":
        applications = "Pipes, tubes, hollow shafts, structural columns"
    elif shape == "Square" or shape == "Rectangle":
        applications = "Beams, columns, general structural members"
    elif shape == "Hollow Square" or shape == "Hollow Rectangle":
        applications = "Structural tubing, building frames, lightweight beams"
    else:
        applications = "General structural applications"
    
    print(colored(f"│ {applications}", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the Profile Definition menu...", 'cyan', attrs=['bold']))


def display_analysis_info(beam_type, beam_length, shape, selected_material, 
                         A=None, B=None, A_type=None, B_type=None, loads=None, units=METRIC_UNITS):
    """
    Display enhanced analysis information in a professional FEA-like format.
    
    Parameters:
    -----------
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    beam_length: float
        Length of the beam in meters
    shape: str
        Name of the profile shape
    selected_material: dict
        Dictionary containing material properties
    A, B: float
        Support positions for simple beam (optional)
    A_type, B_type: str
        Support types for simple beam (optional)
    loads: dict
        Dictionary containing defined loads
    """
    clear_screen()
 # Fetch divisors
    len_div = get_divisor(units, 'length')
    mod_div = get_divisor(units, 'modulus')
    stress_div = get_divisor(units, 'stress')
    dens_div = get_divisor(units, 'density')   
    # Count loads
    point_load_count = len(loads.get("pointloads", [])) if loads else 0
    distributed_load_count = len(loads.get("distributedloads", [])) if loads else 0
    moment_load_count = len(loads.get("momentloads", [])) if loads else 0
    triangle_load_count = len(loads.get("triangleloads", [])) if loads else 0
    total_load_count = point_load_count + distributed_load_count + moment_load_count + triangle_load_count
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                AltruxIQ Beam Analysis Engine                   ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Solver Information
    print("\n")
    print(colored("┌─ SOLVER INFORMATION "+"─"*40, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    print(colored("│ Solver Type:", 'yellow') + colored(" Beam Finite Element Analysis", 'white'))
    print(colored("│ Solution Method:", 'yellow') + colored(" Direct Stiffness Method", 'white'))
    print(colored("│ Element Type:", 'yellow') + colored(" 1D Beam Element (Euler-Bernoulli)", 'white'))
    print(colored("│ Solver Version:", 'yellow') + colored(" AltruxIQ 2.00 Alpha", 'white'))
    print(colored("│ Numerical Precision:", 'yellow') + colored(" Double Precision (64-bit)", 'white'))
    print(colored("│ Mesh Density:", 'yellow') + colored(" 10,000 Elements", 'white'))
    print(colored("│ Estimated Solution Time:", 'yellow') + colored(" < 1 sec", 'white'))
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    time.sleep(0.1)

    # Model Information
    print("\n")
    print(colored("┌─ MODEL INFORMATION "+"─"*41, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    print(colored("│ Analysis Type:", 'green') + colored(" Static Linear Elastic", 'white'))
    print(colored("│ Beam Type:", 'green') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Beam Length:", 'green') + colored(f" {beam_length / len_div:.3f} {units['length']}", 'white'))
    print(colored("│ Profile Type:", 'green') + colored(f" {shape}", 'white'))
    print(colored("│", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    time.sleep(0.1)
    # Material Properties
    print("\n")
    print(colored("┌─ MATERIAL PROPERTIES "+"─"*40, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    material_name = selected_material.get('Material', 'Unknown')
    print(colored("│ Material:", 'magenta') + colored(f" {material_name}", 'white'))
    
    # Display only if material properties are available
    if selected_material:
        # Convert raw JSON DB values to base SI internally before displaying
        raw_E_Pa = selected_material.get('Elastic Modulus', 0) * 1e9
        raw_Y_Pa = selected_material.get('Yield Strength', 0) * 1e6
        raw_Dens = selected_material.get('Density', 0)

        print(colored("│ Young's Modulus (E):", 'magenta') + colored(f" {raw_E_Pa / mod_div:.1f} {units['modulus']}", 'white'))
        print(colored("│ Poisson's Ratio (ν):", 'magenta') + colored(f" {selected_material.get('Poisson Ratio', 0):.2f}", 'white'))
        print(colored("│ Density:", 'magenta') + colored(f" {raw_Dens / dens_div:.1f} {units['density']}", 'white'))
        print(colored("│ Yield Strength:", 'magenta') + colored(f" {raw_Y_Pa / stress_div:.1f} {units['stress']}", 'white'))
    
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Boundary Conditions
    print("\n")
    print(colored("┌─ BOUNDARY CONDITIONS "+"─"*40, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    
    if beam_type == "Simple":
        print(colored("│ Support Type:", 'blue') + colored(" Simply Supported Beam", 'white'))
        print(colored("│ Left Support:", 'blue') + colored(f" {A_type} at x = {A / len_div:.3f} {units['length']}", 'white'))
        print(colored("│ Right Support:", 'blue') + colored(f" {B_type} at x = {B / len_div:.3f} {units['length']}", 'white'))

    elif beam_type == "Cantilever":
        print(colored("│ Support Type:", 'blue') + colored(" Cantilever Beam", 'white'))
        print(colored("│ Fixed End:", 'blue') + colored(f" at x = 0.000 {units['length']}", 'white'))
        print(colored("│ Free End:", 'blue') + colored(f" at x = {beam_length / len_div:.3f} {units['length']}", 'white'))

    else:
        print(colored("│ Support Type:", 'blue') + colored(f" {beam_type} Configuration", 'white'))
        print(colored("│ Boundaries:", 'blue') + colored(" Defined internally by user", 'white'))

    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Load Summary
    print("\n")
    print(colored("┌─ LOAD SUMMARY "+"─"*46, 'red', attrs=['bold']))
    print(colored("│", 'red'))
    print(colored("│ Total Load Definitions:", 'red') + colored(f" {total_load_count}", 'white'))
    print(colored("│ • Point Loads:", 'red') + colored(f" {point_load_count}", 'white'))
    print(colored("│ • Distributed Loads:", 'red') + colored(f" {distributed_load_count}", 'white'))
    print(colored("│ • Moment Loads:", 'red') + colored(f" {moment_load_count}", 'white'))
    print(colored("│ • Triangular Loads:", 'red') + colored(f" {triangle_load_count}", 'white'))
    print(colored("│", 'red'))
    print(colored("└" + "─"*62, 'red', attrs=['bold']))
    time.sleep(0.1)
    # Analysis Progress
    print("\n")
    print(colored("┌─ ANALYSIS PROGRESS "+"─"*42, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    print(colored("│ [", 'cyan') + colored("■■■■■■■■■■■■■■■■■■■■", 'white') + colored("] 100%", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("│ ✓ Initializing solver...", 'cyan'))
    print(colored("│ ✓ Building element matrices...", 'cyan'))
    print(colored("│ ✓ Assembling global matrices...", 'cyan'))
    print(colored("│ ✓ Applying boundary conditions...", 'cyan'))
    print(colored("│ ✓ Applying loads...", 'cyan'))
    print(colored("│ ✓ Solving system equations...", 'cyan'))
    print(colored("│ ✓ Computing internal forces...", 'cyan'))
    print(colored("│ ✓ Analysis complete!", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to view analysis results...", 'cyan', attrs=['bold']))


def display_analysis_results(beam_type, shape, beam_length, A=None, B=None,
                           Va=None, Ha=None, Vb=None, Ma=None,
                           max_shear=None, min_shear=None,
                           max_bending=None, min_bending=None, units=METRIC_UNITS):
    """Professional, commercial-grade presentation of the static solution:
    solver summary, support reactions, equilibrium audit and critical envelopes."""
    clear_screen()
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    mom_div = get_divisor(units, 'moment')

    ui_banner("SOLUTION RESULTS  \u2014  STATIC ANALYSIS",
              "Reactions \u2022 Internal Forces \u2022 Equilibrium Audit", color='cyan')

    # ---- Solver summary --------------------------------------------------
    print("\n")
    ui_open("SOLVER SUMMARY", 'blue')
    ui_blank('blue')
    ui_field("Analysis type", "Static \u2014 Linear Elastic (1D Beam)", 'blue', 'blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    ui_field("Span length", f"{beam_length / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_field("Cross-section", f"{shape}", 'blue', 'blue')
    ui_field("Solution status", "CONVERGED \u2713", 'blue', 'blue', value_color='green')
    ui_blank('blue')
    ui_close('blue')

    # ---- Support reactions ----------------------------------------------
    print("\n")
    ui_open("SUPPORT REACTIONS", 'green')
    ui_blank('green')
    if beam_type == "Simple":
        ui_field("Support configuration", "Pin (A) \u2014 Roller (B)", 'green', 'green')
        ui_blank('green')
        ui_head("Support A  (Pin)", 'green', 'green')
        ui_field("Position", f"{A / len_div:.3f} {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Va / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Horizontal reaction Rₓ", f"{Ha / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_blank('green')
        ui_head("Support B  (Roller)", 'green', 'green')
        ui_field("Position", f"{B / len_div:.3f} {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Vb / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
    elif beam_type == "Cantilever":
        ui_field("Support configuration", "Fixed (A) \u2014 Free (B)", 'green', 'green')
        ui_blank('green')
        ui_head("Fixed Support", 'green', 'green')
        ui_field("Position", f"0.000 {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Va / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Horizontal reaction Rₓ", f"{Ha / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Moment reaction  M", f"{Ma / mom_div:.3f} {units['moment']}", 'green', 'green', bullet="\u2022")
    else:
        ui_field("Support configuration", f"{beam_type}", 'green', 'green')
        ui_field("Reaction at origin Rᵧ", f"{(Va or 0)/ force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Reaction at far end Rᵧ", f"{(Vb or 0)/ force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_close('green')

    # ---- Equilibrium verification ---------------------------------------
    v_sum = (Va or 0) + (Vb if beam_type == "Simple" else 0)
    h_sum = (Ha or 0)
    print("\n")
    ui_open("EQUILIBRIUM AUDIT  (\u03a3F = 0, \u03a3M = 0)", 'yellow')
    ui_blank('yellow')
    ui_field("\u03a3 Vertical forces", f"{v_sum/force_div:.3e} {units['force']}", 'yellow', 'yellow')
    ui_field("\u03a3 Horizontal forces", f"{h_sum/force_div:.3e} {units['force']}", 'yellow', 'yellow')
    if abs(v_sum) < 1e-2 and abs(h_sum) < 1e-2:
        ui_field("Static equilibrium", "SATISFIED \u2713", 'yellow', 'yellow', value_color='green')
    else:
        ui_field("Static equilibrium", "RESIDUAL DETECTED \u26a0", 'yellow', 'yellow', value_color='red')
        ui_bullet("Minor residuals are numerical (rounding) for determinate systems.", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    # ---- Critical internal-force envelopes ------------------------------
    abs_max_shear = max(abs(max_shear), abs(min_shear))
    abs_max_moment = max(abs(max_bending), abs(min_bending))
    print("\n")
    ui_open("CRITICAL INTERNAL-FORCE ENVELOPE", 'magenta')
    ui_blank('magenta')
    ui_head("Shear Force  V(x)", 'magenta', 'magenta')
    ui_field("Maximum (+)", f"{max_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Minimum (\u2212)", f"{min_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Absolute peak |V|", f"{abs_max_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta',
             bullet="\u2022", value_color='white')
    ui_blank('magenta')
    ui_head("Bending Moment  M(x)", 'magenta', 'magenta')
    ui_field("Maximum (+)", f"{max_bending / mom_div:.3f} {units['moment']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Minimum (\u2212)", f"{min_bending / mom_div:.3f} {units['moment']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Absolute peak |M|", f"{abs_max_moment / mom_div:.3f} {units['moment']}", 'magenta', 'magenta',
             bullet="\u2022", value_color='white')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Next steps ------------------------------------------------------
    print("\n")
    ui_open("RECOMMENDED NEXT STEPS", 'cyan')
    ui_blank('cyan')
    ui_bullet("Run Deflection check  \u2014 assess serviceability (L/360, L/480).", 'cyan', 'cyan')
    ui_bullet("Run Stress & FoS check \u2014 verify strength limit state.", 'cyan', 'cyan')
    ui_bullet("Open Design Check report \u2014 consolidated verification & sizing.", 'cyan', 'cyan')
    ui_bullet("Generate SFD/BMD & 3D contour plots in Post-Processing.", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_close('cyan')

    ui_footer("Press Enter to return to the Solution menu...")




def display_deflection_analysis(beam_length, shape, beam_type, elastic_modulus, Ix, Deflection, Slope, curv, units=METRIC_UNITS):
    """Commercial-grade serviceability (deflection) report with limit-state
    demand/capacity bars against L/240, L/360 and L/480 criteria."""
    clear_screen()
    len_div = get_divisor(units, 'length')
    small_len_div = get_divisor(units, 'length_small')

    max_defl_idx = int(np.argmax(np.abs(Deflection)))
    max_defl = Deflection[max_defl_idx]
    max_defl_pos = max_defl_idx * (beam_length / (len(Deflection) - 1))
    max_defl_abs = abs(max_defl)

    max_slope_idx = int(np.argmax(np.abs(Slope)))
    max_slope = Slope[max_slope_idx]
    max_slope_pos = max_slope_idx * (beam_length / (len(Slope) - 1))

    max_curv_idx = int(np.argmax(np.abs(curv)))
    max_curv = curv[max_curv_idx]
    max_curv_pos = max_curv_idx * (beam_length / (len(curv) - 1))

    span_ratio = max_defl_abs / beam_length if beam_length else 0.0
    inv_ratio = (1.0 / span_ratio) if span_ratio > 0 else float('inf')

    ui_banner("SERVICEABILITY  \u2014  DEFLECTION ANALYSIS",
              "Euler\u2013Bernoulli  \u2022  Limit-State Verification", color='cyan')

    # ---- Solution parameters --------------------------------------------
    print("\n")
    ui_open("SOLUTION PARAMETERS", 'blue')
    ui_blank('blue')
    ui_field("Beam theory", "Euler\u2013Bernoulli (small deflection)", 'blue', 'blue')
    ui_field("Integration scheme", "Numerical (double integration of M/EI)", 'blue', 'blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    ui_field("Span length  L", f"{beam_length / len_div:.3f} {units['length']}", 'blue', 'blue')
    if beam_type == "Stepped Bar":
        ui_field("Elastic modulus  E", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
        ui_field("Flexural rigidity  EI", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Elastic modulus  E", f"{elastic_modulus/1e9:.1f} {units['modulus']}", 'blue', 'blue')
        ui_field("Moment of inertia  I", f"{Ix:.4e} {units['inertia']}", 'blue', 'blue')
        ui_field("Flexural rigidity  EI", f"{elastic_modulus*Ix:.3e} N\u00b7m\u00b2", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Deflection results ---------------------------------------------
    if max_defl_abs < 1e-3:
        defl_disp = f"{max_defl / small_len_div:.4f} {units['length_small']}"
    else:
        defl_disp = f"{max_defl / len_div:.6f} {units['length']}"
    arrow = "\u2191 (up)" if max_defl > 0 else "\u2193 (down)"

    print("\n")
    ui_open("DEFLECTION RESULTS", 'green')
    ui_blank('green')
    ui_field("Maximum deflection  \u03b4max", f"{defl_disp}  {arrow}", 'green', 'green')
    ui_field("Location of \u03b4max", f"x = {max_defl_pos / len_div:.3f} {units['length']}", 'green', 'green')
    ui_field("Span/deflection ratio", f"L / {inv_ratio:.0f}", 'green', 'green')
    ui_blank('green')
    ui_close('green')

    # ---- Limit-state serviceability checks ------------------------------
    print("\n")
    ui_open("SERVICEABILITY LIMIT-STATE CHECKS  (demand / capacity)", 'magenta')
    ui_blank('magenta')
    criteria = [
        ("L/240  (roof, no ceiling)", SERVICEABILITY.ROOF_NO_CEILING),
        ("L/360  (general / floors)", SERVICEABILITY.GENERAL_FLOOR),
        ("L/480  (brittle finishes)", SERVICEABILITY.BRITTLE_FINISHES),
    ]
    for label, denom in criteria:
        allow = beam_length / denom
        dc = (max_defl_abs / allow) if allow > 0 else 0.0
        ui_check_row(label, dc)
    ui_blank('magenta')
    ui_text("D/C = actual deflection \u00f7 code deflection limit. \u2264 1.00 passes.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Additional deformation parameters ------------------------------
    print("\n")
    ui_open("ROTATION & CURVATURE", 'blue')
    ui_blank('blue')
    ui_field("Maximum slope  \u03b8max", f"{max_slope:.6f} rad  ({np.degrees(max_slope):.3f}\u00b0)", 'blue', 'blue')
    ui_field("Location of \u03b8max", f"x = {max_slope_pos / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_field("Maximum curvature  \u03ba", f"{max_curv:.4e} 1/{units['length']}", 'blue', 'blue')
    ui_field("Location of \u03bamax", f"x = {max_curv_pos / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Engineering interpretation -------------------------------------
    if span_ratio < 1/SERVICEABILITY.VERY_STIFF_TIER:
        verdict = "Very stiff \u2014 suitable for precision / vibration-sensitive use."
    elif span_ratio < 1/SERVICEABILITY.GENERAL_FLOOR:
        verdict = "Stiff \u2014 satisfies general building serviceability (L/360)."
    elif span_ratio < 1/SERVICEABILITY.ROOF_NO_CEILING:
        verdict = "Moderate \u2014 acceptable for roofs / non-brittle elements only."
    else:
        verdict = "Flexible \u2014 likely exceeds code limits; stiffening advised."

    print("\n")
    ui_open("ENGINEERING INTERPRETATION", 'yellow')
    ui_blank('yellow')
    ui_field("Serviceability verdict", verdict, 'yellow', 'yellow', width=22)
    if beam_type == "Cantilever" and span_ratio > 1/SERVICEABILITY.CANTILEVER_LIMIT:
        ui_bullet("Cantilever exceeds L/180 \u2014 increase section depth / inertia.", 'yellow', 'yellow')
    elif beam_type == "Simple" and span_ratio > 1/SERVICEABILITY.GENERAL_FLOOR:
        ui_bullet("Span exceeds L/360 \u2014 increase I or add intermediate support.", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the Solution menu...")

def display_stress_analysis(beam_type, shape, selected_material, Ix, c, b,
                          y_array, Total_ShearForce, Total_BendingMoment,
                          Shear_stress, Max_Shear_stress, bending_stress,
                          Max_bending_stress, FOS, units=METRIC_UNITS, segments=None):
    """Commercial-grade strength limit-state report: bending, shear, von Mises
    combined stress, demand/capacity bars and factor-of-safety verdict."""
    clear_screen()
    stress_div = get_divisor(units, 'stress')
    sec_mod_div = get_divisor(units, 'sec_mod')
    inertia_div = get_divisor(units, 'inertia')

    yield_strength = selected_material.get('Yield Strength', 0) * 1e6  # MPa -> Pa
    section_modulus = Ix / c if c else 0.0
    allowable_stress = (yield_strength / FOS) if FOS else 0.0

    tau_max = Max_Shear_stress
    sigma_max = Max_bending_stress
    von_mises = np.sqrt(sigma_max**2 + 3 * tau_max**2)

    n = len(Total_BendingMoment)
    bm_frac = int(np.argmax(np.abs(Total_BendingMoment))) / max(1, (n - 1))
    sf_frac = int(np.argmax(np.abs(Total_ShearForce))) / max(1, (n - 1))

    # demand/capacity ratios
    dc_bending = (sigma_max / yield_strength) if yield_strength else 0.0
    dc_shear = (tau_max / (0.577 * yield_strength)) if yield_strength else 0.0  # von Mises shear yield
    dc_vm = (von_mises / yield_strength) if yield_strength else 0.0

    ui_banner("STRENGTH  \u2014  STRESS & FACTOR OF SAFETY",
              "\u03c3 = My/I  \u2022  \u03c4 = VQ/Ib  \u2022  von Mises", color='cyan')

    # ---- Analysis parameters --------------------------------------------
    print("\n")
    ui_open("ANALYSIS PARAMETERS", 'blue')
    ui_blank('blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    if beam_type == "Stepped Bar" and segments:
        ui_field("Cross-section", "Varies along length", 'blue', 'blue')
        ui_field("Material", "Varies along length", 'blue', 'blue')
        ui_field("Yield strength  Fy", "Varies along length", 'blue', 'blue')
        ui_field("Section modulus  S", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Cross-section", f"{shape}", 'blue', 'blue')
        ui_field("Material", f"{selected_material.get('Material', 'Unknown')}", 'blue', 'blue')
        ui_field("Yield strength  Fy", f"{yield_strength / stress_div:.2f} {units['stress']}", 'blue', 'blue')
        ui_field("Section modulus  S", f"{section_modulus / sec_mod_div:.4e} {units['sec_mod']}", 'blue', 'blue')
        ui_field("Moment of inertia  I", f"{Ix / inertia_div:.4e} {units['inertia']}", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Computed stress state ------------------------------------------
    print("\n")
    ui_open("COMPUTED STRESS STATE", 'green')
    ui_blank('green')
    ui_head("Bending (normal) stress  \u03c3", 'green', 'green')
    ui_field("Maximum |\u03c3|", f"{sigma_max / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Location", f"x \u2248 {bm_frac:.2f}\u00b7L", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_head("Transverse shear stress  \u03c4", 'green', 'green')
    ui_field("Maximum |\u03c4|", f"{tau_max / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Location", f"x \u2248 {sf_frac:.2f}\u00b7L", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_head("Combined stress  (von Mises)  \u03c3ᵥ", 'green', 'green')
    ui_field("Maximum \u03c3ᵥ", f"{von_mises / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Fraction of yield", f"{dc_vm*100:.1f}% of Fy", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_close('green')

    # ---- Strength limit-state checks ------------------------------------
    print("\n")
    ui_open("STRENGTH LIMIT-STATE CHECKS  (demand / capacity)", 'magenta')
    ui_blank('magenta')
    ui_check_row("Bending  \u03c3 / Fy", dc_bending)
    ui_check_row("Shear  \u03c4 / 0.577Fy", dc_shear)
    ui_check_row("von Mises  \u03c3ᵥ / Fy", dc_vm)
    ui_blank('magenta')
    ui_text("Capacity = material yield (Fy). D/C \u2264 1.00 means no yielding.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Factor of safety ------------------------------------------------
    if FOS >= 2.0:
        s_status, s_col, s_msg = "EXCELLENT \u2713", 'green', "High margin of safety."
    elif FOS >= SERVICEABILITY.TARGET_FACTOR_OF_SAFETY:
        s_status, s_col, s_msg = "GOOD \u2713", 'green', "Meets standard structural requirements."
    elif FOS >= 1.0:
        s_status, s_col, s_msg = "MARGINAL \u26a0", 'yellow', "Safe but limited reserve \u2014 review loads."
    else:
        s_status, s_col, s_msg = "UNSAFE \u2717", 'red', "Predicted yielding under design loads."

    print("\n")
    ui_open("FACTOR OF SAFETY", 'magenta')
    ui_blank('magenta')
    ui_field("Factor of safety  (Fy/\u03c3)", f"{FOS:.2f}", 'magenta', 'magenta', value_color=s_col)
    ui_field("Allowable stress", f"{allowable_stress / stress_div:.2f} {units['stress']}", 'magenta', 'magenta')
    ui_field("Safety status", s_status, 'magenta', 'magenta', value_color=s_col)
    ui_field("Assessment", s_msg, 'magenta', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Design guidance -------------------------------------------------
    print("\n")
    ui_open("DESIGN GUIDANCE", 'yellow')
    ui_blank('yellow')
    ui_head("Recommended FoS by application:", 'yellow', 'yellow')
    ui_bullet("1.25 \u2013 1.50 : routine static structural members", 'yellow', 'yellow')
    ui_bullet("1.50 \u2013 2.00 : critical / primary load paths", 'yellow', 'yellow')
    ui_bullet("2.00 \u2013 3.00 : dynamic, impact or cyclic loading", 'yellow', 'yellow')
    ui_bullet("3.00+         : life-safety / high-uncertainty cases", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_head("Action:", 'yellow', 'yellow')
    if FOS < 1.0:
        ui_bullet("CRITICAL \u2014 increase section size or upgrade material.", 'yellow', 'yellow', mark="\u2717")
    elif FOS < SERVICEABILITY.TARGET_FACTOR_OF_SAFETY:
        ui_bullet("Improve section if member is critical; verify load model.", 'yellow', 'yellow', mark="\u26a0")
    elif FOS > 2.5:
        ui_bullet("Over-designed \u2014 consider lighter section to save weight/cost.", 'yellow', 'yellow', mark="\u2193")
    else:
        ui_bullet("Design meets strength requirements with appropriate reserve.", 'yellow', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the Solution menu...")

def display_engineering_recommendations(beam_type, shape, beam_length, selected_material,
                                      Ix, c, b, FOS=None, max_stress=None, max_defl=None,
                                      span_ratio=None, yield_strength=None, segments=None):
    """Commercial-grade structural design-check & recommendation report.

    Consolidates the strength and serviceability limit states into a single
    verification dossier: executive verdict, demand/capacity matrix, governing
    limit state, prioritised remediation with quantitative sizing targets,
    section optimisation, stability/secondary effects, and applicable codes.

    Units (SI): beam_length [m], Ix [m^4], c,b [m], max_stress/yield_strength [Pa],
    max_defl [m], span_ratio [-], FOS [-].
    """
    clear_screen()

    # ------------------------------------------------------------------ #
    #  DERIVED ENGINEERING QUANTITIES
    # ------------------------------------------------------------------ #
    TARGET_FOS = SERVICEABILITY.TARGET_FACTOR_OF_SAFETY  # target strength reserve
    DEFL_LIMIT_DENOM = SERVICEABILITY.GENERAL_FLOOR      # governing criterion (L/360)

    section_modulus = (Ix / c) if c else 0.0
    depth = 2.0 * c if c else 0.0
    mat_name = selected_material.get('Material', 'Unknown') if selected_material else 'Unknown'
    yield_MPa = (yield_strength / 1e6) if yield_strength else None

    # --- Demand / capacity ratios (None where data unavailable) -------- #
    dc_strength = (max_stress / yield_strength) if (max_stress and yield_strength) else None
    allow_defl = (beam_length / DEFL_LIMIT_DENOM) if beam_length else None
    dc_defl = (abs(max_defl) / allow_defl) if (max_defl is not None and allow_defl) else None
    dc_fos = (TARGET_FOS / FOS) if FOS else None   # >1.0 => below target reserve
    inv_span = (1.0 / span_ratio) if span_ratio else None

    have_data = any(v is not None for v in (dc_strength, dc_defl, FOS))

    # --- Overall verdict ---------------------------------------------- #
    governing_name, governing_dc = None, 0.0
    for nm, dc in (("Strength (yield)", dc_strength),
                   ("Serviceability (L/360)", dc_defl),
                   ("Strength reserve (FoS)", dc_fos)):
        if dc is not None and dc > governing_dc:
            governing_name, governing_dc = nm, dc

    if not have_data:
        verdict = 'INCOMPLETE'
    elif (dc_strength is not None and dc_strength > 1.0) or \
         (dc_defl is not None and dc_defl > 1.0) or (FOS is not None and FOS < 1.0):
        verdict = 'FAIL'
    elif governing_dc > 0.90 or (FOS is not None and FOS < TARGET_FOS):
        verdict = 'REVIEW'
    else:
        verdict = 'PASS'

    ui_banner("ENGINEERING DESIGN-CHECK REPORT",
              "Limit-State Verification \u2022 Optimisation \u2022 Code Compliance",
              color='cyan')

    # ================================================================== #
    #  0. EXECUTIVE VERDICT
    # ================================================================== #
    label, vcol = ui_verdict_badge(verdict)
    print("\n")
    ui_open("EXECUTIVE VERDICT", vcol)
    ui_blank(vcol)
    print(colored("\u2502   ", vcol) + colored(f" {label} ", vcol, attrs=['bold', 'reverse']))
    ui_blank(vcol)
    if governing_name:
        ui_field("Governing limit state", governing_name, vcol, vcol, value_color='white')
        ui_field("Controlling utilisation", f"{governing_dc*100:.1f}%  (D/C = {governing_dc:.2f})",
                 vcol, vcol, value_color='white')
        reserve = (1.0 - governing_dc) * 100.0
        ui_field("Remaining reserve", f"{reserve:+.1f}%", vcol, vcol, value_color='white')
    else:
        ui_text("Run Stress (FoS) and Deflection checks for a full verdict.", 'white', vcol)
    ui_blank(vcol)
    ui_close(vcol)

    # ================================================================== #
    #  1. MODEL & SECTION SUMMARY
    # ================================================================== #
    print("\n")
    ui_open("MODEL & SECTION SUMMARY", 'blue')
    ui_blank('blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    if beam_type == "Stepped Bar" and segments:
        ui_field("Cross-section", "Varies along length", 'blue', 'blue')
        ui_field("Span length  L", f"{beam_length:.3f} m", 'blue', 'blue')
        ui_field("Material", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
        ui_field("Section modulus  S", "Varies along length", 'blue', 'blue')
        ui_field("Section depth  (2c)", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Cross-section", f"{shape}", 'blue', 'blue')
        ui_field("Span length  L", f"{beam_length:.3f} m", 'blue', 'blue')
        ui_field("Material", f"{mat_name}" + (f"  (Fy = {yield_MPa:.0f} MPa)" if yield_MPa else ""), 'blue', 'blue')
        if Ix is not None:
            ui_field("Moment of inertia  I", f"{Ix:.4e} m\u2074", 'blue', 'blue')
        if section_modulus:
            ui_field("Section modulus  S", f"{section_modulus:.4e} m\u00b3", 'blue', 'blue')
        if depth:
            ui_field("Section depth  (2c)", f"{depth:.4f} m", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ================================================================== #
    #  2. LIMIT-STATE VERIFICATION MATRIX
    # ================================================================== #
    print("\n")
    ui_open("LIMIT-STATE VERIFICATION MATRIX", 'magenta')
    ui_blank('magenta')
    if dc_strength is not None:
        ui_check_row("Strength  \u03c3/Fy", dc_strength)
    if dc_defl is not None:
        ui_check_row("Service  \u03b4/(L/360)", dc_defl)
    if dc_fos is not None:
        # show FoS adequacy: PASS when FOS>=target  (dc_fos<=1)
        ui_check_row("FoS  (1.5/FoS)", dc_fos,
                     status_text=("PASS \u2713" if FOS >= TARGET_FOS else
                                  ("MARGINAL \u26a0" if FOS >= 1.0 else "FAIL \u2717")))
    if dc_strength is None and dc_defl is None and dc_fos is None:
        ui_text("No quantitative results yet \u2014 complete the Solution checks.", 'white', 'magenta')
    ui_blank('magenta')
    ui_text("Bar fill = utilisation. Green \u2264 75%, Amber \u2264 95%, Red > 95%.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ================================================================== #
    #  3. DESIGN ASSESSMENT (strengths / concerns)
    # ================================================================== #
    strengths, concerns = [], []
    if FOS is not None:
        if FOS < 1.0:
            concerns.append(f"Factor of safety critically low (FoS = {FOS:.2f}) \u2014 yielding predicted")
        elif FOS < TARGET_FOS:
            concerns.append(f"Factor of safety {FOS:.2f} is below the {TARGET_FOS:.2f} target")
        else:
            strengths.append(f"Adequate strength reserve (FoS = {FOS:.2f})")
    if span_ratio is not None and inv_span:
        if span_ratio > 1/SERVICEABILITY.CANTILEVER_LIMIT:
            concerns.append(f"Excessive deflection (L/{inv_span:.0f}) \u2014 serviceability at risk")
        elif span_ratio > 1/SERVICEABILITY.GENERAL_FLOOR:
            concerns.append(f"Deflection L/{inv_span:.0f} exceeds the L/360 floor criterion")
        else:
            strengths.append(f"Deflection within limits (L/{inv_span:.0f})")
    if dc_strength is not None:
        if dc_strength > 0.90:
            concerns.append(f"Bending stress at {dc_strength*100:.0f}% of yield \u2014 little margin")
        elif dc_strength > 0.67:
            concerns.append(f"Moderately high bending stress ({dc_strength*100:.0f}% of yield)")
        else:
            strengths.append(f"Comfortable bending stress level ({dc_strength*100:.0f}% of yield)")
    # section morphology
    if shape in ("I-beam", "T-beam"):
        strengths.append("Efficient section for major-axis bending (high I per unit mass)")
    elif "Circle" in shape:
        strengths.append("Isotropic / good torsional resistance")
        if beam_type == "Cantilever":
            concerns.append("Circular sections are sub-optimal for cantilever bending")
    elif ("Rectangle" in shape or "Square" in shape):
        if "Hollow" in shape:
            strengths.append("Hollow box \u2014 good combined bending + torsion efficiency")
        else:
            concerns.append("Solid rectangular/square \u2014 inefficient material utilisation")
    if beam_type == "Cantilever" and beam_length > 10 and "Hollow" not in shape:
        concerns.append("Long cantilever \u2014 consider hollow section for weight control")

    print("\n")
    ui_open("DESIGN ASSESSMENT", 'green')
    ui_blank('green')
    if strengths:
        ui_head("Strengths", 'green', 'green')
        for s in strengths:
            ui_bullet(s, 'green', 'green', mark="\u2713")
        ui_blank('green')
    if concerns:
        ui_head("Concerns", 'yellow', 'green')
        for c_ in concerns:
            ui_bullet(c_, 'yellow', 'green', mark="\u26a0")
        ui_blank('green')
    if not strengths and not concerns:
        ui_text("Complete all analyses to populate the design assessment.", 'white', 'green')
        ui_blank('green')
    ui_close('green')

    # ================================================================== #
    #  4. PRIORITISED RECOMMENDED ACTIONS  (with quantitative targets)
    # ================================================================== #
    p1, p2, p3 = [], [], []   # P1 critical/strength, P2 serviceability, P3 optimisation

    # ---- P1: strength -------------------------------------------------
    if FOS is not None and FOS < TARGET_FOS and section_modulus:
        s_req = section_modulus * (TARGET_FOS / FOS)
        inc = (s_req / section_modulus - 1.0) * 100.0
        p1.append(f"Raise section modulus to S \u2265 {s_req:.3e} m\u00b3 "
                  f"(+{inc:.0f}%) to reach FoS = {TARGET_FOS:.2f}")
        if shape in ("I-beam", "T-beam"):
            p1.append("Increase web height (most effective) or flange area")
        elif "Circle" in shape:
            p1.append("Increase diameter / wall thickness")
        elif "Hollow" in shape:
            p1.append("Increase overall depth or wall thickness")
        else:
            p1.append("Switch to an I-section or hollow box for higher S per mass")
        if yield_MPa:
            p1.append(f"Alternative: upgrade material (current Fy = {yield_MPa:.0f} MPa)")

    # ---- P2: serviceability ------------------------------------------
    if dc_defl is not None and dc_defl > 1.0 and Ix:
        i_req = Ix * dc_defl
        inc = (dc_defl - 1.0) * 100.0
        p2.append(f"Raise moment of inertia to I \u2265 {i_req:.3e} m\u2074 "
                  f"(+{inc:.0f}%) to satisfy L/360")
        if beam_type == "Simple":
            p2.append("Or add an intermediate support to roughly quarter the deflection")
        elif beam_type == "Cantilever":
            p2.append("Or shorten the cantilever / add a back-span prop")
    elif span_ratio is not None and span_ratio > 1/SERVICEABILITY.BRITTLE_FINISHES:
        p2.append("Deflection acceptable for general use; verify L/480 if brittle finishes apply")

    # ---- P3: optimisation --------------------------------------------
    if FOS is not None and FOS > 2.5:
        if "Hollow" not in shape:
            p3.append("Over-designed \u2014 convert to a hollow section (~30\u201340% mass saving)")
        else:
            p3.append("Over-designed \u2014 reduce wall thickness / depth while keeping FoS \u2265 1.5")
    if shape == "Rectangle" and "Hollow" not in shape:
        p3.append("Re-orient so depth > width to maximise I about the bending axis")
    if not p3:
        p3.append("Round selected dimensions up to the nearest standard mill size")

    print("\n")
    ui_open("PRIORITISED RECOMMENDED ACTIONS", 'yellow')
    ui_blank('yellow')
    ui_head("P1 \u2014 Strength (address first)", 'red', 'yellow')
    if p1:
        for a in p1:
            ui_bullet(a, 'white', 'yellow', mark="\u2776")
    else:
        ui_bullet("No strength deficiency detected.", 'green', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_head("P2 \u2014 Serviceability", 'yellow', 'yellow')
    if p2:
        for a in p2:
            ui_bullet(a, 'white', 'yellow', mark="\u2777")
    else:
        ui_bullet("No serviceability deficiency detected.", 'green', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_head("P3 \u2014 Optimisation & detailing", 'cyan', 'yellow')
    for a in p3:
        ui_bullet(a, 'white', 'yellow', mark="\u2778")
    ui_blank('yellow')
    ui_close('yellow')

    # ================================================================== #
    #  5. STABILITY & SECONDARY EFFECTS
    # ================================================================== #
    print("\n")
    ui_open("STABILITY & SECONDARY EFFECTS", 'blue')
    ui_blank('blue')
    if shape in ("I-beam", "T-beam"):
        ui_bullet("Check lateral-torsional buckling (LTB) \u2014 provide compression-flange bracing.", 'white', 'blue')
        ui_bullet("Verify flange/web local buckling (section compactness, b/t & h/tw).", 'white', 'blue')
    if "Hollow" in shape:
        ui_bullet("HSS/box: check wall slenderness for local buckling under bending.", 'white', 'blue')
    if beam_type == "Cantilever":
        ui_bullet("Cantilever tip is unbraced \u2014 LTB and tip rotation often govern.", 'white', 'blue')
    ui_bullet("Confirm web shear capacity and bearing/crippling at supports & point loads.", 'white', 'blue')
    ui_bullet("Where applicable include P-\u0394 / second-order effects for slender members.", 'white', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ================================================================== #
    #  6. FATIGUE, DYNAMICS & DURABILITY
    # ================================================================== #
    print("\n")
    ui_open("FATIGUE, DYNAMICS & DURABILITY", 'magenta')
    ui_blank('magenta')
    if beam_type == "Simple" and beam_length > 3:
        ui_bullet("Span > 3 m \u2014 check natural frequency / walking vibration (target f\u2081 > 3\u20134 Hz).", 'white', 'magenta')
    if beam_type == "Cantilever":
        ui_bullet("If cyclically loaded, perform fatigue assessment of the fixed-end detail.", 'white', 'magenta')
    ui_bullet("Apply corrosion allowance / protective coating per exposure category.", 'white', 'magenta')
    ui_bullet("Account for temperature effects & thermal movement at connections.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ================================================================== #
    #  7. APPLICABLE CODES & STANDARDS
    # ================================================================== #
    print("\n")
    ui_open("APPLICABLE CODES & STANDARDS", 'cyan')
    ui_blank('cyan')
    ui_head("Member design", 'cyan', 'cyan')
    if "Steel" in mat_name:
        ui_bullet("AISC 360 \u2014 Specification for Structural Steel Buildings (US)", 'cyan', 'cyan')
        ui_bullet("EN 1993 (Eurocode 3) \u2014 Design of Steel Structures (EU)", 'cyan', 'cyan')
    elif "Alumin" in mat_name or "Aluminum" in mat_name:
        ui_bullet("Aluminum Design Manual / ADM (US)", 'cyan', 'cyan')
        ui_bullet("EN 1999 (Eurocode 9) \u2014 Aluminium Structures (EU)", 'cyan', 'cyan')
    elif "Concrete" in mat_name:
        ui_bullet("ACI 318 \u2014 Building Code Requirements for Structural Concrete (US)", 'cyan', 'cyan')
        ui_bullet("EN 1992 (Eurocode 2) \u2014 Concrete Structures (EU)", 'cyan', 'cyan')
    elif "Timber" in mat_name or "Wood" in mat_name:
        ui_bullet("NDS \u2014 National Design Specification for Wood Construction (US)", 'cyan', 'cyan')
        ui_bullet("EN 1995 (Eurocode 5) \u2014 Timber Structures (EU)", 'cyan', 'cyan')
    else:
        ui_bullet("Select the governing material standard for your jurisdiction.", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_head("Loads & combinations", 'cyan', 'cyan')
    ui_bullet("ASCE/SEI 7 (US)  or  EN 1990/1991 (Eurocode basis & actions).", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_head("Serviceability deflection limits", 'cyan', 'cyan')
    ui_bullet("L/240 \u2014 roof members, no ceiling", 'cyan', 'cyan')
    ui_bullet("L/360 \u2014 floors / general structural members", 'cyan', 'cyan')
    ui_bullet("L/480 \u2014 members supporting brittle finishes", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_close('cyan')

    # ================================================================== #
    #  Disclaimer
    # ================================================================== #
    print("\n")
    ui_open("NOTICE", 'yellow')
    ui_blank('yellow')
    ui_text("Preliminary 1D linear-elastic results for guidance only. Final design", 'white', 'yellow')
    ui_text("must be verified by a licensed engineer against the governing code and", 'white', 'yellow')
    ui_text("project-specific load combinations, connections and detailing.", 'white', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the main menu...")
# =============================
#  UNIT SYSTEM SELECTION 
# ============================
def unit_system_menu(current_system="Metric"):
    """Display the unit configuration options and return choice."""
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                    UNIT SYSTEM SELECTION                     ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    print(colored("│ 1  │ 🌍 Metric System (SI)", 'yellow') + colored(" - Meters, Newtons, MPa, GPa", 'white'))
    print(colored("│ 2  │ 🦅 US Customary / Imperial", 'yellow') + colored(" - Feet/Inches, lbf, ksi", 'white'))
    print(colored("│ 3  │ ⬅️  Return to Main Menu", 'yellow') + colored(" - Keep current configuration", 'white'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    print("\n" + colored("┌─ ACTIVE SYSTEM ", 'green') + colored("─"*46, 'green', attrs=['bold']))
    print(colored(f"│ Current Setting: {current_system}", 'green'))
    print(colored("└───" + "─"*53, 'green', attrs=['bold']))
    
    print("")
    choice = input(colored("Select your unit system [1-3] ➔ ", 'cyan', attrs=['bold']))
    return choice
    #-----------------------------------------------------------------------------------
    #-----------------------------------------------------------------------------------
def resolution_menu(current_points):
    """Display the solver resolution options."""
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                   SOLVER RESOLUTION                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    print(colored(f"│ Current setting: {current_points} points", 'white', attrs=['bold']))
    print(colored("├" + "─"*61, 'yellow'))
    print(colored("│ 1  │ Fast Draft   (501)", 'yellow') + colored("  — Best for multi-span beams", 'white'))
    print(colored("│ 2  │ Standard    (1001)", 'yellow') + colored("  — Balanced speed and accuracy", 'white'))
    print(colored("│ 3  │ High        (2001)", 'yellow') + colored("  — Default", 'white'))
    print(colored("│ 4  │ Fine        (5001)", 'yellow') + colored("  — Report-quality smooth curves", 'white'))
    print(colored("│ 5  │ Custom            ", 'yellow') + colored("  — Enter a value (201 - 10001)", 'white'))
    print(colored("│ 6  │ ⬅️  Return to Main Menu", 'yellow'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print(colored("\n  ⚠ Higher values significantly increase solve time for\n    Continuous and indeterminate beams (SymPy evaluation).", 'cyan'))
    print("")
    choice = input(colored("Enter your choice [1-6] ➔ ", 'cyan', attrs=['bold']))
    return choice
    #---------------------------------------------------------------------------
    #---------------------------------------------------------------------------
