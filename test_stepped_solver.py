#!/usr/bin/env python3
"""
AltruxIQ — Stepped Solver Validation Suite
============================================
Independent verification of the stepped_solver.py core against analytical
solutions for axial, bending, distributed, and triangular loading.

Run from the project root:
    .venv\Scripts\python.exe test_stepped_solver.py
"""

import sys
import os

# --- PATH INJECTION ---
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# pyrefly: ignore [missing-import]
import numpy as np
# pyrefly: ignore [missing-import]
from solver.stepped_solver import solve_stepped_beam
# pyrefly: ignore [missing-import]
from solver.area_solver import area_from_section


PASS = "[OK]"
FAIL = "[FAIL]"
errs = []


# =============================================================================
#  HELPER
# =============================================================================

def rect_seg(start, end, E=200e9, A=500e-6, I=8.33e-6):
    """Create a rectangular segment dict for quick testing."""
    return {
        'start': start, 'end': end, 'E': E, 'A': A, 'I': I,
        'shape': 'Rectangle',
        'section_dims': {'type': 'Rectangle', 'width': 0.05, 'height': 0.2},
        'c': 0.1, 'b': 0.05, 'y_array': np.linspace(-0.1, 0.1, 1001),
    }


# =============================================================================
#  TEST 5: area_solver.py — All 8 Cross-Section Types
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

    all_ok = True
    for shape, dims, expected in cases:
        computed = area_from_section(shape, dims)
        rel_err = abs(computed - expected) / abs(expected) if expected != 0 else abs(computed)
        ok = rel_err < 1e-12
        if not ok:
            all_ok = False
            print(f"  {FAIL} {shape:20s}: A = {computed:.6e} m^2 (exp {expected:.6e})")
        else:
            print(f"  {PASS} {shape:20s}: A = {computed:.6e} m^2")

    print(f"  TEST 5 {'PASSED' if all_ok else 'FAILED'}")
    if not all_ok:
        errs.append(5)
    return all_ok


# =============================================================================
#  TEST 1: Pure Axial — Two-segment stepped bar
# =============================================================================

def test_pure_axial_two_segment():
    """
    Segment 1: Steel,  L=3.0 m, A=500e-6 m^2, E=200e9 Pa
    Segment 2: Aluminium, L=2.0 m, A=400e-6 m^2, E=70e9 Pa
    Fixed at x=0.  Tensile load P = 10 kN at x=5.0 m.
    """
    print("\n" + "=" * 60)
    print("TEST 1: Pure Axial — Two-Segment Stepped Bar")
    print("=" * 60)

    P = 10_000.0
    L1, E1, A1 = 3.0, 200e9, 500e-6
    L2, E2, A2 = 2.0, 70e9, 400e-6

    segs = [rect_seg(0, L1, E=E1, A=A1), rect_seg(L1, L1 + L2, E=E2, A=A2)]
    r = solve_stepped_beam(segs, [{'pos': 0, 'dof': (1, 1, 1)}], pointloads=[[L1 + L2, P, 0]])

    ok1 = np.allclose(r['AxialForce'], P, rtol=1e-9)
    d_exp = P * (L1 / (E1 * A1) + L2 / (E2 * A2))
    ok2 = abs(r['AxialDisplacement'][-1] - d_exp) / d_exp < 1e-9

    print(f'  {PASS if ok1 else FAIL} Axial force constant:     {P:.1f} N')
    print(f'  {PASS if ok2 else FAIL} Total displacement:       {r["AxialDisplacement"][-1]:.6e} m (exp {d_exp:.6e})')

    if not (ok1 and ok2):
        errs.append(1)
    return ok1 and ok2


# =============================================================================
#  TEST 2: Pure Axial — Three-segment (Image Geometry)
# =============================================================================

def test_pure_axial_three_segment():
    """
    Steel    : L=2.5 m, A=500 mm^2, E=200 GPa
    Aluminium: L=2.0 m, A=400 mm^2, E=70  GPa
    Bronze   : L=1.5 m, A=200 mm^2, E=110 GPa
    Fixed at x=0.  Tensile load P = 20 kN at x=6.0 m.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Pure Axial — Three-Segment (Image Geometry)")
    print("=" * 60)

    P = 20_000.0
    seg_data = [
        (0.0, 2.5, 200e9, 500e-6),
        (2.5, 4.5, 70e9, 400e-6),
        (4.5, 6.0, 110e9, 200e-6),
    ]

    segments = []
    for start, end, E, A in seg_data:
        segments.append(rect_seg(start, end, E=E, A=A))

    r = solve_stepped_beam(
        segments, [{'pos': 0.0, 'dof': (1, 1, 1)}],
        pointloads=[[6.0, P, 0.0]], num_points=2001,
    )

    ok1 = np.allclose(r['AxialForce'], P, rtol=1e-9)
    d_exp = sum(P * (end - start) / (E * A) for start, end, E, A in seg_data)
    ok2 = abs(r['AxialDisplacement'][-1] - d_exp) / d_exp < 1e-9

    print(f'  {PASS if ok1 else FAIL} Axial force constant:     {P:.1f} N')
    print(f'  {PASS if ok2 else FAIL} Total displacement:       {r["AxialDisplacement"][-1]:.6e} m (exp {d_exp:.6e})')

    # Per-segment displacement
    ok3 = True
    for x_end in [2.5, 4.5, 6.0]:
        idx = np.argmin(np.abs(r['X_Field'] - x_end))
        x_actual = r['X_Field'][idx]
        d_num = r['AxialDisplacement'][idx]
        d_an = 0.0
        for s, e, E_mat, A_mat in seg_data:
            if x_actual >= e - 1e-9:
                d_an += P * (e - s) / (E_mat * A_mat)
            elif x_actual > s + 1e-9:
                d_an += P * (x_actual - s) / (E_mat * A_mat)
                break
            else:
                break
        ok_seg = abs(d_num - d_an) / abs(d_an) < 1e-9
        if not ok_seg:
            ok3 = False
        print(f'  {PASS if ok_seg else FAIL} Displacement at x={x_actual:.4f}m: {d_num:.6e} (exp {d_an:.6e})')

    if not (ok1 and ok2 and ok3):
        errs.append(2)
    return ok1 and ok2 and ok3


# =============================================================================
#  TEST 3: Pure Bending — Cantilever with point load at free end
# =============================================================================

def test_pure_bending_cantilever():
    """
    Single segment: L=5.0 m, E=200 GPa, I=8.33e-6 m^4
    Fixed at x=0.  Downward point load P = 1 kN at x=5.0 m.
    """
    print("\n" + "=" * 60)
    print("TEST 3: Pure Bending — Cantilever with End Load")
    print("=" * 60)

    P = 1_000.0
    L = 5.0
    E = 200e9
    I = 8.33e-6

    segs = [rect_seg(0, L, E=E, I=I, A=0.01)]
    r = solve_stepped_beam(segs, [{'pos': 0, 'dof': (1, 1, 1)}], pointloads=[[L, 0, -P]])

    X = r['X_Field']
    ok_sf = np.allclose(r['Total_ShearForce'], P, rtol=1e-9)
    M_an = -P * (L - X)
    ok_bm = np.max(np.abs(r['Total_BendingMoment'] - M_an)) < 1e-6
    v_an = -P * L ** 3 / (3.0 * E * I)
    ok_df = abs(r['Deflection'][-1] - v_an) / abs(v_an) < 1e-6

    print(f'  {PASS if ok_sf else FAIL} Shear force constant:     {P:.1f} N')
    print(f'  {PASS if ok_bm else FAIL} Bending moment error:     {np.max(np.abs(r["Total_BendingMoment"] - M_an)):.6e} N*m')
    print(f'  {PASS if ok_df else FAIL} Tip deflection:           {r["Deflection"][-1]:.6e} m (exp {v_an:.6e})')

    if not all([ok_sf, ok_bm, ok_df]):
        errs.append(3)
    return all([ok_sf, ok_bm, ok_df])


# =============================================================================
#  TEST 4: Combined Axial + Bending — Stepped cantilever
# =============================================================================

def test_combined_axial_bending():
    """
    Two-segment cantilever with both axial and transverse end loads.
    """
    print("\n" + "=" * 60)
    print("TEST 4: Combined Axial + Bending — Stepped Cantilever")
    print("=" * 60)

    Fx = 10_000.0
    Fy = -2_000.0

    segs = [
        rect_seg(0, 3.0, E=200e9, A=500e-6, I=8.33e-6),
        rect_seg(3.0, 5.0, E=70e9, A=400e-6, I=5.0e-6),
    ]

    r = solve_stepped_beam(segs, [{'pos': 0, 'dof': (1, 1, 1)}], pointloads=[[5.0, Fx, Fy]])

    ok_ax = np.allclose(r['AxialForce'], Fx, rtol=1e-9)
    ok_sh = np.allclose(r['Total_ShearForce'], -Fy, rtol=1e-9)

    R = r['Reactions'][0]
    ok_Rx = np.isclose(R['Fx'], -Fx, rtol=1e-9)
    ok_Ry = np.isclose(R['Fy'], -Fy, rtol=1e-9)
    ok_M = np.isclose(R['M'], -Fy * 5.0, rtol=1e-9)

    sum_fx = sum(x['Fx'] for x in r['Reactions']) + Fx
    sum_fy = sum(x['Fy'] for x in r['Reactions']) + Fy
    sum_m = sum(x['M'] for x in r['Reactions']) + Fy * 5.0
    ok_eq = max(abs(sum_fx), abs(sum_fy), abs(sum_m)) < 1e-6

    print(f'  {PASS if ok_ax else FAIL} Axial force constant:     {Fx:.1f} N')
    print(f'  {PASS if ok_sh else FAIL} Shear force constant:     {-Fy:.1f} N')
    print(f'  {PASS if ok_Rx else FAIL} Reaction Fx:              {R["Fx"]:.1f} (exp {-Fx:.1f})')
    print(f'  {PASS if ok_Ry else FAIL} Reaction Fy:              {R["Fy"]:.1f} (exp {-Fy:.1f})')
    print(f'  {PASS if ok_M else FAIL} Reaction M:               {R["M"]:.1f} (exp {-Fy * 5.0:.1f})')
    print(f'  {PASS if ok_eq else FAIL} Global equilibrium:       SumFx={sum_fx:.2e}, SumFy={sum_fy:.2e}, SumM={sum_m:.2e}')

    if not all([ok_ax, ok_sh, ok_Rx, ok_Ry, ok_M, ok_eq]):
        errs.append(4)
    return all([ok_ax, ok_sh, ok_Rx, ok_Ry, ok_M, ok_eq])


# =============================================================================
#  NEW TEST A: Simply Supported Beam, Full-Span UDL
# =============================================================================

def test_ss_udl():
    """
    Analytical: Ra = Rb = wL/2, M_mid = wL^2/8, d_max = -5wL^4/(384EI)
    """
    print("\n" + "=" * 60)
    print("TEST A: Simply Supported Beam — Full-Span UDL")
    print("=" * 60)

    w = 1_000.0
    L = 10.0
    E = 200e9
    I = 1e-4

    segs = [rect_seg(0, L, E=E, I=I)]
    r = solve_stepped_beam(segs,
        [{'pos': 0, 'dof': (1, 1, 0)}, {'pos': L, 'dof': (0, 1, 0)}],
        distributedloads=[[0, L, -w]],
    )

    Ra = next(x['Fy'] for x in r['Reactions'] if abs(x['pos'] - 0) < 1e-6)
    Rb = next(x['Fy'] for x in r['Reactions'] if abs(x['pos'] - L) < 1e-6)
    M_field = r['Total_BendingMoment']
    X_field = r['X_Field']
    mid_idx = np.argmin(np.abs(X_field - L / 2))
    M_mid = M_field[mid_idx]
    d_max = np.min(r['Deflection'])
    d_an = -5.0 * w * L ** 4 / (384.0 * E * I)

    ok_Ra = abs(Ra - w * L / 2.0) / abs(w * L / 2.0) < 1e-9
    ok_Rb = abs(Rb - w * L / 2.0) / abs(w * L / 2.0) < 1e-9
    ok_M = abs(M_mid - w * L ** 2 / 8.0) / (w * L ** 2 / 8.0) < 1e-4
    ok_d = abs(d_max - d_an) / abs(d_an) < 1e-4

    print(f'  {PASS if ok_Ra else FAIL} Reaction Ra:              {Ra:.2f} N (exp {w*L/2:.2f})')
    print(f'  {PASS if ok_Rb else FAIL} Reaction Rb:              {Rb:.2f} N (exp {w*L/2:.2f})')
    print(f'  {PASS if ok_M  else FAIL} M at midspan:             {M_mid:.2f} N*m (exp {w*L**2/8:.2f})')
    print(f'  {PASS if ok_d  else FAIL} Max deflection:           {d_max*1e3:.4f} mm (exp {d_an*1e3:.4f} mm)')

    if not all([ok_Ra, ok_Rb, ok_M, ok_d]):
        errs.append('A')
    return all([ok_Ra, ok_Rb, ok_M, ok_d])


# =============================================================================
#  NEW TEST B: Cantilever with Triangular Load (peak at root, zero at tip)
# =============================================================================

def test_cantilever_triangle():
    """
    Analytical: Ry = w_peak * L / 2, M_wall = w_peak * L^2 / 6
    """
    print("\n" + "=" * 60)
    print("TEST B: Cantilever — Triangular Load (Peak at Root)")
    print("=" * 60)

    w_peak = 6_000.0
    L = 4.0
    E = 200e9
    I = 8.33e-6

    segs = [rect_seg(0, L, E=E, I=I)]
    r = solve_stepped_beam(segs,
        [{'pos': 0, 'dof': (1, 1, 1)}],
        triangleloads=[[0, L, -w_peak, 0]],
    )

    Ry_wall = next(x['Fy'] for x in r['Reactions'] if abs(x['pos']) < 1e-6)
    Mw = next(x['M'] for x in r['Reactions'] if abs(x['pos']) < 1e-6)
    Ry_an = w_peak * L / 2.0
    Mw_an = w_peak * L ** 2 / 6.0

    ok_Ry = abs(Ry_wall - Ry_an) / Ry_an < 1e-6
    ok_Mw = abs(Mw - Mw_an) / Mw_an < 1e-6

    print(f'  {PASS if ok_Ry else FAIL} Reaction Ry:              {Ry_wall:.2f} N (exp {Ry_an:.2f})')
    print(f'  {PASS if ok_Mw else FAIL} Moment at wall:           {Mw:.2f} N*m (exp {Mw_an:.2f})')

    if not all([ok_Ry, ok_Mw]):
        errs.append('B')
    return all([ok_Ry, ok_Mw])


# =============================================================================
#  NEW TEST C: Verify Old Reversed-Centroid Bug IS Fixed
# =============================================================================

def test_bug_fix_verification():
    """
    The old Bug 1 would place the triangular load centroid at 2L/3 from start,
    giving M_wall = w_peak * L^2 / 3 (wrong by 2x).
    Correct M_wall = w_peak * L^2 / 6.
    """
    print("\n" + "=" * 60)
    print("TEST C: Bug Fix Verification — Old Centroid Reversal")
    print("=" * 60)

    w_peak = 6_000.0
    L = 4.0

    # Reuse results from Test B (same geometry)
    segs = [rect_seg(0, L, E=200e9, I=8.33e-6)]
    r = solve_stepped_beam(segs,
        [{'pos': 0, 'dof': (1, 1, 1)}],
        triangleloads=[[0, L, -w_peak, 0]],
    )
    Mw = next(x['M'] for x in r['Reactions'] if abs(x['pos']) < 1e-6)

    wrong_Mw = w_peak * L ** 2 / 3.0
    bug_present = abs(Mw - wrong_Mw) / wrong_Mw < 0.01
    ok = not bug_present

    print(f'  {PASS if ok else FAIL} M_wall = {Mw:.2f} N*m (old bug would give {wrong_Mw:.2f})')
    print(f'  {PASS if ok else FAIL} Bug is fixed: M_wall is correct (not doubled)')

    if not ok:
        errs.append('C')
    return ok


# =============================================================================
#  MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AltruxIQ — Stepped Solver Validation Suite")
    print("=" * 60)

    results = []
    results.append(("Area Solver (8 shapes)", test_area_solver()))
    results.append(("Pure Axial 2-Segment", test_pure_axial_two_segment()))
    results.append(("Pure Axial 3-Segment (Image)", test_pure_axial_three_segment()))
    results.append(("Pure Bending Cantilever", test_pure_bending_cantilever()))
    results.append(("Combined Axial+Bending", test_combined_axial_bending()))
    results.append(("SS Beam UDL", test_ss_udl()))
    results.append(("Cantilever Triangle Load", test_cantilever_triangle()))
    results.append(("Bug Fix Verification", test_bug_fix_verification()))

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'[PASS]' if ok else '[FAIL]'}  {name}")

    print("")
    if errs:
        print(f"  [FAIL] FAILURES in tests: {errs}")
    else:
        print("  [PASS] ALL TESTS PASSED")
    print("=" * 60 + "\n")
