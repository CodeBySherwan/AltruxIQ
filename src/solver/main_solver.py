# --------------------------------------------------------------------------------
#           Libraries
# --------------------------------------------------------------------------------
import numpy as np

# --------------------------------------------------------------------------------
#         Solver Initialization Functions
# --------------------------------------------------------------------------------
def initialize_solver(beam_length, divisions=10000):
    """
    Initialize the solver with beam length and number of divisions.
    """
    Delta = beam_length / divisions
    X_Field = np.arange(0, beam_length + Delta, Delta)  # Discretized beam length
    return X_Field, Delta

def initialize_containers(X_Field):
    """
    Initialize containers for storing results during calculations.
    """
    Reactions = np.array([0.0, 0.0, 0.0])  # [Va, Ha, Vb]
    ShearForce_Recorder = np.zeros(len(X_Field))
    BendingMoment_Recorder = np.zeros(len(X_Field))
    return Reactions, ShearForce_Recorder, BendingMoment_Recorder

# --------------------------------------------------------------------------------
#         Simple Beam Reaction Solver
# --------------------------------------------------------------------------------
def calculate_all_reactions(A, B, pointloads, momentloads, distributedloads, triangleloads):
    """
    Calculate reactions at supports due to all types of loads simultaneously.
    Handles:
    - Point Loads (pointloads)
    - Point Moments (momentloads)
    - Uniform Distributed Loads (distributedloads)
    - Triangular Distributed Loads (triangleloads)
    
    Sign Convention:
    - Positive vertical forces act downward
    - Positive horizontal forces act to the right
    - Positive moments act counter-clockwise
    """
    Va, Vb, Ha = 0, 0, 0  # Initialize reactions (vertical, horizontal, and moment)

    # Point Loads
    if pointloads.shape[0] > 0:
        for n in range(pointloads.shape[0]):
            Xp, Fx, Fy = pointloads[n]
            Vb += Fy * (A - Xp) / (B - A)
            Va += -Fy - (Fy * (A - Xp) / (B - A))
            Ha += Fx

    # Point Moments
    if momentloads.shape[0] > 0:
        for n in range(momentloads.shape[0]):
            Xm, m = momentloads[n]
            Vb += m / (B - A)
            Va += -m / (B - A)

    # Uniform Distributed Loads (UDL)
    if distributedloads.shape[0] > 0:
        for n in range(distributedloads.shape[0]):
            Xstart, Xend, Fy = distributedloads[n]
            Fy_res = Fy * (Xend - Xstart)
            X_res = Xstart + 0.5 * (Xend - Xstart)
            Vb += Fy_res * (A - X_res) / (B - A)
            Va += -Fy_res - (Fy_res * (A - X_res) / (B - A))

    # Triangular Distributed Loads (TRL)
    if triangleloads.shape[0] > 0:
        for n in range(triangleloads.shape[0]):
            Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
            if abs(Fy_start) > 0:
                Fy_res = 0.5 * Fy_start * (Xend - Xstart)
                X_res = Xstart + (1/3) * (Xend - Xstart)
            else:
                Fy_res = 0.5 * Fy_end * (Xend - Xstart)
                X_res = Xstart + (2/3) * (Xend - Xstart)
            Vb += Fy_res * (A - X_res) / (B - A)
            Va += -Fy_res - (Fy_res * (A - X_res) / (B - A))

    return Va, Vb, Ha  # Fixed: Return statement moved outside the loop

# --------------------------------------------------------------------------------
#         cantilever Beam Reaction Solver
# --------------------------------------------------------------------------------
def Calculate_Cantilever_Reactions(pointloads, momentloads, distributedloads, triangleloads):
    """
    Calculate reactions at the fixed support of a cantilever beam.
    
    Sign Convention:
    - Positive vertical forces act upwards (negative downwards)
    - Positive horizontal forces act to the right
    - Positive moments act counterclockwise (negative clockwise)
    """
    Va, Ha, Ma = 0, 0, 0

    # Point Loads
    if pointloads.shape[0] > 0:
        for n in range(pointloads.shape[0]):
            Xp, Fx, Fy = pointloads[n]
            # For equilibrium, reaction force is opposite direction of applied force
            Va -= Fy  # Vertical reaction
            Ha -= Fx  # Horizontal reaction
            # For equilibrium, reaction moment counteracts force*lever_arm
            # Assuming Fy positive is upward, and lever arm is Xp
            Ma -= Fy * Xp  # Moment due to vertical force
            Ma -= Fx * 0  # No moment from horizontal force at neutral axis

    # Point Moments
    if momentloads.shape[0] > 0:
        for n in range(momentloads.shape[0]):
            Xm, M = momentloads[n]
            # For equilibrium, reaction moment is opposite of applied moment
            Ma -= M  # Assuming M positive is counterclockwise

    # Uniform Distributed Loads (UDL)
    if distributedloads.shape[0] > 0:
        for n in range(distributedloads.shape[0]):
            Xstart, Xend, Fy = distributedloads[n]
            # Total force is intensity * length
            total_force = Fy * (Xend - Xstart)
            # Centroid of the distributed load is at the middle
            centroid = (Xstart + Xend) / 2
            # Vertical reaction
            Va -= total_force
            # Moment reaction
            Ma -= total_force * centroid

    if triangleloads.shape[0] > 0:
        for n in range(triangleloads.shape[0]):
            Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
            # Calculate total force of triangular load
            # For a triangular load, total force = average intensity * length
            avg_intensity = (Fy_start + Fy_end) / 2
            length = Xend - Xstart
            total_force = avg_intensity * length
            
            # Calculate centroid position
            # For a trapezoidal load:
            # If Fy_start and Fy_end are both non-zero (trapezoid)
            if abs(Fy_start) > 0 and abs(Fy_end) > 0:
                # Centroid formula for a trapezoid
                h1, h2 = abs(Fy_start), abs(Fy_end)
                centroid_offset = length * (h1 + 2*h2) / (3 * (h1 + h2))
                if abs(Fy_start) > abs(Fy_end):
                    # Larger at start
                    centroid = Xstart + centroid_offset
                else:
                    # Larger at end
                    centroid = Xend - centroid_offset
            # If one end is zero (triangle)
            elif abs(Fy_start) > 0:
                # Triangle with max at start - centroid at 1/3 from start
                centroid = Xstart + length/3
            elif abs(Fy_end) > 0:
                # Triangle with max at end - centroid at 2/3 from start
                centroid = Xstart + 2*length/3
            else:
                # Both zero (shouldn't happen)
                centroid = (Xstart + Xend) / 2
            
            # Add to reactions
            Va -= total_force
            Ma -= total_force * centroid

    return Va, Ha, Ma

# --------------------------------------------------------------------------------
#         Simple Beam Shear Force and Bending Moment Solver
# --------------------------------------------------------------------------------
def calculate_sf_bm(X_Field, A, B, pointloads, momentloads, distributedloads, triangleloads, reactions):
    """
    Calculate Shear Force and Bending Moment at every point along the beam.
    Handles:
    - Point Loads (pointloads)
    - Point Moments (momentloads)
    - Uniform Distributed Loads (distributedloads)
    - Triangular Distributed Loads (triangleloads)

    Returns:
    - Total Shear Force and Bending Moment arrays
    
    Sign Convention:
    - Positive shear force causes clockwise rotation
    - Positive bending moment causes compression in the top fibers
    """
    Va, Vb, Ha  = reactions  # Reactions from supports
    ShearForce = np.zeros(len(X_Field))  # Initialize SF array
    BendingMoment = np.zeros(len(X_Field))  # Initialize BM array

    for i, x in enumerate(X_Field):
        shear = 0
        moment = 0

        # Reaction Forces
        if x > A:
            shear += Va
            moment -= Va * (x - A)
        if x > B:
            shear += Vb
            moment -= Vb * (x - B)

        # Point Loads
        if pointloads.shape[0] > 0:
            for n in range(pointloads.shape[0]):
                Xp, Fx, Fy = pointloads[n]
                if x > Xp:
                    shear += Fy
                    moment -= Fy * (x - Xp)

        # Point Moments
        if momentloads.shape[0] > 0:
            for n in range(momentloads.shape[0]):
                Xm, m = momentloads[n]
                if x > Xm:
                    moment -= m

        # Uniform Distributed Loads (UDL)
        if distributedloads.shape[0] > 0:
            for n in range(distributedloads.shape[0]):
                Xstart, Xend, Fy = distributedloads[n]
                if Xstart < x <= Xend:
                    shear += Fy * (x - Xstart)
                    moment -= Fy * (x - Xstart) * 0.5 * (x - Xstart)
                elif x > Xend:
                    shear += Fy * (Xend - Xstart)
                    moment -= Fy * (Xend - Xstart) * (x - Xstart - 0.5 * (Xend - Xstart))

        # Triangular Distributed Loads (TRL)
        if triangleloads.shape[0] > 0:
            for n in range(triangleloads.shape[0]):
                Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
                if Xstart < x <= Xend:
                    if abs(Fy_start) > 0:
                        Xbase = x - Xstart
                        F_cut = Fy_start - Xbase * (Fy_start / (Xend - Xstart))
                        R1 = 0.5 * Xbase * (Fy_start - F_cut)
                        R2 = Xbase * F_cut
                        shear += R1 + R2
                        moment -= R1 * (2 / 3) * Xbase + R2 * 0.5 * Xbase
                    else:
                        Xbase = x - Xstart
                        F_cut = Fy_end * (Xbase / (Xend - Xstart))
                        R = 0.5 * Xbase * F_cut
                        shear += R
                        moment -= R * (1 / 3) * Xbase
                elif x > Xend:
                    if abs(Fy_start) > 0:
                        R = 0.5 * Fy_start * (Xend - Xstart)
                        Xr = Xstart + (1 / 3) * (Xend - Xstart)
                        shear += R
                        moment -= R * (x - Xr)
                    else:
                        R = 0.5 * Fy_end * (Xend - Xstart)
                        Xr = Xstart + (2 / 3) * (Xend - Xstart)
                        shear += R
                        moment -= R * (x - Xr)

        # Store results
        ShearForce[i] = shear
        BendingMoment[i] = moment

    return ShearForce, -BendingMoment

# --------------------------------------------------------------------------------
#         cantilever Beam Shear Force and Bending Moment Solver
# --------------------------------------------------------------------------------
def Calculate_SF_BM_Cantilever(X_Field, Va, Ha, Ma, pointloads, momentloads, distributedloads, triangleloads):
    """
    Calculate Shear Force and Bending Moment for a cantilever beam.
    
    Sign Convention:
    - Positive vertical forces act upwards (negative downwards)
    - Positive moments act counterclockwise (negative clockwise)
    - Fixed support is at X=0
    """
    ShearForce = np.zeros(len(X_Field))
    BendingMoment = np.zeros(len(X_Field))
    beam_length = X_Field[-1]  # Get beam length from the last X value

    # For cantilever beam, we'll use a right-to-left analysis approach
    # This better matches the physical behavior and calculation approach shown in your PDF
    
    # Initialize at free end (right)
    # For each section from right to left
    for i, x in enumerate(X_Field):
        shear = 0
        moment = 0
        
        # Point Loads - contributions from all point loads right of position x
        if pointloads.shape[0] > 0:
            for n in range(pointloads.shape[0]):
                Xp, Fx, Fy = pointloads[n]
                # If the point load is to the right of our current position
                if Xp > x:
                    # Force is negative when acting downward
                    shear -= Fy  # Add to shear in appropriate direction
                    moment -= Fy * (Xp - x)  # Add moment contribution
        
        # Distributed Loads - partial contributions as needed
        if distributedloads.shape[0] > 0:
            for n in range(distributedloads.shape[0]):
                Xstart, Xend, Fy = distributedloads[n]
                # Only consider portions of UDL to the right of current position
                if Xend > x:
                    start_pos = max(x, Xstart)  # Start from either x or load start
                    load_length = Xend - start_pos
                    load_total = Fy * load_length
                    load_centroid = start_pos + load_length/2
                    shear -= load_total
                    moment -= load_total * (load_centroid - x)
        
        # Moment Loads - contributions from all moment loads right of position x
        if momentloads.shape[0] > 0:
            for n in range(momentloads.shape[0]):
                Xm, M = momentloads[n]
                if Xm > x:
                    moment -= M  # Add moment directly (assuming CCW positive)
        

    
        # Triangular Distributed Loads (TRL)
        if triangleloads.shape[0] > 0:
            for n in range(triangleloads.shape[0]):
                Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
                
                # Only consider portions of triangular load to the right of current position
                if Xend > x:
                    start_pos = max(x, Xstart)
                    
                    # If fully to the right of x
                    if start_pos == x:
                        # Calculate the intensity at position x using linear interpolation
                        t = (x - Xstart) / (Xend - Xstart) if Xend > Xstart else 0
                        Fy_at_x = Fy_start + t * (Fy_end - Fy_start)
                        
                        # Calculate remaining triangular load properties
                        remaining_length = Xend - x
                        
                        # For the part of the load to the right of x
                        # We need to treat this as a trapezoid from x to Xend
                        avg_intensity = (Fy_at_x + Fy_end) / 2
                        total_force = avg_intensity * remaining_length
                        
                        # Calculate centroid position of the remaining part
                        if abs(Fy_at_x) > 0 and abs(Fy_end) > 0:
                            # Centroid formula for a trapezoid
                            h1, h2 = abs(Fy_at_x), abs(Fy_end)
                            centroid_offset = remaining_length * (h1 + 2*h2) / (3 * (h1 + h2))
                            if abs(Fy_at_x) > abs(Fy_end):
                                # Larger at current position
                                centroid = x + centroid_offset
                            else:
                                # Larger at end
                                centroid = Xend - centroid_offset
                        elif abs(Fy_at_x) > 0:
                            # Triangle with max at current position
                            centroid = x + remaining_length/3
                        elif abs(Fy_end) > 0:
                            # Triangle with max at end
                            centroid = x + 2*remaining_length/3
                        else:
                            # Both zero (shouldn't happen)
                            centroid = (x + Xend) / 2
                            
                        # Add to shear and moment
                        shear -= total_force
                        moment -= total_force * (centroid - x)

        # Store calculated values
        ShearForce[i] = shear
        BendingMoment[i] = moment
    
    # Calculate fixed-end reactions to ensure equilibrium
    # These should match the calculated Va, Ha, Ma
    BendingMoment[0] = Ma  # Fixed-end moment

    return ShearForce, BendingMoment

# --------------------------------------------------------------------------------
#         High-Level Solver
# --------------------------------------------------------------------------------
def solve_simple_beam(beam_length, A=None, B=None,
                      pointloads_in=None, distributedloads_in=None,
                      momentloads_in=None, triangleloads_in=None,
                      beam_type="Simple"):
    """
    High-level function to solve a beam completely.
    Supports simple beams (with two supports) and cantilever beams.

    Parameters:
        beam_length : float : Length of the beam
        A, B        : float : Support positions (only for simple beams)
        beam_type   : str   : "simple" or "cantilever"
        
    Returns:
        X_Field     : ndarray : Beam position points
        ShearForce  : ndarray : Shear force values along the beam
        BendingMoment : ndarray : Bending moment values along the beam
        Reactions   : ndarray : Support reactions [Va, Ha, Vb/Ma]
    """
    if pointloads_in is None:
        pointloads = np.empty((0, 3))
    else:
        pointloads = np.array(pointloads_in)

    if distributedloads_in is None:
        distributedloads = np.empty((0, 3))
    else:
        distributedloads = np.array(distributedloads_in)

    if momentloads_in is None:
        momentloads = np.empty((0, 2))
    else:
        momentloads = np.array(momentloads_in)

    if triangleloads_in is None:
        triangleloads = np.empty((0, 4))
    else:
        triangleloads = np.array(triangleloads_in)

    # Initialize Solver
    X_Field, Delta = initialize_solver(beam_length)

    if beam_type == "Simple":
        # Ensure supports are defined for simple beam
        if A is None or B is None:
            raise ValueError("Support positions A and B must be provided for simple beam")
            
        # Solve Reactions
        Reactions = calculate_all_reactions(A, B, pointloads, momentloads, 
                                           distributedloads, triangleloads)
        
        # Solve SF and BM
        Total_ShearForce, Total_BendingMoment = calculate_sf_bm(
            X_Field, A, B, pointloads, momentloads, 
            distributedloads, triangleloads, Reactions)
            
        # Fixed: Add return statement for simple beam
        return X_Field, Total_ShearForce, Total_BendingMoment, Reactions

    elif beam_type == "Cantilever":
        # --- Solve Reactions ---
        Va,Ma,Ha = Calculate_Cantilever_Reactions(
            pointloads, momentloads, distributedloads, triangleloads)

        # --- Solve Shear Force and Bending Moment ---
        Total_ShearForce, Total_BendingMoment = Calculate_SF_BM_Cantilever(
            X_Field, Va,Ma, Ha , pointloads, momentloads, 
            distributedloads, triangleloads)

        Reactions = np.array([Va,Ma,Ha])
        return X_Field, Total_ShearForce, Total_BendingMoment, Reactions

    else:
        raise ValueError("Invalid beam_type. Choose 'simple' or 'cantilever'.")

def solve_cantilever_beam(beam_length, pointloads_in=None, distributedloads_in=None, 
                         momentloads_in=None, triangleloads_in=None):
    """
    High-level function to solve a cantilever beam completely.
    
    Sign Convention:
    - Positive vertical forces act upwards
    - Positive horizontal forces act to the right
    - Positive moments act counterclockwise
    - Fixed support is at X=0
    
    Parameters:
    -----------
    beam_length : float
        Length of the beam
    pointloads_in, distributedloads_in, momentloads_in, triangleloads_in : list
        Lists containing various load data
        
    Returns:
    --------
    X_Field : numpy.ndarray
        Beam position points
    ShearForce : numpy.ndarray
        Shear force values along the beam
    BendingMoment : numpy.ndarray
        Bending moment values along the beam
    Reactions : numpy.ndarray
        Support reactions [Va, Ha, Ma]
    """
    # Convert input lists to numpy arrays
    if pointloads_in is None:
        pointloads = np.empty((0, 3))
    else:
        pointloads = np.array(pointloads_in)

    if distributedloads_in is None:
        distributedloads = np.empty((0, 3))
    else:
        distributedloads = np.array(distributedloads_in)

    if momentloads_in is None:
        momentloads = np.empty((0, 2))
    else:
        momentloads = np.array(momentloads_in)

    if triangleloads_in is None:
        triangleloads = np.empty((0, 4))
    else:
        triangleloads = np.array(triangleloads_in)

    # Initialize solver with beam discretization
    Delta = beam_length / 10000  # Use 10000 divisions for accuracy
    X_Field = np.arange(0, beam_length + Delta, Delta)  # Discretized beam length

    # Calculate reactions at the fixed support
    Va, Ha, Ma = Calculate_Cantilever_Reactions(
        pointloads, momentloads, distributedloads, triangleloads)

    # Calculate shear force and bending moment diagrams
    ShearForce, BendingMoment = Calculate_SF_BM_Cantilever(
        X_Field, Va, Ha, Ma, pointloads, momentloads, 
        distributedloads, triangleloads)
    CorrectedBendingMoment = -BendingMoment
    # Pack reactions into an array
    Reactions = np.array([Va, Ha, Ma])
    
    return X_Field, ShearForce, CorrectedBendingMoment, Reactions