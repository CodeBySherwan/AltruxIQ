# --------------------------------------------------------------------------------
#           Libraries
# --------------------------------------------------------------------------------
# pyrefly: ignore [missing-import]
import numpy as np

# --------------------------------------------------------------------------------
#         Solver Initialization Functions
# --------------------------------------------------------------------------------
def initialize_solver(beam_length, divisions=10000):
    Delta = beam_length / divisions
    X_Field = np.arange(0, beam_length + Delta, Delta) 
    return X_Field, Delta

def initialize_containers(X_Field):
    Reactions = np.array([0.0, 0.0, 0.0])  # [Va, Ha, Vb]
    ShearForce_Recorder = np.zeros(len(X_Field))
    BendingMoment_Recorder = np.zeros(len(X_Field))
    return Reactions, ShearForce_Recorder, BendingMoment_Recorder

# --------------------------------------------------------------------------------
#         Simple Beam Reaction Solver
# --------------------------------------------------------------------------------
def calculate_all_reactions(A, B, pointloads, momentloads, distributedloads, triangleloads):
    Va, Vb, Ha = 0, 0, 0 

    # Point Loads
    if pointloads.shape[0] > 0:
        for n in range(pointloads.shape[0]):
            Xp, Fx, Fy = pointloads[n]
            Vb += Fy * (A - Xp) / (B - A)
            Va += -Fy - (Fy * (A - Xp) / (B - A))
            Ha += Fx

    # Point Moments (Fixed: CCW positive balancing)
    if momentloads.shape[0] > 0:
        for n in range(momentloads.shape[0]):
            Xm, m = momentloads[n]
            Vb += -m / (B - A)
            Va += m / (B - A)

    # Uniform Distributed Loads (UDL)
    if distributedloads.shape[0] > 0:
        for n in range(distributedloads.shape[0]):
            Xstart, Xend, Fy = distributedloads[n]
            Fy_res = Fy * (Xend - Xstart)
            X_res = Xstart + 0.5 * (Xend - Xstart)
            Vb += Fy_res * (A - X_res) / (B - A)
            Va += -Fy_res - (Fy_res * (A - X_res) / (B - A))

    # Triangular/Trapezoidal Distributed Loads (TRL) (Fixed: Generic Centroid)
    if triangleloads.shape[0] > 0:
        for n in range(triangleloads.shape[0]):
            Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
            length = Xend - Xstart
            Fy_res = 0.5 * (Fy_start + Fy_end) * length
            
            if abs(Fy_start + Fy_end) > 1e-9:
                X_res = Xstart + length * (Fy_start + 2*Fy_end) / (3 * (Fy_start + Fy_end))
            else:
                X_res = Xstart + length / 2.0
                
            Vb += Fy_res * (A - X_res) / (B - A)
            Va += -Fy_res - (Fy_res * (A - X_res) / (B - A))

    return Va, Vb, Ha

# --------------------------------------------------------------------------------
#         Cantilever Beam Reaction Solver
# --------------------------------------------------------------------------------
def Calculate_Cantilever_Reactions(pointloads, momentloads, distributedloads, triangleloads):
    Va, Ha, Ma = 0, 0, 0

    if pointloads.shape[0] > 0:
        for n in range(pointloads.shape[0]):
            Xp, Fx, Fy = pointloads[n]
            Va -= Fy  
            Ha -= Fx  
            Ma -= Fy * Xp  

    if momentloads.shape[0] > 0:
        for n in range(momentloads.shape[0]):
            Xm, M = momentloads[n]
            Ma -= M  

    if distributedloads.shape[0] > 0:
        for n in range(distributedloads.shape[0]):
            Xstart, Xend, Fy = distributedloads[n]
            total_force = Fy * (Xend - Xstart)
            centroid = (Xstart + Xend) / 2
            Va -= total_force
            Ma -= total_force * centroid

    # Triangular/Trapezoidal Loads (Fixed: Generic Centroid)
    if triangleloads.shape[0] > 0:
        for n in range(triangleloads.shape[0]):
            Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
            length = Xend - Xstart
            total_force = 0.5 * (Fy_start + Fy_end) * length
            
            if abs(Fy_start + Fy_end) > 1e-9:
                centroid = Xstart + length * (Fy_start + 2*Fy_end) / (3 * (Fy_start + Fy_end))
            else:
                centroid = Xstart + length / 2.0
            
            Va -= total_force
            Ma -= total_force * centroid

    return Va, Ha, Ma

# --------------------------------------------------------------------------------
#         Simple Beam Shear Force and Bending Moment Solver
# --------------------------------------------------------------------------------
def calculate_sf_bm(X_Field, A, B, pointloads, momentloads, distributedloads, triangleloads, reactions):
    Va, Vb, Ha = reactions
    ShearForce = np.zeros(len(X_Field))
    BendingMoment = np.zeros(len(X_Field))

    for i, x in enumerate(X_Field):
        shear = 0
        moment = 0

        if x > A:
            shear += Va
            moment -= Va * (x - A)
        if x > B:
            shear += Vb
            moment -= Vb * (x - B)

        if pointloads.shape[0] > 0:
            for n in range(pointloads.shape[0]):
                Xp, Fx, Fy = pointloads[n]
                if x > Xp:
                    shear += Fy
                    moment -= Fy * (x - Xp)

        if momentloads.shape[0] > 0:
            for n in range(momentloads.shape[0]):
                Xm, m = momentloads[n]
                if x > Xm:
                    moment -= m

        if distributedloads.shape[0] > 0:
            for n in range(distributedloads.shape[0]):
                Xstart, Xend, Fy = distributedloads[n]
                if Xstart < x <= Xend:
                    shear += Fy * (x - Xstart)
                    moment -= Fy * (x - Xstart) * 0.5 * (x - Xstart)
                elif x > Xend:
                    shear += Fy * (Xend - Xstart)
                    moment -= Fy * (Xend - Xstart) * (x - Xstart - 0.5 * (Xend - Xstart))

        # Triangular/Trapezoidal Loads (Fixed: Accurate interior cuts)
        if triangleloads.shape[0] > 0:
            for n in range(triangleloads.shape[0]):
                Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
                L_load = Xend - Xstart
                
                if Xstart < x <= Xend:
                    Xbase = x - Xstart
                    # Linearly interpolated intensity at x
                    F_cut = Fy_start + (Fy_end - Fy_start) * (Xbase / L_load)
                    
                    # Superposition of uniform and triangular components
                    R_rect = Fy_start * Xbase
                    M_rect = R_rect * (Xbase / 2.0)
                    
                    R_tri = 0.5 * (F_cut - Fy_start) * Xbase
                    M_tri = R_tri * (Xbase / 3.0) 
                    
                    shear += R_rect + R_tri
                    moment -= (M_rect + M_tri)
                    
                elif x > Xend:
                    R_tot = 0.5 * (Fy_start + Fy_end) * L_load
                    if abs(Fy_start + Fy_end) > 1e-9:
                        Xr = Xstart + L_load * (Fy_start + 2*Fy_end) / (3 * (Fy_start + Fy_end))
                    else:
                        Xr = Xstart + L_load / 2.0
                    
                    shear += R_tot
                    moment -= R_tot * (x - Xr)

        ShearForce[i] = shear
        BendingMoment[i] = moment

    # Fixed: Return standard BendingMoment directly (removes the `-` inversion bug)
    return ShearForce, BendingMoment

# --------------------------------------------------------------------------------
#         Cantilever Beam Shear Force and Bending Moment Solver
# --------------------------------------------------------------------------------
def Calculate_SF_BM_Cantilever(X_Field, Va, Ha, Ma, pointloads, momentloads, distributedloads, triangleloads):
    ShearForce = np.zeros(len(X_Field))
    BendingMoment = np.zeros(len(X_Field))
    
    for i, x in enumerate(X_Field):
        shear = 0
        moment = 0
        
        if pointloads.shape[0] > 0:
            for n in range(pointloads.shape[0]):
                Xp, Fx, Fy = pointloads[n]
                if Xp > x:
                    shear -= Fy  
                    moment -= Fy * (Xp - x)  
        
        if distributedloads.shape[0] > 0:
            for n in range(distributedloads.shape[0]):
                Xstart, Xend, Fy = distributedloads[n]
                if Xend > x:
                    start_pos = max(x, Xstart) 
                    load_length = Xend - start_pos
                    load_total = Fy * load_length
                    load_centroid = start_pos + load_length/2
                    shear -= load_total
                    moment -= load_total * (load_centroid - x)
        
        if momentloads.shape[0] > 0:
            for n in range(momentloads.shape[0]):
                Xm, M = momentloads[n]
                if Xm > x:
                    moment -= M  
        
        # Triangular/Trapezoidal Loads (Fixed: Valid Right-to-Left Cut)
        if triangleloads.shape[0] > 0:
            for n in range(triangleloads.shape[0]):
                Xstart, Xend, Fy_start, Fy_end = triangleloads[n]
                
                if Xend > x:
                    start_pos = max(x, Xstart)
                    if start_pos == x:
                        t = (x - Xstart) / (Xend - Xstart) if Xend > Xstart else 0
                        Fy_at_x = Fy_start + t * (Fy_end - Fy_start)
                        remaining_length = Xend - x
                        
                        total_force = 0.5 * (Fy_at_x + Fy_end) * remaining_length
                        
                        if abs(Fy_at_x + Fy_end) > 1e-9:
                            centroid = x + remaining_length * (Fy_at_x + 2*Fy_end) / (3 * (Fy_at_x + Fy_end))
                        else:
                            centroid = x + remaining_length / 2.0
                            
                        shear -= total_force
                        moment -= total_force * (centroid - x)

        ShearForce[i] = shear
        BendingMoment[i] = moment
    
    BendingMoment[0] = Ma 
    return ShearForce, BendingMoment

# --------------------------------------------------------------------------------
#         High-Level Solver
# --------------------------------------------------------------------------------
def solve_simple_beam(beam_length, A=None, B=None,
                      pointloads_in=None, distributedloads_in=None,
                      momentloads_in=None, triangleloads_in=None,
                      beam_type="Simple"):
    
    pointloads = np.array(pointloads_in) if pointloads_in is not None else np.empty((0, 3))
    distributedloads = np.array(distributedloads_in) if distributedloads_in is not None else np.empty((0, 3))
    momentloads = np.array(momentloads_in) if momentloads_in is not None else np.empty((0, 2))
    triangleloads = np.array(triangleloads_in) if triangleloads_in is not None else np.empty((0, 4))

    X_Field, Delta = initialize_solver(beam_length)

    if beam_type == "Simple":
        if A is None or B is None:
            raise ValueError("Support positions A and B must be provided for simple beam")
            
        Reactions = calculate_all_reactions(A, B, pointloads, momentloads, distributedloads, triangleloads)
        Total_ShearForce, Total_BendingMoment = calculate_sf_bm(
            X_Field, A, B, pointloads, momentloads, distributedloads, triangleloads, Reactions)
            
        return X_Field, Total_ShearForce, Total_BendingMoment, Reactions

    elif beam_type == "Cantilever":
        Va, Ha, Ma = Calculate_Cantilever_Reactions(pointloads, momentloads, distributedloads, triangleloads)
        Total_ShearForce, Total_BendingMoment = Calculate_SF_BM_Cantilever(
            X_Field, Va, Ha, Ma, pointloads, momentloads, distributedloads, triangleloads)

        Reactions = np.array([Va, Ha, Ma])
        # Bending is intentionally kept un-negated to match Cantilever conventions internally.
        return X_Field, Total_ShearForce, Total_BendingMoment, Reactions

    else:
        raise ValueError("Invalid beam_type. Choose 'Simple' or 'Cantilever'.")

def solve_cantilever_beam(beam_length, pointloads_in=None, distributedloads_in=None, 
                         momentloads_in=None, triangleloads_in=None):
                         
    pointloads = np.array(pointloads_in) if pointloads_in is not None else np.empty((0, 3))
    distributedloads = np.array(distributedloads_in) if distributedloads_in is not None else np.empty((0, 3))
    momentloads = np.array(momentloads_in) if momentloads_in is not None else np.empty((0, 2))
    triangleloads = np.array(triangleloads_in) if triangleloads_in is not None else np.empty((0, 4))

    Delta = beam_length / 10000 
    X_Field = np.arange(0, beam_length + Delta, Delta) 

    Va, Ha, Ma = Calculate_Cantilever_Reactions(pointloads, momentloads, distributedloads, triangleloads)

    ShearForce, BendingMoment = Calculate_SF_BM_Cantilever(
        X_Field, Va, Ha, Ma, pointloads, momentloads, distributedloads, triangleloads)
        
    # Maintain the external correct sign alignment standard for your setup
    CorrectedBendingMoment = -BendingMoment
    Reactions = np.array([Va, Ha, Ma])
    
    return X_Field, ShearForce, CorrectedBendingMoment, Reactions