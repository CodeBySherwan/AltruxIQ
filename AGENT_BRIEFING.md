# AltruxIQ — Agent Briefing & Developer Reference (v3)

> **Purpose**: Full technical context for any AI agent assisting with this project.
> Read this before writing, editing, or debugging any code.
> Every section is authoritative — do not guess what is not documented here.
> **This version supersedes all earlier AltruxIQ briefing documents.**
> Explicitly corrects errors present in v2.

---

## Table of Contents

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
14. [Known Bugs and Applied Fixes](#14-known-bugs-and-applied-fixes)
15. [Development Conventions](#15-development-conventions)
16. [Active Development Notes](#16-active-development-notes)

---

## 1. Project Identity

| Field            | Value                                                          |
|------------------|----------------------------------------------------------------|
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
│   ├── database/
│   │   ├── __init__.py
│   │   ├── materials_database.py     # MaterialDatabase class
│   │   └── sections_database.py      # SectionsDatabase class
│   │
│   ├── plotting/
│   │   ├── __init__.py
│   │   ├── beam_plot.py              # 2D beam schematic + reaction diagram (Plotly)
│   │   ├── export_helper.py          # Centralised present/export workflow
│   │   ├── main_plotting.py          # All 2D SFD/BMD/stress/deflection plots
│   │   ├── plot_theme.py             # Single source of visual truth (colours, fonts)
│   │   ├── plotting_helper.py        # Low-level Plotly shape-drawing helpers
│   │   └── pyvista_plotting.py       # 3D FEA contour viewer (PyVista)
│   │
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── area_solver.py            # NEW: Cross-sectional area A(m²) from section_dims
│   │   ├── indeterminate_solver.py   # PRIMARY SOLVER — stiffness via indeterminatebeam
│   │   ├── main_solver.py            # LEGACY SOLVER — not called from CLI
│   │   ├── moi_solver.py             # MOI solver (all 8 cross-section types)
│   │   ├── stepped_solver.py         # NEW: 2D frame FEM for stepped bars
│   │   └── stress_solver.py          # Stress, deflection, FOS calculations
│   │
│   ├── Temporary/
│   │   └── Improved Solver.py        # Working copy of legacy solver — not active
│   │
│   └── ui/
│       ├── __init__.py
│       ├── cli.py                    # MAIN APPLICATION — all menu logic, global state
│       ├── inputs.py                 # Raw user input handlers
│       └── Menus.py                  # All display/print functions + unit helpers
│
├── beam_projects.json                # Auto-created on first save
├── exports/diagrams/                 # Auto-created by export_helper on first export
├── screenshots/                      # Auto-created by PyVista on first 3D render
├── requirements.txt
└── .gitignore
```

### Path Injection Pattern (universal across all modules)

```python
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
```

This must be preserved in any new file added under `src/`.

---

## 4. Module Reference

### 4.1 `src/ui/cli.py` — Main Application

The application's brain. Contains:

- All **global state variables** (see Section 5.1)
- All **menu routing logic** in `run_extended_menu()`
- Project save/load functions
- Material selection function (`select_material`)
- `NumpyEncoder` class for JSON serialisation of NumPy types
- `init()` — resets all state flags on startup

**Critical constraint**: The entire session state is stored as module-level globals. There
is no session object or class. Any function that modifies state must reference globals
explicitly with `global var_name`.

**Known global scoping defect (Bug-13 — see Section 14)**: `run_extended_menu()` does NOT
declare the analysis result arrays as global (`X_Field`, `Total_ShearForce`,
`Total_BendingMoment`, `Deflection`, `Reactions`, `Slopes`, `Curvatures`, `Shear_stress`,
`bending_stress`, `FOS`, `AxialForce`, `AxialDisplacement`, `segments`). Assignments in
the analysis block create *local* variables. Within a single run of `run_extended_menu()`
the locals persist across loop iterations and work correctly. However, `save_project()` and
other standalone functions read the module-level globals which are never updated, so saved
projects always contain the initial empty arrays for these fields.

**The solve block** (menu `'8'`, sub-choice `'1'`):
- Builds `_supports` list of dicts based on `beam_type`
- **Dispatches to `solve_stepped_beam()`** when `beam_type == "Stepped Bar"`, passing `segments` and supports
- **Dispatches to `solve_beam()`** for all other beam types
- Unpacks standard keys plus `AxialForce` and `AxialDisplacement` (Stepped Bar only)
- Sets `project_state["analysis_complete"] = True`

---

### 4.2 `src/solver/indeterminate_solver.py` — Primary Solver (non-Stepped beams)

**Handles**: Simple, Overhanging Beam, Cantilever, Fixed-Fixed, Propped, Continuous, Custom.
**Does NOT handle**: Stepped Bar — that is routed to `stepped_solver.py`.

**Function**: `solve_beam(beam_length, beam_type, supports, pointloads, distributedloads,
momentloads, triangleloads, E, I, num_points=2001) -> dict`

Uses the `indeterminatebeam` Python package (SymPy-based stiffness method).

**Return value** (dict):
```python
{
    "X_Field":              np.ndarray,   # shape (num_points,)
    "Total_ShearForce":     np.ndarray,   # shape (num_points,)
    "Total_BendingMoment":  np.ndarray,   # shape (num_points,)
    "Deflection":           np.ndarray,   # shape (num_points,), metres
    "Reactions":            list[dict],   # see Section 5.2
    "Slopes":               np.ndarray,   # np.gradient(Deflection, X_Field)
    "Curvatures":           np.ndarray,   # BendingMoment / (E * I)
}
```

**Load sign convention in `_build_loads`**:
- Vertical loads: `PointLoadV(Fy, pos)` — positive Fy = upward (matches user input)
- Horizontal: `PointLoad(Fx, pos, 0)` — positive Fx = rightward
- UDL: `UDLV(w, (start, end))` — positive w = upward
- Moment: `PointTorque(M, pos)` — positive = CCW
- Trapezoidal: `TrapezoidalLoadV(force=(-peak, -low), span=(start, end))` — **negated** because
  the `indeterminatebeam` library's trapezoidal API has opposite sign convention

**Pre-existing code quality issue in `solve_beam()`**: The `support_positions` extraction
block starts with `if beam_type == "Simple":` followed by a separate `if beam_type == "Overhanging Beam":`
(not `elif`). This means for `beam_type == "Simple"`, the correct `support_positions` is
set by the first `if`, then immediately **overwritten** by the `else` clause of the
second `if/elif/else` chain. In practice both expressions produce identical results for
Simple beams (`[A, B]`), so no numerical error occurs — but it is a latent correctness risk
for future maintenance.

---

### 4.3 `src/solver/stepped_solver.py` — Stepped Beam FEM Solver (NEW)

**Handles**: `beam_type == "Stepped Bar"` only.

Implements a 2D frame element FEM with 3 DOFs per node (u, v, θ — axial, transverse,
rotation). Supports combined axial + bending analysis for beams with varying cross-section
and material along their length.

**Public function**:
```python
solve_stepped_beam(
    segments: list,
    supports: list,
    pointloads=None,
    distributedloads=None,
    momentloads=None,
    triangleloads=None,
    num_points: int = 2001,
) -> dict
```

**Return value** (dict):
```python
{
    "X_Field":              np.ndarray,   # shape (num_points,)
    "Total_ShearForce":     np.ndarray,   # shape (num_points,)
    "Total_BendingMoment":  np.ndarray,   # shape (num_points,)
    "Deflection":           np.ndarray,   # shape (num_points,), metres
    "AxialForce":           np.ndarray,   # shape (num_points,), Newtons — NEW
    "AxialDisplacement":    np.ndarray,   # shape (num_points,), metres — NEW
    "Reactions":            list[dict],   # same format as indeterminate_solver
    "Slopes":               np.ndarray,   # shape (num_points,)
    "Curvatures":           np.ndarray,   # shape (num_points,)
}
```

**Segment input format** (each element of the `segments` list):
```python
{
    "start":        float,        # left boundary (m)
    "end":          float,        # right boundary (m)
    "E":            float,        # Young's modulus (Pa)
    "A":            float,        # cross-sectional area (m²)
    "I":            float,        # moment of inertia (m⁴)
    "shape":        str,          # canonical shape name
    "section_dims": dict,         # same format as Section 5.4
    "c":            float,        # neutral axis to extreme fibre (m)
    "b":            float,        # representative width (m)
    "y_array":      np.ndarray,   # np.linspace(-c, c, 10001)
    "material_name": str,
    "yield_strength": float,      # Pa
}
```

**Internal pipeline**:
1. `_build_mesh()` — collects all structural positions (segment boundaries, supports, load positions, distributed-load boundaries + subdivision nodes) into a sorted unique node set
2. `_assemble_global()` — assembles global K and zero F using `_element_stiffness()` per element
3. `_apply_point_loads()` — adds concentrated forces/moments to F
4. `_apply_distributed_loads()` — adds Hermite-consistent equivalent nodal loads via `_hermite_equivalent_loads()`
5. `_apply_boundary_conditions()` — partitions K into free/constrained DOF sets
6. `scipy.linalg.solve(K_ff, F_f)` — direct solve (raises `LinAlgError` on singular K)
7. `_extract_reactions()` — computes R = K·d − F at constrained DOFs
8. `_interpolate_to_field()` — evaluates all results on a uniform grid via Hermite cubic shape functions

**Element stiffness matrix**: standard 6×6 Euler-Bernoulli 2D frame element (axial and
bending decoupled). Bending uses cubic Hermite formulation.

**Hermite-consistent equivalent nodal loads** — analytically derived by integrating
`w(ξ)·Nₖ(ξ)·L dξ` over `ξ ∈ [0, 1]`:
```
V_i = L(7w₁ + 3w₂) / 20
M_i = L²(3w₁ + 2w₂) / 60
V_j = L(3w₁ + 7w₂) / 20
M_j = −L²(2w₁ + 3w₂) / 60
```
Reduces to `wL/2`, `±wL²/12` for UDL (w₁ == w₂). Zero extra nodes, exact for polynomial
loads up to cubic.

**Sign convention**: upward positive for vertical loads; rightward positive for axial;
CCW positive for moments. This is consistent with the user-input convention, with NO
additional negation (unlike `indeterminate_solver.py`'s trapezoidal load negation).

**Mesh density**: `MIN_LOAD_ELEMS = 100` sub-elements per distributed/triangular load
span. This ensures piecewise-cubic Hermite convergence. For a beam with many overlapping
distributed loads the mesh can grow to ~1000 nodes (3000 DOFs); still fast for
`scipy.linalg.solve` but worth noting for performance-sensitive use.

**Bugs fixed internally in stepped_solver.py** (relative to an earlier draft):
- Bug 1 (Critical): triangular load interpolation was reversed (`low + (peak-low)*t` → `peak + (low-peak)*t`)
- Bug 2 (Moderate): distributed load boundary nodes not injected into mesh
- Perf 1: O(n²) node lookup via `list.index()` → O(1) dict lookup
- Perf 2: distributed load sampling replaced by exact Hermite equivalent loads
- Perf 3: `np.linalg.cond()` (full SVD) replaced by `try/except LinAlgError`

---

### 4.4 `src/solver/area_solver.py` — Cross-Sectional Area Solver (NEW)

**Function**: `area_from_section(shape: str, section_dims: dict) -> float`

Returns cross-sectional area A (m²) from the canonical `section_dims` dict produced by
`moi_solver.py`. Used by `define_stepped_segments()` in `inputs.py` to compute A for each
segment before passing it to `solve_stepped_beam()`.

Handles all 8 cross-section types (same set as `moi_solver.py`). Raises `ValueError` for
invalid shapes or missing dimensions.

---

### 4.5 `src/solver/main_solver.py` — Legacy Solver (NOT active in CLI)

Custom numerical solver supporting only "Simple" and "Cantilever". Not called from `cli.py`.
Do not modify unless specifically directed.

---

### 4.6 `src/solver/moi_solver.py` — Moment of Inertia Solver

All `inertia_moment_*` functions return a **6-tuple**:
```python
(Ix, shape_name, c, b_rep, y_array, section_dims)
```

| Return | Type | Description |
|--------|------|-------------|
| `Ix` | float | Second moment of area about neutral axis (m⁴) |
| `shape_name` | str | Canonical shape string |
| `c` | float | Distance from NA to extreme fibre (m) |
| `b_rep` | float | Representative width (m) |
| `y_array` | ndarray | `np.linspace(-c, c, 10001)` |
| `section_dims` | dict | Shape geometry (see Section 5.4) |

Returns `None` on invalid input. Callers must check before unpacking.

`load_section_from_library(entry: dict) -> tuple` — converts a `standard_sections.json`
or `custom_sections.json` entry into the standard 6-tuple.

---

### 4.7 `src/solver/stress_solver.py` — Stress and Deflection

**`width_array_for_section(shape, section_dims, y_array)`** → `np.ndarray`
Builds b(y) — the actual material width at every height. BUG-09 fix for section-accurate
shear stress. Handles all 8 cross-section types.

**`first_moment_of_area_general(b_array, y_array)`** → `np.ndarray`
Q(y) by numerical integration (cumulative_trapezoid from bottom upward). Negatives clamped to 0.

**`calculate_shear_stress(shear_force, Q_array, moment_of_inertia, b)`** → 2D ndarray
Shape `(len(X_Field), len(y_array))`. τ = VQ/(Ib(y)). `b` can be scalar or 1D array.

**`calculate_bending_stress(bending_moment, c, moment_of_inertia)`** → `np.ndarray`
σ = Mc/I. 1D array along beam length.

**`Factor_of_Safety(bending_moment, c, yield_strength, moment_of_inertia)`** → float

**`calculate_beam_deflection(...)`** — double integration via cumulative_trapezoid.
Currently NOT called from CLI (deflection comes from the solvers directly).

---

### 4.8 `src/database/materials_database.py` — Material Database

**Class**: `MaterialDatabase(filename="materials.Json")`

Methods: `list_all_materials()`, `search_by_property()`, `add_custom_material()`,
`delete_custom_material()`, `all_materials` (property = standard + custom).

Custom materials persisted to `data/custom_materials.json`.

---

### 4.9 `src/database/sections_database.py` — Sections Database

**Class**: `SectionsDatabase()`

Methods: `get_standard_families()`, `get_sections_in_family(family)`,
`save_custom_section(dict)`, `delete_custom_section(name)`, `list_custom_sections()`.

Standard sections from `data/standard_sections.json`; custom sections from
`data/custom_sections.json`.

---

### 4.10 `src/ui/Menus.py` — Display Engine and Unit System

`get_divisor(units_dict, quantity)` → float — converts base SI to active display unit.

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

`postprocessing_menu(beam_type)` — menu item count depends on `beam_type`:
- Non-Stepped: 10 items (8 standard + 3D FEA + Back). 3D FEA = item 9, Back = item 10.
- Stepped Bar: 13 items (8 standard + 3 axial items + 3D FEA + Back).
  Axial Force = 9, Axial Displacement = 10, Combined Stress = 11, 3D FEA = 12, Back = 13.

**Critical note**: the `cli.py` postprocessing dispatch uses hardwired sub_choice strings
('9', '10', '11', '12') which are ONLY correct for Stepped Bar. For non-Stepped beams the
3D FEA option (menu item 9) maps to sub_choice `'9'` (the Axial Force handler) and the
actual 3D FEA handler at `'12'` is unreachable. **See Bug-11 in Section 14.**

---

### 4.11 `src/ui/inputs.py` — Input Handlers

**`define_stepped_segments(unit_system, units)`** → `list[dict]` or `None` (NEW)

Interactive wizard. For each segment:
1. Prompts for segment length
2. Calls cross-section selection sub-menu (custom / library / saved)
3. Calls `moi_solver.inertia_moment_*()` or `load_section_from_library()` → 6-tuple
4. Calls `area_from_section()` for A
5. Calls `select_material()` imported from `cli.py`
6. Accumulates segment dict with `start`, `end`, `E`, `A`, `I`, `shape`, `section_dims`, `c`, `b`, `y_array`, `material_name`, `yield_strength`

**Circular import warning**: `define_stepped_segments()` contains a function-level import
`from ui.cli import select_material, load_material_database, Materials`. This is deferred
(runs only when the function is called, at which point `cli.py` is fully loaded), so it
works in practice but is architecturally fragile. Refactoring `select_material` to
`Menus.py` or a separate `ui/material_selector.py` would eliminate the circular dependency.

Other functions (unchanged from v2):
`Beam_Classification()`, `Beam_Length()`, `Beam_Supports()`, `define_continuous_supports()`,
`define_custom_supports()`, `manage_loads()`, `get_solver_resolution()`, `define_custom_material()`.

`Beam_Classification()` now returns `"Stepped Bar"` for choice `'8'`.

---

### 4.12 `src/plotting/main_plotting.py` — 2D Result Plots

Plotly and Matplotlib backends for SFD, BMD, deflection, shear stress, bending stress.

Public functions: `Plotly_sfd_bmd`, `Plotly_shear_force`, `Plotly_bending_moment`,
`Plotly_Deflection`, `Plotly_ShearStress`, `Plotly_BendingStress`,
`Plotly_combined_diagrams`, `Matplot_sfd_bmd`, `Matplot_Deflection`, `Matplot_ShearStress`,
`Matplot_BendingStress`, `Matplot_combined`.

**Missing functions for Stepped Bar** (see Section 16 — Plotting Update Plan):
There are no `Plotly_AxialForce`, `Matplot_AxialForce`, `Plotly_AxialDisplacement`,
`Matplot_AxialDisplacement`, `Plotly_CombinedStress`, or `Matplot_CombinedStress` functions.
The current cli.py calls to `Matplot_sfd_bmd`/`Plotly_sfd_bmd` with `'Axial Force'` as
`plot_type` and `Matplot_BendingStress` with wrong argument count are both bugs (see
Bug-16 and Bug-17 in Section 14).

---

### 4.13 `src/plotting/pyvista_plotting.py` — 3D FEA Viewer

Commercial-grade 3D contour visualiser. Key public functions: `PyVista_shear_force`,
`PyVista_bending_moment`, `PyVista_shear_stress`, `PyVista_bending_stress`,
`PyVista_deflection`, `PyVista_reactions_schematic`, `PyVista_combined`,
`PyVista_animation`.

Classes: `ProbingPlotter` (interactive probing with hover, click-to-pin),
`AnimationPlotter` (load-application animation with GIF export).

**Not yet implemented for Stepped Bar**: `PyVista_axial_force`, `PyVista_axial_displacement`.
Segment-boundary rendering (step-change in cross-section) is also not yet handled — the
mesh is built from a single shape/section_dims, which is only valid for uniform beams.

---

### 4.14 `src/plotting/plot_theme.py` — Visual Identity

Single source of truth for colours, fonts, SERIES dict, Plotly template registration,
Matplotlib rcParams.

`SERIES` dict keys (current): `"shear"`, `"moment"`, `"deflect"`, `"shearstress"`,
`"bendstress"`.

**Missing entries for Stepped Bar** (see Section 16 — Plotting Update Plan):
`"axial"`, `"axialdispl"`, `"combinedstress"` are not yet in the SERIES dict.

---

## 5. Core Data Structures

### 5.1 Global State Variables in `cli.py`

Module-level globals. Persist for the duration of the session.

```python
# Session tracking
current_unit_system: str       # "Metric" or "Imperial"
current_labels: dict           # METRIC_LABELS or IMPERIAL_LABELS
beam_type: str | None          # "Simple", "Cantilever", "Fixed-Fixed", "Propped",
                               # "Continuous", "Overhanging Beam", "Custom",
                               # "Stepped Bar", or None

# Geometry
beam_length: float             # metres (SI)
A: float                       # Pin support position (metres) — standard beams
B: float                       # Roller support position (metres) — standard beams
A_restraint: tuple             # DOF tuple, e.g. (1,1,0)
B_restraint: tuple
A_type: str
B_type: str
supports_list: list            # For Continuous / Custom / Stepped Bar beams

# Cross-section (single-profile beams only — NOT set for Stepped Bar workflow)
Ix: float                      # m⁴
shape: str
c: float                       # m
b: float                       # m
y_array: np.ndarray            # linspace(-c, c, 10001)
section_dims: dict

# Stepped Bar specific
segments: list                 # list of segment dicts (see Section 4.3)
AxialForce: np.ndarray | None  # N, shape (num_points,) — None until solved
AxialDisplacement: np.ndarray | None  # m, shape (num_points,) — None until solved

# Material (SI)
selected_material: dict
density: float                 # kg/m³
yield_strength: float          # Pa
ultimate_strength: float       # Pa
elastic_modulus: float         # Pa
poisson_ratio: float
shear_yield_strength: float    # 0.55 * yield_strength Pa

# Loads
loads: dict                    # see Section 5.3
pointloads, distributedloads, momentloads, triangleloads: list

# Analysis results (SI)
X_Field: np.ndarray            # m
Total_ShearForce: np.ndarray   # N
Total_BendingMoment: np.ndarray # N·m
Deflection: np.ndarray         # m (downward negative)
Slopes: np.ndarray             # rad
Curvatures: np.ndarray         # 1/m
Reactions: list[dict]

# Stress results
Shear_stress: np.ndarray | None  # 2D (len_X × len_y) Pa — None until calculated
bending_stress: np.ndarray | None # 1D (len_X,) Pa — None until calculated
FOS: float | None

# Project
current_project: dict | None
beam_storage: list
project_state: dict            # see Section 5.5
support_types: tuple
num_points: int                # solver resolution, default 2001
Materials: MaterialDatabase | None
SectionsDB: SectionsDatabase | None
```

**Important**: `Ix`, `shape`, `c`, `b`, `y_array`, `section_dims` are **not populated**
in a pure Stepped Bar workflow. `define_stepped_segments()` stores all per-segment geometry
inside the `segments` list. Code that reads these globals must guard with
`if beam_type != "Stepped Bar"`.

---

### 5.2 Reactions Format

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

Backward compatibility: old array format `[Va, Vb, Ha]` or `[Va, Ha, Ma]` is converted
to this dict format in `load_project()`.

---

### 5.3 Loads Format

All values in base SI (N, m, N·m, N/m).

```python
loads = {
    "pointloads":       [[pos, Fx, Fy], ...],
    "distributedloads": [[start, end, w], ...],       # w positive = upward
    "momentloads":      [[pos, M], ...],              # M positive = CCW
    "triangleloads":    [[start, end, peak, low], ...]# peak at start, low at end
}
```

**Triangular load convention** (AltruxIQ): `peak` is the intensity at `start`, `low` is
the intensity at `end`. This is opposite to what the old `main_solver.py` implemented
(bug, now fixed). `stepped_solver.py` uses this convention correctly.

---

### 5.4 Section Dims Format (by shape)

All dimensions in metres. Same format consumed by `stress_solver.width_array_for_section()`,
`area_solver.area_from_section()`, and all PyVista functions.

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

### 5.5 `project_state` Dict

```python
project_state = {
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
though `Ix`, `shape`, `c`, `b`, `y_array`, `section_dims` (the single-profile globals)
remain at their default 0/empty values.

---

### 5.6 Project Save Format

All fields from v2 plus:

```json
{
  "segments": [ { "start": 0.0, "end": 2.0, "E": 210e9, "A": 0.01, "I": 8.33e-6,
                  "shape": "Rectangle", "section_dims": {...}, "c": 0.1, "b": 0.05,
                  "y_array": [...], "material_name": "Structural Steel (S275)",
                  "yield_strength": 275e6 }, ... ],
  "supports_list": [ {"pos": 0.0, "dof": [1,1,1], "ky": null, "kx": null}, ... ]
}
```

**Limitation (Bug-13)**: because `save_project()` reads module-level globals that are never
updated by `run_extended_menu()`, `X_Field`, `Total_ShearForce`, `Total_BendingMoment`,
and `Reactions` in the saved file always contain the **initial empty arrays**, not the
computed results. Loading such a project restores empty arrays. This needs the global
scoping fix before saves become reliable.

---

## 6. Beam Types Supported

| Beam Type | Code String | Support Config | Solver | Statically |
|-----------|-------------|----------------|--------|------------|
| Simple Supported | `"Simple"` | Pin A, Roller B | indeterminate_solver | Determinate |
| Overhanging | `"Overhanging Beam"` | Pin A, Roller B (not at ends) | indeterminate_solver | Determinate |
| Cantilever | `"Cantilever"` | Fixed at x=0 | indeterminate_solver | Determinate |
| Fixed-Fixed | `"Fixed-Fixed"` | Fixed at x=0 and x=L | indeterminate_solver | Indeterminate |
| Propped Cantilever | `"Propped"` | Fixed x=0, Roller x=L | indeterminate_solver | Indeterminate |
| Continuous (n-span) | `"Continuous"` | User-defined positions | indeterminate_solver | Indeterminate |
| Custom | `"Custom"` | Arbitrary user DOF config | indeterminate_solver | Varies |
| **Stepped Bar** | `"Stepped Bar"` | Custom (define_custom_supports) | **stepped_solver** | Varies |

**DOF tuple convention**: `(x_constraint, y_constraint, moment_constraint)`, 1=fixed 0=free.

`beam_type == "Stepped Bar"` triggers:
- `define_stepped_segments()` in Profile Definition instead of single-profile selection
- `define_custom_supports()` in Boundary Conditions
- `solve_stepped_beam()` in Analysis instead of `solve_beam()`
- Extra postprocessing menu items (9, 10, 11) for axial results
- Per-segment stress computation in the stress/FOS block

---

## 7. Cross-Section Types

8 types, unchanged from v2. All handled by `moi_solver.py`, `stress_solver.py`,
`area_solver.py` (new), and `pyvista_plotting.py`.

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

Each segment of a Stepped Bar can use any of these independently.

---

## 8. Load Types and Sign Conventions

Unchanged from v2. All values stored in SI. Positive = upward / rightward / CCW.

**Triangular load format**: `[start, end, peak, low]` where `peak` = intensity at `start`,
`low` = intensity at `end`. Both positive = upward. **This is the corrected convention**;
the old `main_solver.py` had it reversed.

`stepped_solver.py` applies triangular loads without additional sign negation (in contrast
to `indeterminate_solver.py` which negates trapezoidal loads for the external library).

---

## 9. Unit System Architecture

Unchanged from v2. All values stored and computed in base SI. Unit conversion happens only
at display boundaries via `get_divisor()`.

`define_stepped_segments()` uses `CONVERSION_TO_SI[unit_system]["length"]` multiplier
for lengths entered by the user, consistent with all other input handlers.

---

## 10. Analysis Pipeline (End-to-End)

### Standard beams (all types except Stepped Bar)

```
[Pre-processing complete]
         ↓
cli.py: builds _supports list of dicts from beam_type
         ↓
indeterminate_solver.solve_beam(beam_length, beam_type, supports, loads, E=elastic_modulus, I=Ix)
         ↓
_build_supports() → indeterminatebeam.Support objects
_build_loads()    → indeterminatebeam load objects
beam.analyse()    → SymPy stiffness solution
beam.get_shear_force/bending_moment/deflection/reaction → arrays
         ↓
cli.py: local vars X_Field, Total_ShearForce, Total_BendingMoment, Deflection, Reactions, Slopes, Curvatures
         (⚠ module-level globals NOT updated — Bug-13)
         ↓
[Optional] Stress:
    b_array = width_array_for_section(shape, section_dims, y_array)
    Q_array = first_moment_of_area_general(b_array, y_array)
    Shear_stress = calculate_shear_stress(Total_ShearForce, Q_array, Ix, b_array)
    bending_stress = calculate_bending_stress(Total_BendingMoment, c, Ix)
    FOS = Factor_of_Safety(Total_BendingMoment, c, yield_strength, Ix)
         ↓
[Optional] Plotting: main_plotting.py / pyvista_plotting.py
```

### Stepped Bar

```
[Segments defined via define_stepped_segments()]
[Custom supports defined via define_custom_supports()]
[Loads defined via manage_loads()]
         ↓
cli.py: _supports = supports_list
         ↓
stepped_solver.solve_stepped_beam(segments, supports, loads, num_points)
         ↓
_build_mesh()           → sorted unique node set (segment boundaries + load positions + subdivisions)
_assemble_global()      → K (3n×3n), F (3n,)
_apply_point_loads()    → F updated
_apply_distributed_loads() → F updated via Hermite equivalent nodal loads
_apply_boundary_conditions() → K_ff, F_f partition
scipy.linalg.solve(K_ff, F_f) → d_free
_extract_reactions()    → Reactions list of dicts
_interpolate_to_field() → X_Field, ShearForce, BendingMoment, Deflection,
                           AxialForce, AxialDisplacement, Slopes, Curvatures
         ↓
cli.py: local vars populated including AxialForce and AxialDisplacement
         (⚠ module-level globals NOT updated — Bug-13)
         ↓
[Optional] Stress (per-segment):
    For each x_i in X_Field:
        find segment s containing x_i
        b_arr = width_array_for_section(s.shape, s.section_dims, s.y_array)
        Q_arr = first_moment_of_area_general(b_arr, s.y_array)
        tau = calculate_shear_stress(V[i], Q_arr, s.I, b_arr)
        sigma = calculate_bending_stress(M[i], s.c, s.I)
    (⚠ Shear_stress array initialised with wrong shape — Bug-15)
         ↓
[Optional] Axial plots: (⚠ wrong function called — Bug-16/17)
[Optional] 3D FEA: only accessible for Stepped Bar; blocked for non-Stepped — Bug-11
```

---

## 11. Plotting Architecture

### 2D Plots (`main_plotting.py`)

Built on `plot_theme.py` for consistent visual identity. Uses `present_plotly()` from
`export_helper.py` for all Plotly output.

**`_render_single(x, y, key, ...)`** — shared renderer for any series key in
`plot_theme.SERIES`. Stepping bar plots require new series keys (see Section 16).

**`format_loads_for_plotting(loads_dict)`** → list of tuples, used by `beam_plot.py`.

### Beam Schematic (`beam_plot.py`)

`plot_beam_schematic()` handles all beam types including Stepped Bar (rendered as a regular
beam; step-change in cross-section is not visually indicated in the 2D schematic).

### 3D FEA Viewer (`pyvista_plotting.py`)

`_build_beam_mesh()` extrudes a single cross-section polygon along X. For Stepped Bar, only
a uniform cross-section mesh is possible with the current architecture — per-segment
geometry is not yet modelled in PyVista.

---

## 12. Materials Database

Unchanged from v2. 25 standard materials + custom materials in `data/custom_materials.json`.

JSON schema units: Density (kg/m³), Yield/Ultimate Strength (MPa), Elastic Modulus (GPa).
Conversion to SI in `select_material()`: ×1e6 for strength, ×1e9 for modulus.

For Stepped Bar, each segment stores its own `E` and `yield_strength` in SI (Pa) directly
in the segment dict. The module-level `elastic_modulus`, `yield_strength` globals are NOT
used during stepped bar analysis or stress computation.

---

## 13. Dependencies

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
| `pandas` | Listed in requirements; not actively used |
| `dash` + ecosystem | Legacy leftovers; not used — safe to remove |

PyVista is optional; `cli.py` catches `ImportError` and sets `_PYVISTA_AVAILABLE = False`.

---

## 14. Known Bugs and Applied Fixes

### 14.1 Pre-existing Bugs (applied in earlier sessions)

| Bug ID | Description | Status | Location |
|--------|-------------|--------|----------|
| BUG-05 | `NameError: beam_type not defined` out-of-order menu access | Fixed | `cli.py` module-level init |
| BUG-07 | `NameError` for post-processing variables if stress not calculated | Fixed | `cli.py` module-level `Deflection = None`, etc. |
| BUG-09 | Shear stress incorrect for non-rectangular sections (constant b) | Fixed | `stress_solver.width_array_for_section()` |
| BUG-10 | `support_types` not persisted to JSON; schematic markers lost on load | Fixed | `save_project()` / `load_project()` |
| — | Cantilever BendingMoment double-negation | Fixed | `main_solver.py` (legacy, not active) |
| — | Trapezoidal load centroid wrong in main_solver | Fixed | `main_solver.py` (legacy) |
| — | `TrapezoidalLoadV` opposite sign convention in indeterminate_solver | Fixed/Documented | `_build_loads()` negation |
| — | Stepped solver triangular load interpolation reversed | Fixed internally | `stepped_solver.py` docstring |
| — | Stepped solver distributed load boundaries not in mesh | Fixed internally | `stepped_solver._build_mesh()` |
| — | O(n²) node lookup in stepped solver | Fixed internally | `stepped_solver` dict-based lookup |
| — | `np.linalg.cond()` full SVD overhead in stepped solver | Fixed internally | replaced with `try/except LinAlgError` |

---

### 14.2 New Confirmed Bugs (Stepped Bar integration — requires fixing)

---

#### Bug-11 — CRITICAL: 3D FEA visualization inaccessible for all non-Stepped beam types

**File**: `src/ui/cli.py`, postprocessing dispatch inside `selection == '9'`

**Root cause**: When Stepped Bar support was added, three extra menu items (Axial Force,
Axial Displacement, Combined Stress) were inserted before the 3D FEA entry in
`postprocessing_menu()`. The `cli.py` dispatch block hardwires `sub_choice == '12'` as
the 3D FEA handler. For non-Stepped beams the menu only has 10 items, so the 3D FEA option
is displayed as item 9 (`back_choice = '10'`). The user's choice of `'9'` hits the Axial
Force handler (which prints "only available for Stepped Bars" and continues), and the user
can never reach `sub_choice == '12'`.

**Impact**: `PyVista_*` visualizations are completely unreachable for Simple, Cantilever,
Fixed-Fixed, Propped, Continuous, Custom, and Overhanging Beam types.

**Fix**:
```python
# In the postprocessing while-loop, compute beam-type-specific choice numbers:
fea_3d_choice = '12' if beam_type == "Stepped Bar" else '9'
back_choice = '13' if beam_type == "Stepped Bar" else '10'

# Then restructure the dispatch:
if sub_choice == back_choice:
    break
elif sub_choice == fea_3d_choice:
    # 3D FEA PyVista menu (existing code at sub_choice == '12')
    ...
elif beam_type == "Stepped Bar" and sub_choice == '9':   # Axial Force
    ...
elif beam_type == "Stepped Bar" and sub_choice == '10':  # Axial Displacement
    ...
elif beam_type == "Stepped Bar" and sub_choice == '11':  # Combined Stress
    ...
```

---

#### Bug-12 — CRITICAL: `UnboundLocalError` for `segments` in non-Stepped beam workflows

**File**: `src/ui/cli.py`, `run_extended_menu()`

**Root cause**: Python determines at bytecode-compile time whether a variable is local or
global. Because `segments = seg_result` appears inside `run_extended_menu()` (in the
Stepped Bar branch of the Profile Definition block), Python treats `segments` as local
throughout the **entire** function. When a non-Stepped beam project reaches:

```python
display_profile_info(beam_length, shape, Ix, c, b, y_array,
                     units=current_labels, beam_type=beam_type, segments=segments)
```

— and the `segments = seg_result` assignment was never executed — Python raises
`UnboundLocalError: local variable 'segments' referenced before assignment`.

**Impact**: crash when viewing profile info for any non-Stepped beam type in a fresh
session (before the Stepped Bar branch has ever been entered).

**Fix**: Add `global segments` to the globals block at the top of `run_extended_menu()`:
```python
global support_types, supports_list
global segments, AxialForce, AxialDisplacement   # ADD THIS LINE
global beam_type
```

Apply the same fix for all other result variables listed in Bug-13.

---

#### Bug-13 — CRITICAL: Module-level result globals never updated — `save_project()` writes stale data

**File**: `src/ui/cli.py`, `run_extended_menu()`

**Root cause**: The following variables are assigned inside `run_extended_menu()` but are
**not** in its `global` declarations:

```
X_Field, Total_ShearForce, Total_BendingMoment, Deflection,
Reactions, Slopes, Curvatures,
Shear_stress, bending_stress, FOS,
segments, AxialForce, AxialDisplacement, num_points
```

Python therefore creates *local* variables for all of them. Within a single session the
locals persist across `while` loop iterations and all visualizations work correctly.
However, `save_project()`, `load_project()`, and `display_*` functions called from outside
`run_extended_menu()` read the **module-level** globals, which remain at their initial
empty/None values.

**Impact**: Saving a project after analysis writes empty `X_Field`, `Total_ShearForce`,
etc. to the JSON file. A loaded project that was saved post-analysis has no results.

**Fix**: Extend the `global` declaration block at the top of `run_extended_menu()`:
```python
global X_Field, Total_ShearForce, Total_BendingMoment, Deflection
global Reactions, Slopes, Curvatures
global Shear_stress, bending_stress, FOS
global segments, AxialForce, AxialDisplacement
global num_points
```

---

#### Bug-14 — MODERATE: `NameError: len_div` in Overhanging Beam boundary conditions display

**File**: `src/ui/cli.py`, boundary conditions block for `"Overhanging Beam"`

**Root cause**: After `A, B, ... = Beam_Supports(...)`, the code prints support positions:
```python
print(f"Pin Support Position(A): {A / len_div:.3f} {current_labels['length']}")
print(f"Roller Support Position(B): {B / len_div:.3f} {current_labels['length']}")
```
`len_div` is never defined in this scope.

**Impact**: `NameError` crash immediately after user enters supports for an Overhanging Beam.

**Fix**: Add before the print statements:
```python
len_div = get_divisor(current_labels, 'length')
```

---

#### Bug-15 — MODERATE: Shear_stress array wrong shape for Stepped Bar

**File**: `src/ui/cli.py`, stress/FOS calculation block (`sub_choice == '4'`)

**Root cause**:
```python
if beam_type == "Stepped Bar":
    Shear_stress = np.zeros((len(y_array), len(X_Field)))
```
`y_array` is the module-level global, which is `np.array([])` for any Stepped Bar
workflow (since `define_stepped_segments()` never sets the single-profile globals).
`len(y_array)` == 0. The subsequent assignment `Shear_stress[:, i] = tau` where `tau`
has shape `(10001,)` raises:
```
ValueError: could not broadcast input array from shape (10001,) into shape (0,)
```

**Impact**: Stress calculation crashes for every Stepped Bar analysis.

**Fix**:
```python
if beam_type == "Stepped Bar":
    n_y = len(segments[0]['y_array']) if segments else 10001
    Shear_stress = np.zeros((n_y, len(X_Field)))
```
Note: all segments use `np.linspace(-c, c, 10001)`, so `n_y` is always 10001.
The per-row assignment is then shape-consistent.

---

#### Bug-16 — MODERATE: `TypeError` in Combined Stress plot — extra positional argument

**File**: `src/ui/cli.py`, postprocessing `sub_choice == '11'`

**Root cause**:
```python
Matplot_BendingStress(X_Field, combined_stress, beam_length, units=current_labels)
```
Signature of `Matplot_BendingStress` is `(X_Field, BendingStress, units=None)` — only
two positional parameters. `beam_length` is passed as the third positional arg, filling
`units`, while `units=current_labels` as a keyword arg then collides.

```
TypeError: Matplot_BendingStress() got multiple values for argument 'units'
```

Same issue with the Plotly branch:
```python
Plotly_BendingStress(X_Field, combined_stress, beam_length, units=current_labels)
```
Signature: `(X_Field, BendingStress, beam_length, units=None)` — this one IS correct for
Plotly (beam_length is a valid positional arg there). Only the Matplotlib call is broken.

**Fix**:
```python
# Matplotlib branch:
Matplot_BendingStress(X_Field, combined_stress, units=current_labels)
# Plotly branch (already correct — no change needed):
Plotly_BendingStress(X_Field, combined_stress, beam_length, units=current_labels)
```

---

#### Bug-17 — MODERATE: Axial Force and Axial Displacement plots produce no output

**File**: `src/ui/cli.py`, postprocessing `sub_choice == '9'` and `sub_choice == '10'`

**Root cause**: `Matplot_sfd_bmd` and `Plotly_sfd_bmd` are called with `'Axial Force'` or
`'Axial Displacement'` as the `plot_type` argument. Neither function recognises these
values; the `panels` list stays empty and no plot is produced or error raised:

```python
# sub_choice '9' — silent no-op:
Matplot_sfd_bmd(X_Field, AxialForce, Total_BendingMoment, 'Axial Force', units=current_labels)
Plotly_sfd_bmd(X_Field, AxialForce, Total_BendingMoment, beam_length, 'Axial Force', units=current_labels)

# sub_choice '10' — same issue:
Matplot_Deflection(X_Field, AxialDisplacement, units=current_labels)  # This one is OK
Plotly_Deflection(X_Field, AxialDisplacement, beam_length, units=current_labels)  # Also OK
```

Note: `sub_choice == '10'` (Axial Displacement) correctly uses `Matplot_Deflection` and
`Plotly_Deflection`, so that plot is fine. Only `sub_choice == '9'` (Axial Force) is broken.

**Fix**: Create dedicated `Plotly_AxialForce` and `Matplot_AxialForce` functions (see
Section 16 — Plotting Update Plan) and call them:
```python
# sub_choice '9':
if style == '1':
    Matplot_AxialForce(X_Field, AxialForce, units=current_labels)
elif style == '2':
    Plotly_AxialForce(X_Field, AxialForce, beam_length, units=current_labels)
```

---

### 14.3 Pre-existing Code Quality Issues (not crash bugs)

- **Circular import**: `inputs.py` → `ui.cli` → `inputs.py` (deferred function-level import,
  works at runtime, but fragile). Refactor `select_material` out of `cli.py` to break it.
- **`indeterminate_solver._build_supports()`**: uses `if`/`if`/`elif` (not `if`/`elif`/`elif`)
  for Simple vs Overhanging; the `support_positions` set by the first `if` is overwritten
  by the `else` clause of the second chain, giving the same result by coincidence.
- **`num_points` not persisted**: the resolution setting is a local variable in
  `run_extended_menu()` and is not written to the saved project (always saves 2001).
- **PyVista cross-section for Stepped Bar**: `_build_beam_mesh()` uses a single
  shape/section_dims, so stepped cross-section changes along X are not rendered.
- **`display_analysis_results()` equilibrium check**: only sums Va+Vb for Simple beam;
  does not work for Continuous/Fixed-Fixed beams.

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
2. Add `_build_supports()` branch in `indeterminate_solver.py`
3. Add `_supports` construction in `cli.py` solve section
4. Add `support_positions` branch in `indeterminate_solver.py` for Reactions extraction
5. Add support drawing in `beam_plot.plot_beam_schematic()`
6. Add `project_state["supports_saved"]` logic in `cli.py` selection `'2'`

### Adding a New Beam Type (custom FEM solver, like Stepped Bar)

1. All of steps 1, 6 above
2. Write a dedicated solver module analogous to `stepped_solver.py` returning the
   standard dict format (`X_Field`, `Total_ShearForce`, `Total_BendingMoment`,
   `Deflection`, `Reactions`, `Slopes`, `Curvatures`, plus any extras)
3. Add solver dispatch in `cli.py` solve block (analogous to `solve_stepped_beam` branch)
4. Guard all single-profile globals (`Ix`, `shape`, `c`, `b`, `y_array`, `section_dims`)
   with `if beam_type != "YourType"` wherever they are read
5. Add extra postprocessing menu items if the solver produces new result arrays
6. Fix postprocessing dispatch numbering to avoid Bug-11 class errors (use dynamic
   `fea_3d_choice` and `back_choice` based on beam type)

### Output Formatting

- All `print` inside `Menus.py` and `moi_solver.py` use `termcolor.colored()` / `cprint()`
- Box-drawing characters: `╔ ╗ ╚ ╝ ║ ═ ┌ ┐ └ ┘ │ ─ ┬ ┴`
- User-facing numbers always in display units (not SI); use `:.3f` or `:.2e`

### JSON Serialisation

- Always use `NumpyEncoder` when calling `json.dump()` for project files
- `safe_serialize()` converts ndarray → list for project dict values

---

## 16. Active Development Notes

### 16.1 What is Complete and Working

- Full analysis pipeline for all 6 standard beam types (Simple, Cantilever, Fixed-Fixed,
  Propped, Continuous, Custom) via `indeterminate_solver.py`
- **New**: Stepped Bar analysis via `stepped_solver.py` (axial + bending combined FEM)
- **New**: `area_solver.py` for A(m²) from section_dims
- **New**: `define_stepped_segments()` wizard in `inputs.py`
- **New**: Per-segment material and cross-section support
- All 8 cross-section MOI computations
- Shear and bending stress (section-aware, BUG-09 fix)
- Factor of Safety
- Deflection (via solvers)
- All 2D plots (Plotly + Matplotlib)
- 3D FEA viewer with interactive probing, MIN/MAX labels, pinned measurements
- Save/Load project to JSON with backward compatibility
- Dual unit system (Metric/Imperial)
- Standard section library + custom section save/delete
- Custom material add/delete
- Animated load-application 3D viewer (`AnimationPlotter`)
- Plotly diagram export (HTML + browser-based PNG)
- Commercial-grade plot theme (`plot_theme.py`)

### 16.2 Immediate Fixes Required (Ordered by Severity)

These bugs must be fixed before the Stepped Bar feature can be considered stable:

**Priority 1 — Apply global declarations to `run_extended_menu()`** (fixes Bug-12 AND Bug-13):
```python
# At the top of run_extended_menu(), extend to:
global X_Field, Total_ShearForce, Total_BendingMoment, Deflection
global Reactions, Slopes, Curvatures
global Shear_stress, bending_stress, FOS
global segments, AxialForce, AxialDisplacement
global num_points
```

**Priority 2 — Fix postprocessing dispatch** (fixes Bug-11):
```python
fea_3d_choice = '12' if beam_type == "Stepped Bar" else '9'
back_choice   = '13' if beam_type == "Stepped Bar" else '10'
# Replace hardwired '12' and '10' checks with these variables
```

**Priority 3 — Fix Stepped Bar shear stress array shape** (fixes Bug-15):
```python
n_y = len(segments[0]['y_array']) if segments else 10001
Shear_stress = np.zeros((n_y, len(X_Field)))
```

**Priority 4 — Fix `len_div` NameError in Overhanging Beam** (fixes Bug-14):
```python
len_div = get_divisor(current_labels, 'length')
```
(add before the two `print(f"... {A / len_div ...}")` lines)

**Priority 5 — Fix Combined Stress Matplotlib call** (fixes Bug-16):
```python
Matplot_BendingStress(X_Field, combined_stress, units=current_labels)
# remove the extra `beam_length` positional argument
```

**Priority 6 — Fix Axial Force plotting** (fixes Bug-17):
Requires adding new plotting functions first (see Section 16.3), then replace the
`Matplot_sfd_bmd(..., 'Axial Force', ...)` calls with dedicated function calls.

---

### 16.3 Plotting Update Plan — Axial Analysis Support

This plan covers all changes required to give Stepped Bar axial results the same plotting
quality as the existing shear/bending/deflection outputs.

#### Step 1: `src/plotting/plot_theme.py`

Add three new entries to the `SERIES` dict:

```python
SERIES = {
    "shear":         {"line": "#1E66F5", "fill": "rgba(30,102,245,0.12)",  "label": "Shear Force"},
    "moment":        {"line": "#D64550", "fill": "rgba(214,69,80,0.12)",   "label": "Bending Moment"},
    "deflect":       {"line": "#0E9F6E", "fill": "rgba(14,159,110,0.12)",  "label": "Deflection"},
    "shearstress":   {"line": "#0E7C86", "fill": "rgba(14,124,134,0.12)",  "label": "Shear Stress"},
    "bendstress":    {"line": "#7C4DCB", "fill": "rgba(124,77,203,0.12)",  "label": "Bending Stress"},
    # --- NEW ---
    "axial":         {"line": "#E08600", "fill": "rgba(224,134,0,0.12)",   "label": "Axial Force"},
    "axialdispl":    {"line": "#5B8C00", "fill": "rgba(91,140,0,0.12)",    "label": "Axial Displacement"},
    "combinedstress":{"line": "#9C2C77", "fill": "rgba(156,44,119,0.12)", "label": "Combined Stress"},
}
```

No other changes to `plot_theme.py`.

---

#### Step 2: `src/plotting/main_plotting.py`

Add six new public functions, following the exact pattern of existing single-diagram
functions. Insert after `Plotly_BendingStress` and `Matplot_BendingStress`.

**New Plotly functions** (each delegates to `_render_single`):

```python
def Plotly_AxialForce(X_Field, AxialForce, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    _render_single(X_Field / l_div, AxialForce / f_div, "axial",
                   "Axial Force Diagram", u['force'], u['length'],
                   f"Axial Force ({u['force']})")

def Plotly_AxialDisplacement(X_Field, AxialDisplacement, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    _render_single(X_Field / l_div, AxialDisplacement / ls_div, "axialdispl",
                   "Axial Displacement Diagram", u['length_small'], u['length'],
                   f"Axial Displacement ({u['length_small']})", sig=3)

def Plotly_CombinedStress(X_Field, CombinedStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    s_div = get_divisor(u, 'stress')
    _render_single(X_Field / l_div, CombinedStress / s_div, "combinedstress",
                   "Combined Stress Diagram (Bending + Axial)", u['stress'], u['length'],
                   f"Combined Stress ({u['stress']})")
```

**New Matplotlib functions** (each delegates to `_render_single_mpl`):

```python
def Matplot_AxialForce(X_Field, AxialForce, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, AxialForce / f_div, "axial",
                       "Axial Force Diagram", u['force'], u['length'],
                       f"Axial Force ({u['force']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()

def Matplot_AxialDisplacement(X_Field, AxialDisplacement, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, AxialDisplacement / ls_div, "axialdispl",
                       "Axial Displacement Diagram", u['length_small'], u['length'],
                       f"Axial Displacement ({u['length_small']})", sig=3)
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()

def Matplot_CombinedStress(X_Field, CombinedStress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    s_div_val = get_divisor(u, 'stress')
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, CombinedStress / s_div_val, "combinedstress",
                       "Combined Stress Diagram", u['stress'], u['length'],
                       f"Combined Stress ({u['stress']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()
```

**Update `Plotly_combined_diagrams`**: add an optional `AxialForce=None` and
`CombinedStress=None` parameter so the combined view can include axial results for Stepped
Bar sessions:

```python
def Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
                             Deflection=None, ShearStress=None, AxialForce=None,
                             CombinedStress=None, units=None):
    ...
    if AxialForce is not None:
        panels.append(("axial", AxialForce[::step] / f_div,
                       f"Axial Force ({u['force']})", u['force'], "Axial Force Diagram"))
    if CombinedStress is not None:
        s_div = get_divisor(u, 'stress')
        panels.append(("combinedstress", CombinedStress[::step] / s_div,
                       f"Combined Stress ({u['stress']})", u['stress'], "Combined Stress Diagram"))
```

**Update `Matplot_combined`** similarly with `AxialForce=None`, `CombinedStress=None`.

**Add exports** to the module's public API (no `__all__` currently, so just ensure the
names are importable).

---

#### Step 3: `src/ui/cli.py` — Update imports and dispatch

At the top of `cli.py`, extend the import from `main_plotting.py`:

```python
from plotting.main_plotting import (
    ...,                          # existing imports
    Plotly_AxialForce,            # NEW
    Matplot_AxialForce,           # NEW
    Plotly_AxialDisplacement,     # NEW
    Matplot_AxialDisplacement,    # NEW
    Plotly_CombinedStress,        # NEW
    Matplot_CombinedStress,       # NEW
)
```

Replace the postprocessing `sub_choice == '9'` dispatch:

```python
elif sub_choice == '9' and beam_type == "Stepped Bar":  # Axial Force
    if AxialForce is None:
        print_error("Axial Force not available. Run analysis first.")
        time.sleep(2); continue
    try:
        style = input(colored("Choose a style (1 Matplotlib, 2 Plotly) ➔ ", 'cyan'))
        if style == '1':
            Matplot_AxialForce(X_Field, AxialForce, units=current_labels)
        elif style == '2':
            Plotly_AxialForce(X_Field, AxialForce, beam_length, units=current_labels)
        else:
            print_error("Invalid style."); time.sleep(2)
    except Exception as e:
        print_error(f"Error: {e}"); time.sleep(2)
```

Replace `sub_choice == '10'` (Axial Displacement, already uses correct functions but
should guard on `beam_type`):

```python
elif sub_choice == '10' and beam_type == "Stepped Bar":  # Axial Displacement
    if AxialDisplacement is None:
        print_error("Axial Displacement not available. Run analysis first.")
        time.sleep(2); continue
    try:
        style = input(colored("Choose a style (1 Matplotlib, 2 Plotly) ➔ ", 'cyan'))
        if style == '1':
            Matplot_AxialDisplacement(X_Field, AxialDisplacement, units=current_labels)
        elif style == '2':
            Plotly_AxialDisplacement(X_Field, AxialDisplacement, beam_length, units=current_labels)
        else:
            print_error("Invalid style."); time.sleep(2)
    except Exception as e:
        print_error(f"Error: {e}"); time.sleep(2)
```

Replace `sub_choice == '11'` (Combined Stress):

```python
elif sub_choice == '11' and beam_type == "Stepped Bar":  # Combined Stress
    if AxialForce is None or not project_state.get("stress_calculated", False):
        print_error("Run analysis and stress calculation first.")
        time.sleep(2); continue
    try:
        # Compute combined = axial + bending (signed)
        combined_stress = np.zeros_like(X_Field)
        for i, x in enumerate(X_Field):
            seg = next((s for s in segments if s["start"] <= x <= s["end"]), None)
            if seg is None: continue
            sigma_axial = AxialForce[i] / seg["A"]
            M_val = Total_BendingMoment[i]
            sigma_bending = abs(M_val) * seg["c"] / seg["I"] if seg["I"] > 0 else 0.0
            sign = 1.0 if M_val >= 0 else -1.0
            combined_stress[i] = sigma_axial + sign * sigma_bending

        style = input(colored("Choose a style (1 Matplotlib, 2 Plotly) ➔ ", 'cyan'))
        if style == '1':
            Matplot_CombinedStress(X_Field, combined_stress, units=current_labels)
        elif style == '2':
            Plotly_CombinedStress(X_Field, combined_stress, beam_length, units=current_labels)
        else:
            print_error("Invalid style."); time.sleep(2)
    except Exception as e:
        print_error(f"Error: {e}"); time.sleep(2)
```

Update the Combined Plots call (`sub_choice == '8'`) to pass axial data for Stepped Bar:

```python
elif sub_choice == '8':  # Combined
    defl_data  = Deflection    if project_state.get("deflection_calculated") else None
    shear_data = Shear_stress  if project_state.get("stress_calculated")     else None
    axial_data = AxialForce    if (beam_type == "Stepped Bar" and AxialForce is not None) else None
    Plotly_combined_diagrams(
        X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
        Deflection=defl_data, ShearStress=shear_data,
        AxialForce=axial_data, units=current_labels
    )
```

---

#### Step 4: `src/plotting/pyvista_plotting.py` — Axial 3D contour views (future)

Two new public functions following the pattern of `PyVista_shear_force`:

```python
def PyVista_axial_force(X_Field, AxialForce, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "force": "N"}
    l_div, f_div = get_divisor(units, "length"), get_divisor(units, "force")
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, AF_vis = _downsample_for_visuals(X_Field / l_div, AxialForce / f_div, 0.2)
    mesh = _build_beam_mesh(X_vis, AF_vis, shape, section_dims, draw_c, draw_b, "AxialForce")
    pl, pp = _build_fea_plotter(mesh, "AxialForce",
                                 title="Axial Force (Element-Nodal)",
                                 units=units['force'], result_kind="force")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("axial_force"))

def PyVista_axial_displacement(X_Field, AxialDisplacement, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "length_small": "mm"}
    l_div, ls_div = get_divisor(units, "length"), get_divisor(units, "length_small")
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, AD_vis = _downsample_for_visuals(X_Field / l_div, AxialDisplacement / ls_div, 0.2)
    mesh = _build_beam_mesh(X_vis, np.abs(AD_vis), shape, section_dims,
                             draw_c, draw_b, "AxialDisplacement")
    pl, pp = _build_fea_plotter(mesh, "AxialDisplacement",
                                 title="Axial Displacement (Element-Nodal)",
                                 units=units['length_small'], result_kind="displacement")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("axial_displacement"))
```

Add these to `PyVista_combined()` with guards:
```python
if AxialForce is not None:
    PyVista_axial_force(X_Field, AxialForce, beam_length, shape, section_dims, c, b, units)
if AxialDisplacement is not None:
    PyVista_axial_displacement(X_Field, AxialDisplacement, beam_length, shape, section_dims, c, b, units)
```

Note: `_build_beam_mesh` uses a single shape/section_dims — for Stepped Bar the 3D mesh
will show a uniform cross-section (the mesh cannot currently represent segment step-changes).
A full fix requires per-segment mesh stitching in `pyvista_plotting.py`, which is left as a
future enhancement.

Update `PyVista_animation` `scalar_map` to include the two new keys:
```python
scalar_map = {
    ...
    "AxialForce":    (AxialForce,         units["force"],        "force",        "Axial Force"),
    "AxialDispl":    (AxialDisplacement,  units["length_small"], "displacement", "Axial Displacement"),
}
```

---

#### Step 5: `src/ui/cli.py` — PyVista menu for Stepped Bar

Update the `pyvista_menu()` sub-dispatch within `sub_choice == fea_3d_choice` to add
Axial Force (new choice `'2a'` or extend to 11 options total). The simplest approach: add
the two new axial options to `pyvista_menu()` when `beam_type == "Stepped Bar"`, and
update the "back" choice for the PyVista sub-menu similarly.

This is straightforward but requires the same dynamic numbering approach applied to the
outer postprocessing menu. Defer until Bug-11 is fully resolved.

---

### 16.4 Implementation Order

The recommended sequence for a single agent session:

1. Apply all global declarations to `run_extended_menu()` (Bug-12 + Bug-13 — one-line fix each)
2. Fix postprocessing dispatch numbering (Bug-11 — restructure ~15 lines)
3. Fix `len_div` NameError in Overhanging Beam block (Bug-14 — one-line fix)
4. Fix Stepped Bar shear_stress array shape (Bug-15 — one-line fix)
5. Add SERIES entries to `plot_theme.py` (Step 1 above)
6. Add 6 new plotting functions to `main_plotting.py` (Step 2 above)
7. Update `cli.py` imports and postprocessing dispatch calls (Step 3 above, includes Bug-16 + Bug-17 fixes)
8. Add PyVista axial functions to `pyvista_plotting.py` (Step 4 above — can be deferred)
9. Verify save/load round-trip for a Stepped Bar project

---

### 16.5 Known Intentional Architecture Decisions

- **Deflection source**: always from the solver (`indeterminate_solver` or `stepped_solver`);
  `stress_solver.calculate_beam_deflection()` is bypassed.
- **`main_solver.py`**: kept for reference; not called from anywhere in the active CLI.
- **PyVista optional**: app runs without PyVista via `try/except ImportError` guard.
- **MOI solver functions are interactive**: they call `input()` internally by design.
- **`num_points=2001` default**: comment in code suggests reducing to `501` for
  Continuous/Stepped beams to reduce SymPy / mesh evaluation time.
- **Stepped Bar mesh density**: `MIN_LOAD_ELEMS = 100` sub-elements per distributed load
  span. Produces accurate convergence for piecewise-cubic Hermite interpolation but inflates
  mesh size. For a beam with 10 distributed loads this creates ~1000 nodes (3000 DOFs);
  `scipy.linalg.solve` handles this in under a second, but complex multi-load stepped bars
  should use `num_points=501` for the output grid.
