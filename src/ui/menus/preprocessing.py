"""Pre-processing navigation menus: profile, section library, material,
boundary conditions and loads definition.

Extracted from ``ui.Menus`` during the P3 ``ui/menus/`` decomposition
(checkpoint-5). Pure relocation; signatures and behavior unchanged.
"""
import time
from termcolor import colored

from common.units import METRIC_UNITS
from ui.console import clear_screen, print_error
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
    return input(colored("Enter your choice [1-6] ➔ ", 'cyan', attrs=['bold']))
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
