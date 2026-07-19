import time
import datetime
import numpy as np
from termcolor import colored

from common.units import METRIC_UNITS, get_divisor
from ui.console import (
    fmt_datetime,
    fmt_duration,
    session_uptime,
    input_with_live_clock,
    ui_banner,
    ui_open,
    ui_close,
    ui_blank,
    ui_field,
    ui_bar,
    ui_menu_stage,
    clear_screen,
    print_error,
)

# =============================================================================
#  BEAM-FEA DOMAIN UI
# -----------------------------------------------------------------------------
#  Navigation menus and the post-confirmation profile summary screen
#  (``display_profile_info``). The analysis / deflection / stress /
#  engineering-recommendations report renderers now live in ``ui.reports``;
#  the generic terminal kit (widgets, prompts, formatters, session clock)
#  lives in ``ui.console``. Extracted during the P3 decomposition.
# =============================================================================


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
