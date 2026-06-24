#!/usr/bin/env python3
"""
AltruxIQ — Stepped Solver Validation Suite
============================================
Independent verification of the stepped_solver.py core against analytical
solutions for axial, bending, and combined loading.

Run from the project root:
    python test_stepped_solver.py
"""

import sys
import os

# --- PATH INJECTION ---
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import numpy as np
from solver.stepped_solver import solve_stepped_beam
from solver.area_solver import area_from_section


# =============================================================================
#  TEST 1: Pure Axial — Two-segment stepped bar, fixed at left, tensile load
# =============================================================================
def test_pure_axial_two_segment():
    """
    Segment 1: Steel,  L=3.0 m, A=500e-6 m^2, E=200e9 Pa
    Segment 2: Aluminium, L=2.0 m, A=400e-6 m^2, E=70e9 Pa
    Fixed at x=0.  Tensile load P = 10 kN at x=5.0 m.

    Analytical:
      N(x) = +10 000 N  (constant, tension positive)
      δ_total = P * [ L1/(E1·A1) + L2/(E2·A2) ]
    """
    print("\n" + "=" * 60)
    print("TEST 1: Pure Axial — Two-Segment Stepped Bar")
    print("=" * 60)

    P = 10_000.0  # N, tensile
    L1, E1, A1 = 3.0, 200e9, 500e-6
    L2, E2, A2 = 2.0, 70e9, 400e-6

    segments = [
        {
            "start": 0.0, "end": L1,
            "E": E1, "A": A1, "I": 8.33e-6,
            "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
            "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
        },
        {
            "start": L1, "end": L1 + L2,
            "E": E2, "A": A2, "I": 8.33e-6,
            "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
            "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
        },
    ]

    supports = [{"pos": 0.0, "dof": (1, 1, 1)}]  # Fixed
    pointloads = [[L1 + L2, P, 0.0]]  # Fx = P, Fy = 0

    result = solve_stepped_beam(
        segments=segments,
        supports=supports,
        pointloads=pointloads,
        num_points=2001,
    )

    # --- Assertions ---
    axial_force = result["AxialForce"]
    axial_disp = result["AxialDisplacement"]
    X = result["X_Field"]

    # Axial force should be constant = P everywhere
    assert np.allclose(axial_force, P, rtol=1e-10), (
        f"Axial force not constant: min={axial_force.min():.4f}, max={axial_force.max():.4f}"
    )
    print(f"  [OK] Axial force = {P:.1f} N (constant everywhere)")

    # Analytical total displacement
    delta_analytical = P * (L1 / (E1 * A1) + L2 / (E2 * A2))
    delta_numeric = axial_disp[-1]
    error = abs(delta_numeric - delta_analytical) / delta_analytical
    assert error < 1e-10, (
        f"Displacement error too large: numeric={delta_numeric:.6e}, "
        f"analytical={delta_analytical:.6e}, rel_error={error:.2e}"
    )
    print(f"  [OK] Total displacement: numeric={delta_numeric:.6e} m, analytical={delta_analytical:.6e} m")
    print(f"  [OK] Relative error: {error:.2e}")

    # Reactions
    reactions = result["Reactions"]
    assert len(reactions) == 1
    assert np.isclose(reactions[0]["Fx"], -P, rtol=1e-10)
    assert np.isclose(reactions[0]["Fy"], 0.0, atol=1e-10)
    assert np.isclose(reactions[0]["M"], 0.0, atol=1e-10)
    print(f"  [OK] Reaction at wall: Fx={reactions[0]['Fx']:.1f} N (expected {-P:.1f})")

    print("  TEST 1 PASSED [OK]")


# =============================================================================
#  TEST 2: Pure Axial — Three-segment bar (Image example geometry)
# =============================================================================
def test_pure_axial_three_segment():
    """
    Steel    : L=2.5 m, A=500 mm^2, E=200 GPa
    Aluminium: L=2.0 m, A=400 mm^2, E=70  GPa
    Bronze   : L=1.5 m, A=200 mm^2, E=110 GPa
    Fixed at x=0.  Tensile load P = 20 kN at x=6.0 m.

    Analytical displacement:
      δ = P * [ 2.5/(200e9·500e-6) + 2.0/(70e9·400e-6) + 1.5/(110e9·200e-6) ]
    """
    print("\n" + "=" * 60)
    print("TEST 2: Pure Axial — Three-Segment (Image Geometry)")
    print("=" * 60)

    P = 20_000.0  # N

    seg_data = [
        (0.0, 2.5, 200e9, 500e-6),
        (2.5, 4.5, 70e9, 400e-6),
        (4.5, 6.0, 110e9, 200e-6),
    ]

    segments = []
    for start, end, E, A in seg_data:
        segments.append({
            "start": start, "end": end,
            "E": E, "A": A, "I": 8.33e-6,
            "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
            "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
        })

    supports = [{"pos": 0.0, "dof": (1, 1, 1)}]
    pointloads = [[6.0, P, 0.0]]

    result = solve_stepped_beam(
        segments=segments,
        supports=supports,
        pointloads=pointloads,
        num_points=2001,
    )

    axial_force = result["AxialForce"]
    axial_disp = result["AxialDisplacement"]

    # Force should be constant
    assert np.allclose(axial_force, P, rtol=1e-10)
    print(f"  [OK] Axial force = {P:.1f} N (constant)")

    # Analytical displacement
    delta_analytical = sum(
        P * (end - start) / (E * A)
        for start, end, E, A in seg_data
    )
    delta_numeric = axial_disp[-1]
    error = abs(delta_numeric - delta_analytical) / delta_analytical
    assert error < 1e-10
    print(f"  [OK] Total displacement: numeric={delta_numeric:.6e} m, analytical={delta_analytical:.6e} m")
    print(f"  [OK] Relative error: {error:.2e}")

    # Segment-by-segment displacement check
    x_seg_ends = [2.5, 4.5, 6.0]
    for x_end in x_seg_ends:
        idx = np.argmin(np.abs(result["X_Field"] - x_end))
        x_actual = result["X_Field"][idx]
        disp_numeric = axial_disp[idx]
        # Compute analytical displacement at the EXACT X_Field point (not x_end)
        disp_analytical = 0.0
        for s, e, E_mat, A_mat in seg_data:
            if x_actual >= e - 1e-9:
                # Full segment contribution
                disp_analytical += P * (e - s) / (E_mat * A_mat)
            elif x_actual > s + 1e-9:
                # Partial segment contribution
                disp_analytical += P * (x_actual - s) / (E_mat * A_mat)
                break
            else:
                break
        err = abs(disp_numeric - disp_analytical) / abs(disp_analytical) if disp_analytical != 0 else abs(disp_numeric)
        assert err < 1e-10, (
            f"Displacement mismatch at x≈{x_end:.1f}m (actual X_Field={x_actual:.6f}m): "
            f"numeric={disp_numeric:.6e}, analytical={disp_analytical:.6e}, rel_err={err:.2e}"
        )
        print(f"  [OK] Displacement at x={x_actual:.4f}m: numeric={disp_numeric:.6e}, analytical={disp_analytical:.6e}")

    print("  TEST 2 PASSED [OK]")


# =============================================================================
#  TEST 3: Pure Bending — Cantilever with point load at free end
# =============================================================================
def test_pure_bending_cantilever():
    """
    Single segment: L=5.0 m, E=200 GPa, I=8.33e-6 m⁴
    Fixed at x=0.  Downward point load P = 1 kN at x=5.0 m.

    Analytical:
      V(x) = -P  (constant)
      M(x) = -P*(L - x)  (linear, zero at free end, -P*L at wall)
      v(L) = P·L³ / (3·E·I)  (downward deflection, positive in our convention?)

    Note: In our sign convention, positive Fy = upward, so P = -1000 N.
    Positive deflection = upward. So v(L) should be negative.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Pure Bending — Cantilever with End Load")
    print("=" * 60)

    L = 5.0
    E = 200e9
    I = 8.33e-6
    P = 1_000.0  # Magnitude of load

    segments = [{
        "start": 0.0, "end": L,
        "E": E, "A": 0.01, "I": I,
        "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
        "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
    }]

    supports = [{"pos": 0.0, "dof": (1, 1, 1)}]
    pointloads = [[L, 0.0, -P]]  # Fy = -P (downward)

    result = solve_stepped_beam(
        segments=segments,
        supports=supports,
        pointloads=pointloads,
        num_points=2001,
    )

    X = result["X_Field"]
    SF = result["Total_ShearForce"]
    BM = result["Total_BendingMoment"]
    Deflection = result["Deflection"]

    # Shear force should be constant = +P (standard structural analysis convention:
    # positive shear = upward on left face of section)
    assert np.allclose(SF, P, rtol=1e-10), (
        f"Shear force not constant: min={SF.min():.4f}, max={SF.max():.4f}"
    )
    print(f"  [OK] Shear force = {P:.1f} N (constant)")

    # Bending moment: M(x) = -P*(L - x)
    M_analytical = -P * (L - X)
    M_max_error = np.max(np.abs(BM - M_analytical))
    assert M_max_error < 1e-6, f"Bending moment error: {M_max_error:.6f}"
    print(f"  [OK] Bending moment matches analytical: M(x) = -P·(L-x)")
    print(f"  [OK] Max bending moment error: {M_max_error:.6e} N·m")

    # Deflection at free end: v(L) = -P·L³/(3·E·I)
    v_analytical = -P * L**3 / (3.0 * E * I)
    v_numeric = Deflection[-1]
    v_error = abs(v_numeric - v_analytical) / abs(v_analytical)
    assert v_error < 1e-6, (
        f"Deflection error too large: numeric={v_numeric:.6e}, "
        f"analytical={v_analytical:.6e}, rel_error={v_error:.2e}"
    )
    print(f"  [OK] Deflection at free end: numeric={v_numeric:.6e} m, analytical={v_analytical:.6e} m")
    print(f"  [OK] Relative error: {v_error:.2e}")

    # Reactions at wall
    reactions = result["Reactions"]
    assert len(reactions) == 1
    assert np.isclose(reactions[0]["Fx"], 0.0, atol=1e-10)
    assert np.isclose(reactions[0]["Fy"], P, rtol=1e-10)  # Reaction upward balances downward load
    assert np.isclose(reactions[0]["M"], P * L, rtol=1e-10)  # Reaction moment CCW
    print(f"  [OK] Reactions: Fx={reactions[0]['Fx']:.1f}, Fy={reactions[0]['Fy']:.1f}, M={reactions[0]['M']:.1f}")

    print("  TEST 3 PASSED [OK]")


# =============================================================================
#  TEST 4: Combined Axial + Bending — Stepped cantilever
# =============================================================================
def test_combined_axial_bending():
    """
    Two-segment cantilever:
      Segment 1 (0–3 m): E=200 GPa, A=500e-6, I=8.33e-6
      Segment 2 (3–5 m): E=70  GPa, A=400e-6, I=5.0e-6
    Fixed at x=0.
    Loads at x=5 m: Fx = 10 kN (tension), Fy = -2 kN (downward)

    Verify:
      - Axial force = 10 kN everywhere
      - Shear force = -2 kN everywhere
      - Reactions balance applied loads
    """
    print("\n" + "=" * 60)
    print("TEST 4: Combined Axial + Bending — Stepped Cantilever")
    print("=" * 60)

    Fx = 10_000.0
    Fy = -2_000.0

    segments = [
        {
            "start": 0.0, "end": 3.0,
            "E": 200e9, "A": 500e-6, "I": 8.33e-6,
            "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
            "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
        },
        {
            "start": 3.0, "end": 5.0,
            "E": 70e9, "A": 400e-6, "I": 5.0e-6,
            "shape": "Rectangle", "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2},
            "c": 0.1, "b": 0.05, "y_array": np.linspace(-0.1, 0.1, 10001),
        },
    ]

    supports = [{"pos": 0.0, "dof": (1, 1, 1)}]
    pointloads = [[5.0, Fx, Fy]]

    result = solve_stepped_beam(
        segments=segments,
        supports=supports,
        pointloads=pointloads,
        num_points=2001,
    )

    axial_force = result["AxialForce"]
    shear_force = result["Total_ShearForce"]
    reactions = result["Reactions"]

    # Axial force should be constant
    assert np.allclose(axial_force, Fx, rtol=1e-10)
    print(f"  [OK] Axial force = {Fx:.1f} N (constant)")

    # Shear force should be constant (positive = upward on left face)
    assert np.allclose(shear_force, -Fy, rtol=1e-10)
    print(f"  [OK] Shear force = {-Fy:.1f} N (constant)")

    # Reactions
    assert len(reactions) == 1
    R = reactions[0]
    assert np.isclose(R["Fx"], -Fx, rtol=1e-10)
    assert np.isclose(R["Fy"], -Fy, rtol=1e-10)
    assert np.isclose(R["M"], -Fy * 5.0, rtol=1e-10)  # Moment = shear * distance
    print(f"  [OK] Reactions: Fx={R['Fx']:.1f}, Fy={R['Fy']:.1f}, M={R['M']:.1f}")

    # Equilibrium check
    sum_fx = sum(r["Fx"] for r in reactions) + Fx
    sum_fy = sum(r["Fy"] for r in reactions) + Fy
    sum_m = sum(r["M"] for r in reactions) + Fy * 5.0
    assert abs(sum_fx) < 1e-6, f"Fx equilibrium violated: {sum_fx}"
    assert abs(sum_fy) < 1e-6, f"Fy equilibrium violated: {sum_fy}"
    assert abs(sum_m) < 1e-6, f"Moment equilibrium violated: {sum_m}"
    print(f"  [OK] Global equilibrium satisfied: SumFx={sum_fx:.2e}, SumFy={sum_fy:.2e}, SumM={sum_m:.2e}")

    print("  TEST 4 PASSED [OK]")


# =============================================================================
#  TEST 5: area_solver.py — Verify all 8 shapes
# =============================================================================
def test_area_solver():
    """Verify area_from_section for all 8 supported cross-section types."""
    print("\n" + "=" * 60)
    print("TEST 5: area_solver.py — All 8 Cross-Section Types")
    print("=" * 60)

    cases = [
        ("Rectangle", {"type": "Rectangle", "width": 0.05, "height": 0.2}, 0.05 * 0.2),
        ("Square", {"type": "Square", "side": 0.15}, 0.15 ** 2),
        ("Circle", {"type": "Circle", "diameter": 0.1, "radius": 0.05}, np.pi * 0.05 ** 2),
        ("Hollow Circle", {"type": "Hollow Circle", "r_outer": 0.05, "r_inner": 0.04,
                           "diameter_outer": 0.1, "diameter_inner": 0.08},
         np.pi * (0.05 ** 2 - 0.04 ** 2)),
        ("Hollow Square", {"type": "Hollow Square", "outer_width": 0.1, "inner_width": 0.08,
                           "t_wall": 0.01},
         0.1 ** 2 - 0.08 ** 2),
        ("I-beam", {"type": "I-beam", "bf": 0.1, "tf": 0.01, "hw": 0.18, "tw": 0.005, "H": 0.2},
         2 * 0.1 * 0.01 + 0.005 * 0.18),
        ("T-beam", {"type": "T-beam", "bf": 0.1, "tf": 0.01, "hw": 0.18, "tw": 0.005,
                     "y_bar": 0.05, "H": 0.19, "c_top": 0.09, "c_bot": 0.05},
         0.1 * 0.01 + 0.005 * 0.18),
        ("Hollow Rectangle", {"type": "Hollow Rectangle", "outer_b": 0.1, "outer_h": 0.2,
                              "inner_b": 0.08, "inner_h": 0.18, "t_flange": 0.01, "t_web": 0.01},
         0.1 * 0.2 - 0.08 * 0.18),
    ]

    for shape, dims, expected in cases:
        computed = area_from_section(shape, dims)
        rel_err = abs(computed - expected) / abs(expected) if expected != 0 else abs(computed)
        assert rel_err < 1e-12, (
            f"Area mismatch for {shape}: computed={computed:.6e}, expected={expected:.6e}"
        )
        print(f"  [OK] {shape:20s}: A = {computed:.6e} m^2")

    print("  TEST 5 PASSED [OK]")


# =============================================================================
#  MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AltruxIQ — Stepped Solver Validation Suite")
    print("=" * 60)

    try:
        test_area_solver()
        test_pure_axial_two_segment()
        test_pure_axial_three_segment()
        test_pure_bending_cantilever()
        test_combined_axial_bending()

        print("\n" + "=" * 60)
        print("  ALL TESTS PASSED")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n  [X] TEST FAILED: {e}\n")
        raise
    except Exception as e:
        print(f"\n  [X] ERROR: {e}\n")
        raise
