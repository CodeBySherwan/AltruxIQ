import numpy as np
from scipy.integrate import cumulative_trapezoid

# ---------------------------------------------------------------------------
# BUG-09 FIX: Exact Section Geometry Functions
# ---------------------------------------------------------------------------

def width_array_for_section(shape, section_dims, y_array):
    """
    Constructs a 1D array representing the exact width b(y) at every height y.
    Handles I-beams, T-beams, circular, and hollow profiles accurately.
    """
    b_array = np.zeros_like(y_array)
    
    if shape == "I-beam":
        hw = section_dims['hw']
        bf = section_dims['bf']
        tw = section_dims['tw']
        H  = section_dims['H']
        
        # Using 1e-9 tolerance to prevent floating point boundary misses
        in_web = np.abs(y_array) <= (hw / 2.0) + 1e-9
        in_section = np.abs(y_array) <= (H / 2.0) + 1e-9
        
        b_array = np.where(in_web, tw, bf)
        b_array = np.where(in_section, b_array, 0.0)

    elif shape == "T-beam":
        bf = section_dims['bf']
        tw = section_dims['tw']
        tf = section_dims['tf']
        c_top = section_dims['c_top']
        c_bot = section_dims['c_bot']
        
        in_flange = (y_array >= (c_top - tf - 1e-9)) & (y_array <= c_top + 1e-9)
        in_web = (y_array >= -c_bot - 1e-9) & (y_array < (c_top - tf - 1e-9))
        
        b_array = np.where(in_flange, bf, np.where(in_web, tw, 0.0))

    elif shape in ("Circle", "Solid Circle"):
        r = section_dims['radius']
        val = r**2 - y_array**2
        val = np.maximum(val, 0) # Prevent negative square roots
        b_array = 2.0 * np.sqrt(val)

    elif shape == "Hollow Circle":
        ro = section_dims['r_outer']
        ri = section_dims['r_inner']
        
        val_o = ro**2 - y_array**2
        val_o = np.maximum(val_o, 0)
        b_outer = 2.0 * np.sqrt(val_o)
        
        val_i = ri**2 - y_array**2
        val_i = np.maximum(val_i, 0)
        b_inner = 2.0 * np.sqrt(val_i)
        
        b_array = b_outer - b_inner

    elif shape in ("Rectangle", "Square"):
        width = section_dims.get('width', section_dims.get('side'))
        height = section_dims.get('height', section_dims.get('side'))
        c = height / 2.0
        
        b_array = np.full_like(y_array, width)
        b_array = np.where(np.abs(y_array) <= c + 1e-9, b_array, 0.0)

    elif shape == "Hollow Square":
        B = section_dims['outer_width']
        b_inner = section_dims['inner_width']
        c = B / 2.0
        c_inner = b_inner / 2.0
        
        in_web = np.abs(y_array) <= c_inner + 1e-9
        in_section = np.abs(y_array) <= c + 1e-9
        
        b_array = np.where(in_web, B - b_inner, B)
        b_array = np.where(in_section, b_array, 0.0)

    elif shape == "Hollow Rectangle":
        outer_b = section_dims['outer_b']
        inner_b = section_dims['inner_b']
        outer_h = section_dims['outer_h']
        inner_h = section_dims['inner_h']
        
        c = outer_h / 2.0
        c_inner = inner_h / 2.0
        
        in_web = np.abs(y_array) <= c_inner + 1e-9
        in_section = np.abs(y_array) <= c + 1e-9
        
        b_array = np.where(in_web, outer_b - inner_b, outer_b)
        b_array = np.where(in_section, b_array, 0.0)

    else:
        # Fallback 
        b_array = np.ones_like(y_array) * section_dims.get('b', 1.0)
        
    return b_array

def first_moment_of_area_general(b_array, y_array):
    """
    Computes the first moment of area Q(y) exact for any section via numerical integration.
    """
    integrand = b_array * y_array
    
    # Integrating from bottom (-c) upwards. 
    # Because the first moment of area about the NA over the entire cross-section is 0,
    # Q(y) evaluated from the top down is equal to the negative integral from the bottom up.
    integral_bottom_up = cumulative_trapezoid(integrand, y_array, initial=0)
    
    Q_array = -integral_bottom_up
    
    # Eliminate tiny negative floating point inaccuracies
    Q_array[Q_array < 0] = 0.0
    
    return Q_array

def first_moment_of_area_rect(b, h, y_array):
    """
    Legacy fallback function for basic rectangular cross-sections.
    """
    c = h / 2.0
    Q = (b / 2.0) * (c**2 - y_array**2)
    Q[Q < 0] = 0.0
    return Q


# ---------------------------------------------------------------------------
# Standard Post-Processing Engines
# ---------------------------------------------------------------------------

def calculate_beam_deflection(x_field, bending_moment, elastic_modulus, moment_of_inertia):
    """
    Calculate beam deflection using the double integration of the bending moment equation.
    """
    # Calculate curvature: M/(EI)
    curvature = bending_moment / (elastic_modulus * moment_of_inertia)
    
    # Calculate slope by integrating curvature (first integration)
    slope = cumulative_trapezoid(curvature, x_field, initial=0)
    
    # Calculate deflection by integrating slope (second integration)
    deflection = cumulative_trapezoid(slope, x_field, initial=0)
    
    return deflection, slope, curvature

def calculate_shear_stress(shear_force, Q_array, moment_of_inertia, b):
    """
    Calculate shear stress distribution across the beam length and height.
    """
    V = shear_force.reshape(-1, 1)
    Q = Q_array.reshape(1, -1)
    
    if isinstance(b, np.ndarray):
        b = b.reshape(1, -1)
        
    # Safely handle division to prevent RuntimeWarnings where width b is 0
    with np.errstate(divide='ignore', invalid='ignore'):
        shear_stress = (V @ Q) / (moment_of_inertia * b)
        # Force stress to 0 in regions where the material width is 0
        shear_stress = np.where(b == 0, 0.0, shear_stress)
        shear_stress = np.nan_to_num(shear_stress)
    
    return shear_stress

def Bending_Stress(bending_moment, c, moment_of_inertia):
    """
    Calculate bending stress using the formula σ = Mc/I.
    """
    bending_stress = bending_moment * c / moment_of_inertia
    return bending_stress

def calculate_bending_stress(bending_moment, c, moment_of_inertia):
    """
    Duplicate wrapper to handle naming convention variations in cli.py
    """
    return Bending_Stress(bending_moment, c, moment_of_inertia)

def Factor_of_Safety(bending_moment, c, yield_strength, moment_of_inertia):
    """
    Calculate factor of safety with respect to yielding.
    """
    max_bending_stress = np.max(np.abs(bending_moment)) * c / moment_of_inertia
    FOS = yield_strength / max_bending_stress
    return FOS