#!/usr/bin/env python3
"""
AltruxIQ — Stepped Bar assembly & validation unit tests (P6 checkpoint-A)
==========================================================================
Verifies the two pure functions introduced when the ``define_stepped_segments``
monolith was decomposed into per-stage helpers:

* ``assemble_segments`` — builds the 12-key segment dicts consumed by
  ``solver.stepped_solver.solve_stepped_beam``. Its output MUST be
  byte-compatible with what the legacy monolith produced (same keys, same
  SI conversions, cumulative start/end coordinates).
* ``validate_segments_for_solve`` — the Stage [8] pre-solve gate. Each
  failure class must produce a human-readable message; a complete model
  must produce an empty list.

These are pure-function tests — no ``input()`` scripting is needed because
the two functions take explicit arguments (unlike the interactive helpers).

Run from the project root:
    PYTHONPATH=src py -3 test_stepped_assembly.py
"""

import sys
import os
import types

# --- PATH INJECTION (same pattern as test_stepped_solver.py) ---
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import numpy as np
# pyrefly: ignore [missing-import]
from ui.beam.stepped import assemble_segments, validate_segments_for_solve


PASS = "[OK]"
FAIL = "[FAIL]"
errs = []


# =============================================================================
#  Fixtures
# =============================================================================

def _rect_section(shape="Rectangle", width=0.05, height=0.2):
    """A section result tuple in the shape moi_solver returns:
    (Ix, shape, c, b, y_array, section_dims)."""
    Ix = width * height ** 3 / 12.0
    c = height / 2.0
    return (Ix, shape, c, width, np.linspace(-c, c, 101),
            {"type": shape, "width": width, "height": height})


def _steel_material():
    """A material dict in the shape select_material returns.
    Elastic Modulus is in GPa, Yield Strength in MPa (display units)."""
    return {
        "Material": "Steel",
        "Density": 7850,
        "Yield Strength": 250,
        "Ultimate Strength": 400,
        "Elastic Modulus": 200,
        "Poisson Ratio": 0.3,
        "Thermal Expansion": 12e-6,
        "Description": "test steel",
    }


def _aluminium_material():
    return {
        "Material": "Aluminium",
        "Density": 2700,
        "Yield Strength": 95,
        "Ultimate Strength": 110,
        "Elastic Modulus": 70,
        "Poisson Ratio": 0.33,
        "Thermal Expansion": 23e-6,
        "Description": "test aluminium",
    }


def _fake_state(segments, beam_length=None):
    """A stand-in for core.state.ProjectState — validate_segments_for_solve
    only reads .segments and .beam_length via getattr, so a lightweight
    namespace is enough (keeps the test free of the singleton)."""
    ns = types.SimpleNamespace()
    ns.segments = segments
    ns.beam_length = beam_length if beam_length is not None else (
        float(segments[-1]["end"]) if segments else 0.0
    )
    return ns


# =============================================================================
#  TEST 1: assemble_segments — basic 2-segment assembly
# =============================================================================

def test_assemble_basic_two_segment():
    print("\n" + "=" * 60)
    print("TEST 1: assemble_segments — basic 2-segment assembly")
    print("=" * 60)

    lengths = [3.0, 2.0]
    sections = [_rect_section(), _rect_section(width=0.04, height=0.18)]
    materials = [_steel_material(), _aluminium_material()]

    segs = assemble_segments(lengths, sections, materials)

    ok = []
    ok.append(segs is not None)

    # --- 12-key schema per segment ---
    expected_keys = {"start", "end", "length", "E", "A", "I",
                     "shape", "section_dims", "c", "b", "y_array",
                     "material_name", "yield_strength"}
    for i, seg in enumerate(segs):
        keys_ok = expected_keys <= set(seg.keys())
        ok.append(keys_ok)
        if not keys_ok:
            print(f'  {FAIL} segment {i+1} missing keys: '
                  f'{expected_keys - set(seg.keys())}')

    # --- cumulative start/end coordinates ---
    ok.append(abs(segs[0]["start"] - 0.0) < 1e-12)
    ok.append(abs(segs[0]["end"] - 3.0) < 1e-12)
    ok.append(abs(segs[1]["start"] - 3.0) < 1e-12)
    ok.append(abs(segs[1]["end"] - 5.0) < 1e-12)

    # --- length field stored ---
    ok.append(abs(segs[0]["length"] - 3.0) < 1e-12)
    ok.append(abs(segs[1]["length"] - 2.0) < 1e-12)

    # --- SI conversions: E GPa→Pa, yield MPa→Pa ---
    ok.append(abs(segs[0]["E"] - 200e9) < 1.0)
    ok.append(abs(segs[1]["E"] - 70e9) < 1.0)
    ok.append(abs(segs[0]["yield_strength"] - 250e6) < 1.0)
    ok.append(abs(segs[1]["yield_strength"] - 95e6) < 1.0)

    # --- material_name carried through ---
    ok.append(segs[0]["material_name"] == "Steel")
    ok.append(segs[1]["material_name"] == "Aluminium")

    # --- section fields carried through ---
    ok.append(segs[0]["shape"] == "Rectangle")
    ok.append(abs(segs[0]["I"] - (0.05 * 0.2 ** 3 / 12.0)) < 1e-15)
    ok.append(isinstance(segs[0]["y_array"], np.ndarray))

    passed = all(ok)
    print(f'  {PASS if passed else FAIL} 2-segment assembly: schema, coords, '
          f'conversions, carry-through all correct')
    if not passed:
        errs.append(1)
    return passed


# =============================================================================
#  TEST 2: assemble_segments — single segment (edge case)
# =============================================================================

def test_assemble_single_segment():
    print("\n" + "=" * 60)
    print("TEST 2: assemble_segments — single segment")
    print("=" * 60)

    segs = assemble_segments([4.0], [_rect_section()], [_steel_material()])
    ok = segs is not None
    ok = ok and abs(segs[0]["start"] - 0.0) < 1e-12
    ok = ok and abs(segs[0]["end"] - 4.0) < 1e-12
    ok = ok and abs(segs[0]["length"] - 4.0) < 1e-12

    print(f'  {PASS if ok else FAIL} single segment: start=0, end=length=4.0')
    if not ok:
        errs.append(2)
    return ok


# =============================================================================
#  TEST 3: assemble_segments — rejects inconsistent inputs
# =============================================================================

def test_assemble_rejects_inconsistent():
    print("\n" + "=" * 60)
    print("TEST 3: assemble_segments — rejects inconsistent inputs")
    print("=" * 60)

    sec = _rect_section()
    mat = _steel_material()

    cases = [
        ("empty lengths",        [],            [sec],          [mat]),
        ("empty sections",       [3.0],         [],             [mat]),
        ("empty materials",      [3.0],         [sec],          []),
        ("length mismatch",      [3.0, 2.0],    [sec],          [mat]),
        ("None material entry",  [3.0],         [sec],          [None]),
    ]
    all_ok = True
    for label, L, S, M in cases:
        result = assemble_segments(L, S, M)
        case_ok = result is None
        all_ok = all_ok and case_ok
        print(f'  {PASS if case_ok else FAIL} rejected: {label}')

    if not all_ok:
        errs.append(3)
    return all_ok


# =============================================================================
#  TEST 4: assemble_segments — byte-compatible with the solver contract
#         (feed assembled output straight into solve_stepped_beam)
# =============================================================================

def test_assemble_feeds_solver():
    """End-to-end: assemble_segments output must be directly consumable by
    solve_stepped_beam — this pins the schema to the solver's contract
    (same one test_stepped_solver.py::rect_seg builds by hand)."""
    print("\n" + "=" * 60)
    print("TEST 4: assemble_segments — output feeds solve_stepped_beam")
    print("=" * 60)

    # pyrefly: ignore [missing-import]
    from solver.stepped_solver import solve_stepped_beam

    lengths = [3.0, 2.0]
    sections = [_rect_section(), _rect_section(width=0.04, height=0.18)]
    materials = [_steel_material(), _aluminium_material()]
    segs = assemble_segments(lengths, sections, materials)

    P = 10_000.0
    result = solve_stepped_beam(
        segs,
        [{"pos": 0, "dof": (1, 1, 1)}],
        pointloads=[[5.0, P, 0]],
    )

    # Axial force should be constant = P across the bar (pure tension).
    axial_ok = np.allclose(result["AxialForce"], P, rtol=1e-9)
    # Analytical displacement: P*(L1/(E1*A1) + L2/(E2*A2))
    A1 = 0.05 * 0.2
    A2 = 0.04 * 0.18
    d_exp = P * (3.0 / (200e9 * A1) + 2.0 / (70e9 * A2))
    disp_ok = abs(result["AxialDisplacement"][-1] - d_exp) / d_exp < 1e-9

    print(f'  {PASS if axial_ok else FAIL} solver accepted assembled segments; '
          f'axial force = {P:.1f} N')
    print(f'  {PASS if disp_ok else FAIL} displacement matches analytic: '
          f'{result["AxialDisplacement"][-1]:.6e} (exp {d_exp:.6e})')

    passed = axial_ok and disp_ok
    if not passed:
        errs.append(4)
    return passed


# =============================================================================
#  TEST 5: validate_segments_for_solve — accepts a complete model
# =============================================================================

def test_validate_accepts_complete():
    print("\n" + "=" * 60)
    print("TEST 5: validate_segments_for_solve — accepts complete model")
    print("=" * 60)

    segs = assemble_segments([3.0, 2.0],
                             [_rect_section(), _rect_section()],
                             [_steel_material(), _aluminium_material()])
    st = _fake_state(segs)
    problems = validate_segments_for_solve(st)
    ok = problems == []
    print(f'  {PASS if ok else FAIL} complete model → no problems '
          f'(got: {problems})')
    if not ok:
        errs.append(5)
    return ok


# =============================================================================
#  TEST 6: validate_segments_for_solve — catches each failure class
# =============================================================================

def test_validate_catches_failures():
    print("\n" + "=" * 60)
    print("TEST 6: validate_segments_for_solve — catches each failure class")
    print("=" * 60)

    good_seg = {
        "start": 0.0, "end": 3.0, "length": 3.0,
        "E": 200e9, "A": 0.01, "I": 1e-5,
        "shape": "Rectangle", "section_dims": {},
        "c": 0.1, "b": 0.05, "y_array": np.array([]),
        "material_name": "Steel", "yield_strength": 250e6,
    }

    def _msg_any(problems, substr):
        return any(substr in p for p in problems)

    # (label, segments, beam_length, expected-substring-that-must-appear)
    cases = [
        ("no segments",         [],                                0.0,  "No segments defined"),
        ("first start != 0",    [{**good_seg, "start": 1.0, "end": 4.0}], 4.0, "does not start at x = 0"),
        ("gap between segs",    [good_seg, {**good_seg, "start": 4.0, "end": 6.0}], 6.0, "Gap/overlap between segment 1 and segment 2"),
        ("missing shape",       [{**good_seg, "shape": ""}],      3.0,  "Segment 1 has no cross-section"),
        ("missing material",    [{**good_seg, "material_name": ""}], 3.0, "Segment 1 has no material"),
        ("invalid E",           [{**good_seg, "E": 0}],           3.0,  "Segment 1 has an invalid elastic modulus"),
        ("invalid A",           [{**good_seg, "A": 0}],           3.0,  "Segment 1 has an invalid cross-sectional area"),
        ("beam_length mismatch", [good_seg],                      99.0, "does not match the segments"),
    ]

    all_ok = True
    for label, segs, blen, substr in cases:
        st = _fake_state(segs, beam_length=blen)
        problems = validate_segments_for_solve(st)
        case_ok = _msg_any(problems, substr)
        all_ok = all_ok and case_ok
        print(f'  {PASS if case_ok else FAIL} caught: {label}')

    if not all_ok:
        errs.append(6)
    return all_ok


# =============================================================================
#  Runner
# =============================================================================

def main():
    print("\n" + "=" * 60)
    print("AltruxIQ — Stepped Bar Assembly & Validation Tests (P6 ckpt-A)")
    print("=" * 60)

    results = [
        test_assemble_basic_two_segment(),
        test_assemble_single_segment(),
        test_assemble_rejects_inconsistent(),
        test_assemble_feeds_solver(),
        test_validate_accepts_complete(),
        test_validate_catches_failures(),
    ]

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    names = [
        "assemble: basic 2-segment",
        "assemble: single segment",
        "assemble: rejects inconsistent",
        "assemble: feeds solver",
        "validate: accepts complete",
        "validate: catches failures",
    ]
    for name, ok in zip(names, results):
        print(f'  [{"PASS" if ok else "FAIL"}]  {name}')

    print("")
    if all(results):
        print("  [PASS] ALL TESTS PASSED")
    else:
        print(f"  [FAIL] {len(errs)} test(s) failed: {errs}")
    print("=" * 60)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
