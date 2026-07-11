import sys
import os
from termcolor import colored
import time
import numpy as np
# =============================
# Unit Conversion — single source in `common.units`
# =============================
# `system_multiplier(system, qty)` is the drop-in replacement for the legacy
# CONVERSION_TO_SI[system][qty] lookup that used to live here.
from common.units import system_multiplier, default_units, UNIT_SYSTEMS, to_json
from common.config import SOLVER
from common.exceptions import SectionGeometryError

from ui.Menus import (print_error, print_success, print_title, print_option, clear_screen,
                     ui_banner, ui_open, ui_close, ui_blank, ui_field, ui_text, ui_bullet, ui_head)

# =============================================================================
#  PROFESSIONAL INPUT TOOLKIT
# -----------------------------------------------------------------------------
#  Validated, retry-on-error prompt primitives sharing one visual language:
#  a bold cyan label, an inline constraint/units hint, the standard caret, and
#  friendly red error messages. Numeric prompts re-ask on invalid input instead
#  of crashing; optional prompts accept a cancel keyword so the user can back
#  out of any data-entry step cleanly.
# =============================================================================
PROMPT_CARET = "\u2794"
_CANCEL_TOKENS = {"c", "cancel", "q", "quit", "b", "back", "esc"}


def _dim(text):
    return colored(text, 'white', attrs=['dark'])


def _format_prompt(label, unit=None, hint=None, default=None, allow_cancel=False):
    head = "  " + label.strip()
    if unit:
        head += f"  [{unit}]"
    sub = []
    if hint:
        sub.append(hint)
    if default is not None:
        sub.append(f"default: {default}")
    if allow_cancel:
        sub.append("'c' to cancel")
    line = colored(head, 'cyan', attrs=['bold'])
    if sub:
        line += _dim("   (" + "  \u00b7  ".join(sub) + ")")
    line += colored(f"\n  {PROMPT_CARET} ", 'cyan', attrs=['bold'])
    return line


def _range_hint(minimum, maximum, exclusive_min, exclusive_max, symbol="x"):
    if minimum is None and maximum is None:
        return None
    lo = ""
    if minimum is not None:
        lo = f"{minimum} {'<' if exclusive_min else '\u2264'} "
    hi = ""
    if maximum is not None:
        hi = f" {'<' if exclusive_max else '\u2264'} {maximum}"
    return f"{lo}{symbol}{hi}"


def ask_float(label, unit=None, minimum=None, maximum=None,
              exclusive_min=False, exclusive_max=False,
              default=None, allow_cancel=False):
    """Prompt for a float, validating range and retrying on bad input.
    Returns the float, or None if the user cancels (when allowed)."""
    hint = _range_hint(minimum, maximum, exclusive_min, exclusive_max)
    while True:
        raw = input(_format_prompt(label, unit, hint, default, allow_cancel)).strip()
        if not raw and default is not None:
            return float(default)
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            val = float(raw)
        except ValueError:
            print_error("  Please enter a valid number (e.g. 12.5).")
            time.sleep(1.0); continue
        if minimum is not None and (val < minimum or (exclusive_min and val == minimum)):
            rel = "greater than" if exclusive_min else "at least"
            print_error(f"  Value must be {rel} {minimum}{(' ' + unit) if unit else ''}.")
            time.sleep(1.0); continue
        if maximum is not None and (val > maximum or (exclusive_max and val == maximum)):
            rel = "less than" if exclusive_max else "at most"
            print_error(f"  Value must be {rel} {maximum}{(' ' + unit) if unit else ''}.")
            time.sleep(1.0); continue
        return val


def ask_int(label, minimum=None, maximum=None, default=None, allow_cancel=False):
    """Prompt for an integer, validating range and retrying on bad input."""
    hint = _range_hint(minimum, maximum, False, False, symbol="n")
    while True:
        raw = input(_format_prompt(label, None, hint, default, allow_cancel)).strip()
        if not raw and default is not None:
            return int(default)
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            val = int(raw)
        except ValueError:
            print_error("  Please enter a whole number (e.g. 2001).")
            time.sleep(1.0); continue
        if minimum is not None and val < minimum:
            print_error(f"  Value must be at least {minimum}."); time.sleep(1.0); continue
        if maximum is not None and val > maximum:
            print_error(f"  Value must be at most {maximum}."); time.sleep(1.0); continue
        return val


def ask_text(label, required=True, default=None, allow_cancel=False, max_len=None):
    """Prompt for a line of text with optional required / length validation."""
    while True:
        raw = input(_format_prompt(label, None, None, default, allow_cancel)).strip()
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        if not raw:
            if default is not None:
                return default
            if not required:
                return ""
            print_error("  This field cannot be empty."); time.sleep(1.0); continue
        if max_len and len(raw) > max_len:
            print_error(f"  Please keep it under {max_len} characters."); time.sleep(1.0); continue
        return raw


def ask_choice(label, valid, allow_cancel=False):
    """Prompt until the user enters one of ``valid`` tokens. Returns the token."""
    valid = [str(v) for v in valid]
    hint = "options: " + " / ".join(valid)
    while True:
        raw = input(_format_prompt(label, None, hint, None, allow_cancel)).strip()
        if allow_cancel and raw.lower() in _CANCEL_TOKENS:
            return None
        if raw in valid:
            return raw
        print_error(f"  Invalid choice. Pick one of: {', '.join(valid)}."); time.sleep(1.0)


def ask_yes_no(question, default=None):
    """Prompt for a yes/no answer. Returns True/False (default on empty input)."""
    suffix = "(Y/N)" if default is None else ("(Y/n)" if default else "(y/N)")
    while True:
        raw = input(colored(f"  {question} {suffix} {PROMPT_CARET} ",
                            'cyan', attrs=['bold'])).strip().lower()
        if not raw and default is not None:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print_error("  Please answer Y or N."); time.sleep(0.8)


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
        ("8", "Stepped Bar", "Varying cross-section / material",
         "\u2550\u2501\u2501\u2550\u2501\u2501\u2550\u2501\u2501\u2550   (axial + bending)"),
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
    classification = input(colored("  Enter your choice [1-8] \u2794 ", 'cyan', attrs=['bold']))

    mapping = {
        '1': "Simple", '2': "Overhanging Beam", '3': "Cantilever",
        '4': "Fixed-Fixed", '5': "Propped", '6': "Continuous", '7': "Custom",
        '8': "Stepped Bar",
    }
    if classification in mapping:
        return mapping[classification]
    print_error("Invalid selection. Please choose a number between 1 and 8.")
    time.sleep(1.5)
    return Beam_Classification()

def Beam_Length(unit_system="Metric", units=None):
    """Prompt the user to enter the beam length."""
    if units is None: units = default_units()
    multiplier = system_multiplier(unit_system, "length")
    beam_length_raw = ask_float("Enter beam length", unit=units['length'],
                                minimum=0, exclusive_min=True)
    print("")
    return beam_length_raw * multiplier  # Return converted SI value

#==============================
def Beam_Supports(unit_system="Metric", units=None):
    """Prompt the user to define the beam supports."""
    if units is None: units = default_units()
    multiplier = system_multiplier(unit_system, "length")
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
    multiplier = system_multiplier(unit_system, "length")
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
    multiplier = system_multiplier(unit_system, "length")
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
                        ky = ky_raw * (system_multiplier(unit_system, "force") / multiplier)
                        has_y_restraint = True
                    elif s_type == '5':
                        dof = (1, 0, 0)
                        kx_raw = float(input(colored(f"Enter horizontal spring stiffness ({units['force']}/{units['length']}): ➔ ", 'cyan')))
                        kx = kx_raw * (system_multiplier(unit_system, "force") / multiplier)
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
#==================================================================================
def manage_loads(unit_system="Metric", units=None, beam_type=None):
    if units is None:
        units = default_units()
    
    dist_unit = f"{units['force']}/{units['length']}"
    
    # Grab multipliers for conversion to SI before saving
    l_mult = system_multiplier(unit_system, "length")
    f_mult = system_multiplier(unit_system, "force")
    m_mult = system_multiplier(unit_system, "moment")
    d_mult = system_multiplier(unit_system, "distributed")

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
                # Only show horizontal/angled loads for stepped bars
                if beam_type == "Stepped Bar":
                    print(colored("│ 2 - Horizontal Load (X-direction)", 'green'))
                    print(colored("│ 3 - Angled Load (Force & Angle)", 'green'))
                print(colored("┄" + "─"*57, 'green', attrs=['bold']))
                print("\n")
                
                if beam_type == "Stepped Bar":
                    load_type = input(colored("Enter your choice [1, 2, or 3] ➔ ", 'cyan'))
                else:
                    load_type = input(colored("Enter your choice [1] ➔ ", 'cyan'))
                if load_type == '1':
                    
                    y_force = float(input(colored(f"\nEnter Y-force ({units['force']}) [positive up ↑, negative down ↓]: ➔ ", 'cyan'))) * f_mult
                    loads["pointloads"].append([pos, 0, y_force])
                    print_success(f"Added vertical point load: {y_force/f_mult} {units['force']} at x = {pos/l_mult} {units['length']}")
                
                
                elif load_type == '2' and beam_type == "Stepped Bar":
                    x_force = float(input(colored(f"\nEnter X-force ({units['force']}) [positive right →, negative left ←]: ➔ ", 'cyan'))) * f_mult
                    loads["pointloads"].append([pos, x_force, 0])
                    print_success(f"Added horizontal point load: {x_force/f_mult} {units['force']} at x = {pos/l_mult} {units['length']}")
                
                elif load_type == '3' and beam_type == "Stepped Bar":
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
                    print_error("Invalid point load type selection.")
                    time.sleep(2)
                
                time.sleep(1.5)
            
            except (ValueError, EOFError) as e:
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
                    print_error("End position must be greater than start position.")
                    time.sleep(2)
                    continue
                
                loads["distributedloads"].append([start, end, intensity])
                print_success(f"Added UDL: {intensity/d_mult} {dist_unit} from x = {start/l_mult} {units['length']} to x = {end/l_mult} {units['length']}")
                time.sleep(1.5)
            
            except (ValueError, EOFError) as e:
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
            
            except (ValueError, EOFError) as e:
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
                    print_error("End position must be greater than start position.")
                    time.sleep(2)
                    continue
                
                intensity = float(input(colored(f"Enter peak load intensity ({dist_unit}): ➔ ", 'cyan'))) * d_mult
                intensityL = float(input(colored(f"Enter lowest load intensity ({dist_unit}): ➔ ", 'cyan'))) * d_mult
                
                loads["triangleloads"].append([start, end, intensity, intensityL])
                print_success(f"Added triangular load from x = {start/l_mult} {units['length']} to x = {end/l_mult} {units['length']}")
                print_success(f"Peak intensity: {intensity/d_mult} {dist_unit}, Lowest intensity: {intensityL/d_mult} {dist_unit}")
                time.sleep(1.5)
            
            except (ValueError, EOFError) as e:
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
            print_error("Invalid selection. Please try again.")
            time.sleep(2)
    
    return loads
#--------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
def get_solver_resolution():
    """
    Prompt the user to enter a custom solver resolution between 201 and 10001.
    """
    return ask_int("Enter custom solver resolution",
                   minimum=SOLVER.MIN_NUM_POINTS, maximum=SOLVER.MAX_NUM_POINTS,
                   default=SOLVER.DEFAULT_NUM_POINTS, allow_cancel=True)
#--------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------
def define_custom_material(unit_system="Metric", units=None):
    """Interactive wizard to create a custom material entry."""
    if units is None: units = default_units()
    clear_screen()
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║               DEFINE CUSTOM MATERIAL                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    name = ask_text("Enter material name", required=True, allow_cancel=True, max_len=60)
    if name is None:
        return None

    # Inputs in active units, converted to JSON base schema (kg/m³, MPa, GPa)
    # via common.units.to_json — single source of truth for the storage convention
    dens_val = ask_float("Enter density", unit=units['density'], minimum=0, exclusive_min=True, allow_cancel=True)
    if dens_val is None: return None
    json_dens = to_json(units, 'density', dens_val)

    yield_val = ask_float("Enter yield strength", unit=units['stress'], minimum=0, exclusive_min=True, allow_cancel=True)
    if yield_val is None: return None
    json_yield = to_json(units, 'stress', yield_val)

    ult_val = ask_float("Enter ultimate strength", unit=units['stress'], minimum=0, exclusive_min=True, allow_cancel=True)
    if ult_val is None: return None
    json_ult = to_json(units, 'stress', ult_val)

    if json_yield >= json_ult:
        print_error("Yield Strength must be less than Ultimate Strength.")
        time.sleep(2)
        return None

    mod_val = ask_float("Enter elastic modulus", unit=units['modulus'], minimum=0, exclusive_min=True, allow_cancel=True)
    if mod_val is None: return None
    json_mod = to_json(units, 'modulus', mod_val)

    poisson = ask_float("Enter Poisson's ratio", minimum=0, maximum=0.5, exclusive_min=True, exclusive_max=True, default=0.3, allow_cancel=True)
    if poisson is None: return None

    therm = ask_float("Enter thermal expansion coefficient (1/°C, 0 to skip)", default=0, allow_cancel=True)
    if therm is None: return None
    desc = ask_text("Enter a short description", required=False, allow_cancel=True, max_len=120)
    if desc is None:
        desc = ""

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
#==================================================================================
def define_stepped_segments(unit_system="Metric", units=None):
    """
    Interactive wizard for defining stepped beam segments.
    Each segment has its own cross-section, material, and length.
    
    Returns a list of segment dicts:
        [
            {
                "start": float, "end": float,
                "E": float, "A": float, "I": float,
                "shape": str, "section_dims": dict,
                "c": float, "b": float, "y_array": np.ndarray,
                "material_name": str,
            }, ...
        ]
    """
    import numpy as np

    if units is None:
        units = default_units()
    
    l_mult = system_multiplier(unit_system, "length")
    inv_len = 1.0 / l_mult
    
    # Import needed modules (path injection is already done at top of inputs.py)
    from solver import moi_solver
    from solver.area_solver import area_from_section
    from ui.Menus import choose_profile, print_error, print_success, clear_screen, print_title, print_option, display_section_library

    segments = []
    
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║              STEPPED BEAM SEGMENT DEFINITION                 ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        
        if segments:
            print(colored("┌─ DEFINED SEGMENTS ─" + "─"*43, 'green', attrs=['bold']))
            for i, seg in enumerate(segments, 1):
                print(colored(f"│ {i}. {seg['shape']:15s}  L={seg['length']*inv_len:.3f} {units['length']}  E={seg['E']/1e9:.1f} GPa  A={seg['A']*1e6:.2f} mm²  I={seg['I']*1e12:.2e} mm⁴", 'white'))
            print(colored("└" + "─"*62, 'green', attrs=['bold']))
            print("")
        
        try:
            num_segs = int(input(colored("Enter number of segments: ➔ ", 'cyan')))
            if num_segs < 1:
                print_error("At least 1 segment required.")
                time.sleep(1.5)
                continue
            break
        except ValueError:
            print_error("Please enter a valid number.")
            time.sleep(1.5)
    
    total_length = 0.0
    
    for i in range(num_segs):
        clear_screen()
        print(colored(f"╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored(f"║           DEFINING SEGMENT {i+1} OF {num_segs}                             ║", 'cyan', attrs=['bold']))
        print(colored(f"╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        
        # Segment length
        seg_len_raw = ask_float(f"Segment {i+1} length", unit=units['length'], minimum=0, exclusive_min=True, allow_cancel=True)
        if seg_len_raw is None:
            return None
        seg_len = seg_len_raw * l_mult
        
        # Cross-section selection
        print("")
        print(colored("┌─ SELECT CROSS-SECTION FOR THIS SEGMENT ─" + "─"*20, 'yellow', attrs=['bold']))
        
        from database.sections_database import SectionsDatabase
        sections_db = SectionsDatabase()
        
        while True:
            print_option("  1. ✍️  Enter Custom Dimensions (Manual)")
            print_option("  2. 📚 Standard Section Library")
            print_option("  3. 💾 My Saved Sections")
            print("")
            src_choice = input(colored("Choose option [1-3] ➔ ", 'cyan')).strip()
            
            result = None
            if src_choice == '1':
                profile_choice = choose_profile()
                if profile_choice in ('1', '2', '3', '4', '5', '6', '7', '8'):
                    if profile_choice == '1': result = moi_solver.inertia_moment_ibeam(units=units)
                    elif profile_choice == '2': result = moi_solver.inertia_moment_tbeam(units=units)
                    elif profile_choice == '3': result = moi_solver.inertia_moment_circle(units=units)
                    elif profile_choice == '4': result = moi_solver.inertia_moment_hollow_circle(units=units)
                    elif profile_choice == '5': result = moi_solver.inertia_moment_square(units=units)
                    elif profile_choice == '6': result = moi_solver.inertia_moment_hollow_square(units=units)
                    elif profile_choice == '7': result = moi_solver.inertia_moment_rectangle(units=units)
                    elif profile_choice == '8': result = moi_solver.inertia_moment_hollow_rectangle(units=units)
                else:
                    print_error("Invalid profile selection.")
                    continue
                if result is None:
                    print_error("Invalid dimensions entered. Try again.")
                    continue
                break
                
            elif src_choice == '2':
                families = sections_db.get_standard_families()
                if not families:
                    print_error("Standard library is empty or missing.")
                    continue
                clear_screen()
                print_title("STANDARD SECTION FAMILIES")
                for j, fam in enumerate(families, 1):
                    print_option(f"  {j}. {fam}")
                print_option(f"  0. Back")
                print("")
                try:
                    fam_idx = int(input(colored("Choose a family ➔ ", 'cyan')))
                    if fam_idx == 0: continue
                    selected_family = families[fam_idx - 1]
                    sections_in_fam = sections_db.get_sections_in_family(selected_family)
                    sec_idx = display_section_library(sections_in_fam, title=f"{selected_family} Sections", is_custom=False)
                    if sec_idx is not None:
                        entry = sections_in_fam[sec_idx]
                        result = moi_solver.load_section_from_library(entry)
                        if result:
                            break
                        else:
                            print_error("Failed to parse section data.")
                except (ValueError, IndexError):
                    print_error("Invalid selection.")
                    time.sleep(1)
                    continue
                    
            elif src_choice == '3':
                custom_secs = sections_db.list_custom_sections()
                if not custom_secs:
                    print_error("No saved custom sections found.")
                    continue
                sec_idx = display_section_library(custom_secs, title="MY SAVED SECTIONS", is_custom=True)
                if sec_idx is not None:
                    entry = custom_secs[sec_idx]
                    result = moi_solver.load_section_from_library(entry)
                    if result:
                        break
                    else:
                        print_error("Failed to parse section data.")
            else:
                print_error("Invalid choice. Please enter 1, 2, or 3.")
        
        Ix, shape, c, b, y_array, section_dims = result
        
        # Compute cross-sectional area
        try:
            A = area_from_section(shape, section_dims)
        except SectionGeometryError as e:
            print_error(f"Error computing area: {e}")
            time.sleep(2)
            return None
        
        # Material selection from library
        print("")
        print(colored("┌─ SELECT MATERIAL FOR THIS SEGMENT ─" + "─"*20, 'magenta', attrs=['bold']))

        # Lazy import: select_material / load_material_database still live in
        # ui.cli (to be moved to ui/materials/selector.py in P3). Materials is
        # no longer a cli.py module global — it lives on state.Materials.
        from core.state import state
        from ui.cli import select_material, load_material_database
        if state.Materials is None:
            load_material_database()

        selected_mat = select_material(unit_system, units)
        if selected_mat is None:
            print_error("Material selection is required for segment.")
            time.sleep(1.5)
            return None
            
        E = float(selected_mat["Elastic Modulus"]) * 1e9
        E_gpa = float(selected_mat["Elastic Modulus"])
        yield_mpa = float(selected_mat["Yield Strength"])
        material_name = selected_mat["Material"]
        
        seg_start = total_length
        seg_end = total_length + seg_len
        total_length = seg_end
        
        segments.append({
            "start": seg_start,
            "end": seg_end,
            "length": seg_len,
            "E": E,
            "A": A,
            "I": Ix,
            "shape": shape,
            "section_dims": section_dims,
            "c": c,
            "b": b,
            "y_array": y_array,
            "material_name": material_name,
            "yield_strength": yield_mpa * 1e6,
        })
        
        print_success(f"Segment {i+1} defined: {shape}, L={seg_len*inv_len:.3f} {units['length']}")
        time.sleep(1)
    
    print_success(f"All {num_segs} segments defined. Total length = {total_length*inv_len:.3f} {units['length']}")
    time.sleep(1.5)
    return segments
