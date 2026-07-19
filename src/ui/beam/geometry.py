"""Beam geometry and support-definition wizards.

Interactive prompts for beam length and support layouts: simple pin/roller
pairs, continuous multi-support spans, and fully custom support
configurations (pin / roller / fixed / elastic springs, with restraint
validation).

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3). Pure relocation; signatures and behavior unchanged.
"""
import time
from termcolor import colored

from common.units import to_si, default_units
from ui.console import print_error, print_success, clear_screen
from ui.console.prompts import ask_float

def Beam_Length(unit_system="Metric", units=None):
    """Prompt the user to enter the beam length."""
    if units is None: units = default_units()
    multiplier = to_si(unit_system, "length")
    beam_length_raw = ask_float("Enter beam length", unit=units['length'],
                                minimum=0, exclusive_min=True)
    print("")
    return beam_length_raw * multiplier  # Return converted SI value

#==============================

def Beam_Supports(unit_system="Metric", units=None):
    """Prompt the user to define the beam supports."""
    if units is None: units = default_units()
    multiplier = to_si(unit_system, "length")
    A_raw = ask_float("Enter position of Pin Support A", unit=units['length'], minimum=0)
    A = A_raw * multiplier
    A_restraint = (1, 1, 0)
    A_type = "Pin Support"

    B_raw = ask_float("Enter position of Roller Support B", unit=units['length'], minimum=0)
    B = B_raw * multiplier
    B_restraint = (0, 1, 0)
    B_type = "Roller Support"

    if A >= B:
        print_error("Support A must be to the left of Support B.")
        print("")
        time.sleep(1.2)
        return Beam_Supports(unit_system, units)
    print("")
    return A, B, A_restraint, B_restraint, A_type, B_type



def define_continuous_supports(beam_length, unit_system="Metric", units=None):
    """
    Prompt the user to enter multiple support coordinates for a continuous beam.
    Returns a list of dicts: [{"pos": float, "dof": (0,1,0), "ky": None, "kx": None}, ...]
    """
    if units is None: units = default_units()
    multiplier = to_si(unit_system, "length")
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
    if units is None: units = default_units()
    multiplier = to_si(unit_system, "length")
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
                        ky = ky_raw * (to_si(unit_system, "force") / multiplier)
                        has_y_restraint = True
                    elif s_type == '5':
                        dof = (1, 0, 0)
                        kx_raw = float(input(colored(f"Enter horizontal spring stiffness ({units['force']}/{units['length']}): ➔ ", 'cyan')))
                        kx = kx_raw * (to_si(unit_system, "force") / multiplier)
                        has_x_restraint = True
                    else:
                        print_error("Invalid choice.")
                        continue
                    break
                    
                supports.append({"pos": pos, "dof": dof, "ky": ky, "kx": kx})
                
            # Validations
            if not has_y_restraint:
                print_error("Beam has no vertical restraint. It will fail to solve. Please re-enter.")
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
