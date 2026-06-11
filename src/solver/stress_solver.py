import numpy as np
from scipy.integrate import cumulative_trapezoid

def calculate_beam_deflection(x_field, bending_moment, elastic_modulus, moment_of_inertia):
    """
    Calculate beam deflection using the double integration of the bending moment equation.
    
    Parameters:
    -----------
    x_field : numpy.ndarray
        Array of x coordinates along the beam length.
    bending_moment : numpy.ndarray
        Array of bending moment values corresponding to x_field positions.
    elastic_modulus : float
        Young's modulus of the beam material in Pa.
    moment_of_inertia : float
        Moment of inertia of the beam cross-section in m^4.
    
    Returns:
    --------
    deflection : numpy.ndarray
        Array of deflection values along the beam length.
    slope : numpy.ndarray
        Array of slope values along the beam length.
    curvature : numpy.ndarray
        Array of curvature values along the beam length.
    """
    # Calculate curvature: M/(EI)
    curvature = bending_moment / (elastic_modulus * moment_of_inertia)
    
    # Calculate slope by integrating curvature (first integration)
    # We use cumulative trapezoidal integration
    slope = cumulative_trapezoid(curvature, x_field, initial=0)
    
    # Apply boundary conditions for slope
    # For a simply supported beam, slope at supports is not zero
    # We need to apply corrections based on support conditions
    
    # Calculate deflection by integrating slope (second integration)
    deflection = cumulative_trapezoid(slope, x_field, initial=0)
    
    # Apply boundary conditions for deflection
    # For a simply supported beam, deflection at supports should be zero
    # Find indices closest to support positions (assuming support positions are in the data)
    # This implementation assumes a simply supported beam with supports at the ends
    # In a real application, you would adjust based on actual support positions
    
    # Apply zero deflection at x=0 (already satisfied by initial=0 in cumtrapz)
    # Apply zero deflection at x=beam_length
    # Simple linear correction to enforce boundary conditions
    correction = deflection[-1] * (x_field / x_field[-1])
    deflection = deflection - correction
    
    return deflection, slope, curvature

def first_moment_of_area_rect(width, y_array):
    """
    Calculate the first moment of area (Q) for a rectangular cross-section.
    
    Parameters:
    -----------
    width : float
        Width of the rectangular section in m.
    y_array : numpy.ndarray
        Array of y coordinates for evaluation points.
    
    Returns:
    --------
    Q_array : numpy.ndarray
        First moment of area at each evaluation point.
    """
    # For a rectangular section, Q = A' * y'
    # where A' is the area of the portion above or below the point of interest
    # and y' is the distance from the neutral axis to the centroid of A'
    
    Q_array = np.zeros_like(y_array)
    
    for i, y in enumerate(y_array):
        # Calculate the area above the point of interest
        A_prime = width * (y_array[-1] - y)
        # Calculate the distance from the neutral axis to the centroid of A'
        y_prime = (y_array[-1] + y) / 2 - y
        # Calculate Q = A' * y'
        Q_array[i] = A_prime * y_prime
    
    return Q_array

def calculate_shear_stress(shear_force, first_moment_area, moment_of_inertia, width):
    """
    Calculate shear stress using the formula τ = VQ/(Ib).
    
    Parameters:
    -----------
    shear_force : numpy.ndarray
        Array of shear force values along the beam length.
    first_moment_area : numpy.ndarray
        Array of first moment of area values.
    moment_of_inertia : float
        Moment of inertia of the beam cross-section.
    width : float
        Width of the section at the point of interest.
    
    Returns:
    --------
    shear_stress : numpy.ndarray
        Array of shear stress values along the beam length.
    """
    # Calculate shear stress using the formula τ = VQ/(Ib)
    # We calculate a separate stress value for each point in the shear_force array
    
    # Reshape arrays for broadcasting
    V = shear_force.reshape(-1, 1)  # Column vector
    Q = first_moment_area.reshape(1, -1)  # Row vector
    
    # Calculate shear stress matrix (each row is a position along beam, each column is a position in cross-section)
    shear_stress = (V @ Q) / (moment_of_inertia * width)
    
    return shear_stress

def calculate_bending_stress(bending_moment, c, moment_of_inertia):
    """
    Calculate bending stress using the formula σ = Mc/I.
    
    Parameters:
    -----------
    bending_moment : numpy.ndarray
        Array of bending moment values along the beam length.
    c : float
        Distance from neutral axis to extreme fiber.
    moment_of_inertia : float
        Moment of inertia of the beam cross-section.
    
    Returns:
    --------
    bending_stress : numpy.ndarray
        Array of bending stress values along the beam length.
    """
    # Calculate bending stress using the formula σ = Mc/I
    bending_stress = bending_moment * c / moment_of_inertia
    
    return bending_stress

def Factor_of_Safety(bending_moment, c, yield_strength, moment_of_inertia):
    """
    Calculate factor of safety with respect to yielding.
    
    Parameters:
    -----------
    bending_moment : numpy.ndarray
        Array of bending moment values along the beam length.
    c : float
        Distance from neutral axis to extreme fiber.
    yield_strength : float
        Yield strength of the material in Pa.
    moment_of_inertia : float
        Moment of inertia of the beam cross-section.
    
    Returns:
    --------
    FOS : float
        Minimum factor of safety along the beam.
    """
    # Calculate maximum bending stress
    max_bending_stress = np.max(np.abs(bending_moment)) * c / moment_of_inertia
    
    # Calculate factor of safety
    FOS = yield_strength / max_bending_stress

    
    return FOS