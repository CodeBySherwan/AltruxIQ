"""Main workflow and project-management navigation menus.

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
import datetime
from termcolor import colored

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
)
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
