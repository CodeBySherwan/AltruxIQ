import sys
import os
from termcolor import colored
import time
import numpy as np
# =============================
# Unit Conversion Multipliers
# =============================
CONVERSION_TO_SI = {
    "Metric": {
        "length": 1.0,
        "force": 1.0,
        "moment": 1.0,
        "distributed": 1.0
    },
    "Imperial": {
        "length": 0.3048,           # ft to m
        "force": 4.4482216,         # lbf to N
        "moment": 1.3558179,        # lbf·ft to N·m
        "distributed": 14.5939      # lbf/ft to N/m
    }
}
# --- PATH INJECTION (The Fix) ---
# 1. Get the directory of cli.py (ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent directory (src folder)
src_dir = os.path.dirname(current_dir)
# 3. Add the src folder to Python's search path if it's not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ui.Menus import (print_error, print_success, print_title, print_option, clear_screen,
                     ui_banner, ui_open, ui_close, ui_blank, ui_field, ui_text, ui_bullet, ui_head)

#  Beam Classification Setup

def Beam_Classification():
    """Prompt the user to select a structural system (beam idealisation)
    with schematic previews and determinacy notes. Returns the internal
    beam-type keyword expected by the solver/controller."""
    clear_screen()
    ui_banner("STAGE 1  \u2014  STRUCTURAL SYSTEM",
              "Select the beam idealisation & support topology", color='cyan')

    systems = [
        ("1", "Simple Supported Beam", "Statically determinate",
         "\u25b3 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 \u25cb   (pin \u2014 roller)"),
        ("2", "Overhanging Beam", "Statically determinate",
         "\u2500\u2500 \u25b3 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 \u25cb \u2500\u2500   (cantilevered ends)"),
        ("3", "Cantilever Beam", "Statically determinate",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501   (fixed \u2014 free)"),
        ("4", "Fixed\u2013Fixed Beam", "Indeterminate (3\u00b0)",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2503   (fixed \u2014 fixed)"),
        ("5", "Propped Cantilever", "Indeterminate (1\u00b0)",
         "\u2503\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501 \u25cb   (fixed \u2014 roller)"),
        ("6", "Continuous Beam", "Indeterminate (multi-span)",
         "\u25b3 \u2500\u2500\u2500\u2500 \u25cb \u2500\u2500\u2500\u2500 \u25cb \u2500\u2500\u2500\u2500 \u25cb"),
        ("7", "Custom Beam", "User-defined supports",
         "? \u2500\u2500\u2500\u2500 ? \u2500\u2500\u2500\u2500 ? \u2500\u2500\u2500\u2500 ?"),
    ]

    print("\n")
    ui_open("SELECT BEAM TYPE", 'yellow')
    ui_blank('yellow')
    for num, name, determ, schematic in systems:
        print(colored(f"\u2502 {num} \u2502 ", 'yellow')
              + colored(name.ljust(24), 'yellow', attrs=['bold'])
              + colored(determ, 'cyan'))
        print(colored("\u2502     \u2192 ", 'yellow') + colored(schematic, 'white'))
        ui_blank('yellow')
    ui_close('yellow')

    print("")
    classification = input(colored("  Enter your choice [1-7] \u2794 ", 'cyan', attrs=['bold']))

    mapping = {
        '1': "Simple", '2': "Overhanging Beam", '3': "Cantilever",
        '4': "Fixed-Fixed", '5': "Propped", '6': "Continuous", '7': "Custom",
    }
    if classification in mapping:
        return mapping[classification]
    print_error("Invalid selection! Please choose a number between 1 and 7.")
    time.sleep(1.5)
    return Beam_Classification()

def Beam_Length(unit_system="Metric", units=None):
    """Prompt the user to enter the beam length."""
    if units is None: units = {'length': 'm'}
    multiplier = CONVERSION_TO_SI[unit_system]["length"]
    
    beam_length_raw = float(input(colored(f"Enter Beam Length ({units['length']}): ➔ ", 'cyan')))
    if beam_length_raw <= 0:
        print_error("Beam length must be positive.")
        time.sleep(1)
        return Beam_Length(unit_system, units)
    print("")
    return beam_length_raw * multiplier  # Return converted SI value

#==============================
def Beam_Supports(unit_system="Metric", units=None):
    """Prompt the user to define the beam supports."""
    if units is None: units = {'length': 'm'}
    multiplier = CONVERSION_TO_SI[unit_system]["length"]
    
    try:
        A_raw = float(input(colored(f"Enter Position of Pin Support A ({units['length']}): ➔ ", 'cyan')))
        A = A_raw * multiplier
        A_restraint = (1, 1, 0)
        A_type = "Pin Support"
    
        B_raw = float(input(colored(f"Enter Position of Roller Support B ({units['length']}): ➔ ", 'cyan')))
        B = B_raw * multiplier
        B_restraint = (0, 1, 0)
        B_type = "Roller Support"
    
        if A < 0 or B < 0:
            print_error("Support positions must be positive.")
            time.sleep(1)
            print("")
            return Beam_Supports(unit_system, units)
        if A >= B:
             print_error("Support A must be to the left of Support B.")
             print("")
             time.sleep(1)
             return Beam_Supports(unit_system, units)  
        print("")
        return A, B, A_restraint, B_restraint, A_type, B_type
    except ValueError as ve:
        print_error(f"Input error: {ve}")
        return None, None, None, None, None, None


def define_continuous_supports(beam_length, unit_system="Metric", units=None):
    """
    Prompt the user to enter multiple support coordinates for a continuous beam.
    Returns a list of dicts: [{"pos": float, "dof": (0,1,0), "ky": None, "kx": None}, ...]
    """
    if units is None: units = {'length': 'm'}
    multiplier = CONVERSION_TO_SI[unit_system]["length"]
    inv_multiplier = 1.0 / multiplier
    
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║                CONTINUOUS BEAM SUPPORTS                      ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("\n")
        
        print(colored(f"Beam Length: {beam_length * inv_multiplier:.2f} {units['length']}", 'white', attrs=['bold']))
        print(colored("Continuous beams require defining the exact position of all supports.", 'white'))
        print("\n")
        
        try:
            num_supports = int(input(colored("Enter total number of supports (minimum 2): ➔ ", 'cyan')))
            if num_supports < 2:
                print_error("A continuous beam must have at least 2 supports.")
                time.sleep(1.5)
                continue
                
            supports = []
            for i in range(num_supports):
                while True:
                    pos_raw = float(input(colored(f"  Enter position for Support {i+1} ({units['length']}): ➔ ", 'cyan')))
                    pos = pos_raw * multiplier
                    
                    if pos < 0 or pos > beam_length:
                        print_error(f"Support position must be between 0 and beam length.")
                        continue
                        
                    if any(abs(s["pos"] - pos) < 1e-5 for s in supports):
                        print_error("A support already exists at this location. Enter a unique position.")
                        continue
                        
                    # Pin the first support to keep beam horizontally stable; roll the others
                    dof = (1, 1, 0) if i == 0 else (0, 1, 0)
                    
                    supports.append({
                        "pos": pos,
                        "dof": dof,
                        "ky": None,
                        "kx": None
                    })
                    break
                    
            # Sort chronologically along span length
            supports.sort(key=lambda x: x["pos"])
            
            print_success(f"\nSuccessfully configured {len(supports)} supports!")
            time.sleep(1.5)
            return supports
            
        except ValueError:
            print_error("Invalid input. Please enter valid numeric digits.")
            time.sleep(1.5)
#=====================================================================================
def define_custom_supports(beam_length, unit_system="Metric", units=None):
    """Interactive wizard for defining arbitrary support configurations."""
    if units is None: units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
    multiplier = CONVERSION_TO_SI[unit_system]["length"]
    inv_multiplier = 1.0 / multiplier
    
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║                CUSTOM BEAM SUPPORTS                          ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("\n")
        
        try:
            num_supports = int(input(colored("Enter total number of supports: ➔ ", 'cyan')))
            if num_supports < 2:
                print(colored("Warning: A beam with fewer than 2 supports may be unstable unless fully fixed.", 'yellow'))
                
            supports = []
            has_x_restraint = False
            has_y_restraint = False
            
            for i in range(num_supports):
                print(colored(f"\n--- Defining Support {i+1} ---", 'yellow', attrs=['bold']))
                
                # 1. Get Position
                while True:
                    pos_raw = float(input(colored(f"Enter position ({units['length']}): ➔ ", 'cyan')))
                    pos = pos_raw * multiplier
                    
                    if pos < 0 or pos > beam_length:
                        print_error("Support position must be between 0 and beam length.")
                        continue
                    if any(abs(s["pos"] - pos) < 1e-5 for s in supports):
                        print_error("A support already exists at this location.")
                        continue
                    break
                    
                # 2. Get DOF
                print(colored("Support Types:", 'green'))
                print(colored("  [1] Pin          — Restrains X and Y (Free rotation)", 'white'))
                print(colored("  [2] Roller       — Restrains Y only", 'white'))
                print(colored("  [3] Fixed        — Restrains all (X, Y, Moment)", 'white'))
                print(colored("  [4] Vertical Spring — Restrains Y elastically", 'white'))
                print(colored("  [5] Horizontal Spring — Restrains X elastically", 'white'))
                
                while True:
                    s_type = input(colored("Choose support type [1-5]: ➔ ", 'cyan'))
                    dof = (0, 0, 0)
                    ky, kx = None, None
                    
                    if s_type == '1':
                        dof = (1, 1, 0)
                        has_x_restraint, has_y_restraint = True, True
                    elif s_type == '2':
                        dof = (0, 1, 0)
                        has_y_restraint = True
                    elif s_type == '3':
                        dof = (1, 1, 1)
                        has_x_restraint, has_y_restraint = True, True
                    elif s_type == '4':
                        dof = (0, 1, 0)
                        ky_raw = float(input(colored(f"Enter vertical spring stiffness ({units['force']}/{units['length']}): ➔ ", 'cyan')))
                        ky = ky_raw * (CONVERSION_TO_SI[unit_system]["force"] / multiplier)
                        has_y_restraint = True
                    elif s_type == '5':
                        dof = (1, 0, 0)
                        kx_raw = float(input(colored(f"Enter horizontal spring stiffness ({units['force']}/{units['length']}): ➔ ", 'cyan')))
                        kx = kx_raw * (CONVERSION_TO_SI[unit_system]["force"] / multiplier)
                        has_x_restraint = True
                    else:
                        print_error("Invalid choice.")
                        continue
                    break
                    
                supports.append({"pos": pos, "dof": dof, "ky": ky, "kx": kx})
                
            # Validations
            if not has_y_restraint:
                print_error("Beam has no vertical restraint! It will fail to solve. Please re-enter.")
                time.sleep(2.5)
                continue
            if not has_x_restraint:
                print(colored("Warning: Beam has no horizontal restraint. It may be horizontally unstable.", 'red'))
                time.sleep(2.5)
                
            supports.sort(key=lambda x: x["pos"])
            print_success(f"\nSuccessfully configured {len(supports)} custom supports!")
            time.sleep(1.5)
            return supports
            
        except ValueError:
            print_error("Invalid input. Please enter valid numeric digits.")
            time.sleep(1.5)
#==================================================================================
def manage_loads(unit_system="Metric", units=None):
    if units is None:
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
    
    dist_unit = f"{units['force']}/{units['length']}"
    
    # Grab multipliers for conversion to SI before saving
    l_mult = CONVERSION_TO_SI[unit_system]["length"]
    f_mult = CONVERSION_TO_SI[unit_system]["force"]
    m_mult = CONVERSION_TO_SI[unit_system]["moment"]
    d_mult = CONVERSION_TO_SI[unit_system]["distributed"]

    loads = {
        "pointloads": [], "distributedloads": [], "momentloads": [], "triangleloads": []
    }   
    
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║                  LOADS DEFINITION                            ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("\n")
        
        # Display load definitions menu
        print(colored("┌─ LOAD TYPES "+"─"*48, 'yellow', attrs=['bold']))
        
        menu_items = [
            ("➕ Add Point Load", "Concentrated force at a single point"),
            ("📏 Add Distributed Load", "Uniform load over a length"),
            ("🔄 Add Moment Load", "Applied torque at a specific point"),
            ("📐 Add Triangular Load", "Linearly varying load over a length"),
            ("📋 Show Current Loads", "View all defined loads"),
            ("🗑️  Remove All Loads", "Clear all load definitions"),
            ("⬅️  Return to Main Menu", "Go back to the main menu")
        ]
        
        for idx, (title, description) in enumerate(menu_items, 1):
            print(colored(f"│ {idx:2d} │ {title}", 'yellow') + 
                  colored(f" - {description}", 'white'))
        
        print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
        
        # Display sign convention info
        print("\n")
        print(colored("┌─ SIGN CONVENTION "+"─"*44, 'magenta', attrs=['bold']))
        print(colored("│ Coordinate System:", 'magenta', attrs=['bold']))
        print(colored("│  • X-axis: Horizontal along beam (positive right)", 'magenta'))
        print(colored("│  • Y-axis: Vertical (positive up)", 'magenta'))
        print(colored("│", 'magenta'))
        print(colored("│ Forces:", 'magenta', attrs=['bold']))
        print(colored("│  • Positive Y-force: Upward ↑", 'magenta'))
        print(colored("│  • Positive X-force: Rightward →", 'magenta'))
        print(colored("│", 'magenta'))
        print(colored("│ Moments:", 'magenta', attrs=['bold']))
        print(colored("│  • Positive moment: Counter-clockwise ↺", 'magenta'))
        print(colored("└───" + "─"*57, 'magenta', attrs=['bold']))
        
        print("\n")
        choice = input(colored("Enter your choice [1-7] ➔ ", 'cyan', attrs=['bold']))
    
        if choice == '1':  # Add Point Load
            try:
                clear_screen()
                print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                print(colored("║                  POINT LOAD DEFINITION                       ║", 'cyan', attrs=['bold']))
                print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                print("\n")
                
                # Visual representation of point load
                print(colored("┌─ POINT LOAD DIAGRAM "+"─"*40, 'yellow', attrs=['bold']))
                print(colored("│", 'yellow'))
                print(colored("│                  ↓ P (Force)", 'white'))
                print(colored("│                  │", 'white'))
                print(colored("│                  │", 'white'))
                print(colored("│  ─────────────────────────────────────────", 'white'))
                print(colored("│                  ↑", 'white'))
                print(colored("│                  x (Position)", 'white'))
                print(colored("│", 'yellow'))
                print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
                
                print("\n")
                pos = float(input(colored(f"Enter position x ({units['length']}): ➔ ", 'cyan'))) * l_mult

                print("\n")
                print(colored("┌─ LOAD TYPE "+"─"*48, 'green', attrs=['bold']))
                print(colored("│ 1 - Vertical Load (Y-direction)", 'green'))
                print(colored("│ 2 - Horizontal Load (X-direction)", 'green'))
                print(colored("│ 3 - Angled Load (Force & Angle)", 'green'))
                print(colored("└───" + "─"*57, 'green', attrs=['bold']))
                print("\n")
                
                load_type = input(colored("Enter your choice [1, 2, or 3] ➔ ", 'cyan'))
                
                if load_type == '1':
                    y_force = float(input(colored(f"\nEnter Y-force ({units['force']}) [positive up ↑, negative down ↓]: ➔ ", 'cyan'))) * f_mult
                    loads["pointloads"].append([pos, 0, y_force])
                    print_success(f"Added vertical point load: {y_force/f_mult} {units['force']} at x = {pos/l_mult} {units['length']}")
                
                elif load_type == '2':
                    x_force = float(input(colored(f"\nEnter X-force ({units['force']}) [positive right →, negative left ←]: ➔ ", 'cyan'))) * f_mult
                    loads["pointloads"].append([pos, x_force, 0])
                    print_success(f"Added horizontal point load: {x_force/f_mult} {units['force']} at x = {pos/l_mult} {units['length']}")
                
                elif load_type == '3':
                    print("\n")
                    print(colored("┌─ ANGLED LOAD "+"─"*46, 'blue', attrs=['bold']))
                    print(colored("│  Angle measured from positive X-axis", 'blue'))
                    print(colored("│         ↑ 90°", 'blue'))
                    print(colored("│         │", 'blue'))
                    print(colored("│  180° ←─┼─→ 0°", 'blue'))
                    print(colored("│         │", 'blue'))
                    print(colored("│        270°", 'blue'))
                    print(colored("└───" + "─"*57, 'blue', attrs=['bold']))
                    print("\n")
                    
                    force_mag = float(input(colored(f"Enter Force magnitude ({units['force']}): ➔ ", 'cyan'))) * f_mult
                    angle = float(input(colored("Enter angle (degrees): ➔ ", 'cyan')))
                    x_force = force_mag * np.cos(np.radians(angle))
                    y_force = force_mag * np.sin(np.radians(angle))
                    loads["pointloads"].append([pos, x_force, y_force])
                    print_success(f"Added angled point load: {force_mag/f_mult} {units['force']} at {angle}° at x = {pos/l_mult} {units['length']}")
                
                else:
                    print_error("Invalid point load type selection!")
                    time.sleep(2)
                
                time.sleep(1.5)
            
            except Exception as e:
                print_error(f"Error adding point load: {e}")
                time.sleep(2)
    
        elif choice == '2':  # Add Distributed Load (UDL)
            try:
                clear_screen()
                print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                print(colored("║              DISTRIBUTED LOAD DEFINITION                     ║", 'cyan', attrs=['bold']))
                print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                print("\n")
                
                # Visual representation of UDL
                print(colored("┌─ UNIFORM DISTRIBUTED LOAD DIAGRAM "+"─"*26, 'yellow', attrs=['bold']))
                print(colored("│", 'yellow'))
                print(colored("│              ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓", 'white'))
                print(colored("│              ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼ ▼", 'white'))
                print(colored("│              ┏━━━━━━━━━━━━━━━━┓", 'white'))
                print(colored("│  ────────────┻━━━━━━━━━━━━━━━━┻──────────────", 'white'))
                print(colored("│              ↑              ↑", 'white'))
                print(colored("│          start_pos       end_pos", 'white'))
                print(colored("│", 'yellow'))
                print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
                
                print("\n")
                print(colored("┌─ ENGINEERING NOTE "+"─"*43, 'blue', attrs=['bold']))
                print(colored("│ Distributed loads are important in FEA as they", 'blue'))
                print(colored("│ more accurately represent real-world loading", 'blue'))
                print(colored("│ conditions like self-weight, snow loads, or", 'blue'))
                print(colored("│ pressure loads compared to point loads.", 'blue'))
                print(colored("└───" + "─"*57, 'blue', attrs=['bold']))
                print("\n")
                
                start = float(input(colored(f"Enter start position ({units['length']}) for UDL: ➔ ", 'cyan'))) * l_mult
                end = float(input(colored(f"Enter end position ({units['length']}) for UDL: ➔ ", 'cyan'))) * l_mult
                intensity = float(input(colored(f"Enter load intensity ({dist_unit}) [positive up ↑, negative down ↓]: ➔ ", 'cyan'))) * d_mult
                
                # Validation
                if start >= end:
                    print_error("End position must be greater than start position!")
                    time.sleep(2)
                    continue
                
                loads["distributedloads"].append([start, end, intensity])
                print_success(f"Added UDL: {intensity/d_mult} {dist_unit} from x = {start/l_mult} {units['length']} to x = {end/l_mult} {units['length']}")
                time.sleep(1.5)
            
            except Exception as e:
                print_error(f"Error adding distributed load: {e}")
                time.sleep(2)
    
        elif choice == '3':  # Add Moment Load
            try:
                clear_screen()
                print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                print(colored("║                  MOMENT LOAD DEFINITION                      ║", 'cyan', attrs=['bold']))
                print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                print("\n")
                
                # Visual representation of moment load
                print(colored("┌─ MOMENT LOAD DIAGRAM "+"─"*39, 'yellow', attrs=['bold']))
                print(colored("│", 'yellow'))
                print(colored("│                   ↺ M (Moment)", 'white'))
                print(colored("│                  ╭─╮", 'white'))
                print(colored("│                  │ │", 'white'))
                print(colored("│  ─────────────────────────────────────────", 'white'))
                print(colored("│                  ↑", 'white'))
                print(colored("│                  x (Position)", 'white'))
                print(colored("│", 'yellow'))
                print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
                
                print("\n")
                print(colored("┌─ ENGINEERING NOTE "+"─"*43, 'blue', attrs=['bold']))
                print(colored("│ In FEA, moments are crucial for modeling", 'blue'))
                print(colored("│ connections, applied torques, and rotational", 'blue'))
                print(colored("│ constraints. Remember that positive moments", 'blue'))
                print(colored("│ are counter-clockwise (↺).", 'blue'))
                print(colored("└───" + "─"*57, 'blue', attrs=['bold']))
                print("\n")
                
                pos = float(input(colored(f"Enter position ({units['length']}) for Moment Load: ➔ ", 'cyan'))) * l_mult
                moment = float(input(colored(f"Enter moment magnitude ({units['moment']}) [positive CCW ↺, negative CW ↻]: ➔ ", 'cyan'))) * m_mult
                
                loads["momentloads"].append([pos, moment])
                print_success(f"Added moment load: {moment/m_mult} {units['moment']} at x = {pos/l_mult} {units['length']}")
                time.sleep(1.5)
            
            except Exception as e:
                print_error(f"Error adding moment load: {e}")
                time.sleep(2)
    
        elif choice == '4':  # Add Triangular Load
            try:
                clear_screen()
                print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                print(colored("║              TRIANGULAR LOAD DEFINITION                      ║", 'cyan', attrs=['bold']))
                print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                print("\n")
                
                # Visual representation of triangular load
                print(colored("┌─ TRIANGULAR LOAD DIAGRAM "+"─"*36, 'yellow', attrs=['bold']))
                print(colored("│", 'yellow'))
                print(colored("│              ↓  ↓  ↓  ↓  ↓", 'white'))
                print(colored("│              │  │  │  │  │", 'white'))
                print(colored("│              ▼  ▼  ▼  ▼  ▼", 'white'))
                print(colored("│              ┏━━━━━━┓", 'white'))
                print(colored("│  ────────────┻━━━━━━┻──────────────────", 'white'))
                print(colored("│              ↑      ↑", 'white'))
                print(colored("│          start_pos end_pos", 'white'))
                print(colored("│", 'yellow'))
                print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
                
                print("\n")
                print(colored("┌─ ENGINEERING NOTE "+"─"*43, 'blue', attrs=['bold']))
                print(colored("│ Triangular loads are ideal for modeling", 'blue'))
                print(colored("│ linearly varying loads such as hydrostatic", 'blue'))
                print(colored("│ pressure, wind loads on certain structures,", 'blue'))
                print(colored("│ or soil pressure distributions.", 'blue'))
                print(colored("└───" + "─"*57, 'blue', attrs=['bold']))
                print("\n")
                
                start = float(input(colored(f"Enter start position ({units['length']}) for Triangular Load: ➔ ", 'cyan'))) * l_mult
                end = float(input(colored(f"Enter end position ({units['length']}) for Triangular Load: ➔ ", 'cyan'))) * l_mult
                
                # Validation
                if start >= end:
                    print_error("End position must be greater than start position!")
                    time.sleep(2)
                    continue
                
                intensity = float(input(colored(f"Enter peak load intensity ({dist_unit}): ➔ ", 'cyan'))) * d_mult
                intensityL = float(input(colored(f"Enter lowest load intensity ({dist_unit}): ➔ ", 'cyan'))) * d_mult
                
                loads["triangleloads"].append([start, end, intensity, intensityL])
                print_success(f"Added triangular load from x = {start/l_mult} {units['length']} to x = {end/l_mult} {units['length']}")
                print_success(f"Peak intensity: {intensity/d_mult} {dist_unit}, Lowest intensity: {intensityL/d_mult} {dist_unit}")
                time.sleep(1.5)
            
            except Exception as e:
                print_error(f"Error adding triangular load: {e}")
                time.sleep(2)
    
        elif choice == '5':  # Show Current Loads
            clear_screen()
            
            print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
            print(colored("║                    CURRENT LOADS                             ║", 'cyan', attrs=['bold']))
            print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
            print("\n")
            
            # Point Loads Table
            if loads['pointloads']:
                print(colored("┌─ POINT LOADS "+"─"*47, 'yellow', attrs=['bold']))
                print(colored(f"│ Position ({units['length']}) | X-Force ({units['force']}) | Y-Force ({units['force']})", 'yellow'))
                print(colored("├" + "─"*61, 'yellow'))
                for i, load in enumerate(loads['pointloads'], 1):
                    pos, x_force, y_force = load
                    print(colored(f"│ {i:2d}) {pos/l_mult:9.2f} | {x_force/f_mult:10.2f} | {y_force/f_mult:10.2f}", 'white'))
                print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
                print("")
            else:
                print(colored("┌─ POINT LOADS "+"─"*47, 'yellow', attrs=['bold']))
                print(colored("│ No point loads defined", 'yellow'))
                print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
                print("")
            
            # Distributed Loads Table
            if loads['distributedloads']:
                print(colored("┌─ DISTRIBUTED LOADS "+"─"*42, 'green', attrs=['bold']))
                print(colored(f"│ Start ({units['length']}) | End ({units['length']}) | Intensity ({dist_unit})", 'green'))
                print(colored("├" + "─"*61, 'green'))
                for i, load in enumerate(loads['distributedloads'], 1):
                    start, end, intensity = load
                    print(colored(f"│ {i:2d}) {start/l_mult:7.2f} | {end/l_mult:6.2f} | {intensity/d_mult:13.2f}", 'white'))
                print(colored("└" + "─"*62, 'green', attrs=['bold']))
                print("")
            else:
                print(colored("┌─ DISTRIBUTED LOADS "+"─"*42, 'green', attrs=['bold']))
                print(colored("│ No distributed loads defined", 'green'))
                print(colored("└" + "─"*62, 'green', attrs=['bold']))
                print("")
            
            # Moment Loads Table
            if loads['momentloads']:
                print(colored("┌─ MOMENT LOADS "+"─"*46, 'magenta', attrs=['bold']))
                print(colored(f"│ Position ({units['length']}) | Magnitude ({units['moment']})", 'magenta'))
                print(colored("├" + "─"*61, 'magenta'))
                for i, load in enumerate(loads['momentloads'], 1):
                    pos, moment = load
                    print(colored(f"│ {i:2d}) {pos/l_mult:9.2f} | {moment/m_mult:15.2f} {'(CCW ↺)' if moment > 0 else '(CW ↻)'}", 'white'))
                print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
                print("")
            else:
                print(colored("┌─ MOMENT LOADS "+"─"*46, 'magenta', attrs=['bold']))
                print(colored("│ No moment loads defined", 'magenta'))
                print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
                print("")
            
            # Triangular Loads Table
            if loads['triangleloads']:
                print(colored("┌─ TRIANGULAR LOADS "+"─"*43, 'blue', attrs=['bold']))
                print(colored(f"│ Start ({units['length']}) | End ({units['length']}) | Peak ({dist_unit}) | Low ({dist_unit})", 'blue'))
                print(colored("├" + "─"*61, 'blue'))
                for i, load in enumerate(loads['triangleloads'], 1):
                    start, end, peak, low = load
                    print(colored(f"│ {i:2d}) {start/l_mult:7.2f} | {end/l_mult:6.2f} | {peak/d_mult:10.2f} | {low/d_mult:9.2f}", 'white'))
                print(colored("└" + "─"*62, 'blue', attrs=['bold']))
            else:
                print(colored("┌─ TRIANGULAR LOADS "+"─"*43, 'blue', attrs=['bold']))
                print(colored("│ No triangular loads defined", 'blue'))
                print(colored("└" + "─"*62, 'blue', attrs=['bold']))
            
            print("\n")
            input(colored("Press Enter to continue...", 'cyan', attrs=['bold']))
    
        elif choice == '6':  # Remove All Loads
            clear_screen()
            print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
            print(colored("║                    WARNING                                   ║", 'red', attrs=['bold']))
            print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
            print("\n")
            
            confirm = input(colored("Are you sure you want to remove all loads? (Y/N): ➔ ", 'cyan'))
            
            if confirm.lower() == 'y':
                loads = {
                    "pointloads": [],
                    "distributedloads": [],
                    "momentloads": [],
                    "triangleloads": []
                }
                print_success("All loads have been removed!")
                time.sleep(2)
            else:
                print(colored("No loads were removed.", 'yellow'))
                time.sleep(2)
    
        elif choice == '7':  # Return to Main Menu
            break
        
        else:
            print_error("Invalid selection! Please try again.")
            time.sleep(2)
    
    return loads
#--------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
def get_solver_resolution():
    """
    Prompt the user to enter a custom solver resolution between 201 and 10001.
    """
    while True:
        try:
            pts = int(input(colored("Enter custom resolution (201 - 10001): ➔ ", 'cyan')))
            if 201 <= pts <= 10001:
                return pts
            else:
                print_error("Value must be between 201 and 10001.")
        except ValueError:
            print_error("Invalid input. Please enter an integer.")
#--------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------
def define_custom_material(unit_system="Metric", units=None):
    """Interactive wizard to create a custom material entry."""
    if units is None: units = {'density': 'kg/m³', 'stress': 'MPa', 'modulus': 'GPa'}
    clear_screen()
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║               DEFINE CUSTOM MATERIAL                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    try:
        name = input(colored("Enter Material Name: ➔ ", 'cyan')).strip()
        if not name:
            print_error("Name cannot be empty.")
            time.sleep(1.5)
            return None

        is_imperial = (unit_system == "Imperial")
        
        # Inputs in active units, converted to JSON base schema (kg/m³, MPa, GPa)
        dens_val = float(input(colored(f"Enter Density ({units['density']}): ➔ ", 'cyan')))
        json_dens = dens_val * 16.01846 if is_imperial else dens_val
        
        yield_val = float(input(colored(f"Enter Yield Strength ({units['stress']}): ➔ ", 'cyan')))
        json_yield = yield_val * 6.894757 if is_imperial else yield_val
        
        ult_val = float(input(colored(f"Enter Ultimate Strength ({units['stress']}): ➔ ", 'cyan')))
        json_ult = ult_val * 6.894757 if is_imperial else ult_val
        
        if json_yield >= json_ult:
            print_error("Yield Strength must be less than Ultimate Strength.")
            time.sleep(2)
            return None
            
        mod_val = float(input(colored(f"Enter Elastic Modulus ({units['modulus']}): ➔ ", 'cyan')))
        json_mod = mod_val * 0.006894757 if is_imperial else mod_val
        
        poisson = float(input(colored("Enter Poisson's Ratio (e.g., 0.3): ➔ ", 'cyan')))
        if not (0.0 < poisson < 0.5):
            print_error("Poisson's Ratio must be between 0 and 0.5.")
            time.sleep(2)
            return None
            
        therm = float(input(colored("Enter Thermal Expansion Coefficient (1/°C) [e.g., 1.2e-5, or 0 to skip]: ➔ ", 'cyan')))
        desc = input(colored("Enter a short description: ➔ ", 'cyan')).strip()
        
        material_dict = {
            "Material": name,
            "Density": round(json_dens, 2),
            "Yield Strength": round(json_yield, 2),
            "Ultimate Strength": round(json_ult, 2),
            "Elastic Modulus": round(json_mod, 2),
            "Poisson Ratio": round(poisson, 3),
            "Thermal Expansion": therm if therm != 0 else 0,
            "Description": desc
        }
        
        return material_dict
        
    except ValueError:
        print_error("Invalid numeric input. Material creation aborted.")
        time.sleep(2)
        return None
