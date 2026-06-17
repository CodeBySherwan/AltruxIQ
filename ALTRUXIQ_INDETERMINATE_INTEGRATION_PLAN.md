# AltruxIQ — IndeterminateBeam Integration Plan
**Version:** 1.0  
**Date of API Audit:** June 2026  
**Package installed:** `indeterminatebeam==2.4.0`  
**Purpose:** Replace the custom `main_solver.py` with the `indeterminatebeam` Python package as the analysis backend. All facts below are derived from live API probing — not assumptions.

---

## 0. Quick Reference: What Is Changing and Why

| Current State | Target State |
|---|---|
| Custom `main_solver.py` — only Simple + Cantilever | `indeterminatebeam` package — Simple, Cantilever, Fixed-Fixed, Propped Cantilever, Continuous (n-span) |
| Manual BVP solving via section method (O(n²) Python loops) | SymPy-based stiffness method (exact, indeterminate-capable) |
| Separate `stress_solver.calculate_beam_deflection()` using double numerical integration | Deflection extracted directly from IndeterminateBeam's stiffness solution (exact for all beam types) |
| `Reactions` is a positional numpy array with beam-type-dependent index order | `Reactions` becomes a list of dicts, one per support — beam-type-independent |

**What does NOT change:**  
`moi_solver.py`, `stress_solver.py` (cross-section stress, Q(y), FOS), all plotting modules, `materials_database.py`, and the full CLI menu structure remain untouched. Only the solver backend and the parts of `cli.py` that call it are updated.

---

## 1. Dependency

```bash
pip install indeterminatebeam
```

Current stable version: **2.4.0**. No other new dependencies are introduced — the package pulls SymPy and Plotly which are already present.

---

## 2. PROVEN Sign Convention Table (from live probing)

This is the most critical section. Every load mapping below was verified by running the package and checking numerical output. **Do not invert without re-testing.**

### 2.1 Load Input Signs

| AltruxIQ storage format | Rule | IndeterminateBeam constructor |
|---|---|---|
| `pointloads[n] = [pos, Fx, Fy]` where **Fy+ = downward** | Negate Fy | `PointLoadV(-Fy, pos)` |
| `pointloads[n] = [pos, Fx, 0]` where **Fx+ = rightward** | No flip | `PointLoad(Fx, pos, 0)` |
| `distributedloads[n] = [start, end, w]` where **w+ = downward** | Negate w | `UDLV(-w, (start, end))` |
| `momentloads[n] = [pos, M]` where **M+ = CCW** | No flip | `PointTorque(M, pos)` |
| `triangleloads[n] = [start, end, peak, low]` where **peak is at start, low at end, both + = downward** | Negate both | `TrapezoidalLoadV(force=(-peak, -low), span=(start, end))` |

> **Proof for PointLoadV:** `PointLoadV(-10000, 2.5)` on a 5 m simply supported beam gives Va=5000, Vb=5000 (correct for a 10 kN downward load). Positive PointLoadV = **upward**.

> **Proof for UDLV:** `UDLV(-1000, (0,4))` gives Va=Vb=2000 (correct for 1 kN/m downward over 4 m). Positive UDLV = **upward**.

> **Proof for PointTorque:** `PointTorque(1000, 2)` on a 4 m beam gives Va=+250, which matches CCW torque lifting the left support. **Same CCW+ convention as AltruxIQ — no flip needed.**

> **Proof for TrapezoidalLoadV:** constructor signature is `TrapezoidalLoadV(force=(start_val, end_val), span=(start_x, end_x))`. `force` values follow the same sign as PointLoadV (positive = upward).

### 2.2 Result Output Signs

| Quantity | IndeterminateBeam sign | AltruxIQ sign | Action |
|---|---|---|---|
| `get_reaction(x, 'y')` | Positive = upward | Positive = upward | **No flip.** Store directly as `Va`, `Vb`, etc. |
| `get_reaction(x, 'm')` | Positive = CCW | Positive = CCW | **No flip.** Store directly as `Ma`. |
| `get_reaction(x, 'x')` | Positive = rightward | Positive = rightward | **No flip.** Store as `Ha`. |
| `get_shear_force(x)` | Standard (left section: up = positive) | Same convention (post BUG-08 fix) | **No flip.** |
| `get_bending_moment(x)` | Positive = sagging (confirmed: +12000 at midspan under downward load) | Positive = sagging | **No flip.** |
| `get_deflection(x)` | Negative = downward (confirmed: midspan deflection returns `-0.01489` under downward load) | Negative = downward (standard) | **No flip.** |

---

## 3. New Reactions Format (Breaking Change in `cli.py`)

### 3.1 Problem with the old format

Old `Reactions` was a positional numpy array whose indices meant different things depending on `beam_type`:
- Simple: `Reactions = [Va, Vb, Ha]` — index 0 is Va, index 1 is Vb  
- Cantilever: `Reactions = [Va, Ha, Ma]` — index 0 is Va, index 1 is Ha  

This made every downstream consumer check `beam_type` before indexing. It also cannot represent Fixed-Fixed or Continuous beams which have more than two supports.

### 3.2 New format

Replace `Reactions` (numpy array) with `Reactions` as a **Python list of dicts**, one dict per support. Keep the global variable name `Reactions` to minimise CLI changes.

```python
Reactions = [
    {"pos": 0.0,  "Fy": 5000.0, "Fx": 0.0, "M": 0.0},
    {"pos": 5.0,  "Fy": 5000.0, "Fx": 0.0, "M": 0.0},
    # For continuous beams, more dicts follow
]
```

### 3.3 Downstream code that must be updated in `cli.py`

Locate every block that unpacks `Reactions` by index and replace with dict access. There are exactly **two such blocks** in the current `cli.py`, both in `selection == '8'` (Analysis/Simulation):

**Block 1 — after `sub_choice == '1'` (run analysis):**
```python
# OLD:
if beam_type == "Simple":
    Va = Reactions[0]; Ha = Reactions[2]; Vb = Reactions[1]
else:
    Va = Reactions[0]; Ha = Reactions[1]; Ma = Reactions[2]

# NEW (works for all beam types):
Va = next((r["Fy"] for r in Reactions if r["pos"] == A), 0.0)
Ha = next((r["Fx"] for r in Reactions if r["pos"] == A), 0.0)
Vb = next((r["Fy"] for r in Reactions if r["pos"] == B), 0.0)
Ma = next((r["M"]  for r in Reactions if r["pos"] == A), 0.0)
```

**Block 2 — `sub_choice == '2'` (view analysis results):** Same replacement pattern.

### 3.4 `plot_reaction_diagram()` in `beam_plot.py`

The current function signature is `plot_reaction_diagram(A, B, reactions, support_types)` and it hardcodes `Va, Vb, Ha = reactions[0], reactions[1], reactions[2]`. This must be updated to accept the new list-of-dicts format. Pass the full `Reactions` list and iterate over it to draw arrows.

### 3.5 JSON persistence (`save_project()` / `load_project()`)

`safe_serialize()` handles numpy arrays but the new `Reactions` is already a plain Python list of dicts — JSON serialisable natively. Update `save_project()` to write it directly and `load_project()` to read it back as-is (no `np.array()` conversion on load).

---

## 4. Deflection: Paradigm Shift

**Old approach:** After analysis, `cli.py` Menu 8 Sub-choice 3 calls `calculate_beam_deflection()` from `stress_solver.py` which performs double numerical integration of M(x)/(EI). This is approximate (no BC correction for off-end supports) and fails for indeterminate beams (reactions from the indeterminate solver would be correct, but the double integration still cannot enforce the correct boundary conditions without explicit correction).

**New approach:** `indeterminatebeam` computes deflection as part of its stiffness solution — exact, BC-compliant, works for all beam types. The adapter extracts deflection as a numpy array at the same time as SFD and BMD, and returns it alongside them.

**What this means for `cli.py`:**
- Menu 8, Sub-choice 3 ("Calculate Deflection") is simplified: it just calls the adapter again (or uses the result already stored in `Deflection` if the adapter populates it during the main solve).
- `calculate_beam_deflection()` in `stress_solver.py` is **kept but demoted to legacy**. Add a docstring note: `LEGACY: Use the deflection array returned by indeterminate_solver.solve_beam() for all beam types.`

**Recommended approach — populate `Deflection` at solve time:**  
Have the adapter return `(X_Field, Total_ShearForce, Total_BendingMoment, Deflection, Reactions)` so that one call to `solve_beam()` populates all five globals. Then Sub-choice 3 becomes a display-only step (call `display_deflection_analysis()`), and `project_state["deflection_calculated"]` is set to `True` immediately after the main analysis.

---

## 5. File Action Summary

| File | Action | Reason |
|---|---|---|
| `src/solver/indeterminate_solver.py` | **CREATE** | New adapter between AltruxIQ and IndeterminateBeam package |
| `src/solver/main_solver.py` | **DELETE** | Fully replaced by adapter |
| `src/Temporary/Improved Solver.py` | **DELETE** | Staging copy of main_solver.py — no longer needed |
| `src/ui/cli.py` | **MODIFY** | Update solver call, Reactions unpacking, remove deflection sub-step, add new beam types |
| `src/ui/inputs.py` | **MODIFY** | Add Fixed-Fixed, Propped Cantilever, Continuous options to `Beam_Classification()` |
| `src/ui/Menus.py` | **MODIFY** | Update beam classification display; add support entry UI for new types |
| `src/plotting/beam_plot.py` | **MODIFY** | Update `plot_reaction_diagram()` to accept list-of-dicts Reactions format |
| `src/solver/stress_solver.py` | **NO CHANGE** | Shear stress, Q(y), bending stress, FOS — not provided by IndeterminateBeam |
| `src/solver/moi_solver.py` | **NO CHANGE** | Cross-section geometry unaffected |
| `src/plotting/main_plotting.py` | **NO CHANGE** | All plot functions consume numpy arrays — format unchanged |
| `src/plotting/plotting_helper.py` | **NO CHANGE** | Low-level trace builders — unaffected |
| `src/database/materials_database.py` | **NO CHANGE** | Unaffected |
| `src/ui/Menus.py` (most functions) | **NO CHANGE** (see exceptions above) | Display logic is independent of solver |

---

## 6. CREATE: `src/solver/indeterminate_solver.py`

This is the single new file. It is the complete replacement for `main_solver.py`. All AltruxIQ callers currently import from `main_solver`; the only call site is `cli.py` (two calls: `solve_simple_beam` and `solve_cantilever_beam`). Both are replaced by a single call to `solve_beam()`.

### 6.1 Function signature

```python
def solve_beam(
    beam_length: float,
    beam_type: str,
    supports: list,
    pointloads: list,
    distributedloads: list,
    momentloads: list,
    triangleloads: list,
    E: float = 210e9,
    I: float = 8.33e-6,
    num_points: int = 2001,
) -> dict:
```

**`beam_type` values (new set):**
- `"Simple"` — pin + roller (existing)
- `"Cantilever"` — fixed at x=0 (existing)
- `"Fixed-Fixed"` — fixed at both ends (NEW)
- `"Propped"` — fixed at x=0, roller at x=beam_length (NEW)
- `"Continuous"` — arbitrary supports passed via `supports` list (NEW)

**`supports` parameter:** A list of dicts. For beam types other than `"Continuous"`, this is **constructed internally** by the adapter based on `beam_type` and the positions `A`, `B`. For `"Continuous"`, the caller must supply the full list.

```python
# Structure of each support dict
{
    "pos": float,           # x-coordinate (m)
    "dof": tuple,           # e.g. (1,1,0) for pin, (0,1,0) for roller, (1,1,1) for fixed
    "ky": float | None,     # optional vertical spring stiffness (N/m)
    "kx": float | None,     # optional horizontal spring stiffness (N/m)
}
```

### 6.2 Return value

```python
{
    "X_Field":            np.ndarray,   # shape (num_points,) — positions along beam
    "Total_ShearForce":   np.ndarray,   # shape (num_points,) — SFD in N
    "Total_BendingMoment": np.ndarray,  # shape (num_points,) — BMD in N·m (sagging positive)
    "Deflection":         np.ndarray,   # shape (num_points,) — in m (downward negative)
    "Reactions":          list,         # list of dicts — see Section 3.2
}
```

### 6.3 Complete implementation spec

```python
# src/solver/indeterminate_solver.py
import numpy as np
from indeterminatebeam import (
    Beam, Support,
    PointLoadV, PointLoad,
    UDLV, TrapezoidalLoadV,
    PointTorque,
)


def _build_supports(beam_type: str, beam_length: float, supports: list) -> list:
    """
    Returns a list of Support objects.
    For non-Continuous beam types, ignores the `supports` argument
    and builds the correct supports from `beam_type` and `beam_length`.
    """
    if beam_type == "Simple":
        A = supports[0]["pos"]
        B = supports[1]["pos"]
        return [Support(A, (1, 1, 0)), Support(B, (0, 1, 0))]

    elif beam_type == "Cantilever":
        return [Support(0, (1, 1, 1))]

    elif beam_type == "Fixed-Fixed":
        return [Support(0, (1, 1, 1)), Support(beam_length, (1, 1, 1))]

    elif beam_type == "Propped":
        # Fixed at x=0, roller at x=beam_length
        return [Support(0, (1, 1, 1)), Support(beam_length, (0, 1, 0))]

    elif beam_type == "Continuous":
        # Caller supplies full supports list
        result = []
        for s in supports:
            dof = tuple(s["dof"])
            ky  = s.get("ky", None)
            kx  = s.get("kx", None)
            if ky is not None:
                result.append(Support(s["pos"], dof, ky=ky))
            else:
                result.append(Support(s["pos"], dof))
        return result

    else:
        raise ValueError(f"Unknown beam_type: '{beam_type}'. "
                         f"Valid: Simple, Cantilever, Fixed-Fixed, Propped, Continuous")


def _build_loads(pointloads, distributedloads, momentloads, triangleloads) -> list:
    """
    Converts AltruxIQ load lists to IndeterminateBeam load objects.
    Sign flips applied per the verified sign convention table.
    AltruxIQ: positive Fy = downward, positive w = downward.
    IndeterminateBeam: positive = upward. Therefore ALL vertical loads are negated.
    AltruxIQ: positive moment = CCW = same as IndeterminateBeam. No flip.
    AltruxIQ: positive Fx = rightward = same as IndeterminateBeam. No flip.
    """
    loads = []

    for load in (pointloads or []):
        pos, Fx, Fy = float(load[0]), float(load[1]), float(load[2])
        if Fy != 0:
            loads.append(PointLoadV(-Fy, pos))      # NEGATE: AltruxIQ down+ → IB up+
        if Fx != 0:
            loads.append(PointLoad(Fx, pos, 0))     # NO FLIP: same rightward+ convention

    for load in (distributedloads or []):
        start, end, w = float(load[0]), float(load[1]), float(load[2])
        loads.append(UDLV(-w, (start, end)))        # NEGATE

    for load in (momentloads or []):
        pos, M = float(load[0]), float(load[1])
        loads.append(PointTorque(M, pos))           # NO FLIP: CCW+ in both systems

    for load in (triangleloads or []):
        start, end = float(load[0]), float(load[1])
        peak, low  = float(load[2]), float(load[3]) # peak at start, low at end
        loads.append(TrapezoidalLoadV(force=(-peak, -low), span=(start, end)))  # NEGATE

    return loads


def _extract_reactions(beam_obj: Beam, supports: list) -> list:
    """
    Extracts reaction forces from each support position and returns
    a list of dicts in AltruxIQ's new Reactions format.
    """
    reactions = []
    for s in supports:
        pos = s.x if hasattr(s, 'x') else s._x0   # access support position
        # Fallback: iterate known positions from caller's support list
        pass

    # Safer: iterate over the original support dicts
    # This function is called with the original Support objects
    # so we read position from each Support object's internal attribute
    return reactions


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
    Unified beam solver using the IndeterminateBeam package.

    Parameters
    ----------
    beam_length : float
        Total beam length in metres.
    beam_type : str
        One of: "Simple", "Cantilever", "Fixed-Fixed", "Propped", "Continuous".
    supports : list of dicts
        Each dict: {"pos": float, "dof": tuple, "ky": float|None, "kx": float|None}
        For Simple, Cantilever, Fixed-Fixed, Propped: provide at minimum the support
        positions. The adapter builds the correct DoF tuples automatically.
        For Continuous: provide the full list with correct DoF tuples.
    pointloads, distributedloads, momentloads, triangleloads : list
        AltruxIQ load lists in their native format. Sign conventions are
        handled internally — callers do NOT need to flip signs.
    E : float
        Young's modulus in Pa. Required for deflection calculation.
    I : float
        Second moment of area in m^4. Required for deflection calculation.
    num_points : int
        Number of discrete X positions for result arrays. Default 2001.
        Higher values improve plot resolution but increase SymPy evaluation time.

    Returns
    -------
    dict with keys:
        "X_Field"             : np.ndarray of shape (num_points,)
        "Total_ShearForce"    : np.ndarray of shape (num_points,)
        "Total_BendingMoment" : np.ndarray of shape (num_points,)
        "Deflection"          : np.ndarray of shape (num_points,)
        "Reactions"           : list of dicts [{"pos", "Fy", "Fx", "M"}, ...]
    """
    # --- Step 1: Build the IndeterminateBeam Beam object ---
    beam = Beam(beam_length, E=E, I=I)

    # --- Step 2: Build and attach supports ---
    ib_supports = _build_supports(beam_type, beam_length, supports)
    beam.add_supports(*ib_supports)

    # --- Step 3: Build and attach loads ---
    ib_loads = _build_loads(pointloads, distributedloads, momentloads, triangleloads)
    if ib_loads:
        beam.add_loads(*ib_loads)

    # --- Step 4: Analyse ---
    beam.analyse()

    # --- Step 5: Extract result arrays ---
    X_Field = np.linspace(0, beam_length, num_points)

    # evaluate() calls are independent; vectorise for speed
    Total_ShearForce    = np.array([float(beam.get_shear_force(x))    for x in X_Field])
    Total_BendingMoment = np.array([float(beam.get_bending_moment(x)) for x in X_Field])
    Deflection          = np.array([float(beam.get_deflection(x))     for x in X_Field])

    # --- Step 6: Extract reactions ---
    # Determine unique support positions from the original supports list
    support_positions = [s["pos"] for s in supports]

    # For built-in types, reconstruct from beam_type
    if beam_type == "Simple":
        support_positions = [supports[0]["pos"], supports[1]["pos"]]
    elif beam_type == "Cantilever":
        support_positions = [0.0]
    elif beam_type == "Fixed-Fixed":
        support_positions = [0.0, beam_length]
    elif beam_type == "Propped":
        support_positions = [0.0, beam_length]
    elif beam_type == "Continuous":
        support_positions = [s["pos"] for s in supports]

    Reactions = []
    for pos in support_positions:
        r = beam.get_reaction(pos)          # returns [Fx, Fy, M]
        if r is not None:
            Reactions.append({
                "pos": pos,
                "Fx":  float(r[0]),
                "Fy":  float(r[1]),        # positive = upward
                "M":   float(r[2]),        # positive = CCW
            })
        else:
            Reactions.append({"pos": pos, "Fx": 0.0, "Fy": 0.0, "M": 0.0})

    return {
        "X_Field":             X_Field,
        "Total_ShearForce":    Total_ShearForce,
        "Total_BendingMoment": Total_BendingMoment,
        "Deflection":          Deflection,
        "Reactions":           Reactions,
    }
```

> **Performance note:** `beam.get_shear_force(x)` evaluates a SymPy piecewise expression at each point. For 2001 points, expect ~1–3 seconds on a typical machine. If speed is critical, reduce `num_points` to 501 and upsample with `np.interp()` after extraction.

---

## 7. MODIFY: `src/ui/cli.py`

### 7.1 Import block changes

**Remove:**
```python
from solver.main_solver import solve_simple_beam, solve_cantilever_beam
```

**Add:**
```python
from solver.indeterminate_solver import solve_beam
```

### 7.2 New global variables to declare at module level

Add these alongside the existing globals, after `beam_type = None`:
```python
# New beam types require a generic support list
supports_list = []          # List of dicts: [{"pos":x, "dof":tuple, "ky":None, "kx":None}]
Deflection    = None        # NOW populated by solve_beam(), not a separate calculation step
```

The existing `Deflection = None` declaration is already present — **keep it**. It will now be populated during the main analysis step (Menu 8, Sub-choice 1) rather than in Sub-choice 3.

### 7.3 Menu 8, Sub-choice 1 — Replace solver call

**Remove the entire `if beam_type == "Simple": ... elif beam_type == "Cantilever": ...` block** that calls `solve_simple_beam()` / `solve_cantilever_beam()` and replace it with:

```python
# Build the supports_list from existing AltruxIQ globals
# (For Simple/Cantilever, A and B are already set; for new types, handled by inputs.py)
if beam_type == "Simple":
    _supports = [
        {"pos": A, "dof": (1,1,0), "ky": None, "kx": None},
        {"pos": B, "dof": (0,1,0), "ky": None, "kx": None},
    ]
elif beam_type == "Cantilever":
    _supports = [{"pos": 0.0, "dof": (1,1,1), "ky": None, "kx": None}]
elif beam_type == "Fixed-Fixed":
    _supports = [
        {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
        {"pos": beam_length, "dof": (1,1,1), "ky": None, "kx": None},
    ]
elif beam_type == "Propped":
    _supports = [
        {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
        {"pos": beam_length, "dof": (0,1,0), "ky": None, "kx": None},
    ]
elif beam_type == "Continuous":
    _supports = supports_list   # populated by the new inputs.py function

result = solve_beam(
    beam_length=beam_length,
    beam_type=beam_type,
    supports=_supports,
    pointloads=pointloads,
    distributedloads=distributedloads,
    momentloads=momentloads,
    triangleloads=triangleloads,
    E=elastic_modulus,
    I=Ix,
    num_points=2001,
)

X_Field             = result["X_Field"]
Total_ShearForce    = result["Total_ShearForce"]
Total_BendingMoment = result["Total_BendingMoment"]
Deflection          = result["Deflection"]          # ← now available immediately
Reactions           = result["Reactions"]

project_state["analysis_complete"]     = True
project_state["deflection_calculated"] = True       # ← mark both at once
project_state["has_unsaved_changes"]   = True
```

### 7.4 Menu 8, Sub-choice 1 — Fix Reactions unpacking after solve

Replace the current positional unpacking of `Reactions` with dict access:

```python
# Extract per-support values for display (works for all beam types)
Va = next((r["Fy"] for r in Reactions if r["pos"] == A),    0.0)
Ha = next((r["Fx"] for r in Reactions if r["pos"] == A),    0.0)
Vb = next((r["Fy"] for r in Reactions if r["pos"] == B),    0.0)
Ma = next((r["M"]  for r in Reactions if r["pos"] == 0.0),  0.0)  # fixed-end moment
```

For Continuous beams, extract all `Fy` values:
```python
all_reactions_Fy = {r["pos"]: r["Fy"] for r in Reactions}
```

### 7.5 Menu 8, Sub-choice 2 — View analysis results

Same replacement as 7.4 — the `display_analysis_results()` call passes `Va, Vb, Ha, Ma` as keyword arguments, so the existing `display_analysis_results()` function signature does not need to change.

### 7.6 Menu 8, Sub-choice 3 — Calculate Deflection (simplified)

Because `Deflection` is now populated at analysis time, Sub-choice 3 becomes display-only:

**Remove:** The call to `calculate_beam_deflection(...)`.  
**Keep:** The `display_deflection_analysis(...)` call with the same arguments as before — `Deflection` is already populated.  
**Change the progress messages** to indicate deflection was computed as part of the structural analysis rather than as a separate integration step.

If the user runs Sub-choice 3 before Sub-choice 1, the existing guard `if not project_state.get("analysis_complete", False)` already prevents this — no additional guard needed.

### 7.7 Menu 2 — Beam Classification guard

After `beam_type` is set, also set `project_state["supports_saved"] = True` for **all** non-Simple beam types (not just Cantilever). Fixed-Fixed and Propped have no user-configurable supports:

```python
if beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
    project_state["supports_saved"] = True
elif beam_type == "Continuous":
    project_state["supports_saved"] = False  # user must define intermediate supports
```

### 7.8 Menu 5 — Boundary Conditions

Extend the existing guard:
```python
if beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
    print_error("Boundary conditions are automatically determined for this beam type.")
    time.sleep(2)
elif beam_type == "Simple":
    # ... existing supports menu (unchanged)
elif beam_type == "Continuous":
    # Call new function: define_continuous_supports()  — see inputs.py changes
```

### 7.9 `save_project()` — Reactions serialisation

`Reactions` is now a list of dicts (already JSON-serialisable). Update `save_project()`:

```python
# OLD:
'Reactions': safe_serialize(Reactions),   # converted ndarray to list

# NEW:
'Reactions': Reactions,                    # already a list of dicts
```

### 7.10 `load_project()` — Reactions deserialisation

```python
# OLD:
Reactions = np.array(current_project.get('Reactions', []))

# NEW:
Reactions = current_project.get('Reactions', [])
# If loading an OLD project (saved before this migration), Reactions will be a plain list
# [Va, Vb, Ha] or [Va, Ha, Ma]. Detect and convert:
if Reactions and not isinstance(Reactions[0], dict):
    # Legacy format: convert to new format using beam_type
    if beam_type == "Simple":
        Reactions = [
            {"pos": A, "Fx": float(Reactions[2]), "Fy": float(Reactions[0]), "M": 0.0},
            {"pos": B, "Fx": 0.0,                 "Fy": float(Reactions[1]), "M": 0.0},
        ]
    elif beam_type == "Cantilever":
        Reactions = [
            {"pos": 0.0, "Fx": float(Reactions[1]), "Fy": float(Reactions[0]), "M": float(Reactions[2])},
        ]
    else:
        Reactions = []
```

---

## 8. MODIFY: `src/ui/inputs.py` — New Beam Classifications

### 8.1 `Beam_Classification()` — Add new options

Append to the existing menu (after option 3 Cantilever):

```
4 - Fixed-Fixed Beam
    Both ends fully fixed; no translation or rotation at either support.
    Visual: |━━━━━━━━━━━━━━━━━━━━━━━━━━━|
    Applications: Columns, portal frames, tunnel linings

5 - Propped Cantilever
    Fixed at left end, roller at right end.
    Visual: |━━━━━━━━━━━━━━━━━━━━━━━━━━━△
    Applications: Balconies with end support, reinforced slabs

6 - Continuous Beam
    Multiple spans with intermediate roller/pin supports.
    Visual: ◯━━━━━━━━△━━━━━━━━△━━━━━━━━◯
    Applications: Multi-span bridges, continuous floor systems
```

Return values:
- `'4'` → `"Fixed-Fixed"`
- `'5'` → `"Propped"`
- `'6'` → `"Continuous"`

### 8.2 New function: `define_continuous_supports(beam_length, unit_system, units)` 

Add to `inputs.py`. This function prompts the user to define intermediate support positions (rollers by default) and returns a list of support dicts.

```python
def define_continuous_supports(beam_length, unit_system="Metric", units=None):
    """
    Prompts for intermediate support positions on a continuous beam.
    End supports (pin at x=0 and roller at x=beam_length) are added automatically.
    Returns a list of support dicts for use with solve_beam().
    """
    if units is None:
        units = {'length': 'm'}
    multiplier = CONVERSION_TO_SI[unit_system]["length"]
    
    supports = [
        {"pos": 0.0,         "dof": (1,1,0), "ky": None, "kx": None},  # left pin
    ]
    
    print(colored("Define intermediate supports (rollers). Enter 'done' when finished.", 'cyan'))
    while True:
        raw = input(colored(f"Intermediate support position ({units['length']}) or 'done': ", 'cyan'))
        if raw.strip().lower() == 'done':
            break
        try:
            pos = float(raw) * multiplier
            if 0 < pos < beam_length:
                supports.append({"pos": pos, "dof": (0,1,0), "ky": None, "kx": None})
                print_success(f"Added roller at x = {pos:.3f} m")
            else:
                print_error(f"Position must be between 0 and {beam_length} m (exclusive).")
        except ValueError:
            print_error("Invalid input. Enter a number or 'done'.")
    
    # Sort by position, add right end roller
    supports.append({"pos": beam_length, "dof": (0,1,0), "ky": None, "kx": None})
    supports.sort(key=lambda s: s["pos"])
    return supports
```

---

## 9. MODIFY: `src/ui/Menus.py` — Minor Additions

### 9.1 `analysis_simulation_menu()` — No change needed

The menu items are generic enough to cover all beam types.

### 9.2 `display_analysis_results()` — No change needed

It already accepts `Va, Vb, Ha, Ma` as optional keyword arguments. The dict-access extraction in `cli.py` provides these same variables.

### 9.3 Optional: Add "Continuous" beam type display

In `Beam_Classification` display function, add diagrams for Fixed-Fixed, Propped, and Continuous (low priority — functional correctness first).

---

## 10. MODIFY: `src/plotting/beam_plot.py`

### 10.1 `plot_reaction_diagram()`

Current signature:
```python
def plot_reaction_diagram(A, B, reactions, support_types, units=None)
```

`reactions` was a 3-element array. Update to accept the new list-of-dicts:

```python
def plot_reaction_diagram(reactions, units=None):
    """
    reactions: list of dicts [{"pos": float, "Fy": float, "Fx": float, "M": float}, ...]
    Iterates over all supports, draws the correct arrow type for each.
    """
    # ... existing figure setup ...
    for r in reactions:
        pos   = r["pos"] / len_div
        Fy    = r["Fy"]  / force_div
        Fx    = r["Fx"]  / force_div
        M     = r["M"]   / moment_div
        if Fy != 0:
            traces.append(draw_reaction(pos, Fy, unit=units['force']))
        if Fx != 0:
            traces.append(draw_horizontal_reaction(pos, Fx, unit=units['force']))
        if M != 0:
            traces.extend(draw_moment_load(pos, M, unit=units['moment']))
```

Update the call in `cli.py` Sub-choice '1' of the postprocessing menu:
```python
# OLD:
plot_reaction_diagram(A, B, Reactions, support_types)

# NEW:
plot_reaction_diagram(Reactions, units=current_labels)
```

---

## 11. DELETE: Files to Remove

### `src/solver/main_solver.py`
**Reason:** Fully replaced by `indeterminate_solver.py`. No other file imports from it except `cli.py` (confirmed by audit).  
**Action:** Delete the file after updating the import in `cli.py`.

### `src/Temporary/Improved Solver.py`
**Reason:** Staging copy identical to `main_solver.py`. Never imported; used only as a scratch pad during development.  
**Action:** Delete the file and the `src/Temporary/` directory if it becomes empty.

---

## 12. KEEP UNCHANGED (with reasons)

| File | Why unchanged |
|---|---|
| `src/solver/stress_solver.py` | Shear stress `τ = VQ/(Ib)`, bending stress `σ = Mc/I`, FOS — IndeterminateBeam does not compute cross-section stress. The input to these functions is `Total_ShearForce` and `Total_BendingMoment` as numpy arrays — format unchanged. |
| `src/solver/moi_solver.py` | Cross-section geometry (Ix, c, b, y_array, section_dims) is completely independent of the beam solver. |
| `src/plotting/main_plotting.py` | All functions accept numpy arrays. The arrays from the new solver have the same shape and sign conventions. |
| `src/plotting/plotting_helper.py` | Low-level Plotly trace builders — independent of solver. |
| `src/database/materials_database.py` | Unaffected. |

---

## 13. JSON Project Format — Changes to `beam_projects.json`

### Fields that change

| Field | Old format | New format |
|---|---|---|
| `Reactions` | `[float, float, float]` — positional, beam-type-dependent | `[{"pos": float, "Fy": float, "Fx": float, "M": float}, ...]` |

### New fields added

```json
{
    "beam_type": "Continuous",
    "supports_list": [
        {"pos": 0.0,  "dof": [1,1,0], "ky": null, "kx": null},
        {"pos": 3.0,  "dof": [0,1,0], "ky": null, "kx": null},
        {"pos": 6.0,  "dof": [0,1,0], "ky": null, "kx": null}
    ]
}
```

For Simple and Cantilever beams, `supports_list` mirrors the existing `support_A_pos` / `support_B_pos` fields — it is redundant but explicit. Add it during `save_project()` so old data is preserved and new data is explicit.

### Backward compatibility

Old projects saved before this migration will have `Reactions` as a list of numbers and no `supports_list` field. The updated `load_project()` detects and converts these (see Section 7.10).

---

## 14. New Beam Types: What Each Adds

| Beam Type | Supports required from user | Reactions returned | Moment at support |
|---|---|---|---|
| `Simple` (existing) | Pin position A, Roller position B | Va, Vb, Ha | None |
| `Cantilever` (existing) | None (fixed at x=0 always) | Va, Ha, Ma | Yes (fixed end) |
| `Fixed-Fixed` (NEW) | None (fixed at x=0 and x=L always) | Va, Vb, Ha, Ma_left, Ma_right | Both ends |
| `Propped` (NEW) | None (fixed x=0, roller x=L) | Va, Vb, Ha, Ma_left | Left end only |
| `Continuous` (NEW) | User defines intermediate roller positions | One Fy per support | None unless fixed |

---

## 15. Testing Checklist

After implementing all changes, verify each case below by running the program and checking results against known analytical solutions.

### Solver correctness
- [ ] **Simple beam, central point load:** Va = Vb = P/2. BM at midspan = PL/4. Deflection at midspan = PL³/(48EI).
- [ ] **Simple beam, UDL:** Va = Vb = wL/2. BM at midspan = wL²/8.
- [ ] **Cantilever, tip point load:** Va = P. Ma = -PL. Deflection at tip = PL³/(3EI).
- [ ] **Cantilever, UDL:** Va = wL. Ma = -wL²/2. Deflection at tip = wL⁴/(8EI).
- [ ] **Fixed-Fixed, central point load:** Va = Vb = P/2. Ma_left = Ma_right = PL/8.
- [ ] **Propped cantilever, UDL:** Va = 5wL/8. Vb = 3wL/8. Ma = wL²/8.
- [ ] **Continuous beam (2 spans, equal UDL):** Central reaction ≈ 1.25wL. End reactions ≈ 0.375wL each.

### Sign convention
- [ ] Downward point load gives negative deflection (downward).
- [ ] Sagging BM (midspan, simply supported) gives positive BM value.
- [ ] SFD jumps positive to negative at a downward point load location (left to right).
- [ ] Cantilever fixed-end moment displayed with correct sign.

### Reaction format
- [ ] `Reactions` is a list of dicts, not a numpy array.
- [ ] `save_project()` serialises Reactions correctly (no `safe_serialize` numpy conversion needed).
- [ ] `load_project()` restores Reactions as list of dicts.
- [ ] Old projects (legacy format) load without error via the backward-compat block.

### Integration with stress solver
- [ ] Shear stress calculation runs after new-format SFD is stored.
- [ ] Bending stress and FOS calculations unaffected.
- [ ] Deflection displayed correctly from new Deflection array (not from double integration).

### Plotting
- [ ] `plot_reaction_diagram()` draws correct arrows for all support types.
- [ ] SFD, BMD, deflection plots render correctly for Fixed-Fixed and Continuous beams.
- [ ] `Matplot_combined()` and `Plotly_combined_diagrams()` work when deflection is pre-populated.

---

## 16. Known Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **SymPy evaluation is slow for 2001 points** | Medium | Default to 1001 points; allow user to set resolution in a global config |
| **TrapezoidalLoadV with zero total load (peak = 0, low = 0)** | Low | Guard: if `peak == 0 and low == 0`, skip adding the load |
| **SymPy returns symbolic 0 / tiny float at boundaries** | Low | Already handled — `float()` cast in extraction loop converts all to Python floats |
| **Existing JSON projects have legacy Reactions format** | Medium | Handled by backward-compat block in `load_project()` |
| **IndeterminateBeam raises if no loads added** | Low | Guard: if all load lists are empty, add a zero-magnitude placeholder or display a warning before calling `analyse()` |
| **Continuous beam with only 1 intermediate support** | Low | No special handling needed — IndeterminateBeam handles arbitrary supports |
| **Unit system: IndeterminateBeam always works in SI** | None | AltruxIQ already converts all inputs to SI before solver. No issue. |
| **`plot_reaction_diagram()` signature change breaks existing calls** | High | There is exactly 1 call site in cli.py (postprocessing menu, sub_choice='1'). Update that single call. |

---

## 17. Implementation Order (Recommended)

Execute in this exact order to maintain a runnable state at each step:

1. **Install package:** `pip install indeterminatebeam`
2. **Create** `src/solver/indeterminate_solver.py` (full implementation)
3. **Modify** `src/ui/cli.py` — update import only (change `from solver.main_solver import ...` to `from solver.indeterminate_solver import solve_beam`)
4. **Modify** `src/ui/cli.py` — Menu 8, Sub-choice 1 (replace solver call block)
5. **Modify** `src/ui/cli.py` — Menu 8, Sub-choice 3 (simplify deflection step)
6. **Modify** `src/ui/cli.py` — fix Reactions unpacking in Sub-choices 1 and 2
7. **Modify** `src/ui/cli.py` — update `save_project()` and `load_project()` for new Reactions format
8. **Modify** `src/plotting/beam_plot.py` — update `plot_reaction_diagram()` signature and call site
9. **Modify** `src/ui/cli.py` — update postprocessing Sub-choice '1' call to `plot_reaction_diagram()`
10. **Run testing checklist** for Simple and Cantilever beams (existing functionality verified)
11. **Modify** `src/ui/inputs.py` — add Fixed-Fixed, Propped, Continuous to `Beam_Classification()`
12. **Modify** `src/ui/inputs.py` — add `define_continuous_supports()` function
13. **Modify** `src/ui/cli.py` — Menu 2 and Menu 5 handling for new beam types
14. **Run testing checklist** for new beam types
15. **Delete** `src/solver/main_solver.py`
16. **Delete** `src/Temporary/Improved Solver.py`
17. **Update** `AGENT_BRIEFING.md` — set main_solver.py as DELETED, add indeterminate_solver.py

---

*End of integration plan. All sign conventions, API signatures, and numerical results in this document were verified by live execution against `indeterminatebeam==2.4.0` on the target machine before writing.*
