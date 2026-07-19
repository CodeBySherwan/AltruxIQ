"""Load-definition wizard for beam analyses.

Interactive, menu-driven wizard for adding and removing point, distributed,
moment and triangular loads (with display-unit input converted to SI and
on-screen sign-convention guidance), plus a tabular review of the loads
defined so far.

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3). Pure relocation; signatures and behavior unchanged.
"""
import time
import numpy as np
from termcolor import colored

from common.units import to_si, default_units
from ui.console import print_error, print_success, clear_screen

#==================================================================================

def manage_loads(unit_system="Metric", units=None, beam_type=None):
    if units is None:
        units = default_units()
    
    dist_unit = f"{units['force']}/{units['length']}"
    
    # Grab multipliers for conversion to SI before saving
    l_mult = to_si(unit_system, "length")
    f_mult = to_si(unit_system, "force")
    m_mult = to_si(unit_system, "moment")
    d_mult = to_si(unit_system, "distributed")

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
