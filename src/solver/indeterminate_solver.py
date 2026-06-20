# src/solver/indeterminate_solver.py
"""
AltruxIQ — Indeterminate Beam Solver Adapter
============================================
An adapter layer replacing the legacy custom procedural main_solver.py.
Leverages the 'indeterminatebeam' package to analyze both determinate 
and indeterminate structural beams (Simple, Cantilever, Fixed-Fixed, 
Propped Cantilever, and Continuous n-span beams).

Handles internal conversion of coordinate systems and load sign conventions.
"""

import numpy as np
from indeterminatebeam import (
    Beam, 
    Support,
    PointLoadV, 
    PointLoad,
    UDLV, 
    TrapezoidalLoadV,
    PointTorque,
)


def _build_supports(beam_type: str, beam_length: float, supports: list) -> list:
    """
    Constructs and returns a list of indeterminatebeam Support objects.
    
    For standard classifications (Simple, Cantilever, Fixed-Fixed, Propped), 
    the degrees of freedom (DoF) are hardcoded based on beam mechanics conventions.
    For Continuous beams, custom configurations are parsed from the input list.
    """
    if beam_type == "Simple":
        # Supports list contains support A and support B positions
        A = supports[0]["pos"]
        B = supports[1]["pos"]
        return [Support(A, (1, 1, 0)), Support(B, (0, 1, 0))]

    if beam_type == "Overhanging Beam":
        # Supports list contains support A and support B positions
        A = supports[0]["pos"]
        B = supports[1]["pos"]
        return [Support(A, (1, 1, 0)), Support(B, (0, 1, 0))]

    elif beam_type == "Cantilever":
        # Fixed at the left end (x = 0)
        return [Support(0.0, (1, 1, 1))]

    elif beam_type == "Fixed-Fixed":
        # Fixed at both boundaries (x = 0 and x = L)
        return [Support(0.0, (1, 1, 1)), Support(beam_length, (1, 1, 1))]

    elif beam_type == "Propped":
        # Propped Cantilever: Fixed at left end (x = 0), Roller at right end (x = L)
        return [Support(0.0, (1, 1, 1)), Support(beam_length, (0, 1, 0))]

    elif beam_type == "Continuous" or beam_type == "Custom":
        # Dynamically build user-defined boundaries
        result = []
        for s in supports:
            dof = tuple(s["dof"])
            ky = s.get("ky", None)
            kx = s.get("kx", None)
            
            # Support constructor supports elastic spring constants if defined
            if ky is not None or kx is not None:
                result.append(Support(s["pos"], dof, ky=ky, kx=kx))
            else:
                result.append(Support(s["pos"], dof))
        return result

    else:
        raise ValueError(
            f"Unknown beam_type: '{beam_type}'. "
            f"Valid options: Simple, Cantilever, Fixed-Fixed, Propped, Continuous"
        )


def _build_loads(pointloads, distributedloads, momentloads, triangleloads) -> list:
    """
    Converts AltruxIQ load arrays/lists into package-compliant load objects.
    Maps and mirrors sign conventions according to the live-tested calibration:
      - Vertical loads (PointLoadV, UDLV, TrapezoidalLoadV) are negated (AltruxIQ down+ -> IB up+)
      - Horizontal and Moment/Torque loads preserve original signs (same rightward+ / CCW+ standard)
    """
    loads = []

    # 1. Point Loads: [pos, Fx, Fy]
    for load in (pointloads or []):
        pos, Fx, Fy = float(load[0]), float(load[1]), float(load[2])
        if Fy != 0:
            loads.append(PointLoadV(Fy, pos))      # Negated: AltruxIQ downward is positive
        if Fx != 0:
            loads.append(PointLoad(Fx, pos, 0))     # No flip: rightward is positive

    # 2. Distributed Loads (UDL): [start, end, w]
    for load in (distributedloads or []):
        start, end, w = float(load[0]), float(load[1]), float(load[2])
        if w != 0:
            loads.append(UDLV(w, (start, end)))    # Negated: AltruxIQ downward is positive

    # 3. Moment Loads: [pos, M]
    for load in (momentloads or []):
        pos, M = float(load[0]), float(load[1])
        if M != 0:
            loads.append(PointTorque(M, pos))       # No flip: CCW is positive in both systems

    # 4. Triangular / Trapezoidal Loads: [start, end, peak, low]
    for load in (triangleloads or []):
        start, end = float(load[0]), float(load[1])
        peak, low = float(load[2]), float(load[3])
        
        # Risk Mitigation: Skip adding if total magnitude evaluates to exactly zero
        if peak == 0.0 and low == 0.0:
            continue
            
        loads.append(TrapezoidalLoadV(force=(-peak, -low), span=(start, end)))  # Negated

    return loads


def solve_beam(
    beam_length: float,
    beam_type: str,
    supports: list,
    pointloads=None,
    distributedloads=None,
    momentloads=None,
    triangleloads=None,
    E: float = 210e9,
    I: float = 8.33e-6,
    num_points: int = 2001,
) -> dict:
    """
    Unified execution engine for beam analysis utilizing the stiffness method backend.

    Parameters
    ----------
    beam_length : float
        Total beam length (m).
    beam_type : str
        "Simple", "Cantilever", "Fixed-Fixed", "Propped", or "Continuous".
    supports : list of dicts
        List containing boundary locations and structures. 
        Format: [{"pos": float, "dof": tuple, "ky": float|None, "kx": float|None}]
    pointloads, distributedloads, momentloads, triangleloads : list, optional
        Native AltruxIQ load arrays.
    E : float, default 210e9
        Young's Modulus (Pa). Used for direct deflection resolution.
    I : float, default 8.33e-6
        Second Moment of Area (m^4). Used for direct deflection resolution.
    num_points : int, default 2001
        Resolution array size for downstream graphing modules.

    Returns
    -------
    dict
        Contains evaluated numpy arrays ("X_Field", "Total_ShearForce", 
        "Total_BendingMoment", "Deflection") and a unified structured list of "Reactions".
    """
    # 1. Initialize core Beam structural properties
    beam = Beam(beam_length, E=E, I=I)

    # 2. Build and register support constraints
    ib_supports = _build_supports(beam_type, beam_length, supports)
    beam.add_supports(*ib_supports)

    # 3. Compile and apply exterior loads
    ib_loads = _build_loads(pointloads, distributedloads, momentloads, triangleloads)
    
    # Risk Mitigation: The underlying engine requires at least 1 load to compute matrices.
    # If no forces are active, apply a zero-magnitude point force placeholder at origin.
    if not ib_loads:
        ib_loads.append(PointLoadV(0.0, 0.0))
        
    beam.add_loads(*ib_loads)

    # 4. Invoke solver mechanics (Stiffness analysis via SymPy)
    beam.analyse()

    # 5. Extract vector metrics along the length of the beam
    X_Field = np.linspace(0, beam_length, num_points)

    # Convert SymPy expressions sequentially to concrete float elements
    Total_ShearForce = np.array([float(beam.get_shear_force(x)) for x in X_Field])
    Total_BendingMoment = np.array([float(beam.get_bending_moment(x)) for x in X_Field])
    Deflection = np.array([float(beam.get_deflection(x)) for x in X_Field])
    Slopes = np.gradient(Deflection, X_Field)
    Curvatures = Total_BendingMoment / (E * I)
    # 6. Extract unified Reactions format (List of Dicts)
    # Reconstruct exact support tracking coordinates based on classification
    if beam_type == "Simple":
        support_positions = [supports[0]["pos"], supports[1]["pos"]]   
    if beam_type == "Overhanging Beam":
        support_positions = [supports[0]["pos"], supports[1]["pos"]]
    elif beam_type == "Cantilever":
        support_positions = [0.0]
    elif beam_type == "Fixed-Fixed" or beam_type == "Propped":
        support_positions = [0.0, beam_length]
    elif beam_type == "Continuous" or beam_type == "Custom":
        support_positions = [s["pos"] for s in supports]
    else:
        support_positions = [s["pos"] for s in supports]

    Reactions = []
    for pos in support_positions:
        r = beam.get_reaction(pos)  # Returns array/list: [Fx, Fy, M]
        if r is not None:
            Reactions.append({
                "pos": float(pos),
                "Fx": float(r[0]),   # Positive = Rightward
                "Fy": float(r[1]),   # Positive = Upward
                "M": float(r[2]),    # Positive = Counter-Clockwise (CCW)
            })
        else:
            Reactions.append({
                "pos": float(pos), 
                "Fx": 0.0, 
                "Fy": 0.0, 
                "M": 0.0
            })

    return {
        "X_Field": X_Field,
        "Total_ShearForce": Total_ShearForce,
        "Total_BendingMoment": Total_BendingMoment,
        "Deflection": Deflection,
        "Reactions": Reactions,
        "Slopes" : Slopes,
        "Curvatures":Curvatures
}