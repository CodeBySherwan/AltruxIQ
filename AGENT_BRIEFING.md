# AltruxIQ — Agent Briefing & Developer Reference (v4)

> **Purpose**: Full technical context for any AI agent assisting with this project.
> Read this before writing, editing, or debugging any code.
> Every section is authoritative — do not guess what is not documented here.
> **This version supersedes all earlier AltruxIQ briefing documents (v1–v3).**
>
> **What changed from v3** (verified against the actual codebase, not inferred
> from changelogs):
> - v3's Section 14.2 listed seven "confirmed bugs" (Bug-11 through Bug-17) as
>   open. **All seven are already fixed in the current code.** They are moved
>   to §14.2 "Resolved" below, with the actual fix quoted from the live source
>   so the resolution is verifiable, not just asserted.
> - Session state moved from ~30 `cli.py` module-level globals to a single
>   `core/state.py::ProjectState` dataclass (`state` singleton). §5.1 is
>   rewritten to match; every `global X` pattern in v3's examples is now
>   `state.X`.
> - `common/paths.py`, `common/units.py`, `common/config.py`,
>   `common/exceptions.py` did not exist in v3 and are now the foundation
>   layer. New §4.0 documents them.
> - Two new **open** correctness bugs found by the latest architecture audit
>   (see `SESSION_HANDOFF.md`) are added to §14.3: a live crash in
>   `ui/inputs.py` (P0-1) and a silent unit-system bug in
>   `display_engineering_recommendations` (P0-2). **These are the current
>   highest-priority open issues, full stop.**
> - One bug that v3 described as fixed (`indeterminate_solver` if/if/elif
>   chain) turns out to be **only partially fixed** — see §14.3, "residual".
> - For the full prioritized action list (bug fixes → cleanup → module
>   decomposition → future-proofing), see **`SESSION_HANDOFF.md`**. This file
>   is the stable technical reference; `SESSION_HANDOFF.md` is the current
>   session's task queue.

---

## Table of Contents

0. [Foundation Layer (`common/`, `core/`)](#0-foundation-layer-common-core)
1. [Project Identity](#1-project-identity)
2. [Quick Start](#2-quick-start)
3. [Repository Structure](#3-repository-structure)
4. [Module Reference](#4-module-reference)
5. [Core Data Structures](#5-core-data-structures)
6. [Beam Types Supported](#6-beam-types-supported)
7. [Cross-Section Types](#7-cross-section-types)
8. [Load Types and Sign Conventions](#8-load-types-and-sign-conventions)
9. [Unit System Architecture](#9-unit-system-architecture)
10. [Analysis Pipeline (End-to-End)](#10-analysis-pipeline-end-to-end)
11. [Plotting Architecture](#11-plotting-architecture)
12. [Materials Database](#12-materials-database)
13. [Dependencies](#13-dependencies)
14. [Known Bugs — Resolved and Open](#14-known-bugs--resolved-and-open)
15. [Development Conventions](#15-development-conventions)
16. [Active Development Notes](#16-active-development-notes)

---

## 0. Foundation Layer (`common/`, `core/`)

These packages did not exist in earlier versions of this briefing and are now
the single source of truth for their respective concerns. **No other module
should duplicate what lives here** — that duplication is exactly what these
modules were created to eliminate, and re-introducing it (e.g. a hardcoded
`0.3048` conversion factor, or a raw `os.path.join` for a data file) is a
regression.

| Module | Owns | Key exports |
|---|---|---|
| `common/paths.py` | Every on-disk location the app touches | `PROJECT_ROOT`, `DATA_DIR`, `EXPORTS_DIR`, `DIAGRAM_EXPORT_DIR`, `SCREENSHOTS_DIR`, `MATERIALS_DB_FILE`, `CUSTOM_MATERIALS_FILE`, `STANDARD_SECTIONS_FILE`, `CUSTOM_SECTIONS_FILE`, `PROJECTS_FILE`, `ensure_src_in_path()`, `ensure_writable_dirs()` |
| `common/units.py` | All unit conversion (display↔SI, display↔JSON), unit label dicts | `METRIC_UNITS`, `IMPERIAL_UNITS`, `UNIT_SYSTEMS`, `get_divisor()`, `from_si()`, `to_si()`, `system_multiplier()`, `to_json()`, `from_json()`, `get_scale()`, `is_imperial()`, `default_units()` |
| `common/config.py` | Frozen engineering constants (NOT user-editable settings — see `SESSION_HANDOFF.md` §P5-3 for why these must stay separate) | `SOLVER` (`SolverDefaults`: `DEFAULT_NUM_POINTS`, `MIN_NUM_POINTS`, `MAX_NUM_POINTS`, `MIN_LOAD_SUBDIVISIONS`, `FALLBACK_STEEL_E_PA`, `FALLBACK_STEEL_I_M4`), `SERVICEABILITY` (`ServiceabilityLimits`: L/240, L/360, L/480, L/180, L/500 denominators, `TARGET_FACTOR_OF_SAFETY`) |
| `common/exceptions.py` | Domain exception hierarchy | `AltruxIQError` → `ValidationError` → `SectionGeometryError`; `AltruxIQError` → `SolverError` → `SingularStiffnessMatrixError`; `AltruxIQError` → `PersistenceError` |
| `core/state.py` | Session state (replaces the old globals model — see §5.1) | `ProjectState` dataclass, `state` singleton instance |

**All unit conversion goes through `common/units.py`.** All computation is base
SI internally; conversion happens only at (a) the display boundary via
`get_divisor()`/`from_si()`/`to_si()`, and (b) the JSON-persistence boundary via
`to_json()`/`from_json()` — the materials JSON stores strength in MPa and
modulus in GPa, not base-SI Pa, which is why the JSON-schema factors
(`_JSON_FACTORS`) are a separate table from the SI factors (`_SI_FACTORS`) in
`units.py`. Do not conflate the two.

**All filesystem paths go through `common/paths.py`.** No module should
compute a project-relative path from `__file__` arithmetic — that pattern is
what `paths.py` was created to eliminate project-wide.

---

## 1. Project Identity

| Field            | Value                                                          |
|------------------|------------------------------------------------------------------|
| **Current Name** | AltruxIQ                                                       |
| **Version**      | 2.00 Alpha                                                     |
| **Type**         | Python CLI desktop application — structural beam FEA           |
| **Developer**    | Sherwan, mechanical engineer                                   |
| **Language**     | Python 3.x (64-bit)                                            |
| **Interface**    | Terminal / CLI (no GUI framework)                              |
| **Entry Point**  | `python src/ui/cli.py`                                         |

### What the Application Does

AltruxIQ is a structural beam analysis tool modelled on commercial FEA software (ANSYS,
SolidWorks Simulation). Given a beam geometry, cross-section profile, material, support
conditions, and applied loads, it computes:

- Reaction forces at supports
- Shear force diagram (SFD)
- Bending moment diagram (BMD)
- **Axial force diagram (AFD) — Stepped Bar only**
- **Axial displacement diagram — Stepped Bar only**
- Beam deflection and slope
- Shear stress distribution across the cross-section
- Bending (normal) stress
- **Combined bending + axial stress — Stepped Bar only**
- Factor of Safety against yielding
- 3D FEA-style contour visualisations

All results are displayable in two unit systems (Metric SI and US Customary/Imperial) and
can be saved to / loaded from a JSON project file.

---

## 2. Quick Start

```bash
pip install -r requirements.txt
python src/ui/cli.py
```

The application is entirely menu-driven. Navigation is by number key.

### Recommended Workflow Order (standard beam)

```
[2] Define Beam Type
[3] Profile Definition
    [1] Enter Beam Length
    [2] Define Profile (cross-section)
[4] Material Selection → [1] Select Material
[5] Boundary Conditions  (auto-handled for Simple, Cantilever, Fixed-Fixed, Propped)
[6] Loads Definition → [1] Define Loads
[8] Analysis/Simulation → [1] Solve Beam → [4] Calculate Stress & FOS
[9] Postprocessing/Visualization
```

### Additional Workflow for Stepped Bar

```
[2] Beam Type → "Stepped Bar"
[3] Profile Definition → [2] Define Profile
    → Launches define_stepped_segments() wizard:
        For each segment: enter length → select cross-section → select material
        ⚠ CURRENTLY BROKEN — see §14.3 P0-1. The material-selection step of
        this wizard raises ImportError. Fix before relying on this workflow.
[5] Boundary Conditions → define_custom_supports() wizard
[6] Loads Definition → manage_loads() (same as standard)
[8] Solve → dispatches to solve_stepped_beam() instead of solve_beam()
    Results include AxialForce, AxialDisplacement in addition to standard outputs
[9] Postprocessing → extra items 9/10/11 for axial/combined plots (Stepped Bar only)
```

---

## 3. Repository Structure

```
project_root/
│
├── data/
│   ├── __init__.py
│   ├── materials.json            # 25 pre-defined engineering materials
│   ├── custom_materials.json     # User-defined materials (auto-created)
│   ├── standard_sections.json    # Standard section library (IPE, HEA, W, ...)
│   └── custom_sections.json      # User-saved cross-sections (auto-created)
│
├── src/
│   ├── common/                        # FOUNDATION LAYER — see §0. New since v3.
│   │   ├── __init__.py
│   │   ├── paths.py                   # All filesystem paths — single source of truth
│   │   ├── units.py                   # All unit conversion — single source of truth
│   │   ├── config.py                  # Frozen engineering constants (SOLVER, SERVICEABILITY)
│   │   └── exceptions.py              # AltruxIQError hierarchy
│   │
│   ├── core/                          # Session state. New since v3.
│   │   └── state.py                   # ProjectState dataclass + `state` singleton
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── materials_database.py     # MaterialDatabase class
│   │   └── sections_database.py      # SectionsDatabase class
│   │
│   ├── plotting/
│   │   ├── __init__.py
│   │   ├── beam_plot.py              # 2D beam schematic + reaction diagram (Plotly)
│   │   ├── export_helper.py          # Centralised present/export workflow
│   │   ├── main_plotting.py          # All 2D SFD/BMD/stress/deflection/axial plots
│   │   ├── plot_theme.py             # Single source of visual truth (colours, fonts, SERIES)
│   │   ├── plotting_helper.py        # Low-level Plotly shape-drawing helpers
│   │   └── pyvista_plotting.py       # 3D FEA contour viewer (PyVista)
│   │
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── area_solver.py            # Cross-sectional area A(m²) from section_dims
│   │   ├── indeterminate_solver.py   # PRIMARY SOLVER — stiffness via indeterminatebeam
│   │   ├── moi_solver.py             # MOI solver (all 8 cross-section types)
│   │   ├── stepped_solver.py         # 2D frame FEM for stepped bars
│   │   ├── stress_solver.py          # Stress, deflection, FOS calculations
│   │   └── Legacy/
│   │       └── main_solver.py        # LEGACY SOLVER — not called from CLI, kept for reference
│   │
│   └── ui/
│       ├── __init__.py
│       ├── cli.py                    # MAIN APPLICATION — menu logic, orchestration, state.*
│       ├── inputs.py                 # Raw user input handlers, ask_*() prompt toolkit
│       └── Menus.py                  # All display/print functions + unit re-exports
│
├── beam_projects.json                # Auto-created on first save
├── exports/diagrams/                 # Auto-created by export_helper on first export
├── screenshots/                      # Auto-created by PyVista on first 3D render
├── requirements.txt
├── AGENT_BRIEFING.md                 # This file
├── SESSION_HANDOFF.md                # Current session's prioritized task queue
└── .gitignore
```

### Path resolution (current — NOT `__file__` arithmetic)

Every module that needs a project path imports it from `common/paths.py`:

```python
from common.paths import DATA_DIR, CUSTOM_MATERIALS_FILE, PROJECTS_FILE
```

`common/paths.py` itself resolves `PROJECT_ROOT` once, from its own location:
```python
_THIS_FILE = Path(__file__).resolve()
SRC_DIR: Path = _THIS_FILE.parent.parent          # .../src
PROJECT_ROOT: Path = SRC_DIR.parent                # repo root
```
This is the **only** place `__file__` arithmetic should occur. If you find a
new module doing its own `os.path.dirname(os.path.abspath(__file__))` walk,
that is a regression — route it through `common/paths.py` instead. (One
legitimate exception remains: `cli.py`'s own `sys.path` bootstrap at the top of
the file, which exists only to be able to `import common.paths` at all before
`src/` is on the path — see §14.3 for why this is still slightly redundant and
the deferred fix.)

---

## 4. Module Reference

### 4.0 `common/` and `core/` — see §0 above for the full table.

### 4.1 `src/ui/cli.py` — Main Application

The application's orchestration layer. Contains:

- **No module-level state variables anymore.** All session state lives on the
  `state` singleton imported from `core.state` (`from core.state import
  state`). See §5.1.
- All **menu routing logic** in `run_extended_menu()`, which reads/writes
  `state.*` attributes instead of `global`-declared module variables.
- Project save/load functions (`save_project`, `load_project`,
  `save_projects_to_disk`, `load_projects_from_disk`) — these are still
  procedural free functions mixing file I/O + serialization + UI prompts; see
  `SESSION_HANDOFF.md` §P4-1 for the planned `ProjectRepository` split.
- Material selection function (`select_material`) — still lives here, which is
  the root cause of the circular-import crash in §14.3 P0-1. Planned move to
  `ui/materials/selector.py` (see `SESSION_HANDOFF.md` §P3).
- `NumpyEncoder` class for JSON serialisation of NumPy types.
- `init()` — resets `state.project_state` flags on startup.

**The solve block** (menu `'8'`, sub-choice `'1'`):
- Builds `_supports` list of dicts based on `state.beam_type`
- **Dispatches to `solve_stepped_beam()`** when `state.beam_type == "Stepped
  Bar"`, passing `state.segments` and `_supports`
- **Dispatches to `solve_beam()`** for all other beam types
- Unpacks standard keys plus `AxialForce`/`AxialDisplacement` (Stepped Bar
  only) into `state.*` attributes
- Sets `state.project_state["analysis_complete"] = True`

**Postprocessing dispatch (§14.2's former Bug-11)** now correctly computes
beam-type-dependent menu numbering:
```python
fea_3d_choice = '12' if state.beam_type == "Stepped Bar" else '9'
back_choice = '13' if state.beam_type == "Stepped Bar" else '10'
```
This is confirmed present in the current `run_extended_menu()` — do not
"re-fix" this, it is already correct.

---

### 4.2 `src/solver/indeterminate_solver.py` — Primary Solver (non-Stepped beams)

**Handles**: Simple, Overhanging Beam, Cantilever, Fixed-Fixed, Propped, Continuous, Custom.
**Does NOT handle**: Stepped Bar — routed to `stepped_solver.py`.

**Function**: `solve_beam(beam_length, beam_type, supports, pointloads, distributedloads,
momentloads, triangleloads, E=SOLVER.FALLBACK_STEEL_E_PA, I=SOLVER.FALLBACK_STEEL_I_M4,
num_points=SOLVER.DEFAULT_NUM_POINTS) -> dict`

Uses the `indeterminatebeam` Python package (SymPy-based stiffness method). Default `E`/`I`
now come from `common.config.SOLVER`, not hardcoded literals.

**Return value** (dict):
```python
{
    "X_Field":              np.ndarray,   # shape (num_points,)
    "Total_ShearForce":     np.ndarray,   # shape (num_points,)
    "Total_BendingMoment":  np.ndarray,   # shape (num_points,)
    "Deflection":           np.ndarray,   # shape (num_points,), metres
    "Reactions":            list[dict],   # see §5.2
    "Slopes":               np.ndarray,   # np.gradient(Deflection, X_Field)
    "Curvatures":           np.ndarray,   # BendingMoment / (E * I)
}
```

**Load sign convention in `_build_loads`** (unchanged from earlier versions):
- Vertical loads: `PointLoadV(Fy, pos)` — positive Fy = upward
- Horizontal: `PointLoad(Fx, pos, 0)` — positive Fx = rightward
- UDL: `UDLV(w, (start, end))` — positive w = upward
- Moment: `PointTorque(M, pos)` — positive = CCW
- Trapezoidal: `TrapezoidalLoadV(force=(-peak, -low), span=(start, end))` — **negated**
  because the `indeterminatebeam` library's trapezoidal API has the opposite sign
  convention

**`_build_supports()` dispatch — this part IS fixed.** Simple and Overhanging Beam are
now handled by proper `if`/`elif` branches, each returning immediately:
```python
if beam_type == "Simple":
    A = supports[0]["pos"]; B = supports[1]["pos"]
    return [Support(A, (1, 1, 0)), Support(B, (0, 1, 0))]
elif beam_type == "Overhanging Beam":
    A = supports[0]["pos"]; B = supports[1]["pos"]
    return [Support(A, (1, 1, 0)), Support(B, (0, 1, 0))]
```

**⚠ Residual issue — NOT the same code path, NOT fixed.** Inside `solve_beam()` itself
(a different function from `_build_supports()`), the `support_positions` extraction block
used for reaction lookup still has the historical `if`/`if`/`elif` pattern:
```python
if beam_type == "Simple":
    support_positions = [supports[0]["pos"], supports[1]["pos"]]
if beam_type == "Overhanging Beam":                       # ← should be `elif`
    support_positions = [supports[0]["pos"], supports[1]["pos"]]
elif beam_type == "Cantilever":
    support_positions = [0.0]
```
For `beam_type == "Simple"`, the first `if` sets `support_positions`, then the second
`if`/`elif`/`elif` chain's condition (`beam_type == "Overhanging Beam"`) is false, so it
falls through *without* re-entering the `elif` chain's other branches — meaning the value
set by the first `if` survives untouched for `"Simple"`. Both `"Simple"` and `"Overhanging
Beam"` produce the identical result `[A, B]` either way, so **no numeric bug currently
exists**, but the pattern is fragile: adding a new beam type between these two checks
without converting the first `if` to `elif` risks silent incorrect reaction extraction.
Low priority; fix opportunistically by converting the first `if` to `elif` chain entry, or
flag for `SESSION_HANDOFF.md` if doing a dedicated solver-module pass.

---

### 4.3 `src/solver/stepped_solver.py` — Stepped Beam FEM Solver

**Handles**: `beam_type == "Stepped Bar"` only.

Implements a 2D frame element FEM with 3 DOFs per node (u, v, θ). Supports combined
axial + bending analysis for beams with varying cross-section and material along their
length. This is the module explicitly named as the generalization target for a future
`frame2d`/`truss2d` shared kernel (see `SESSION_HANDOFF.md` §P5-1/P5-2).

**Public function**:
```python
solve_stepped_beam(
    segments: list,
    supports: list,
    pointloads=None,
    distributedloads=None,
    momentloads=None,
    triangleloads=None,
    num_points: int = SOLVER.DEFAULT_NUM_POINTS,
) -> dict
```

**Return value** (dict):
```python
{
    "X_Field":              np.ndarray,
    "Total_ShearForce":     np.ndarray,
    "Total_BendingMoment":  np.ndarray,
    "Deflection":           np.ndarray,
    "AxialForce":           np.ndarray,   # Newtons
    "AxialDisplacement":    np.ndarray,   # metres
    "Reactions":            list[dict],
    "Slopes":               np.ndarray,
    "Curvatures":           np.ndarray,
}
```

**Segment input format** (each element of the `segments` list) — unchanged from earlier
versions; see §5.4 for `section_dims` format nested inside each segment dict.

**Internal pipeline** (unchanged): `_build_mesh()` → `_assemble_global()` →
`_apply_point_loads()` → `_apply_distributed_loads()` (exact Hermite-consistent
equivalent nodal loads, not sampling) → `_apply_boundary_conditions()` →
`scipy.linalg.solve()` (raises `SingularStiffnessMatrixError` on a singular matrix, via
`common.exceptions`, not a bare `LinAlgError`) → `_extract_reactions()` →
`_interpolate_to_field()`.

**Mesh density**: `MIN_LOAD_ELEMS = SOLVER.MIN_LOAD_SUBDIVISIONS` (100) sub-elements per
distributed/triangular load span — sourced from `common.config`, not a local constant.

**All bugs described in earlier drafts of this module (reversed triangular-load
interpolation, missing load-boundary mesh nodes, O(n²) node lookup, oversized stiffness
matrix from load sampling) are fixed and documented inline in the module's own docstring.**
No open issues in this module as of this briefing.

---

### 4.4 `src/solver/area_solver.py` — Cross-Sectional Area Solver

**Function**: `area_from_section(shape: str, section_dims: dict) -> float`

Returns cross-sectional area A (m²) from the canonical `section_dims` dict. Raises
`SectionGeometryError` (from `common.exceptions`, not a bare `ValueError`) for invalid
shapes or missing/inconsistent dimensions.

**Minor cleanup item**: this file has unused `import os` / `import sys` left over from the
pre-`paths.py` era — the module doesn't touch the filesystem at all. Harmless but should be
removed (see `SESSION_HANDOFF.md` §P1-1).

---

### 4.5 `src/solver/Legacy/main_solver.py` — Legacy Solver (NOT active in CLI)

Custom numerical solver supporting only "Simple" and "Cantilever". Not called from `cli.py`.
Moved into a `Legacy/` subfolder (was previously at `src/solver/main_solver.py` directly).
Do not modify unless specifically directed.

---

### 4.6 `src/solver/moi_solver.py` — Moment of Inertia Solver

All `inertia_moment_*` functions return a **6-tuple**:
```python
(Ix, shape_name, c, b_rep, y_array, section_dims)
```
Unchanged from earlier versions — see §5.4 for `section_dims` format.

**Previously reported issue, now fixed**: `print_derived_properties()` used to hardcode
`"m²"`/`"m³"` strings regardless of active unit system. It now correctly reads
`units['area']`/`units['length']` from the passed-in `units` dict (defaulting to
`common.units.default_units()` if none given):
```python
print(colored(f"│ Cross-sectional Area (A):          {A:.6e} {units['area']}", 'magenta'))
print(colored(f"│ Elastic Section Modulus (Se=Ix/c): {Se:.6e} {units['length']}³", 'magenta'))
```

Raises `SectionGeometryError` (via `common.exceptions`) on invalid dimensions instead of a
bare `ValueError`.

---

### 4.7 `src/solver/stress_solver.py` — Stress and Deflection

Unchanged in behavior from earlier versions. Correctly stays pure-SI internally with no
unit-conversion logic of its own — conversion is entirely the display layer's
responsibility, which is the correct separation of concerns.

Public functions: `width_array_for_section()`, `first_moment_of_area_general()`,
`calculate_shear_stress()`, `calculate_bending_stress()`, `Factor_of_Safety()`,
`calculate_beam_deflection()` (not currently called from CLI — deflection comes from the
solvers directly).

---

### 4.8 `src/database/materials_database.py` — Material Database

**Class**: `MaterialDatabase(filename="materials.json")`

Path resolution now goes through `common.paths.DATA_DIR` / `CUSTOM_MATERIALS_FILE` — no
more `__file__` arithmetic in this module. The `filename` parameter is accepted only for
backward compatibility with existing call sites; the actual directory always comes from
`common.paths`.

Methods: `list_all_materials()`, `search_by_property()`, `add_custom_material()`,
`delete_custom_material()`, `all_materials` (property = standard + custom).

---

### 4.9 `src/database/sections_database.py` — Sections Database

**Class**: `SectionsDatabase()`

Path resolution via `common.paths.STANDARD_SECTIONS_FILE` / `CUSTOM_SECTIONS_FILE`.

Methods: `get_standard_families()`, `get_sections_in_family(family)`,
`save_custom_section(dict)`, `delete_custom_section(name)`, `list_custom_sections()`.

---

### 4.10 `src/ui/Menus.py` — Display Engine

`get_divisor`, `from_si`, `to_si`, `system_multiplier`, `get_scale`, `default_units`,
`is_imperial` are **re-exported** from `common.units` for backward compatibility with
existing call sites (`from ui.Menus import get_divisor` still works), but the canonical
implementation lives in `common/units.py` — do not add new unit logic here.

`SERVICEABILITY` limits (L/240, L/360, L/480 etc.) are imported from `common.config`, not
defined locally — the earlier duplication across this file's deflection-check functions is
resolved.

**Open issue**: `display_engineering_recommendations()` has no `units` parameter and
hardcodes SI unit labels regardless of active session unit system. See §14.3 P0-2 — this
is a currently-open correctness bug, not a historical one.

`postprocessing_menu(beam_type)` — menu item count still depends on `beam_type` (10 items
non-Stepped, 13 items Stepped Bar); the `cli.py` dispatch now correctly computes
`fea_3d_choice`/`back_choice` dynamically (§4.1) rather than hardcoding menu numbers, so
the class of bug this used to cause (former Bug-11) cannot recur here unless a future
edit re-hardcodes a menu number.

---

### 4.11 `src/ui/inputs.py` — Input Handlers

Houses the generic `ask_float`/`ask_int`/`ask_text`/`ask_choice`/`ask_yes_no` prompt
toolkit (well-factored, shares `_format_prompt`/`PROMPT_CARET`/retry semantics) alongside
beam-domain wizards (`Beam_Classification`, `Beam_Length`, `Beam_Supports`,
`define_continuous_supports`, `define_custom_supports`, `manage_loads`,
`define_stepped_segments`, `define_custom_material`). See `SESSION_HANDOFF.md` §P3 for the
planned split of these into `ui/console/` (generic) vs `ui/beam/` (domain) packages.

**`define_stepped_segments(unit_system, units)`** → `list[dict]` or `None`

**⚠ CURRENTLY BROKEN — see §14.3 P0-1.** This function contains:
```python
from ui.cli import select_material, load_material_database, Materials
if Materials is None:
    load_material_database()
```
`Materials` is no longer a `cli.py` module-level name — it was migrated to
`state.Materials` when session state moved to `core/state.py::ProjectState`. This import
will raise `ImportError` the moment this line executes, which happens on every attempt to
assign a segment's material during the Stepped Bar profile wizard. **This is the single
highest-priority open bug in the codebase** — it blocks the entire Stepped Bar workflow
described in §2's "Additional Workflow for Stepped Bar" section. Do not attempt to use or
test Stepped Bar material assignment until this is fixed; see §14.3 for the fix.

Unit conversion in this file goes entirely through `common.units.system_multiplier()` /
`common.units.to_json()` — the old hardcoded `16.01846`/`6.894757`/`0.006894757` literals
(from `define_custom_material`) are gone.

---

### 4.12 `src/plotting/main_plotting.py` — 2D Result Plots

Plotly and Matplotlib backends for SFD, BMD, deflection, shear stress, bending stress,
**and stepped-bar axial results**.

**Previously reported as missing, now present and in use**: `Plotly_AxialForce`,
`Matplot_AxialForce`, `Plotly_AxialDisplacement`, `Matplot_AxialDisplacement`,
`Plotly_CombinedStress`, `Matplot_CombinedStress` all exist as dedicated functions (not
misuse of `Plotly_sfd_bmd`/`Matplot_BendingStress` with an invalid `plot_type` string, which
is what earlier drafts of the Stepped Bar feature did). `cli.py`'s postprocessing dispatch
(`sub_choice == '9'`/`'10'`/`'11'`, Stepped Bar only) calls these correctly. `
Plotly_combined_diagrams` / `Matplot_combined` also accept optional `AxialForce=`/
`CombinedStress=` parameters for the Stepped Bar combined view.

Unit scaling for all of the above goes through `common.units.get_scale(units)`, which
returns a `UnitScale` namedtuple — `(units, length, length_small, force, moment, stress)`
divisors in one call. Note this **is not** the old local `_get_scale` that used to exist in
this file (which had a stress-divisor bug — see §14.2 resolved list); it is now `units.py`'s
canonical implementation.

---

### 4.13 `src/plotting/pyvista_plotting.py` — 3D FEA Viewer

Commercial-grade 3D contour visualiser. Path resolution via `common.paths.SCREENSHOTS_DIR`
/ `EXPORTS_DIR`, though internally the module still round-trips through `str()` and
`os.path.join`/`os.makedirs` rather than staying in `pathlib` throughout — cosmetic
inconsistency, see `SESSION_HANDOFF.md` §P1-3.

**Still not implemented for Stepped Bar** (unchanged from earlier versions):
`PyVista_axial_force`, `PyVista_axial_displacement` do not exist yet. Segment-boundary
rendering (step-change in cross-section) is also not yet handled — `_build_beam_mesh()`
takes a single shape/`section_dims`, valid only for uniform-section beams.

---

### 4.14 `src/plotting/plot_theme.py` — Visual Identity

**Previously reported as missing, now present**: the `SERIES` dict includes `"axial"`,
`"axialdispl"`, and `"combinedstress"` entries alongside the original `"shear"`,
`"moment"`, `"deflect"`, `"shearstress"`, `"bendstress"`. Stepped Bar plots share the same
visual identity system as standard beam plots — no separate styling module exists or is
needed.

---

## 5. Core Data Structures

### 5.1 Session State — `core.state.ProjectState`

**This entire section is a rewrite from v3.** Earlier versions of this briefing described
~30 module-level globals in `cli.py`. That model is gone. Session state is now a single
dataclass instance:

```python
from core.state import state
```

`state` is a `ProjectState` (defined in `src/core/state.py`) — a mutable singleton
constructed once at import time and shared across every function in `cli.py` and every
function that receives it as an argument. There is **no `global` keyword anywhere in the
current `run_extended_menu()`** for these fields; they are simply `state.attribute_name`
reads/writes, which sidesteps the entire class of Python global-scoping bugs that used to
exist (the former Bug-12/Bug-13 — see §14.2).

```python
@dataclass
class ProjectState:
    # --- UI & Environment State ---
    current_unit_system: str = "Metric"
    current_labels: dict = field(default_factory=lambda: METRIC_UNITS)
    beam_storage: list = field(default_factory=list)
    current_project: dict | None = None
    Materials: Any = None          # ← was a bare cli.py global in v3; now here
    SectionsDB: Any = None
    project_state: dict = field(default_factory=lambda: {...})  # see §5.5

    # --- Beam Geometry & Supports ---
    beam_length: float = 0.0
    A: float = 0.0
    B: float = 0.0
    A_restraint: list = field(default_factory=list)
    B_restraint: list = field(default_factory=list)
    A_type: str = ""
    B_type: str = ""
    support_types: tuple = ("pin", "roller")
    beam_type: str | None = None
    supports_list: list = field(default_factory=list)
    segments: list = field(default_factory=list)

    # --- Material Properties ---
    selected_material: str = ''
    elastic_modulus: float = 0.0
    density: float = 0.0
    yield_strength: float = 0.0
    ultimate_strength: float = 0.0
    poisson_ratio: float = 0.0

    # --- Cross-Section Properties ---
    shape: str = ""
    Ix: float = 0.0
    c: float = 0.0
    b: float = 0.0
    y_array: np.ndarray = field(default_factory=lambda: np.array([]))
    section_dims: dict = field(default_factory=dict)

    # --- Loads ---
    loads: dict = field(default_factory=dict)
    pointloads: list = field(default_factory=list)
    distributedloads: list = field(default_factory=list)
    momentloads: list = field(default_factory=list)
    triangleloads: list = field(default_factory=list)

    # --- Analysis Results ---
    num_points: int = SOLVER.DEFAULT_NUM_POINTS   # sourced from common.config
    X_Field: np.ndarray = field(default_factory=lambda: np.array([]))
    Total_ShearForce: np.ndarray = field(default_factory=lambda: np.array([]))
    Total_BendingMoment: np.ndarray = field(default_factory=lambda: np.array([]))
    Reactions: np.ndarray = field(default_factory=lambda: np.array([]))
    Deflection: Any = None
    Slope: Any = None
    Slopes: Any = None
    Curvatures: Any = None
    Shear_stress: Any = None
    bending_stress: Any = None
    FOS: Any = None
    AxialForce: Any = None
    AxialDisplacement: Any = None

state = ProjectState()   # module-level singleton; this is what everyone imports
```

**Important consequence for save/load**: because `save_project()`/`load_project()` now
read/write `state.*` directly (not disconnected module globals), the former Bug-13 class of
issue — "saved projects always contain the initial empty arrays because the analysis
results were local variables shadowing the never-updated module globals" — **cannot recur**
under this model. `state.X_Field` etc. are the single copy of the data; there is no shadow
copy to go stale.

**Important note for Stepped Bar**: `state.Ix`, `state.shape`, `state.c`, `state.b`,
`state.y_array`, `state.section_dims` are **not populated** in a pure Stepped Bar workflow —
`define_stepped_segments()` stores all per-segment geometry inside `state.segments`
instead. Code that reads these attributes must guard with
`if state.beam_type != "Stepped Bar"`.

---

### 5.2 Reactions Format

Unchanged from earlier versions:
```python
Reactions = [
    {
        "pos": float,   # Support position (m)
        "Fx":  float,   # Horizontal reaction (N), positive = rightward
        "Fy":  float,   # Vertical reaction (N), positive = upward
        "M":   float,   # Moment reaction (N·m), positive = CCW
    },
    ...
]
```
Backward compatibility: old array format `[Va, Vb, Ha]` or `[Va, Ha, Ma]` is converted to
this dict format in `load_project()`.

---

### 5.3 Loads Format

Unchanged from earlier versions — all values in base SI (N, m, N·m, N/m). See v3 content;
no changes to this schema.

```python
loads = {
    "pointloads":       [[pos, Fx, Fy], ...],
    "distributedloads": [[start, end, w], ...],       # w positive = upward
    "momentloads":      [[pos, M], ...],              # M positive = CCW
    "triangleloads":    [[start, end, peak, low], ...]# peak at start, low at end
}
```

---

### 5.4 Section Dims Format (by shape)

Unchanged from earlier versions. All dimensions in metres. Same format consumed by
`stress_solver.width_array_for_section()`, `area_solver.area_from_section()`, and all
PyVista functions.

```python
# I-beam
{"type": "I-beam",  "bf": float, "tf": float, "hw": float, "tw": float, "H": float}
# T-beam
{"type": "T-beam",  "bf": float, "tf": float, "hw": float, "tw": float,
 "y_bar": float, "H": float, "c_top": float, "c_bot": float}
# Circle
{"type": "Circle",          "diameter": float, "radius": float}
# Hollow Circle
{"type": "Hollow Circle",   "r_outer": float, "r_inner": float,
 "diameter_outer": float, "diameter_inner": float}
# Rectangle
{"type": "Rectangle",       "width": float, "height": float}
# Square
{"type": "Square",          "side": float}
# Hollow Square
{"type": "Hollow Square",   "outer_width": float, "inner_width": float, "t_wall": float}
# Hollow Rectangle
{"type": "Hollow Rectangle","outer_b": float, "outer_h": float,
 "inner_b": float, "inner_h": float, "t_flange": float, "t_web": float}
```

---

### 5.5 `state.project_state` Dict

```python
state.project_state = {
    "is_loaded":             bool,
    "profile_saved":         bool,  # True for Stepped Bar when segments defined
    "material_saved":        bool,
    "loads_saved":           bool,
    "supports_saved":        bool,
    "analysis_complete":     bool,
    "deflection_calculated": bool,
    "stress_calculated":     bool,
    "has_unsaved_changes":   bool,
}
```
For Stepped Bar: `profile_saved = True` after `define_stepped_segments()` completes, even
though `state.Ix`/`state.shape`/etc. (the single-profile attributes) remain at their
default 0/empty values — this is expected, see §5.1's note.

---

### 5.6 Project Save Format

Unchanged schema from earlier versions, now sourced from `state.*` instead of module
globals:
```json
{
  "segments": [ { "start": 0.0, "end": 2.0, "E": 210e9, "A": 0.01, "I": 8.33e-6,
                  "shape": "Rectangle", "section_dims": {...}, "c": 0.1, "b": 0.05,
                  "y_array": [...], "material_name": "Structural Steel (S275)",
                  "yield_strength": 275e6 }, ... ],
  "supports_list": [ {"pos": 0.0, "dof": [1,1,1], "ky": null, "kx": null}, ... ],
  "num_points": 2001
}
```
`num_points` is correctly persisted (was a known gap in earlier versions, now resolved —
`state.num_points` is read/written directly, no local-variable shadowing possible).

---

## 6. Beam Types Supported

Unchanged from earlier versions:

| Beam Type | Code String | Support Config | Solver | Statically |
|-----------|-------------|----------------|--------|------------|
| Simple Supported | `"Simple"` | Pin A, Roller B | indeterminate_solver | Determinate |
| Overhanging | `"Overhanging Beam"` | Pin A, Roller B (not at ends) | indeterminate_solver | Determinate |
| Cantilever | `"Cantilever"` | Fixed at x=0 | indeterminate_solver | Determinate |
| Fixed-Fixed | `"Fixed-Fixed"` | Fixed at x=0 and x=L | indeterminate_solver | Indeterminate |
| Propped Cantilever | `"Propped"` | Fixed x=0, Roller x=L | indeterminate_solver | Indeterminate |
| Continuous (n-span) | `"Continuous"` | User-defined positions | indeterminate_solver | Indeterminate |
| Custom | `"Custom"` | Arbitrary user DOF config | indeterminate_solver | Varies |
| Stepped Bar | `"Stepped Bar"` | Custom (define_custom_supports) | stepped_solver | Varies |

**DOF tuple convention**: `(x_constraint, y_constraint, moment_constraint)`, 1=fixed 0=free.

---

## 7. Cross-Section Types

Unchanged from earlier versions — 8 types, all handled by `moi_solver.py`,
`stress_solver.py`, `area_solver.py`, and `pyvista_plotting.py`.

| # | Name | `shape` String | MOI Function |
|---|------|---------------|-------------|
| 1 | I-Beam | `"I-beam"` | `inertia_moment_ibeam()` |
| 2 | T-Beam | `"T-beam"` | `inertia_moment_tbeam()` |
| 3 | Solid Circle | `"Circle"` | `inertia_moment_circle()` |
| 4 | Hollow Circle | `"Hollow Circle"` | `inertia_moment_hollow_circle()` |
| 5 | Square | `"Square"` | `inertia_moment_square()` |
| 6 | Hollow Square | `"Hollow Square"` | `inertia_moment_hollow_square()` |
| 7 | Rectangle | `"Rectangle"` | `inertia_moment_rectangle()` |
| 8 | Hollow Rectangle | `"Hollow Rectangle"` | `inertia_moment_hollow_rectangle()` |

---

## 8. Load Types and Sign Conventions

Unchanged from earlier versions. All values stored in SI. Positive = upward / rightward /
CCW. Triangular load format: `[start, end, peak, low]` where `peak` = intensity at `start`,
`low` = intensity at `end`, both positive = upward.

---

## 9. Unit System Architecture

**Rewritten from v3 to reflect `common/units.py` as the actual single source of truth**
(v3 described `get_divisor()` as living in `Menus.py`; it has since moved to
`common/units.py` and is only re-exported from `Menus.py` for backward compatibility — see
§4.10).

All values stored and computed in base SI. Unit conversion happens only at display
boundaries via `common.units.get_divisor()` (SI→display) and `common.units.to_si()`
(display→SI), and at the JSON-persistence boundary via `to_json()`/`from_json()`
(materials JSON stores MPa/GPa, not base-SI Pa — see §0).

| quantity | Metric divisor | Imperial divisor |
|----------|----------------|------------------|
| `'length'` | 1.0 | 0.3048 |
| `'length_small'` | 0.001 (→ mm) | 0.0254 (→ in) |
| `'force'` | 1.0 | 4.4482216 |
| `'moment'` | 1.0 | 1.3558179 |
| `'stress'` | 1e6 (→ MPa) | 6894757.29 (→ ksi) |
| `'modulus'` | 1e9 (→ GPa) | 6894757.29 (→ ksi) |
| `'density'` | 1.0 | 16.01846 |
| `'inertia'` | 1.0 | (0.0254)⁴ |
| `'sec_mod'` | 1.0 | (0.0254)³ |
| `'area'` | 1.0 | (0.3048)² |
| `'distributed'` | 1.0 | 14.5939 |

`define_stepped_segments()` and every other input handler use
`common.units.system_multiplier(unit_system, quantity)` for the display→SI conversion of
user-entered values — the old hardcoded literals in `inputs.py` are gone (see §4.11).

**Known API redundancy (not a bug, a cleanup item)**: `units.py` currently exposes both
`to_si(units_dict, quantity, value)` and `system_multiplier(unit_system, quantity)`, which
resolve through the same internal `_system_key()` lookup and differ only in whether they
accept a dict or a string. See `SESSION_HANDOFF.md` §P2-1 for the proposed collapse into
one function.

---

## 10. Analysis Pipeline (End-to-End)

### Standard beams (all types except Stepped Bar)

```
[Pre-processing complete — state.project_state flags all True]
         ↓
cli.py: builds _supports list of dicts from state.beam_type
         ↓
indeterminate_solver.solve_beam(beam_length=state.beam_length, beam_type=state.beam_type,
    supports=_supports, ..., E=state.elastic_modulus, I=state.Ix, num_points=state.num_points)
         ↓
_build_supports() → indeterminatebeam.Support objects
_build_loads()    → indeterminatebeam load objects
beam.analyse()    → SymPy stiffness solution
beam.get_shear_force/bending_moment/deflection/reaction → arrays
         ↓
cli.py: result unpacked directly into state.X_Field, state.Total_ShearForce,
        state.Total_BendingMoment, state.Deflection, state.Reactions, state.Slopes,
        state.Curvatures  (no global-scoping risk — see §5.1)
         ↓
[Optional] Stress:
    b_array = width_array_for_section(state.shape, state.section_dims, state.y_array)
    Q_array = first_moment_of_area_general(b_array, state.y_array)
    state.Shear_stress = calculate_shear_stress(state.Total_ShearForce, Q_array, state.Ix, b_array)
    state.bending_stress = calculate_bending_stress(state.Total_BendingMoment, state.c, state.Ix)
    state.FOS = Factor_of_Safety(state.Total_BendingMoment, state.c, state.yield_strength, state.Ix)
         ↓
[Optional] Plotting: main_plotting.py / pyvista_plotting.py — reads state.* directly
```

### Stepped Bar

```
[Segments defined via define_stepped_segments() — ⚠ CURRENTLY BROKEN, see §14.3 P0-1]
[Custom supports defined via define_custom_supports()]
[Loads defined via manage_loads()]
         ↓
cli.py: _supports = state.supports_list
         ↓
stepped_solver.solve_stepped_beam(segments=state.segments, supports=_supports, ...,
    num_points=state.num_points)
         ↓
_build_mesh() → _assemble_global() → _apply_point_loads() → _apply_distributed_loads()
    → _apply_boundary_conditions() → scipy.linalg.solve() → _extract_reactions()
    → _interpolate_to_field()
         ↓
cli.py: result unpacked into state.X_Field, ..., state.AxialForce, state.AxialDisplacement
         ↓
[Optional] Stress (per-segment):
    n_y = len(state.segments[0]['y_array']) if state.segments else 10001   # correctly sized
    state.Shear_stress = np.zeros((n_y, len(state.X_Field)))
    For each x_i in state.X_Field:
        find segment s containing x_i
        b_arr = width_array_for_section(s.shape, s.section_dims, s.y_array)
        Q_arr = first_moment_of_area_general(b_arr, s.y_array)
        tau = calculate_shear_stress(V[i], Q_arr, s.I, b_arr)
        sigma = calculate_bending_stress(M[i], s.c, s.I)
         ↓
[Optional] Axial plots: Plotly_AxialForce / Matplot_AxialForce / Plotly_AxialDisplacement /
    Matplot_AxialDisplacement / Plotly_CombinedStress / Matplot_CombinedStress — all
    dedicated functions, correctly dispatched (see §4.12)
[Optional] 3D FEA: correctly reachable for both Stepped Bar and standard beams via the
    dynamic fea_3d_choice/back_choice computation in cli.py (see §4.1)
```

---

## 11. Plotting Architecture

Unchanged in structure from earlier versions, with the additions noted in §4.12/§4.14
(axial/combined-stress plotting functions and `SERIES` entries now exist and are wired up).

### 2D Plots (`main_plotting.py`)

Built on `plot_theme.py` for consistent visual identity. Uses `present_plotly()` from
`export_helper.py` for all Plotly output. `_render_single(x, y, key, ...)` is the shared
renderer for any series key in `plot_theme.SERIES` — this now includes `"axial"`,
`"axialdispl"`, `"combinedstress"`.

### Beam Schematic (`beam_plot.py`)

`plot_beam_schematic()` handles all beam types including Stepped Bar (rendered as a regular
beam; step-change in cross-section is not visually indicated in the 2D schematic — this is
unchanged/still a known limitation, not a bug).

### 3D FEA Viewer (`pyvista_plotting.py`)

`_build_beam_mesh()` extrudes a single cross-section polygon along X. For Stepped Bar, only
a uniform cross-section mesh is possible with the current architecture (see §4.13) — this
remains an open enhancement, not a regression.

---

## 12. Materials Database

Unchanged from earlier versions. 25 standard materials + custom materials in
`data/custom_materials.json`. JSON schema units: Density (kg/m³), Yield/Ultimate Strength
(MPa), Elastic Modulus (GPa). Conversion to SI in `select_material()`: ×1e6 for strength,
×1e9 for modulus — this could route through `common.units.from_json()`/`to_si()` instead of
the inline `* 1e6`/`* 1e9` literals currently present; low-priority cleanup, not filed as a
numbered issue since the values are correct, just not centrally sourced.

For Stepped Bar, each segment stores its own `E` and `yield_strength` in SI (Pa) directly
in the segment dict. `state.elastic_modulus`/`state.yield_strength` are NOT used during
Stepped Bar analysis or stress computation.

---

## 13. Dependencies

Unchanged from earlier versions:

| Package | Role |
|---------|------|
| `indeterminatebeam` | Core structural solver for all non-Stepped beam types |
| `numpy` | All numerical arrays |
| `sympy` | Underlying algebra for indeterminatebeam |
| `scipy` | `cumulative_trapezoid` (stress_solver), `linalg.solve` (stepped_solver) |
| `pyvista` | 3D interactive FEA viewer |
| `vtk` | Required by PyVista |
| `plotly` | 2D interactive plots |
| `matplotlib` | 2D static plots |
| `termcolor` | Coloured CLI output |

PyVista is optional; `cli.py` catches `ImportError` and sets `_PYVISTA_AVAILABLE = False`.

---

## 14. Known Bugs — Resolved and Open

### 14.1 Resolved in earlier sessions (pre-v3, still correct)

| Bug ID | Description | Status |
|--------|-------------|--------|
| BUG-05 | `NameError: beam_type not defined` out-of-order menu access | Fixed |
| BUG-07 | `NameError` for post-processing variables if stress not calculated | Fixed |
| BUG-09 | Shear stress incorrect for non-rectangular sections (constant b) | Fixed |
| BUG-10 | `support_types` not persisted to JSON | Fixed |

---

### 14.2 Resolved — verified fixed against the current code (previously listed as OPEN in v3)

**Every item below was listed as an unresolved "New Confirmed Bug" in v3 of this
briefing. Each has been checked directly against the current source and confirmed fixed.
They are retained here only as a historical record — do not re-investigate or "re-fix"
these; doing so wastes a session on already-solved problems.**

| Former ID | Description | Verified fix location |
|---|---|---|
| Bug-11 | 3D FEA visualization unreachable for non-Stepped beams (hardcoded `sub_choice == '12'`) | `cli.py` postprocessing loop now computes `fea_3d_choice = '12' if state.beam_type == "Stepped Bar" else '9'` and `back_choice` dynamically — confirmed present, see §4.1 |
| Bug-12 | `UnboundLocalError` for `segments` in non-Stepped workflows | Resolved structurally — `segments` is `state.segments`, an attribute access, not a local variable subject to Python's local/global compile-time inference |
| Bug-13 | Module-level result globals (`X_Field`, `Reactions`, etc.) never updated; `save_project()` wrote stale/empty data | Resolved structurally by the `ProjectState` migration (§5.1) — there is no longer a "module global" vs. "function-local shadow" distinction to go stale |
| Bug-14 | `NameError: len_div` in Overhanging Beam boundary-conditions display | `len_div = get_divisor(state.current_labels, 'length')` is now defined before use in that block |
| Bug-15 | `Shear_stress` array wrong shape for Stepped Bar (`len(y_array)==0`) | Now sized from the segment's own array: `n_y = len(state.segments[0]['y_array']) if state.segments else 10001` |
| Bug-16 | `TypeError` in Combined Stress plot (extra positional arg to `Matplot_BendingStress`) | Replaced with a dedicated `Matplot_CombinedStress(X_Field, combined_stress, units=...)` function — no signature collision |
| Bug-17 | Axial Force / Displacement plots silently produced no output (`'Axial Force'` not a valid `plot_type`) | Replaced with dedicated `Plotly_AxialForce`/`Matplot_AxialForce`/`Plotly_AxialDisplacement`/`Matplot_AxialDisplacement` functions, correctly called from `cli.py` |

Also resolved (were listed under v3 §14.3 "code quality issues", not numbered bugs):
- `num_points` not persisted → now `state.num_points`, correctly saved/loaded (§5.6)
- `display_analysis_results()` equilibrium check → generalized, not Simple-beam-specific
- `moi_solver.print_derived_properties()` hardcoded `"m²"`/`"m³"` → now unit-aware (§4.6)

---

### 14.3 OPEN — current priority. Full detail and fixes in `SESSION_HANDOFF.md`.

#### P0-1 — CRASH: `ui/inputs.py` imports a `cli.py` global that no longer exists

**File**: `src/ui/inputs.py`, `define_stepped_segments()`
```python
from ui.cli import select_material, load_material_database, Materials
if Materials is None:
    load_material_database()
```
`Materials` was migrated to `state.Materials` during the `ProjectState` refactor; this
import now raises `ImportError` on every Stepped Bar material-assignment attempt. **This is
the highest-priority open bug** — it fully blocks the Stepped Bar workflow. Minimal fix:
```python
from core.state import state
from database.materials_database import MaterialDatabase
...
if state.Materials is None:
    state.Materials = MaterialDatabase()
selected_mat = select_material(unit_system, units)
```
Structural fix (recommended): move `select_material` out of `cli.py` entirely, which
removes the underlying reason this circular-import pattern exists at all — see
`SESSION_HANDOFF.md` §P3, `ui/materials/selector.py`.

#### P0-2 — SILENT WRONG OUTPUT: `display_engineering_recommendations` ignores unit system

**File**: `src/ui/Menus.py::display_engineering_recommendations` — no `units` parameter;
hardcodes `"m"`/`"m⁴"`/`"m³"` labels on raw SI values regardless of
`state.current_unit_system`. An Imperial-mode user sees mislabeled SI numbers in the
Design-Check report. Fix: add `units=` parameter, divide by `get_divisor(units, ...)`
throughout, thread `units=state.current_labels` from the `cli.py` call site. Full patch in
`SESSION_HANDOFF.md` §P0-2.

#### Residual (low severity) — see §4.2

`indeterminate_solver.solve_beam()`'s internal `support_positions` extraction block still
has an `if`/`if`/`elif` pattern for Simple vs. Overhanging Beam (distinct from
`_build_supports()`, which is correctly `if`/`elif`). Currently produces correct results by
coincidence (both branches compute the same `[A, B]`); fragile for future beam-type
additions. Not a numeric bug today — tracked for opportunistic cleanup.

#### Cleanup-only (no behavior change) — see `SESSION_HANDOFF.md` §P1

- Unused `import os`/`import sys` in `area_solver.py` and `stepped_solver.py`
- Stale comment in `inputs.py` referencing removed path-injection code
- `pyvista_plotting.py` mixes `pathlib` and `os.path` idioms
- `cli.py`'s manual `sys.path` bootstrap duplicates `ensure_src_in_path()`'s effect (deferred — needs launch-contract sign-off)
- `METRIC_UNITS`/`IMPERIAL_UNITS` (Menus.py) vs. `METRIC_LABELS`/`IMPERIAL_LABELS` (cli.py) naming inconsistency for the same objects

---

## 15. Development Conventions

### Adding a New Cross-Section

1. Add `inertia_moment_<name>(units=None)` in `moi_solver.py` returning 6-tuple
2. Add `area_from_section` branch in `area_solver.py` for the new shape
3. Add branch in `choose_profile()` in `Menus.py`
4. Add `profile_choice == 'n'` branch in `cli.py` (menu 3 → sub_choice 2)
5. Add `elif shape == "Name":` in `stress_solver.width_array_for_section()`
6. Add `elif shape == "Name":` in `pyvista_plotting._build_cross_section_loops()`

### Adding a New Beam Type (standard)

1. Add to `Beam_Classification()` in `inputs.py`
2. Add `_build_supports()` branch in `indeterminate_solver.py` — use proper `if`/`elif`,
   not the pattern flagged as residual in §14.3
3. Add `_supports` construction in `cli.py` solve section (reads `state.*`)
4. Add `support_positions` branch in `indeterminate_solver.solve_beam()` for Reactions
   extraction — again, `elif`, not a second independent `if`
5. Add support drawing in `beam_plot.plot_beam_schematic()`
6. Add `state.project_state["supports_saved"]` logic in `cli.py` selection `'2'`

### Adding a New Beam Type (custom FEM solver, like Stepped Bar)

1. All of steps 1, 5 above
2. Write a dedicated solver module analogous to `stepped_solver.py` returning the standard
   dict format
3. Add solver dispatch in `cli.py` solve block — better yet, use the solver-registry
   pattern from `SESSION_HANDOFF.md` §P5-1 instead of extending the `if/elif` chain further
4. Guard all single-profile `state.*` attributes (`Ix`, `shape`, `c`, `b`, `y_array`,
   `section_dims`) with `if state.beam_type != "YourType"` wherever read
5. Add extra postprocessing menu items if the solver produces new result arrays — use the
   dynamic-numbering pattern already established for Stepped Bar (§4.1), do not hardcode
   menu item numbers (this is exactly how the former Bug-11 was introduced)

### Output Formatting

- All `print` inside `Menus.py` and `moi_solver.py` use `termcolor.colored()` / `cprint()`
- Box-drawing characters: `╔ ╗ ╚ ╝ ║ ═ ┌ ┐ └ ┘ │ ─ ┬ ┴`
- User-facing numbers always in display units (not SI); use `:.3f` or `:.2e`
- **Every display function must accept and use a `units=` parameter.** `display_engineering_recommendations` is the one current exception (§14.3 P0-2) — do not treat it as a template for new report functions.

### JSON Serialisation

- Always use `NumpyEncoder` when calling `json.dump()` for project files
- `safe_serialize()` converts ndarray → list for project dict values

### Exception Handling

- **Never use bare `except Exception:`**. Narrow to specific tuples (e.g.
  `(ValueError, TypeError, OSError)`) so genuine programming bugs (`AttributeError`,
  `NameError`) propagate immediately.
- Use `common.exceptions` for domain-specific errors: `AltruxIQError`, `ValidationError`,
  `SectionGeometryError`, `SolverError`, `SingularStiffnessMatrixError`,
  `PersistenceError`.
- In `pyvista_plotting.py`, VTK-callback defensive blocks are the only permitted exception
  to the narrowing rule — they protect the C++ event loop from crashing Python.

### Path and Unit Rules (new section — codifies §0)

- **Never** compute a path with `__file__` arithmetic outside `common/paths.py`.
- **Never** hardcode a unit-conversion factor (`0.3048`, `6894757.29`, etc.) outside
  `common/units.py`'s `_SI_FACTORS`/`_JSON_FACTORS` tables.
- **Never** add a magic engineering constant (a deflection-limit denominator, a fallback
  material property, a mesh-density constant) outside `common/config.py`.
- If a new module needs a path, factor, or constant that doesn't exist yet in `common/`,
  add it there first, then import it — do not inline it "just this once."

---

## 16. Active Development Notes

### 16.1 What is Complete and Working

- Full analysis pipeline for all 7 standard beam types via `indeterminate_solver.py`
- Stepped Bar analysis via `stepped_solver.py` (axial + bending combined FEM) — **solver
  itself is correct and bug-free; the wizard that feeds it materials is currently broken,
  see §14.3 P0-1**
- `area_solver.py` for A(m²) from `section_dims`
- All 8 cross-section MOI computations
- Shear and bending stress (section-aware)
- Factor of Safety
- Deflection (via solvers)
- All 2D plots (Plotly + Matplotlib), including Stepped Bar axial/combined-stress plots
- 3D FEA viewer with interactive probing, MIN/MAX labels, pinned measurements — reachable
  for both Stepped Bar and standard beam types
- Save/Load project to JSON with backward compatibility, correct `num_points` persistence
- Dual unit system (Metric/Imperial) — with the one exception at §14.3 P0-2
- Standard section library + custom section save/delete
- Custom material add/delete
- Animated load-application 3D viewer (`AnimationPlotter`)
- Plotly diagram export (HTML + browser-based PNG)
- Commercial-grade plot theme (`plot_theme.py`), including Stepped Bar series
- Foundation layer: `common/paths.py`, `common/units.py`, `common/config.py`,
  `common/exceptions.py`, `core/state.py`

### 16.2 Immediate Priorities

**Do not re-derive this list from scratch — it is maintained in `SESSION_HANDOFF.md`,
which is the authoritative, actively-updated task queue.** Summary as of this briefing:

1. **P0 (fix now)**: §14.3 P0-1 (Stepped Bar material crash), P0-2 (unit-system-ignored
   report)
2. **P1**: dead-import/stale-comment cleanup, `pathlib`/`os.path` consistency in
   `pyvista_plotting.py`
3. **P2**: `units.py` API consolidation (`to_si`/`system_multiplier`)
4. **P3**: module decomposition of `cli.py`/`Menus.py`/`inputs.py` into
   `console/`/`beam/`/`materials/`/`reports/`/`menus/`/`project/` subpackages
5. **P4**: `ProjectRepository` (save/load), `LiveClock` widget class, logging config
6. **P5**: solver registry (`@register_solver`), plugin contract
   (`EngineeringModule` protocol), settings/config split (`common/settings.py` vs.
   `common/config.py`)

### 16.3 Known Intentional Architecture Decisions

- **Deflection source**: always from the solver (`indeterminate_solver` or
  `stepped_solver`); `stress_solver.calculate_beam_deflection()` is bypassed by design.
- **`Legacy/main_solver.py`**: kept for reference; not called from anywhere in the active
  CLI.
- **PyVista optional**: app runs without PyVista via `try/except ImportError` guard.
- **MOI solver functions are interactive**: they call `input()` internally by design —
  this is also why `moi_solver.py` is not currently unit-testable without mocking `input()`,
  a known limitation if test coverage is added later.
- **`num_points=SOLVER.DEFAULT_NUM_POINTS` (2001) default**: reducing to a lower value for
  Continuous/Stepped beams remains a performance option exposed via the Solver Resolution
  menu, not an automatic behavior.
- **Stepped Bar mesh density**: `SOLVER.MIN_LOAD_SUBDIVISIONS` (100) sub-elements per
  distributed-load span, sourced from `common.config`, not a local constant.