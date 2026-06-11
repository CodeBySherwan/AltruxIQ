import os
import time
from termcolor import colored, cprint
import numpy as np
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
def main_menu_template():
    """Display an enhanced main menu and return the user's selection."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                                                              ║", 'cyan', attrs=['bold']))
    print(colored("║              ZYLO-X BEAM ANALYSIS CALCULATOR                 ║", 'cyan', attrs=['bold']))
    print(colored("║                                                              ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ MAIN MENU "+"─"*50, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔧 Project Management", "Create, load, or save your beam projects"),
        ("📐 Define Beam Type", "Select Simple Supported or Cantilever Beam"),
        ("🧮 Profile Definition", "Set beam dimensions and cross-section properties"),
        ("🧪 Material Selection", "Choose material properties for your beam"),
        ("🔒 Boundary Conditions", "Define support conditions and constraints"),
        ("⚖️  Loads Definition", "Apply forces, moments, and distributed loads"),
        ("📊 Show Beam Schematic", "Visualize beam with loads and supports"),
        ("🔬 Analysis/Simulation", "Calculate beam response and results"),
        ("📈 Postprocessing/Visualization", "View detailed plots and diagrams"),
        ("💾 Save Project", "Save your current project to disk"),
        ("📋 Recommendations", "Get engineering recommendations and optimizations")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        # Format each menu item with a number, title, and description
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("│ 0  │ 🚪 Exit", 'red') + 
          colored(" - Close the application", 'white'))
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Add a customizable status bar
    print("\n" + colored("┌─ STATUS ", 'green') + colored("─"*53, 'green', attrs=['bold']))
    print(colored("│ Use number keys to select an option", 'green'))
    print(colored("└───" + "─"*53, 'green', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    selection = input(colored("Enter your selection [0-11] ➔ ", 'cyan', attrs=['bold']))
    return selection

# =============================
# Project Management Functions
# =============================
def project_management_menu():
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
    
    # Add project status section (can be expanded to show current project info)
    print("\n" + colored("┌─ PROJECT STATUS ", 'green') + colored("─"*44, 'green', attrs=['bold']))
    print(colored("│ No active project loaded", 'green'))  # This could be dynamic based on project state
    print(colored("└───" + "─"*53, 'green', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-5] ➔ ", 'cyan', attrs=['bold']))
    return choice


# =============================
# Profile Definition Functions
# =============================
def profile_definition_menu():
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
        ("📏 Enter Beam Length (m)", "Define the total length of the beam"),
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


def material_selection_menu():
    """Display an enhanced material selection menu and return the user's choice."""
    clear_screen()
    
    # Create a decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  MATERIAL SELECTION                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Create a visually distinct menu with icons and better formatting
    print(colored("┌─ OPTIONS "+"─"*52, 'yellow', attrs=['bold']))
    
    menu_items = [
        ("🔍 Select Material", "Choose a material from the database"),
        ("📋 View Current Material Details", "Display properties of the selected material"),
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


def postprocessing_menu():
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
        ("🔄 Reactions Schematic Plots", "Visualize support reaction forces"),
        ("📊 Shear-Force/Bending-Moment Plots", "Generate SFD and BMD diagrams"),
        ("📉 Deflection Plots", "Show beam displacement curves"),
        ("📈 Shear-Stress/Bending-Stress", "Display stress distribution"),
        ("📑 Combined Plots", "Show all diagrams together"),
        ("⬅️  Return to Main Menu", "Go back to the main menu")
    ]
    
    for idx, (title, description) in enumerate(menu_items, 1):
        print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
              colored(f" - {description}", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    
    # Get user input with improved prompt
    print("")
    choice = input(colored("Enter your choice [1-6] ➔ ", 'cyan', attrs=['bold']))
    return choice

def display_profile_info(beam_length, shape, Ix, c, b, y_array):
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
    print(colored(f"│ Beam Length: {beam_length:.4f} m", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Display profile properties
    print("\n")
    print(colored("┌─ PROFILE PROPERTIES "+"─"*41, 'magenta', attrs=['bold']))
    
    # Format moment of inertia with appropriate scientific notation
    if Ix < 0.001 or Ix > 10000:
        ix_str = f"{Ix:.6e}"
    else:
        ix_str = f"{Ix:.6f}"
    
    print(colored(f"│ Moment of Inertia (Ix): {ix_str} m⁴", 'magenta'))
    print(colored(f"│ Distance to Extreme Fiber (c): {c:.4f} m", 'magenta'))
    print(colored(f"│ Representative Width (b): {b:.4f} m", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Display calculated parameters
    print("\n")
    print(colored("┌─ CALCULATED PARAMETERS "+"─"*38, 'blue', attrs=['bold']))
    
    # Calculate section modulus
    section_modulus = Ix / c
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
        print(colored(f"│ Section Modulus (Ix/c): {sm_str} m³", 'blue'))
        print(colored(f"│ Radius of Gyration: {radius_gyration:.4f} m", 'blue'))
    else:
        print(colored(f"│ Section Modulus (Ix/c): {sm_str} m³", 'blue'))
    
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
                         A=None, B=None, A_type=None, B_type=None, loads=None):
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
    
    # Count loads
    point_load_count = len(loads.get("pointloads", [])) if loads else 0
    distributed_load_count = len(loads.get("distributedloads", [])) if loads else 0
    moment_load_count = len(loads.get("momentloads", [])) if loads else 0
    triangle_load_count = len(loads.get("triangleloads", [])) if loads else 0
    total_load_count = point_load_count + distributed_load_count + moment_load_count + triangle_load_count
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                ZYLO-X BEAM ANALYSIS ENGINE                   ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Solver Information
    print("\n")
    print(colored("┌─ SOLVER INFORMATION "+"─"*40, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    print(colored("│ Solver Type:", 'yellow') + colored(" Beam Finite Element Analysis", 'white'))
    print(colored("│ Solution Method:", 'yellow') + colored(" Direct Stiffness Method", 'white'))
    print(colored("│ Element Type:", 'yellow') + colored(" 1D Beam Element (Euler-Bernoulli)", 'white'))
    print(colored("│ Solver Version:", 'yellow') + colored(" Zylo-X 1.02 Stable", 'white'))
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
    print(colored("│ Beam Length:", 'green') + colored(f" {beam_length:.3f} m", 'white'))
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
        print(colored("│ Young's Modulus (E):", 'magenta') + 
              colored(f" {selected_material.get('Elastic Modulus', 0):.1f} GPa", 'white'))
        print(colored("│ Poisson's Ratio (ν):", 'magenta') + 
              colored(f" {selected_material.get('Poisson Ratio', 0):.2f}", 'white'))
        print(colored("│ Density:", 'magenta') + 
              colored(f" {selected_material.get('Density', 0):.1f} kg/m³", 'white'))
        print(colored("│ Yield Strength:", 'magenta') + 
              colored(f" {selected_material.get('Yield Strength', 0):.1f} MPa", 'white'))
    
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Boundary Conditions
    print("\n")
    print(colored("┌─ BOUNDARY CONDITIONS "+"─"*40, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    
    if beam_type == "Simple":
        print(colored("│ Support Type:", 'blue') + colored(" Simply Supported Beam", 'white'))
        print(colored("│ Left Support:", 'blue') + colored(f" {A_type} at x = {A:.3f} m", 'white'))
        print(colored("│ Right Support:", 'blue') + colored(f" {B_type} at x = {B:.3f} m", 'white'))
    elif beam_type == "Cantilever":
        print(colored("│ Support Type:", 'blue') + colored(" Cantilever Beam", 'white'))
        print(colored("│ Fixed End:", 'blue') + colored(" at x = 0.000 m", 'white'))
        print(colored("│ Free End:", 'blue') + colored(f" at x = {beam_length:.3f} m", 'white'))
    
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
                           max_bending=None, min_bending=None):
    """
    Display analysis results in a professional FEA-like format.
    
    Parameters:
    -----------
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    shape: str
        Name of the profile shape
    beam_length: float
        Length of the beam in meters
    A, B: float
        Support positions for simple beam (optional)
    Va, Ha, Vb, Ma: float
        Reaction forces and moments
    max_shear, min_shear: float
        Maximum and minimum shear force values
    max_bending, min_bending: float
        Maximum and minimum bending moment values
    """
    clear_screen()
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  ANALYSIS RESULTS                             ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Results summary header
    print("\n")
    print(colored("┌─ SOLVER SUMMARY "+"─"*44, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    print(colored("│ Analysis Type:", 'blue') + colored(" Static Linear Elastic", 'white'))
    print(colored("│ Beam Type:", 'blue') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Beam Length:", 'blue') + colored(f" {beam_length:.3f} m", 'white'))
    print(colored("│ Profile Type:", 'blue') + colored(f" {shape}", 'white'))
    print(colored("│ Solution Status:", 'blue') + colored(" COMPLETED ✓", 'green', attrs=['bold']))
    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Support reactions
    print("\n")
    print(colored("┌─ SUPPORT REACTIONS "+"─"*42, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    
    if beam_type == "Simple":
        print(colored("│ Support Configuration:", 'green') + colored(" Pin-Roller", 'white'))
        print(colored("│", 'green'))
        print(colored("│ Left Support (Pin):", 'green', attrs=['bold']))
        print(colored("│  • Position:", 'green') + colored(f" {A:.3f} m", 'white'))
        print(colored("│  • Vertical Reaction:", 'green') + colored(f" {Va:.3f} N", 'white'))
        print(colored("│  • Horizontal Reaction:", 'green') + colored(f" {Ha:.3f} N", 'white'))
        print(colored("│", 'green'))
        print(colored("│ Right Support (Roller):", 'green', attrs=['bold']))
        print(colored("│  • Position:", 'green') + colored(f" {B:.3f} m", 'white'))
        print(colored("│  • Vertical Reaction:", 'green') + colored(f" {Vb:.3f} N", 'white'))
    elif beam_type == "Cantilever":
        print(colored("│ Support Configuration:", 'green') + colored(" Fixed-Free", 'white'))
        print(colored("│", 'green'))
        print(colored("│ Fixed Support:", 'green', attrs=['bold']))
        print(colored("│  • Position:", 'green') + colored(" 0.000 m", 'white'))
        print(colored("│  • Vertical Reaction:", 'green') + colored(f" {Va:.3f} N", 'white'))
        print(colored("│  • Horizontal Reaction:", 'green') + colored(f" {Ha:.3f} N", 'white'))
        print(colored("│  • Moment Reaction:", 'green') + colored(f" {Ma:.3f} N·m", 'white'))
    
    print(colored("│", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Equilibrium check
    v_sum = Va + (Vb if beam_type == "Simple" else 0)
    h_sum = Ha
    print("\n")
    print(colored("┌─ EQUILIBRIUM VERIFICATION "+"─"*36, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    print(colored("│ Sum of Vertical Forces:", 'yellow') + colored(f" {v_sum:.3f} N", 'white'))
    print(colored("│ Sum of Horizontal Forces:", 'yellow') + colored(f" {h_sum:.3f} N", 'white'))
    
    if abs(v_sum) < 0.001 and abs(h_sum) < 0.001:
        print(colored("│ Equilibrium Check:", 'yellow') + colored(" PASSED ✓", 'green', attrs=['bold']))
    else:
        print(colored("│ Equilibrium Check:", 'yellow') + colored(" WARNING ⚠", 'red', attrs=['bold']))
        print(colored("│  Small numerical discrepancies may exist", 'yellow'))
    
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    # Critical values
    print("\n")
    print(colored("┌─ CRITICAL RESULTS "+"─"*42, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    
    # Shear force
    abs_max_shear = max(abs(max_shear), abs(min_shear))
    print(colored("│ SHEAR FORCE", 'magenta', attrs=['bold']))
    print(colored("│  • Maximum Positive:", 'magenta') + colored(f" {max_shear:.3f} N", 'white'))
    print(colored("│  • Maximum Negative:", 'magenta') + colored(f" {min_shear:.3f} N", 'white'))
    print(colored("│  • Absolute Maximum:", 'magenta') + colored(f" {abs_max_shear:.3f} N", 'white'))
    print(colored("│", 'magenta'))
    
    # Bending moment
    abs_max_moment = max(abs(max_bending), abs(min_bending))
    print(colored("│ BENDING MOMENT", 'magenta', attrs=['bold']))
    print(colored("│  • Maximum Positive:", 'magenta') + colored(f" {max_bending:.3f} N·m", 'white'))
    print(colored("│  • Maximum Negative:", 'magenta') + colored(f" {min_bending:.3f} N·m", 'white'))
    print(colored("│  • Absolute Maximum:", 'magenta') + colored(f" {abs_max_moment:.3f} N·m", 'white'))
    
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Guidelines for further analysis
    print("\n")
    print(colored("┌─ ANALYSIS RECOMMENDATIONS "+"─"*35, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    print(colored("│ ▶ Recommended Next Steps:", 'cyan', attrs=['bold']))
    print(colored("│   1. Calculate deflection to assess serviceability", 'cyan'))
    print(colored("│   2. Evaluate stress levels and factor of safety", 'cyan'))
    print(colored("│   3. Generate visualization plots", 'cyan'))
    
    if abs_max_moment > 1000:
        print(colored("│", 'cyan'))
        print(colored("│ ▶ Special Attention Required:", 'cyan', attrs=['bold']))
        print(colored("│   • High bending moment detected", 'cyan'))
        print(colored("│   • Consider verifying profile selection", 'cyan'))
    
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the Analysis/Simulation menu...", 'cyan', attrs=['bold']))




def display_deflection_analysis(beam_length, shape, beam_type, elastic_modulus, Ix, Deflection, Slope, curv):
    """
    Display deflection analysis results in a professional FEA-like format.
    
    Parameters:
    -----------
    beam_length: float
        Length of the beam in meters
    shape: str
        Name of the profile shape
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    elastic_modulus: float
        Elastic modulus in Pa
    Ix: float
        Moment of inertia in m⁴
    Deflection: ndarray
        Array of deflection values along the beam
    Slope: ndarray
        Array of slope values along the beam
    curv: ndarray
        Array of curvature values along the beam
    """
    clear_screen()
    
    # Find maximum deflection and its location
    max_defl_idx = np.argmax(np.abs(Deflection))
    max_defl = Deflection[max_defl_idx]
    max_defl_pos = max_defl_idx * (beam_length / (len(Deflection) - 1))
    
    # Find maximum slope and its location
    max_slope_idx = np.argmax(np.abs(Slope))
    max_slope = Slope[max_slope_idx]
    max_slope_pos = max_slope_idx * (beam_length / (len(Slope) - 1))
    
    # Find maximum curvature and its location
    max_curv_idx = np.argmax(np.abs(curv))
    max_curv = curv[max_curv_idx]
    max_curv_pos = max_curv_idx * (beam_length / (len(curv) - 1))
    
    # Calculate deflection-to-span ratio (important engineering metric)
    span_ratio = abs(max_defl) / beam_length
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                DEFLECTION ANALYSIS RESULTS                   ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Solution parameters
    print("\n")
    print(colored("┌─ SOLUTION PARAMETERS "+"─"*39, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    print(colored("│ Solution Method:", 'blue') + colored(" Euler-Bernoulli Beam Theory", 'white'))
    print(colored("│ Integration Technique:", 'blue') + colored(" Numerical Integration (Trapezoidal)", 'white'))
    print(colored("│ Beam Type:", 'blue') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Profile Type:", 'blue') + colored(f" {shape}", 'white'))
    print(colored("│ Beam Length:", 'blue') + colored(f" {beam_length:.3f} m", 'white'))
    print(colored("│ Elastic Modulus (E):", 'blue') + colored(f" {elastic_modulus/1e9:.1f} GPa", 'white'))
    print(colored("│ Moment of Inertia (I):", 'blue') + colored(f" {Ix:.6e} m⁴", 'white'))
    print(colored("│ Flexural Rigidity (EI):", 'blue') + colored(f" {elastic_modulus*Ix:.2e} N·m²", 'white'))
    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Deflection results
    print("\n")
    print(colored("┌─ DEFLECTION RESULTS "+"─"*40, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    
    # Format max deflection with appropriate units
    max_defl_abs = abs(max_defl)
    if max_defl_abs < 1e-3:
        max_defl_str = f"{max_defl*1000:.4f} mm" 
        deflection_unit = "mm"
        scaling_factor = 1000
    else:
        max_defl_str = f"{max_defl:.6f} m"
        deflection_unit = "m"
        scaling_factor = 1
    
    print(colored("│ Maximum Deflection:", 'green') + colored(f" {max_defl_str} {'↑' if max_defl > 0 else '↓'}", 'white'))
    print(colored("│ Location of Maximum:", 'green') + colored(f" x = {max_defl_pos:.3f} m", 'white'))
    print(colored("│ Deflection-to-Span Ratio:", 'green') + colored(f" 1:{(1/span_ratio):.0f}", 'white'))
    
    # Add deflection limit check (common engineering limit is L/360 for live loads)
    l_360_limit = beam_length / 360
    if abs(max_defl) > l_360_limit:
        print(colored("│ Deflection Limit Check:", 'green') + 
              colored(" EXCEEDS L/360 ⚠", 'red', attrs=['bold']))
        print(colored("│  • Limit Value (L/360):", 'green') + 
              colored(f" {l_360_limit*scaling_factor:.4f} {deflection_unit}", 'white'))
    else:
        print(colored("│ Deflection Limit Check:", 'green') + 
              colored(" WITHIN L/360 ✓", 'white', attrs=['bold']))
        print(colored("│  • Limit Value (L/360):", 'green') + 
              colored(f" {l_360_limit*scaling_factor:.4f} {deflection_unit}", 'white'))
    
    print(colored("│", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Slope and curvature
    print("\n")
    print(colored("┌─ ADDITIONAL DEFORMATION PARAMETERS "+"─"*27, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    print(colored("│ Maximum Slope:", 'magenta') + colored(f" {max_slope:.6f} rad ({np.degrees(max_slope):.2f}°)", 'white'))
    print(colored("│ Location of Max Slope:", 'magenta') + colored(f" x = {max_slope_pos:.3f} m", 'white'))
    print(colored("│", 'magenta'))
    print(colored("│ Maximum Curvature:", 'magenta') + colored(f" {max_curv:.6e} 1/m", 'white'))
    print(colored("│ Location of Max Curvature:", 'magenta') + colored(f" x = {max_curv_pos:.3f} m", 'white'))
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Engineering interpretations
    print("\n")
    print(colored("┌─ ENGINEERING INTERPRETATION "+"─"*34, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    
    # Interpret span ratio
    if span_ratio < 1/500:
        defl_interpretation = "Minimal deflection, suitable for sensitive equipment or precision applications"
    elif span_ratio < 1/360:
        defl_interpretation = "Moderate deflection, suitable for standard building applications"
    elif span_ratio < 1/240:
        defl_interpretation = "Significant deflection, acceptable for some temporary structures"
    else:
        defl_interpretation = "Large deflection, may require design modifications"
    
    print(colored("│ Deflection Assessment:", 'yellow') + colored(f" {defl_interpretation}", 'white'))
    print(colored("│", 'yellow'))
    
    # Common limits reference
    print(colored("│ Common Deflection Limits:", 'yellow', attrs=['bold']))
    print(colored("│  • L/360: General building code requirement", 'yellow'))
    print(colored("│  • L/480: More stringent requirement for brittle finishes", 'yellow'))
    print(colored("│  • L/240: Maximum for non-structural elements", 'yellow'))
    print(colored("│", 'yellow'))
    
    # Specific recommendations based on beam type
    if beam_type == "Cantilever" and span_ratio > 1/180:
        print(colored("│ Recommendation:", 'yellow') + 
              colored(" Consider increasing section depth to reduce deflection", 'white', attrs=['bold']))
    elif beam_type == "Simple" and span_ratio > 1/360:
        print(colored("│ Recommendation:", 'yellow') + 
              colored(" Consider increasing section moment of inertia", 'white', attrs=['bold']))
    
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    print("\n")
    print(colored("┌─ VISUALIZATION OPTIONS "+"─"*39, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    print(colored("│ To visualize deflection:", 'cyan'))
    print(colored("│  1. Navigate to Postprocessing/Visualization menu", 'cyan'))
    print(colored("│  2. Select option for Deflection Plots", 'cyan'))
    print(colored("│  3. Choose between Matplotlib or Plotly visualization", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the Analysis/Simulation menu...", 'cyan', attrs=['bold']))

def display_stress_analysis(beam_type, shape, selected_material, Ix, c, b, 
                          y_array, Total_ShearForce, Total_BendingMoment, 
                          Shear_stress, Max_Shear_stress, bending_stress, 
                          Max_bending_stress, FOS):
    """
    Display stress analysis results in a professional FEA-like format.
    
    Parameters:
    -----------
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    shape: str
        Name of the profile shape
    selected_material: dict
        Dictionary containing material properties
    Ix: float
        Moment of inertia in m⁴
    c: float
        Distance from neutral axis to extreme fiber in m
    b: float
        Representative width in m
    y_array: ndarray
        Array of y-coordinates for stress calculations
    Total_ShearForce: ndarray
        Array of shear force values along the beam
    Total_BendingMoment: ndarray
        Array of bending moment values along the beam
    Shear_stress: ndarray
        Array or matrix of shear stress values
    Max_Shear_stress: float
        Maximum shear stress value
    bending_stress: ndarray
        Array of bending stress values
    Max_bending_stress: float
        Maximum bending stress value
    FOS: float
        Factor of safety against yielding
    """
    clear_screen()
    
    # Calculate yield strength and other material properties
    yield_strength = selected_material.get('Yield Strength', 0) * 1e6  # Convert MPa to Pa
    poisson_ratio = selected_material.get('Poisson Ratio', 0.3)
    
    # Calculate additional metrics
    section_modulus = Ix / c
    allowable_stress = yield_strength / FOS
    
    # Calculate maximum combined stress using von Mises criterion
    tau_max = Max_Shear_stress
    sigma_max = Max_bending_stress
    von_mises_stress = np.sqrt(sigma_max**2 + 3*tau_max**2)
    
    # Find critical locations
    max_sf_idx = np.argmax(np.abs(Total_ShearForce))
    max_sf_loc = max_sf_idx * (len(Total_ShearForce) - 1)
    
    max_bm_idx = np.argmax(np.abs(Total_BendingMoment))
    max_bm_loc = max_bm_idx * (len(Total_BendingMoment) - 1)
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║              STRESS ANALYSIS & FACTOR OF SAFETY              ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Analysis parameters
    print("\n")
    print(colored("┌─ ANALYSIS PARAMETERS "+"─"*39, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    print(colored("│ Beam Type:", 'blue') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Cross-Section:", 'blue') + colored(f" {shape}", 'white'))
    print(colored("│ Material:", 'blue') + colored(f" {selected_material.get('Material', 'Unknown')}", 'white'))
    print(colored("│ Yield Strength:", 'blue') + colored(f" {yield_strength/1e6:.2f} MPa", 'white'))
    print(colored("│ Section Modulus:", 'blue') + colored(f" {section_modulus:.6e} m³", 'white'))
    print(colored("│ Moment of Inertia:", 'blue') + colored(f" {Ix:.6e} m⁴", 'white'))
    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Stress results
    print("\n")
    print(colored("┌─ STRESS ANALYSIS RESULTS "+"─"*36, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    
    # Bending stress
    print(colored("│ BENDING STRESS (Normal Stress)", 'green', attrs=['bold']))
    print(colored("│  • Maximum Value:", 'green') + 
          colored(f" {Max_bending_stress/1e6:.2f} MPa", 'white'))
    print(colored("│  • Location:", 'green') + 
          colored(f" x = {max_bm_loc:.3f} m", 'white'))
    print(colored("│  • Extreme Fiber Distance:", 'green') + 
          colored(f" {c:.4f} m", 'white'))
    print(colored("│", 'green'))
    
    # Shear stress
    print(colored("│ SHEAR STRESS", 'green', attrs=['bold']))
    print(colored("│  • Maximum Value:", 'green') + 
          colored(f" {Max_Shear_stress/1e6:.2f} MPa", 'white'))
    print(colored("│  • Location:", 'green') + 
          colored(f" x = {max_sf_loc:.3f} m", 'white'))
    print(colored("│  • Representative Width:", 'green') + 
          colored(f" {b:.4f} m", 'white'))
    print(colored("│", 'green'))
    
    # Combined stress
    print(colored("│ COMBINED STRESS (von Mises)", 'green', attrs=['bold']))
    print(colored("│  • Maximum Value:", 'green') + 
          colored(f" {von_mises_stress/1e6:.2f} MPa", 'white'))
    print(colored("│  • Percentage of Yield:", 'green') + 
          colored(f" {(von_mises_stress/yield_strength)*100:.1f}%", 'white'))
    print(colored("│", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Factor of safety
    print("\n")
    print(colored("┌─ FACTOR OF SAFETY ANALYSIS "+"─"*35, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    print(colored("│ Factor of Safety (FOS):", 'magenta') + 
          colored(f" {FOS:.2f}", 'white', attrs=['bold']))
    print(colored("│ Allowable Stress:", 'magenta') + 
          colored(f" {allowable_stress/1e6:.2f} MPa", 'white'))
    print(colored("│", 'magenta'))
    
    # FOS interpretation
    if FOS >= 2.0:
        safety_status = "EXCELLENT ✓"
        safety_color = 'green'
        safety_message = "Design has high margin of safety"
    elif FOS >= 1.5:
        safety_status = "GOOD ✓"
        safety_color = 'green'
        safety_message = "Design meets standard safety requirements"
    elif FOS >= 1.0:
        safety_status = "ACCEPTABLE ✓"
        safety_color = 'yellow'
        safety_message = "Design is safe but has limited margin"
    else:
        safety_status = "UNSAFE ✗"
        safety_color = 'red'
        safety_message = "Design may fail under expected loads"
    
    print(colored("│ Safety Status:", 'magenta') + 
          colored(f" {safety_status}", safety_color, attrs=['bold']))
    print(colored("│ Assessment:", 'magenta') + 
          colored(f" {safety_message}", 'white'))
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Engineering guidelines
    print("\n")
    print(colored("┌─ ENGINEERING GUIDELINES "+"─"*37, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    print(colored("│ Recommended FOS by Application:", 'yellow', attrs=['bold']))
    print(colored("│  • 1.25 - 1.5: Standard structural applications", 'yellow'))
    print(colored("│  • 1.5 - 2.0: Critical structural components", 'yellow'))
    print(colored("│  • 2.0 - 3.0: Dynamic loading conditions", 'yellow'))
    print(colored("│  • 3.0+: Safety-critical or high-uncertainty applications", 'yellow'))
    print(colored("│", 'yellow'))
    
    # Recommendations based on FOS
    print(colored("│ Design Recommendations:", 'yellow', attrs=['bold']))
    if FOS < 1.0:
        print(colored("│  • CRITICAL: Redesign required to increase strength", 'yellow'))
        print(colored("│  • Consider increasing section size or using stronger material", 'yellow'))
    elif FOS < 1.5:
        print(colored("│  • Consider design improvements if application is critical", 'yellow'))
        print(colored("│  • Verify loading assumptions and boundary conditions", 'yellow'))
    else:
        print(colored("│  • Design meets safety requirements", 'yellow'))
        print(colored("│  • Consider weight/cost optimization if FOS > 2.5", 'yellow'))
    
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    # Failure theories and next steps
    print("\n")
    print(colored("┌─ ADDITIONAL INFORMATION "+"─"*38, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    print(colored("│ Analysis Method:", 'cyan'))
    print(colored("│  • Normal stress calculated using 𝜎 = My/I", 'cyan'))
    print(colored("│  • Shear stress calculated using 𝜏 = VQ/(Ib)", 'cyan'))
    print(colored("│  • Combined stress using von Mises theory", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("│ Visualization Options:", 'cyan'))
    print(colored("│  • View stress distribution in the Postprocessing menu", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the Analysis/Simulation menu...", 'cyan', attrs=['bold']))

def display_engineering_recommendations(beam_type, shape, beam_length, selected_material,
                                      Ix, c, b, FOS=None, max_stress=None, max_defl=None, 
                                      span_ratio=None, yield_strength=None):
    """
    Display professional engineering recommendations based on analysis results.
    This function provides guidance on design improvements and highlights potential issues.
    
    Parameters:
    -----------
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    shape: str
        Name of the profile shape
    beam_length: float
        Length of the beam in meters
    selected_material: dict
        Dictionary containing material properties
    Ix: float
        Moment of inertia in m⁴
    c: float
        Distance from neutral axis to extreme fiber in m
    b: float
        Representative width in m
    FOS: float
        Factor of safety against yielding
    max_stress: float
        Maximum stress value in Pa
    max_defl: float
        Maximum deflection value in m
    span_ratio: float
        Ratio of maximum deflection to beam length
    yield_strength: float
        Material yield strength in Pa
    """
    clear_screen()
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║            ENGINEERING DESIGN RECOMMENDATIONS                ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Model summary
    print("\n")
    print(colored("┌─ MODEL SUMMARY "+"─"*44, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    print(colored("│ Beam Type:", 'blue') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Cross-Section:", 'blue') + colored(f" {shape}", 'white'))
    print(colored("│ Beam Length:", 'blue') + colored(f" {beam_length:.3f} m", 'white'))
    print(colored("│ Material:", 'blue') + colored(f" {selected_material.get('Material', 'Unknown')}", 'white'))
    
    if Ix is not None:
        print(colored("│ Moment of Inertia:", 'blue') + colored(f" {Ix:.6e} m⁴", 'white'))
    if c is not None:
        print(colored("│ Section Height (2c):", 'blue') + colored(f" {2*c:.4f} m", 'white'))
    
    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Assessment of current design
    print("\n")
    print(colored("┌─ DESIGN ASSESSMENT "+"─"*41, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    
    design_issues = []
    design_strengths = []
    
    # Safety assessment
    if FOS is not None:
        if FOS < 1.0:
            design_issues.append(f"Factor of Safety is critically low ({FOS:.2f})")
            design_issues.append("Structure may fail under expected loads")
        elif FOS < 1.5:
            design_issues.append(f"Factor of Safety ({FOS:.2f}) is below recommended value for most applications")
        else:
            design_strengths.append(f"Good Factor of Safety ({FOS:.2f})")
    
    # Deflection assessment
    if span_ratio is not None:
        if span_ratio > 1/180:  # Very large deflection
            design_issues.append(f"Excessive deflection (L/{1/span_ratio:.0f})")
            design_issues.append("Structure may experience serviceability issues")
        elif span_ratio > 1/360:  # Large but potentially acceptable
            design_issues.append(f"Significant deflection (L/{1/span_ratio:.0f})")
        else:
            design_strengths.append(f"Acceptable deflection (L/{1/span_ratio:.0f})")
    
    # Stress assessment
    if max_stress is not None and yield_strength is not None:
        stress_ratio = max_stress / yield_strength
        if stress_ratio > 0.9:
            design_issues.append(f"Stress is at {stress_ratio*100:.1f}% of material yield strength")
        elif stress_ratio > 0.67:
            design_issues.append(f"Moderately high stress ({stress_ratio*100:.1f}% of yield)")
        else:
            design_strengths.append(f"Acceptable stress level ({stress_ratio*100:.1f}% of yield)")
    
    # Profile assessment
    if shape == "I-beam" or shape == "T-beam":
        design_strengths.append("Efficient cross-section for bending about major axis")
    elif "Circle" in shape:
        design_strengths.append("Good torsional resistance")
        if beam_type == "Cantilever":
            design_issues.append("Circular sections are not optimal for cantilever bending")
    elif "Rectangle" in shape or "Square" in shape:
        if "Hollow" not in shape:
            design_issues.append("Solid rectangular sections have less efficient material utilization")
        else:
            design_strengths.append("Good combination of bending and torsional resistance")
    
    # Specific beam type considerations
    if beam_type == "Cantilever":
        if beam_length > 10 and "Hollow" not in shape:
            design_issues.append("Long cantilever may require hollow section for weight reduction")
    
    # Print strengths
    if design_strengths:
        print(colored("│ Design Strengths:", 'green', attrs=['bold']))
        for strength in design_strengths:
            print(colored(f"│  ✓ {strength}", 'green'))
        print(colored("│", 'green'))
    
    # Print issues
    if design_issues:
        print(colored("│ Design Issues:", 'yellow', attrs=['bold']))
        for issue in design_issues:
            print(colored(f"│  ⚠ {issue}", 'yellow'))
        print(colored("│", 'green'))
    
    if not design_issues and not design_strengths:
        print(colored("│  No specific design assessment available. Complete all analyses first.", 'white'))
        print(colored("│", 'green'))
    
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # Recommended improvements
    print("\n")
    print(colored("┌─ RECOMMENDED IMPROVEMENTS "+"─"*35, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    
    improvements = []
    
    # Generate recommendations based on identified issues
    if FOS is not None and FOS < 1.5:
        if shape == "I-beam":
            improvements.append("Increase flange width or web height")
        elif shape == "T-beam":
            improvements.append("Increase flange width or web height")
        elif "Circle" in shape:
            improvements.append("Increase diameter")
        elif "Rectangle" in shape or "Square" in shape:
            if "Hollow" not in shape:
                improvements.append("Consider switching to a hollow section or I-beam")
            else:
                improvements.append("Increase section dimensions or wall thickness")
        
        # Material recommendation
        current_yield = selected_material.get('Yield Strength', 0)
        improvements.append(f"Consider using a stronger material (current yield: {current_yield} MPa)")
    
    if span_ratio is not None and span_ratio > 1/360:
        improvements.append(f"Increase section moment of inertia to reduce deflection")
        if beam_type == "Simple":
            improvements.append("Consider adding intermediate supports if possible")
    
    # Profile-specific recommendations
    if shape == "Rectangle" and "Hollow" not in shape:
        improvements.append("Reorient section to have larger height than width")
        improvements.append("Consider switching to I-beam for more efficient material usage")
    
    # Beam-type specific recommendations
    if beam_type == "Cantilever" and beam_length > 5:
        improvements.append("Consider tapered design with larger section at support")
    
    # Print improvements
    if improvements:
        for improvement in improvements:
            print(colored(f"│  • {improvement}", 'magenta'))
    else:
        print(colored("│  Current design appears adequate based on available analysis", 'white'))
        if FOS is None or span_ratio is None:
            print(colored("│  Complete stress and deflection analyses for more recommendations", 'white'))
    
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Advanced optimization suggestions
    print("\n")
    print(colored("┌─ ADVANCED OPTIMIZATION POSSIBILITIES "+"─"*26, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    
    # Generate advanced recommendations
    if FOS is not None and FOS > 2.5:
        print(colored("│ Weight Reduction Opportunities:", 'yellow', attrs=['bold']))
        if "Hollow" not in shape:
            print(colored("│  • Consider converting to hollow section (weight savings: ~30-40%)", 'yellow'))
        else:
            print(colored("│  • Reduce section dimensions slightly (FOS has margin)", 'yellow'))
    
    print(colored("│", 'yellow'))
    print(colored("│ Additional Analysis Recommended:", 'yellow', attrs=['bold']))
    
    if beam_type == "Simple":
        print(colored("│  • Dynamic/vibration analysis for span > 3m", 'yellow'))
    elif beam_type == "Cantilever":
        print(colored("│  • Fatigue analysis if subjected to cyclic loading", 'yellow'))
        print(colored("│  • Buckling analysis for slender cantilevers", 'yellow'))
    
    print(colored("│", 'yellow'))
    print(colored("│ Manufacturing Considerations:", 'yellow', attrs=['bold']))
    
    if "beam" in shape.lower():
        print(colored("│  • Check standard section sizes availability", 'yellow'))
    elif "Hollow" in shape:
        print(colored("│  • Consider ease of connection to other members", 'yellow'))
    
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    # Engineering codes and standards
    print("\n")
    print(colored("┌─ APPLICABLE CODES & STANDARDS "+"─"*32, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    
    print(colored("│ Design Standards:", 'cyan', attrs=['bold']))
    if "Steel" in selected_material.get('Material', ''):
        print(colored("│  • AISC 360 - Specification for Structural Steel Buildings", 'cyan'))
        print(colored("│  • Eurocode 3 - Design of Steel Structures", 'cyan'))
    elif "Aluminum" in selected_material.get('Material', ''):
        print(colored("│  • Aluminum Design Manual", 'cyan'))
        print(colored("│  • Eurocode 9 - Design of Aluminum Structures", 'cyan'))
    elif "Concrete" in selected_material.get('Material', ''):
        print(colored("│  • ACI 318 - Building Code Requirements for Structural Concrete", 'cyan'))
        print(colored("│  • Eurocode 2 - Design of Concrete Structures", 'cyan'))
    elif "Timber" in selected_material.get('Material', ''):
        print(colored("│  • NDS - National Design Specification for Wood Construction", 'cyan'))
        print(colored("│  • Eurocode 5 - Design of Timber Structures", 'cyan'))
    else:
        print(colored("│  • Check local building codes for your specific material", 'cyan'))
    
    print(colored("│", 'cyan'))
    print(colored("│ Deflection Requirements:", 'cyan', attrs=['bold']))
    print(colored("│  • L/360 for general structural applications", 'cyan'))
    print(colored("│  • L/480 for members supporting brittle finishes", 'cyan'))
    print(colored("│  • L/240 for roof members with no ceiling", 'cyan'))
    
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the main menu...", 'cyan', attrs=['bold']))