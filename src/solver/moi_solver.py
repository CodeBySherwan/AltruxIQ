# --------------------------------------------------------------------------------
#  Moment of Inertia (MOI) Solver — Improved
#  Returns 6-tuple: (Ix, shape_name, c, b_rep, y_array, section_dims)
#
#  section_dims: exact geometric dict used by stress_solver.width_array_for_section
#                to compute the correct shear-stress width b(y) at every height.
# --------------------------------------------------------------------------------
# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from termcolor import cprint, colored

from common.exceptions import SectionGeometryError
# --------------------------------------------------------------------------------
# --------------------------------------------------------------------------------
def get_moi_scale(units_dict):
    """
    Returns (len_div, i_div, len_unit, i_unit) to dynamically scale 
    cross-sectional properties for display purposes.
    """
    if units_dict is None:
        # Default fallback to Metric (SI) if no units dict is provided
        return 1.0, 1.0, "m", "m⁴"
    
    is_imperial = units_dict.get('length') == 'ft'
    if is_imperial:
        # Cross-section dimensions are conventionally shown in inches (in) and in⁴ for Imperial
        return 0.0254, (0.0254)**4, "in", "in⁴"
    else:
        # Default behavior for Metric (meters and m⁴)
        return 1.0, 1.0, "m", "m⁴"
# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

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

def print_derived_properties(Ix, c, A,units=None):
    """Print derived engineering properties: Se, rg (exact for all sections)."""
    Se   = Ix / c                   # Elastic section modulus (m³)
    r_g  = np.sqrt(Ix / A)          # Radius of gyration (m)
    print(colored("┌─ DERIVED ENGINEERING PROPERTIES " + "─"*29, 'magenta', attrs=['bold']))
    print(colored(f"│ Cross-sectional Area (A):          {A:.6e} m²", 'magenta'))
    print(colored(f"│ Elastic Section Modulus (Se=Ix/c): {Se:.6e} m³", 'magenta'))
    print(colored(f"│ Radius of Gyration (r=√(Ix/A)):    {r_g:.6e} m", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    print("")

def display_cross_section(shape_type):
    """Display ASCII art visualization of the selected cross-section."""
    print(colored("┌─ Cross-Section Visualization " + "─"*35, 'yellow', attrs=['bold']))

    if shape_type == "I-beam":
        print(colored("│", 'yellow'))
        print(colored("│  ▔▔▔▔▔▔▔▔▔▔▔▔", 'white'))
        print(colored("│       ▏  ▏       ", 'white'))
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
    elif shape_type in ("Circle", "Solid Circle"):
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
    elif shape_type in ("Square", "Rectangle"):
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))
    elif shape_type in ("Hollow Square", "Hollow Rectangle"):
        print(colored("│", 'yellow'))
        print(colored("│  ▄▄▄▄▄▄▄▄▄▄", 'white'))
        print(colored("│  █▄▄▄▄▄▄▄▄█", 'white'))
        print(colored("│  █        █", 'white'))
        print(colored("│  █▀▀▀▀▀▀▀▀█", 'white'))
        print(colored("│  ▀▀▀▀▀▀▀▀▀▀", 'white'))
        print(colored("│", 'yellow'))

    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    print("")

def _validate_positive(**kwargs):
    """Raise SectionGeometryError if any value is not strictly positive."""
    for name, val in kwargs.items():
        if val <= 0:
            raise SectionGeometryError(f"{name} must be a positive number (got {val}).")

# ---------------------------------------------------------------------------
# Profile Functions  (all return 6-tuple)
# ---------------------------------------------------------------------------

def inertia_moment_ibeam(units=None):
    """
    I-Beam (doubly-symmetric).

    Returns
    -------
    Ix, "I-beam", c, tw, y_array, section_dims
    section_dims keys: type, bf, tf, hw, tw, H
    """
    try:
        print_header("I-BEAM PROFILE")
        display_cross_section("I-beam")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        bf = float(input(colored("│ Flange width,    bf: ", 'cyan')))
        tf = float(input(colored("│ Flange thickness, tf: ", 'cyan')))
        hw = float(input(colored("│ Web height,      hw: ", 'cyan')))
        tw = float(input(colored("│ Web thickness,   tw: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(bf=bf, tf=tf, hw=hw, tw=tw)
        if tw >= bf:
            raise SectionGeometryError("Web thickness tw must be less than flange width bf.")

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    # Geometry
    H  = 2.0 * tf + hw
    c  = H / 2.0
    A  = 2.0 * bf * tf + tw * hw

    # Moment of inertia (parallel-axis theorem)
    d          = c - tf / 2.0                   # flange centroid distance from NA
    I_flange   = (bf * tf**3) / 12.0 + bf * tf * d**2
    I_web      = (tw * hw**3) / 12.0
    Ix_total   = 2.0 * I_flange + I_web
    y_array    = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    # Display
    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Total Height  H = 2tf + hw:        {H / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Flange width  bf:                  {bf / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Flange thickness tf:               {tf / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Web height    hw:                  {hw / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Web thickness tw:                  {tw / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Flange-to-web width ratio bf/tw:   {bf/tw:.2f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {'type': 'I-beam', 'bf': bf, 'tf': tf, 'hw': hw, 'tw': tw, 'H': H}
    return Ix_total, "I-beam", c, tw, y_array, section_dims


def inertia_moment_tbeam(units=None):
    """
    T-Beam (singly-symmetric, flange at top).

    Returns
    -------
    Ix, "T-beam", c, tw, y_array, section_dims
    section_dims keys: type, bf, tf, hw, tw, y_bar, H
    """
    try:
        print_header("T-BEAM PROFILE")
        display_cross_section("T-beam")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        bf = float(input(colored("│ Flange width,    bf: ", 'cyan')))
        tf = float(input(colored("│ Flange thickness, tf: ", 'cyan')))
        hw = float(input(colored("│ Web height,      hw: ", 'cyan')))
        tw = float(input(colored("│ Web thickness,   tw: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(bf=bf, tf=tf, hw=hw, tw=tw)
        if tw >= bf:
            raise SectionGeometryError("Web thickness tw must be less than flange width bf.")

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    # Geometry — measure from the BOTTOM of the section upward
    H        = tf + hw
    A_flange = bf * tf
    A_web    = tw * hw
    A_total  = A_flange + A_web

    y_flange_centroid = H - tf / 2.0   # flange centroid from bottom
    y_web_centroid    = hw / 2.0       # web centroid from bottom
    y_bar = (A_flange * y_flange_centroid + A_web * y_web_centroid) / A_total

    # Distances from NA
    d_flange = y_flange_centroid - y_bar
    d_web    = y_web_centroid    - y_bar

    # Moment of inertia about NA (parallel-axis theorem)
    I_flange = (bf * tf**3) / 12.0 + A_flange * d_flange**2
    I_web    = (tw * hw**3) / 12.0 + A_web    * d_web**2
    Ix_total = I_flange + I_web

    # c = max distance from NA to extreme fibre
    c_top    = H - y_bar    # distance from NA to top of flange (positive direction)
    c_bot    = y_bar        # distance from NA to bottom of web
    c        = max(c_top, c_bot)

    y_array = np.linspace(-c, c, 10001)

    # Asymmetric section moduli
    Se_top = Ix_total / c_top
    Se_bot = Ix_total / c_bot

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    # derived unit
    a_div = (0.3048)**2 if units and units.get('length') == 'ft' else 1.0
    sm_div = (0.0254)**3 if units and units.get('length') == 'ft' else 1.0
    a_unit = "ft²" if units and units.get('length') == 'ft' else "m²"
    sm_unit = "in³" if units and units.get('length') == 'ft' else "m³"

    # Display
    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')

    print(colored("┌─ NEUTRAL AXIS & SECTION GEOMETRY " + "─"*28, 'yellow', attrs=['bold']))
    print(colored(f"│ Centroid from bottom of section:   {y_bar / len_div:.4f} {len_unit}", 'yellow'))
    print(colored(f"│ Centroid from top of section:      {(H - y_bar) / len_div:.4f} {len_unit}", 'yellow'))
    print(colored(f"│ Distance NA→extreme bottom (c_bot):{c_bot / len_div:.4f} {len_unit}", 'yellow'))
    print(colored(f"│ Distance NA→extreme top   (c_top): {c_top / len_div:.4f} {len_unit}", 'yellow'))
    print(colored(f"│ Design c (governing):              {c / len_div:.4f} {len_unit}", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    print("")

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Total Height  H = tf + hw:         {H / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Flange width  bf:                  {bf / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Flange thickness tf:               {tf / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Web height    hw:                  {hw / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Web thickness tw:                  {tw / len_div:.4f} {len_unit}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print(colored("┌─ DERIVED ENGINEERING PROPERTIES " + "─"*29, 'magenta', attrs=['bold']))
    print(colored(f"│ Cross-sectional Area (A):          {A_total / a_div:.6e} {a_unit}", 'magenta'))
    print(colored(f"│ Section Modulus top  (Se=Ix/c_top):{Se_top / sm_div:.6e} {sm_unit}", 'magenta'))
    print(colored(f"│ Section Modulus bot  (Se=Ix/c_bot):{Se_bot / sm_div:.6e} {sm_unit}", 'magenta'))
    print(colored(f"│ Radius of Gyration (r=√(Ix/A)):    {np.sqrt(Ix_total/A_total) / len_div:.6e} {len_unit}", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    print("")

    section_dims = {
        'type': 'T-beam',
        'bf': bf, 'tf': tf, 'hw': hw, 'tw': tw,
        'y_bar': y_bar, 'H': H,
        'c_top': c_top, 'c_bot': c_bot,
    }
    return Ix_total, "T-beam", c, tw, y_array, section_dims


def inertia_moment_circle(units=None):
    """
    Solid circular cross-section.

    Returns
    -------
    Ix, "Circle", c, diameter, y_array, section_dims
    section_dims keys: type, diameter, radius
    """
    try:
        print_header("SOLID CIRCULAR PROFILE")
        display_cross_section("Circle")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        diameter = float(input(colored("│ Diameter d: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(diameter=diameter)

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    r        = diameter / 2.0
    c        = r
    Ix_total = (np.pi * r**4) / 4.0
    A        = np.pi * r**2
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = r)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Diameter d:                        {diameter / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Radius  r:                         {r / len_div:.4f} {len_unit}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {'type': 'Circle', 'diameter': diameter, 'radius': r}
    return Ix_total, "Circle", c, diameter, y_array, section_dims


def inertia_moment_hollow_circle(units=None):
    """
    Hollow circular (annular) cross-section.

    Returns
    -------
    Ix, "Hollow Circle", c, outer_diameter, y_array, section_dims
    section_dims keys: type, r_outer, r_inner, diameter_outer, diameter_inner
    """
    try:
        print_header("HOLLOW CIRCULAR PROFILE")
        display_cross_section("Hollow Circle")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_diameter = float(input(colored("│ Outer diameter D_o: ", 'cyan')))
        inner_diameter = float(input(colored("│ Inner diameter D_i: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(outer_diameter=outer_diameter, inner_diameter=inner_diameter)
        if inner_diameter >= outer_diameter:
            raise SectionGeometryError("Inner diameter must be strictly less than outer diameter.")

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    r_o      = outer_diameter / 2.0
    r_i      = inner_diameter / 2.0
    t_wall   = r_o - r_i
    c        = r_o
    Ix_total = (np.pi * (r_o**4 - r_i**4)) / 4.0
    A        = np.pi * (r_o**2 - r_i**2)
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = r_o)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Outer diameter D_o:                {outer_diameter / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Inner diameter D_i:                {inner_diameter / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Wall thickness t = (D_o-D_i)/2:    {t_wall / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Diameter ratio D_i/D_o:            {inner_diameter/outer_diameter:.4f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {
        'type': 'Hollow Circle',
        'r_outer': r_o, 'r_inner': r_i,
        'diameter_outer': outer_diameter, 'diameter_inner': inner_diameter,
    }
    return Ix_total, "Hollow Circle", c, outer_diameter, y_array, section_dims


def inertia_moment_rectangle(units=None):
    """
    Solid rectangular cross-section.

    Returns
    -------
    Ix, "Rectangle", c, b, y_array, section_dims
    section_dims keys: type, width, height
    """
    try:
        print_header("RECTANGULAR PROFILE")
        display_cross_section("Rectangle")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        b = float(input(colored("│ Width  b: ", 'cyan')))
        h = float(input(colored("│ Height h: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(b=b, h=h)

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    c        = h / 2.0
    Ix_total = b * h**3 / 12.0
    A        = b * h
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = h/2)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Width  b:                          {b / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Height h:                          {h / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Aspect ratio h/b:                  {h/b:.2f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {'type': 'Rectangle', 'width': b, 'height': h}
    return Ix_total, "Rectangle", c, b, y_array, section_dims


def inertia_moment_square(units=None):
    """
    Solid square cross-section.

    Returns
    -------
    Ix, "Square", c, a, y_array, section_dims
    section_dims keys: type, side
    """
    try:
        print_header("SQUARE PROFILE")
        display_cross_section("Square")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        a = float(input(colored("│ Side length a: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(a=a)

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    c        = a / 2.0
    Ix_total = a**4 / 12.0
    A        = a**2
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = a/2)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Side length a:                     {a / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Diagonal length a√2:               {a*1.4142 / len_div:.4f} {len_unit}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {'type': 'Square', 'side': a}
    return Ix_total, "Square", c, a, y_array, section_dims


def inertia_moment_hollow_square(units=None):
    """
    Hollow square cross-section (square tube).

    Returns
    -------
    Ix, "Hollow Square", c, outer_width, y_array, section_dims
    section_dims keys: type, outer_width, inner_width, t_wall
    """
    try:
        print_header("HOLLOW SQUARE PROFILE")
        display_cross_section("Hollow Square")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_width = float(input(colored("│ Outer side length B: ", 'cyan')))
        inner_width = float(input(colored("│ Inner side length b: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(outer_width=outer_width, inner_width=inner_width)
        if inner_width >= outer_width:
            raise SectionGeometryError("Inner side length must be strictly less than outer side length.")

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    t_wall   = (outer_width - inner_width) / 2.0
    c        = outer_width / 2.0
    Ix_total = (outer_width**4 - inner_width**4) / 12.0
    A        = outer_width**2 - inner_width**2
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = B/2)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Outer side length B:               {outer_width / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Inner side length b:               {inner_width / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Wall thickness t = (B-b)/2:        {t_wall / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Side ratio b/B:                    {inner_width/outer_width:.4f}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {
        'type': 'Hollow Square',
        'outer_width': outer_width, 'inner_width': inner_width, 't_wall': t_wall,
    }
    return Ix_total, "Hollow Square", c, outer_width, y_array, section_dims


def inertia_moment_hollow_rectangle(units=None):
    """
    Hollow rectangular cross-section (rectangular tube).

    Returns
    -------
    Ix, "Hollow Rectangle", c, outer_b, y_array, section_dims
    section_dims keys: type, outer_b, outer_h, inner_b, inner_h, t_flange, t_web
    """
    try:
        print_header("HOLLOW RECTANGULAR PROFILE")
        display_cross_section("Hollow Rectangle")

        print(colored("┌─ ENTER DIMENSIONS (in meters) " + "─"*32, 'yellow', attrs=['bold']))
        print(colored("│", 'yellow'))
        outer_b = float(input(colored("│ Outer width  B: ", 'cyan')))
        outer_h = float(input(colored("│ Outer height H: ", 'cyan')))
        inner_b = float(input(colored("│ Inner width  b: ", 'cyan')))
        inner_h = float(input(colored("│ Inner height h: ", 'cyan')))
        print(colored("│", 'yellow'))
        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        _validate_positive(outer_b=outer_b, outer_h=outer_h, inner_b=inner_b, inner_h=inner_h)
        if inner_b >= outer_b:
            raise SectionGeometryError("Inner width b must be strictly less than outer width B.")
        if inner_h >= outer_h:
            raise SectionGeometryError("Inner height h must be strictly less than outer height H.")

    except (SectionGeometryError, ValueError, TypeError, EOFError) as e:
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                          ERROR                               ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print(colored(f"  {e}", 'red'))
        return None

    c        = outer_h / 2.0
    t_flange = (outer_h - inner_h) / 2.0   # top/bottom wall thickness
    t_web    = (outer_b - inner_b) / 2.0   # side wall thickness
    I_outer  = outer_b * outer_h**3 / 12.0
    I_inner  = inner_b * inner_h**3 / 12.0
    Ix_total = I_outer - I_inner
    A        = outer_b * outer_h - inner_b * inner_h
    y_array  = np.linspace(-c, c, 10001)

    len_div, i_div, len_unit, i_unit = get_moi_scale(units)

    print_result("MOMENT OF INERTIA", Ix_total / i_div, i_unit, precision=6, color='green')
    print_result("NEUTRAL AXIS DISTANCE (c = H/2)", c / len_div, len_unit, precision=4, color='yellow')

    print(colored("┌─ CROSS-SECTION PARAMETERS " + "─"*35, 'blue', attrs=['bold']))
    print(colored(f"│ Outer width  B:                    {outer_b / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Outer height H:                    {outer_h / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Inner width  b:                    {inner_b / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Inner height h:                    {inner_h / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Top/bottom wall thickness t_f:     {t_flange / len_div:.4f} {len_unit}", 'blue'))
    print(colored(f"│ Side wall thickness t_w:           {t_web / len_div:.4f} {len_unit}", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    print("")

    print_derived_properties(Ix_total, c, A, units)

    section_dims = {
        'type': 'Hollow Rectangle',
        'outer_b': outer_b, 'outer_h': outer_h,
        'inner_b': inner_b, 'inner_h': inner_h,
        't_flange': t_flange, 't_web': t_web,
    }
    return Ix_total, "Hollow Rectangle", c, outer_b, y_array, section_dims

def load_section_from_library(entry: dict) -> tuple:
    """
    Convert a sections_database entry into the standard MOI 6-tuple.
    Returns (Ix, shape_name, c, b_rep, y_array, section_dims) or None on error.
    """
    try:
        Ix    = float(entry["Ix"])
        shape = entry["shape"]
        c     = float(entry["c"])
        b_rep = float(entry.get("tw", entry.get("outer_b", entry.get("diameter", c*2))))
        y_array = np.linspace(-c, c, 10001)
        section_dims = entry.get("section_dims", {})
        return Ix, shape, c, b_rep, y_array, section_dims
    except (KeyError, TypeError, ValueError) as e:
        print(colored(f"Error loading section data: {e}", 'red'))
        return None   