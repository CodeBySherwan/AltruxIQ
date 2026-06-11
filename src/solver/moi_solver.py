# --------------------------------------------------------------------------------
#            Moment of Inertia (MOI) Solver with Neutral Axis Distance (c) & Width (b)
# --------------------------------------------------------------------------------
import numpy as np
from termcolor import cprint, colored

# --- Helper Functions for Visual Enhancement ---

def print_header(title):
    """Print a decorated header for MOI solver sections."""
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored(f"║{title:^64}║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")

def print_result(title, value, unit, precision=6, color='green'):
    """Print a formatted result with proper units."""
    print(colored("┌─ " + title + " " + "─"*(60-len(title)), color, attrs=['bold']))
    if isinstance(value, float):
        if abs(value) < 0.01 or abs(value) > 10000:
            value_str = f"{value:.{precision}e} {unit}"
        else:
            value_str = f"{value:.{precision}f} {unit}"
    else:
        value_str = f"{value} {unit}"
    print(colored(f"│ {value_str}", color))
    print(colored("└" + "─"*62, color, attrs=['bold']))
    print("")

def display_cross_section(shape_type):
    """Display ASCII art visualization of the selected cross-section."""
    print(colored("┌─ Cross-Section Visualization "+"─"*35, 'yellow', attrs=['bold']))
    
    if shape_type == "I-beam":
        print(colored("│", 'yellow'))
        print(colored("│  ▔▔▔▔▔▔▔▔▔▔▔▔", 'white'))
        print(colored("│       ▏  ▏       ",   'white'))
        print(colored("│       ▏  ▏       ", 'white'))
        print(colored("│       ▏  ▏       ", 'white'))
        print(colored("│  ▁▁▁▁▁▁▁▁▁▁▁▁", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type == "T-beam":
        print(colored("│", 'yellow'))
        print(colored("│  ▔▔▔▔▔▔▔▔▔▔▔", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│        ▏      ", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type == "Circle" or shape_type == "Solid Circle":
        print(colored("│", 'yellow'))
        print(colored("│         ▗▄▄▄▖", 'white'))
        print(colored("│       ▗▛    ▜▖", 'white'))
        print(colored("│      ▐       ▌", 'white'))
        print(colored("│       ▝▙    ▟▘", 'white'))
        print(colored("│         ▝▀▀▀▘", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type == "Hollow Circle":
        print(colored("│", 'yellow'))
        print(colored("│         ▗▄▄▄▖", 'white'))
        print(colored("│       ▗▛    ▜▖", 'white'))
        print(colored("│      ▐  ▗▄▖  ▌", 'white'))
        print(colored("│       ▝▙▝▀▘▟▘", 'white'))
        print(colored("│         ▝▀▀▀▘", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type == "Square" or shape_type == "Rectangle":
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type == "Hollow Square" or shape_type == "Hollow Rectangle":
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █▄▄▄▄▄▄▄▄█", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █▀▀▀▀▀▀▀▀█", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))
    
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    print("")

# --- Functions for Different Cross-Sections ---

def inertia_moment_ibeam():
    try:
        print_header("I-BEAM PROFILE")
        display_cross_section("I-beam")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        bf = float(input(colored("│ Flange width, bf: ", 'cyan')))
        tf = float(input(colored("│ Flange height, tf: ", 'cyan')))
        hw = float(input(colored("│ Web height, hw: ", 'cyan')))
        tw = float(input(colored("│ Web thickness, tw: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter numeric values only.", 'yellow'))
        return None

    # Calculate moment of inertia
    H = 2 * tf + hw
    c = H / 2
    d = c - tf / 2

    I_flange = (bf * tf**3) / 12
    I_flange_total = I_flange + bf * tf * (d**2)
    I_web = (tw * hw**3) / 12
    Ix_total = 2 * I_flange_total + I_web
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Total Height: {H:.4f} m", 'blue'))
    print(colored(f"│ Total Width (flange): {bf:.4f} m", 'blue'))
    print(colored(f"│ Representative width (web): {tw:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "I-beam", c, tw, y_array

def inertia_moment_tbeam():
    try:
        print_header("T-BEAM PROFILE")
        display_cross_section("T-beam")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        bf = float(input(colored("│ Flange width, bf: ", 'cyan')))
        tf = float(input(colored("│ Flange thickness, tf: ", 'cyan')))
        hw = float(input(colored("│ Web height, hw: ", 'cyan')))
        tw = float(input(colored("│ Web thickness, tw: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter numeric values only.", 'yellow'))
        return None

    # Calculate centroid and moment of inertia
    A_flange = bf * tf
    A_web = tw * hw
    y_flange = tf / 2
    y_web = tf + hw / 2
    A_total = A_flange + A_web
    y_bar = (A_flange * y_flange + A_web * y_web) / A_total
    c = max(y_bar, tf + hw - y_bar)
    
    # Calculate moment of inertia
    I_flange = (bf * tf**3) / 12
    I_web = (tw * hw**3) / 12
    I_flange_total = I_flange + A_flange * (y_bar - y_flange)**2
    I_web_total = I_web + A_web * (y_web - y_bar)**2
    Ix_total = I_flange_total + I_web_total
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Total Height: {tf + hw:.4f} m", 'blue'))
    print(colored(f"│ Centroid Position: {y_bar:.4f} m from top", 'blue'))
    print(colored(f"│ Representative width (web): {tw:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "T-beam", c, tw, y_array

def inertia_moment_circle():
    try:
        print_header("CIRCULAR PROFILE")
        display_cross_section("Circle")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        diameter = float(input(colored("│ Diameter of the circle: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter numeric values only.", 'yellow'))
        return None

    # Calculate moment of inertia
    r = diameter / 2.0
    c = r
    Ix_total = (np.pi * (r**4)) / 4
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {np.pi * r**2:.4f} m²", 'blue'))
    print(colored(f"│ Representative width: {diameter:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Circle", c, diameter, y_array

def inertia_moment_rectangle():
    try:
        print_header("RECTANGULAR PROFILE")
        display_cross_section("Rectangle")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        b = float(input(colored("│ Base (width) of the rectangle: ", 'cyan')))
        h = float(input(colored("│ Height of the rectangle: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter numeric values only.", 'yellow'))
        return None

    # Calculate moment of inertia
    c = h / 2
    Ix_total = b * h**3 / 12
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {b * h:.4f} m²", 'blue'))
    print(colored(f"│ Aspect Ratio (h/b): {h/b:.2f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Rectangle", c, b, y_array

def inertia_moment_square():
    try:
        print_header("SQUARE PROFILE")
        display_cross_section("Square")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        a = float(input(colored("│ Side length of the square: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter numeric values only.", 'yellow'))
        return None

    # Calculate moment of inertia
    c = a / 2
    Ix_total = a**4 / 12
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {a**2:.4f} m²", 'blue'))
    print(colored(f"│ Diagonal Length: {a*1.414:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Square", c, a, y_array

def inertia_moment_hollow_circle():
    try:
        print_header("HOLLOW CIRCULAR PROFILE")
        display_cross_section("Hollow Circle")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_diameter = float(input(colored("│ Outer diameter of the hollow circle: ", 'cyan')))
        inner_diameter = float(input(colored("│ Inner diameter of the hollow circle: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
        
        # Validate input
        if inner_diameter >= outer_diameter:
            raise ValueError("Inner diameter must be less than outer diameter.")
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter valid numeric values.", 'yellow'))
        return None

    # Calculate moment of inertia
    r_outer = outer_diameter / 2.0
    r_inner = inner_diameter / 2.0
    c = r_outer
    Ix_total = (np.pi * (r_outer**4 - r_inner**4)) / 4
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {np.pi * (r_outer**2 - r_inner**2):.4f} m²", 'blue'))
    print(colored(f"│ Wall Thickness: {r_outer - r_inner:.4f} m", 'blue'))
    print(colored(f"│ Radius Ratio (r_inner/r_outer): {r_inner/r_outer:.4f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Hollow Circle", c, outer_diameter, y_array

def inertia_moment_hollow_square():
    try:
        print_header("HOLLOW SQUARE PROFILE")
        display_cross_section("Hollow Square")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_width = float(input(colored("│ Outer side length of the hollow square: ", 'cyan')))
        inner_width = float(input(colored("│ Inner side length of the hollow square: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
        
        # Validate input
        if inner_width >= outer_width:
            raise ValueError("Inner width must be less than outer width.")
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter valid numeric values.", 'yellow'))
        return None

    # Calculate moment of inertia
    c = outer_width / 2
    Ix_total = (outer_width**4 - inner_width**4) / 12
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {outer_width**2 - inner_width**2:.4f} m²", 'blue'))
    print(colored(f"│ Wall Thickness: {(outer_width - inner_width)/2:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Hollow Square", c, outer_width, y_array

def inertia_moment_hollow_rectangle():
    try:
        print_header("HOLLOW RECTANGULAR PROFILE")
        display_cross_section("Hollow Rectangle")
        
        print(colored("┌─ ENTER DIMENSIONS (in meters) "+"─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_b = float(input(colored("│ Outer base (width) of the hollow rectangle: ", 'cyan')))
        outer_h = float(input(colored("│ Outer height of the hollow rectangle: ", 'cyan')))
        inner_b = float(input(colored("│ Inner base (width) of the hollow rectangle: ", 'cyan')))
        inner_h = float(input(colored("│ Inner height of the hollow rectangle: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
        
        # Validate input
        if inner_b >= outer_b or inner_h >= outer_h:
            raise ValueError("Inner dimensions must be less than outer dimensions.")
    except Exception as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"Invalid input: {e}", 'red'))
        print(colored("Please enter valid numeric values.", 'yellow'))
        return None

    # Calculate moment of inertia
    c = outer_h / 2
    I_outer = outer_b * (outer_h**3) / 12
    I_inner = inner_b * (inner_h**3) / 12
    Ix_total = I_outer - I_inner
    y_array = np.linspace(-c, c, 10001)
    
    # Print results with enhanced formatting
    print_result("MOMENT OF INERTIA", Ix_total, "m⁴", precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE", c, "m", precision=4, color='yellow')
    
    # Display cross-section parameters for reference
    print(colored("┌─ CROSS-SECTION PARAMETERS "+"─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Area: {outer_b*outer_h - inner_b*inner_h:.4f} m²", 'blue'))
    print(colored(f"│ Horizontal Wall Thickness: {(outer_b - inner_b)/2:.4f} m", 'blue'))
    print(colored(f"│ Vertical Wall Thickness: {(outer_h - inner_h)/2:.4f} m", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    return Ix_total, "Hollow Rectangle", c, outer_b, y_array