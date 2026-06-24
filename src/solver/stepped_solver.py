# src/solver/stepped_solver.py
"""
AltruxIQ — Stepped Beam 2D Frame Element FEM Solver
======================================================
Custom finite-element solver for stepped beams with varying cross-section
and material properties along the length. Handles combined axial + bending
analysis using the standard 2D frame element (3 DOFs per node: u, v, θ).

Segmentation: each beam portion with uniform E, A, I is a "segment".
The mesh is automatically built at segment boundaries, support positions,
and load positions. Distributed loads are sampled into equivalent point
loads for numerical robustness.

All inputs and outputs are in base SI (N, m, Pa, kg/m³).

Return format mirrors ``indeterminate_solver.solve_beam()`` so the CLI
routing layer can consume either solver without distinction.
"""

import numpy as np
from scipy.linalg import solve
import os
import sys

# --- PATH INJECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from solver.area_solver import area_from_section


# =============================================================================
#  INTERNAL HELPERS
# =============================================================================

def _element_stiffness(E: float, A: float, I: float, L: float) -> np.ndarray:
    """
    6×6 stiffness matrix for a prismatic 2D frame element.
    DOFs: [u_i, v_i, θ_i, u_j, v_j, θ_j]
    """
    k = np.zeros((6, 6))

    # --- Axial component ---
    EA_L = E * A / L
    k[0, 0] =  EA_L
    k[0, 3] = -EA_L
    k[3, 0] = -EA_L
    k[3, 3] =  EA_L

    # --- Bending component ---
    EI = E * I
    EI_L3 = EI / (L ** 3)

    k[1, 1] =  12.0 * EI_L3
    k[1, 2] =   6.0 * EI_L3 * L
    k[1, 4] = -12.0 * EI_L3
    k[1, 5] =   6.0 * EI_L3 * L

    k[2, 1] =   6.0 * EI_L3 * L
    k[2, 2] =   4.0 * EI_L3 * (L ** 2)
    k[2, 4] =  -6.0 * EI_L3 * L
    k[2, 5] =   2.0 * EI_L3 * (L ** 2)

    k[4, 1] = -12.0 * EI_L3
    k[4, 2] =  -6.0 * EI_L3 * L
    k[4, 4] =  12.0 * EI_L3
    k[4, 5] =  -6.0 * EI_L3 * L

    k[5, 1] =   6.0 * EI_L3 * L
    k[5, 2] =   2.0 * EI_L3 * (L ** 2)
    k[5, 4] =  -6.0 * EI_L3 * L
    k[5, 5] =   4.0 * EI_L3 * (L ** 2)

    return k


def _sample_distributed_loads(distributedloads, triangleloads, beam_length):
    """
    Convert distributed and triangular loads into equivalent point loads.
    Sampling density: 20 points per metre (minimum 5 per load).
    Returns a list of point loads: [pos, Fx, Fy].
    """
    extra_pointloads = []

    # --- UDLs ---
    for load in (distributedloads or []):
        start, end, w = float(load[0]), float(load[1]), float(load[2])
        if start >= end or w == 0.0:
            continue
        n = max(5, int((end - start) * 20.0))
        dx = (end - start) / n
        for i in range(n):
            x = start + (i + 0.5) * dx
            F = w * dx
            extra_pointloads.append([x, 0.0, F])

    # --- Triangular / trapezoidal loads ---
    for load in (triangleloads or []):
        start, end = float(load[0]), float(load[1])
        peak, low = float(load[2]), float(load[3])
        if start >= end or (peak == 0.0 and low == 0.0):
            continue
        n = max(5, int((end - start) * 20.0))
        dx = (end - start) / n
        for i in range(n):
            x = start + (i + 0.5) * dx
            w = low + (peak - low) * (x - start) / (end - start)
            F = w * dx
            extra_pointloads.append([x, 0.0, F])

    return extra_pointloads


def _build_mesh(segments, supports, pointloads, momentloads, extra_pointloads):
    """
    Build a 1D mesh from segments, supports, and loads.

    Returns
    -------
    nodes : list of float
        Sorted unique positions.
    elements : list of dict
        Each element: {"start": float, "end": float, "E": float, "A": float, "I": float,
                       "segment_idx": int, "shape": str, "section_dims": dict,
                       "c": float, "b": float, "y_array": np.ndarray}
    """
    positions = set()

    # Segment boundaries
    for seg in segments:
        positions.add(float(seg["start"]))
        positions.add(float(seg["end"]))

    # Supports
    for s in (supports or []):
        positions.add(float(s["pos"]))

    # Point loads
    for pl in (pointloads or []):
        positions.add(float(pl[0]))

    # Moment loads
    for ml in (momentloads or []):
        positions.add(float(ml[0]))

    # Extra point loads (from distributed loads)
    for pl in extra_pointloads:
        positions.add(float(pl[0]))

    nodes = sorted(positions)

    # Build elements
    elements = []
    for i in range(len(nodes) - 1):
        x_i = nodes[i]
        x_j = nodes[i + 1]
        L = x_j - x_i
        if L < 1e-9:
            continue

        # Find which segment this element belongs to (use midpoint)
        mid = (x_i + x_j) / 2.0
        seg_idx = None
        seg_props = None
        for idx, seg in enumerate(segments):
            if float(seg["start"]) - 1e-9 <= mid <= float(seg["end"]) + 1e-9:
                seg_idx = idx
                seg_props = seg
                break

        if seg_props is None:
            raise ValueError(
                f"Element from x={x_i:.6f} to x={x_j:.6f} does not belong to any segment."
            )

        elements.append({
            "start": x_i,
            "end": x_j,
            "L": L,
            "E": float(seg_props["E"]),
            "A": float(seg_props["A"]),
            "I": float(seg_props["I"]),
            "segment_idx": seg_idx,
            "shape": seg_props.get("shape", ""),
            "section_dims": seg_props.get("section_dims", {}),
            "c": float(seg_props.get("c", 0.0)),
            "b": float(seg_props.get("b", 0.0)),
            "y_array": seg_props.get("y_array", np.array([])),
        })

    return nodes, elements


def _assemble_global(nodes, elements):
    """
    Assemble the global stiffness matrix K and global load vector F.

    Returns
    -------
    K : np.ndarray, shape (3*n_nodes, 3*n_nodes)
    F : np.ndarray, shape (3*n_nodes,)
    """
    n_nodes = len(nodes)
    n_dofs = 3 * n_nodes
    K = np.zeros((n_dofs, n_dofs))
    F = np.zeros(n_dofs)

    for elem in elements:
        L = elem["L"]
        E = elem["E"]
        A = elem["A"]
        I = elem["I"]
        k_e = _element_stiffness(E, A, I, L)

        # Find node indices for this element
        i_idx = nodes.index(elem["start"])
        j_idx = nodes.index(elem["end"])

        dofs = [3 * i_idx, 3 * i_idx + 1, 3 * i_idx + 2,
                3 * j_idx, 3 * j_idx + 1, 3 * j_idx + 2]

        for r in range(6):
            for c in range(6):
                K[dofs[r], dofs[c]] += k_e[r, c]

    return K, F


def _apply_loads(K, F, nodes, pointloads, momentloads, extra_pointloads):
    """
    Apply point loads and moments to the global load vector F.
    Modifies F in-place.
    """
    # Combine all point loads
    all_pointloads = list(pointloads or []) + list(extra_pointloads)

    for pl in all_pointloads:
        pos = float(pl[0])
        Fx = float(pl[1])
        Fy = float(pl[2])

        # Find nearest node (or exact match)
        # Since we built nodes at all load positions, there should be an exact match
        try:
            idx = nodes.index(pos)
        except ValueError:
            # Find closest node within tolerance
            diffs = [abs(n - pos) for n in nodes]
            min_diff = min(diffs)
            if min_diff < 1e-6:
                idx = diffs.index(min_diff)
            else:
                raise ValueError(f"Point load at x={pos} has no corresponding node.")

        F[3 * idx] += Fx
        F[3 * idx + 1] += Fy

    for ml in (momentloads or []):
        pos = float(ml[0])
        M = float(ml[1])

        try:
            idx = nodes.index(pos)
        except ValueError:
            diffs = [abs(n - pos) for n in nodes]
            min_diff = min(diffs)
            if min_diff < 1e-6:
                idx = diffs.index(min_diff)
            else:
                raise ValueError(f"Moment load at x={pos} has no corresponding node.")

        F[3 * idx + 2] += M

    return F


def _apply_boundary_conditions(K, F, nodes, supports):
    """
    Identify constrained DOFs from support definitions and apply boundary
    conditions using direct elimination (prescribed displacement = 0).

    DOF convention per node: 0 = u (axial), 1 = v (transverse), 2 = θ (rotation)

    Returns
    -------
    K_ff : np.ndarray
        Stiffness matrix for free DOFs.
    F_f : np.ndarray
        Load vector for free DOFs.
    free_dofs : list of int
        Indices of free DOFs.
    constrained_dofs : list of int
        Indices of constrained DOFs.
    """
    n_nodes = len(nodes)
    n_dofs = 3 * n_nodes
    constrained = set()

    for s in (supports or []):
        pos = float(s["pos"])
        try:
            idx = nodes.index(pos)
        except ValueError:
            diffs = [abs(n - pos) for n in nodes]
            min_diff = min(diffs)
            if min_diff < 1e-6:
                idx = diffs.index(min_diff)
            else:
                raise ValueError(f"Support at x={pos} has no corresponding node.")

        dof = s.get("dof", (1, 1, 0))
        if len(dof) < 3:
            dof = tuple(list(dof) + [0] * (3 - len(dof)))

        for d_idx, constrained_flag in enumerate(dof[:3]):
            if constrained_flag:
                constrained.add(3 * idx + d_idx)

    free_dofs = [d for d in range(n_dofs) if d not in constrained]
    constrained_dofs = sorted(constrained)

    if not free_dofs:
        raise ValueError("All DOFs are constrained. The structure is over-constrained.")

    K_ff = K[np.ix_(free_dofs, free_dofs)]
    F_f = F[free_dofs]

    # Check for stability (non-singular K_ff)
    if np.linalg.cond(K_ff) > 1e14:
        raise ValueError(
            "Global stiffness matrix is near-singular. "
            "The structure may be unstable or under-constrained."
        )

    return K_ff, F_f, free_dofs, constrained_dofs


def _extract_reactions(K, F, displacements, free_dofs, constrained_dofs, nodes):
    """
    Compute reactions at constrained DOFs.
    R = K·d - F  (evaluated at constrained DOFs)

    Returns
    -------
    list of dicts : same format as indeterminate_solver Reactions
    """
    n_dofs = len(displacements)
    # R = K @ d - F for all DOFs, then pick constrained ones
    R_all = K @ displacements - F

    # Group by node
    reactions_by_node = {}
    for dof in constrained_dofs:
        node_idx = dof // 3
        local_dof = dof % 3  # 0=Fx, 1=Fy, 2=M
        if node_idx not in reactions_by_node:
            reactions_by_node[node_idx] = {"pos": float(nodes[node_idx]), "Fx": 0.0, "Fy": 0.0, "M": 0.0}
        if local_dof == 0:
            reactions_by_node[node_idx]["Fx"] = float(R_all[dof])
        elif local_dof == 1:
            reactions_by_node[node_idx]["Fy"] = float(R_all[dof])
        elif local_dof == 2:
            reactions_by_node[node_idx]["M"] = float(R_all[dof])

    return list(reactions_by_node.values())


def _interpolate_to_field(nodes, elements, displacements, num_points):
    """
    Interpolate FEM results onto a uniform evaluation field with `num_points`.

    Returns
    -------
    dict with:
        X_Field, Total_ShearForce, Total_BendingMoment, Deflection,
        AxialForce, AxialDisplacement, Slopes, Curvatures
    """
    total_length = nodes[-1]
    X_Field = np.linspace(0.0, total_length, num_points)

    n_nodes = len(nodes)

    # Pre-allocate
    AxialForce = np.zeros(num_points)
    Total_ShearForce = np.zeros(num_points)
    Total_BendingMoment = np.zeros(num_points)
    Deflection = np.zeros(num_points)
    AxialDisplacement = np.zeros(num_points)
    Slopes = np.zeros(num_points)
    Curvatures = np.zeros(num_points)

    for elem in elements:
        x_i = elem["start"]
        x_j = elem["end"]
        L = elem["L"]
        E = elem["E"]
        I = elem["I"]
        A = elem["A"]

        i_idx = nodes.index(x_i)
        j_idx = nodes.index(x_j)

        d_i = displacements[3 * i_idx:3 * i_idx + 3]
        d_j = displacements[3 * j_idx:3 * j_idx + 3]

        u_i, v_i, th_i = d_i
        u_j, v_j, th_j = d_j

        # Element internal forces (constant within element)
        N_elem = E * A / L * (u_j - u_i)          # Axial force (tension positive)
        V_elem = E * I / (L ** 3) * (12.0 * (v_i - v_j) + 6.0 * L * (th_i + th_j))

        # End moments
        M_i = E * I / (L ** 2) * (-6.0 * v_i - 4.0 * L * th_i + 6.0 * v_j - 2.0 * L * th_j)
        M_j = E * I / (L ** 2) * ( 6.0 * v_i + 2.0 * L * th_i - 6.0 * v_j + 4.0 * L * th_j)

        # Find evaluation points inside this element
        mask = (X_Field >= x_i - 1e-9) & (X_Field <= x_j + 1e-9)
        x_local = X_Field[mask] - x_i
        xi = x_local / L

        if len(xi) == 0:
            continue

        # --- Axial ---
        AxialForce[mask] = N_elem
        AxialDisplacement[mask] = u_i + (u_j - u_i) * xi

        # --- Bending (cubic shape functions) ---
        # N1 = 1 - 3ξ² + 2ξ³
        # N2 = L(ξ - 2ξ² + ξ³)
        # N3 = 3ξ² - 2ξ³
        # N4 = L(-ξ² + ξ³)
        N1 = 1.0 - 3.0 * xi ** 2 + 2.0 * xi ** 3
        N2 = L * (xi - 2.0 * xi ** 2 + xi ** 3)
        N3 = 3.0 * xi ** 2 - 2.0 * xi ** 3
        N4 = L * (-xi ** 2 + xi ** 3)

        Deflection[mask] = N1 * v_i + N2 * th_i + N3 * v_j + N4 * th_j

        # Slope = dv/dx = (1/L) * dN/dξ · [v_i, θ_i, v_j, θ_j]
        dN1 = -6.0 * xi + 6.0 * xi ** 2
        dN2 = L * (1.0 - 4.0 * xi + 3.0 * xi ** 2)
        dN3 = 6.0 * xi - 6.0 * xi ** 2
        dN4 = L * (-2.0 * xi + 3.0 * xi ** 2)
        Slopes[mask] = (1.0 / L) * (dN1 * v_i + dN2 * th_i + dN3 * v_j + dN4 * th_j)

        # Curvature = d²v/dx² = (1/L²) * d²N/dξ² · [v_i, θ_i, v_j, θ_j]
        d2N1 = -6.0 + 12.0 * xi
        d2N2 = L * (-4.0 + 6.0 * xi)
        d2N3 = 6.0 - 12.0 * xi
        d2N4 = L * (-2.0 + 6.0 * xi)
        Curvatures[mask] = (1.0 / (L ** 2)) * (d2N1 * v_i + d2N2 * th_i + d2N3 * v_j + d2N4 * th_j)

        # Bending moment (linear interpolation between end moments)
        Total_BendingMoment[mask] = M_i + (M_j - M_i) * xi
        Total_ShearForce[mask] = V_elem

    return {
        "X_Field": X_Field,
        "Total_ShearForce": Total_ShearForce,
        "Total_BendingMoment": Total_BendingMoment,
        "Deflection": Deflection,
        "AxialForce": AxialForce,
        "AxialDisplacement": AxialDisplacement,
        "Slopes": Slopes,
        "Curvatures": Curvatures,
    }


# =============================================================================
#  PUBLIC API
# =============================================================================

def solve_stepped_beam(
    segments: list,
    supports: list,
    pointloads=None,
    distributedloads=None,
    momentloads=None,
    triangleloads=None,
    num_points: int = 2001,
) -> dict:
    """
    Unified execution engine for stepped beam analysis via 2D frame FEM.

    Parameters
    ----------
    segments : list of dicts
        Each segment defines a uniform beam portion:
        {
            "start": float,      # m
            "end": float,        # m
            "E": float,          # Pa
            "A": float,          # m²
            "I": float,          # m⁴
            "shape": str,        # e.g. "Rectangle"
            "section_dims": dict,
            "c": float,          # m
            "b": float,          # m
            "y_array": np.ndarray,
        }
        Segments must be contiguous and ordered from x=0 to x=L_total.
    supports : list of dicts
        Each support: {"pos": float, "dof": (int, int, int)}
        DOF: (u_constraint, v_constraint, θ_constraint) — 1=constrained, 0=free
    pointloads : list of [pos, Fx, Fy]
    distributedloads : list of [start, end, w]  (w positive = upward)
    momentloads : list of [pos, M]  (M positive = CCW)
    triangleloads : list of [start, end, peak, low]
    num_points : int, default 2001
        Number of evaluation points for output arrays.

    Returns
    -------
    dict
        {
            "X_Field": np.ndarray,
            "Total_ShearForce": np.ndarray,
            "Total_BendingMoment": np.ndarray,
            "Deflection": np.ndarray,
            "AxialForce": np.ndarray,
            "AxialDisplacement": np.ndarray,
            "Reactions": list[dict],
            "Slopes": np.ndarray,
            "Curvatures": np.ndarray,
        }
    """
    # -----------------------------------------------------------------------
    # 1. Validate segments
    # -----------------------------------------------------------------------
    if not segments:
        raise ValueError("At least one segment must be defined.")

    # Sort segments by start position
    segments = sorted(segments, key=lambda s: float(s["start"]))

    # Check contiguity
    for i in range(len(segments) - 1):
        if abs(float(segments[i]["end"]) - float(segments[i + 1]["start"])) > 1e-6:
            raise ValueError(
                f"Segments are not contiguous: gap between "
                f"segment {i} (ends at {segments[i]['end']}) and "
                f"segment {i+1} (starts at {segments[i+1]['start']})."
            )

    # Check first segment starts at 0
    if float(segments[0]["start"]) > 1e-6:
        raise ValueError(f"First segment must start at x=0 (got {segments[0]['start']}).")

    total_length = float(segments[-1]["end"])

    # -----------------------------------------------------------------------
    # 2. Convert distributed loads to point loads
    # -----------------------------------------------------------------------
    extra_pointloads = _sample_distributed_loads(distributedloads, triangleloads, total_length)

    # -----------------------------------------------------------------------
    # 3. Build mesh
    # -----------------------------------------------------------------------
    nodes, elements = _build_mesh(segments, supports, pointloads, momentloads, extra_pointloads)

    if len(nodes) < 2:
        raise ValueError("Mesh has fewer than 2 nodes. Check segment and load definitions.")

    # -----------------------------------------------------------------------
    # 4. Assemble global system
    # -----------------------------------------------------------------------
    K, F = _assemble_global(nodes, elements)
    F = _apply_loads(K, F, nodes, pointloads, momentloads, extra_pointloads)

    # -----------------------------------------------------------------------
    # 5. Apply boundary conditions and solve
    # -----------------------------------------------------------------------
    K_ff, F_f, free_dofs, constrained_dofs = _apply_boundary_conditions(K, F, nodes, supports)

    d_free = solve(K_ff, F_f)

    # Reconstruct full displacement vector
    n_dofs = 3 * len(nodes)
    displacements = np.zeros(n_dofs)
    displacements[free_dofs] = d_free

    # -----------------------------------------------------------------------
    # 6. Extract reactions
    # -----------------------------------------------------------------------
    Reactions = _extract_reactions(K, F, displacements, free_dofs, constrained_dofs, nodes)

    # -----------------------------------------------------------------------
    # 7. Interpolate to uniform field
    # -----------------------------------------------------------------------
    results = _interpolate_to_field(nodes, elements, displacements, num_points)
    results["Reactions"] = Reactions

    return results
