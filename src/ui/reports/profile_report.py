"""Post-confirmation profile summary report renderer.

Relocated from ``ui.Menus`` into ``ui.reports`` during the P3
``ui/menus/`` decomposition (checkpoint-5) — it is a domain renderer
(the profile summary screen), not a navigation menu. Pure relocation;
signature and behavior unchanged.
"""
import numpy as np
from termcolor import colored

from common.units import METRIC_UNITS, get_divisor
from ui.console import clear_screen
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
