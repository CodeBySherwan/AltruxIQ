# AltruxIQ — Agent Briefing & Developer Reference

> **Purpose of this document**: Full technical context for any AI agent assisting with this
> project. Read this before writing, editing, or debugging any code. Every section is
> authoritative — do not guess what is not documented here; ask Sherwan instead.

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

| Field            | Value                                                  |
|------------------|--------------------------------------------------------|
| **Current Name** | AltruxIQ                                               |                        
| **Version**      | 2.00 Alpha                                             |
| **Type**         | Python CLI desktop application — structural beam FEA   |
| **Developer**    | Sherwan , mechanical engineer                          |
| **Language**     | Python 3.x (64-bit)                                    |
| **Interface**    | Terminal / CLI (no GUI framework)                      |
| **Entry Point**  | `python src/ui/cli.py`                                 |

### What the Application Does

AltruxIQ is a structural beam analysis tool modelled on commercial FEA software (ANSYS,
SolidWorks Simulation). Given a beam geometry, cross-section profile, material, support
conditions, and applied loads, it computes:

- Reaction forces at supports
- Shear force diagram (SFD)
- Bending moment diagram (BMD)
- Beam deflection and slope
- Shear stress distribution across the cross-section
- Bending (normal) stress
- Factor of Safety against yielding
- 3D FEA-style contour visualisations

All results are displayable in two unit systems (Metric SI and US Customary/Imperial) and
can be saved to / loaded from a JSON project file.

---

## 2. Quick Start

```bash
# Install dependencies (Python 3.x required)
pip install -r requirements.txt

# Run the application
python src/ui/cli.py
```

The application is **entirely menu-driven**. Navigation is by number key. No arguments are
accepted from the command line.

### Recommended Workflow Order (inside the app)

```
[2] Define Beam Type
[3] Profile Definition
    [1] Enter Beam Length
    [2] Define Profile (cross-section)
[4] Material Selection
    [1] Select Material
[5] Boundary Conditions  (auto-handled for Simple, Cantilever, Fixed-Fixed, Propped)
[6] Loads Definition
    [1] Define Loads
[8] Analysis/Simulation
    [1] Solve Beam
    [3] Calculate Deflection   (now auto-included in step 1 via indeterminate_solver)
    [4] Calculate Stress & FOS
[9] Postprocessing/Visualization
    (pick any plot type)
```

---

## 3. Repository Structure

```
project_root/
│
├── data/
│   ├── __init__.py
│   └── materials.json          # 25 pre-defined engineering materials
│
├── src/
│   ├── database/
│   │   ├── __init__.py
│   │   └── materials_database.py   # MaterialDatabase class
│   │
│   ├── plotting/
│   │   ├── __init__.py
│   │   ├── beam_plot.py            # 2D beam schematic + reaction diagram (Plotly)
│   │   ├── main_plotting.py        # All 2D SFD/BMD/stress/deflection plots (Plotly + Matplotlib)
│   │   ├── plotting_helper.py      # Low-level Plotly shape-drawing helpers
│   │   └── pyvista_plotting.py     # 3D FEA contour viewer (PyVista)
│   │
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── indeterminate_solver.py # PRIMARY SOLVER — stiffness method via indeterminatebeam
│   │   ├── main_solver.py          # LEGACY SOLVER — custom numerical (Simple + Cantilever only)
│   │   ├── moi_solver.py           # Moment of Inertia solver (all 8 cross-section types)
│   │   └── stress_solver.py        # Stress, deflection (double integration), FOS calculations
│   │
│   ├── Temporary/
│   │   └── Improved Solver.py      # Working copy of refactored main_solver — not active
│   │
│   └── ui/
│       ├── __init__.py
│       ├── cli.py                  # MAIN APPLICATION — all menu logic, global state
│       ├── inputs.py               # Raw user input handlers (loads, supports, beam type)
│       └── Menus.py                # All display/print functions + unit system helpers
│
├── beam_projects.json              # Auto-created on first save
├── screenshots/                    # Auto-created by PyVista on first 3D render
├── requirements.txt
└── .gitignore
```

### Path Injection Pattern (universal across all modules)

Every file that imports from a sibling module uses this pattern to avoid import errors:

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
- Project save/load functions (`save_project`, `load_project`, etc.)
- Material selection function (`select_material`)
- The `NumpyEncoder` class for JSON serialisation of NumPy types
- `init()` — resets all state flags on startup

**Critical constraint**: The entire session state is stored as module-level globals. There is
no session object or class. Any function that modifies state must reference globals explicitly
with `global var_name`.

**The solve block** (menu selection `'8'`, sub-choice `'1'`):
- Builds `_supports` list of dicts appropriate for the beam type
- Calls `solve_beam()` from `indeterminate_solver.py`
- Unpacks `X_Field`, `Total_ShearForce`, `Total_BendingMoment`, `Deflection`, `Reactions`,
  `Slopes`, `Curvatures` from the returned dict
- Sets `project_state["analysis_complete"] = True`
- Deflection is now automatically available after solve (no separate calculation step needed)

---

### 4.2 `src/solver/indeterminate_solver.py` — Primary Solver

**This is the active solver.** The legacy `main_solver.py` is **not** called from the CLI.

**Function**: `solve_beam(beam_length, beam_type, supports, pointloads, distributedloads,
momentloads, triangleloads, E, I, num_points=2001) -> dict`

Uses the `indeterminatebeam` Python package (SymPy-based stiffness method) to handle all
beam types including statically indeterminate cases.

**Return value** (dict):
```python
{
    "X_Field":              np.ndarray,   # shape (num_points,)
    "Total_ShearForce":     np.ndarray,   # shape (num_points,)
    "Total_BendingMoment":  np.ndarray,   # shape (num_points,)
    "Deflection":           np.ndarray,   # shape (num_points,)  — metres
    "Reactions":            list[dict],   # see Section 5.2
    "Slopes":               np.ndarray,   # np.gradient(Deflection, X_Field)
    "Curvatures":           np.ndarray,   # BendingMoment / (E * I)
}
```

**Internal helpers**:

| Helper | Purpose |
|--------|---------|
| `_build_supports(beam_type, beam_length, supports)` | Returns list of `indeterminatebeam.Support` objects |
| `_build_loads(pointloads, distributedloads, momentloads, triangleloads)` | Returns list of load objects for the solver |

**Load sign convention for `_build_loads`**:
- Point loads: `PointLoadV(Fy, pos)` — positive Fy = upward (matches user input)
- Horizontal: `PointLoad(Fx, pos, 0)` — positive Fx = rightward
- UDL: `UDLV(w, (start, end))` — positive w = upward
- Moment: `PointTorque(M, pos)` — positive = CCW
- Trapezoidal: `TrapezoidalLoadV(force=(-peak, -low), span=(start, end))` — **negated** because
  the `indeterminatebeam` library's trapezoidal API has the opposite sign convention

**Default properties** (used when no material/section is selected):
- E = 210 GPa (structural steel)
- I = 8.33 × 10⁻⁶ m⁴

---

### 4.3 `src/solver/main_solver.py` — Legacy Solver (NOT active in CLI)

Custom numerical solver supporting only `"Simple"` and `"Cantilever"` beam types. Uses a
direct integration approach with 10,000 divisions.

**Status**: Present in codebase, not called from `cli.py`. The `src/Temporary/Improved Solver.py`
is a refactored version of this. Neither is active. Do not modify unless specifically directed.

Key functions:
- `calculate_all_reactions(A, B, pointloads, momentloads, distributedloads, triangleloads)`
- `calculate_sf_bm(X_Field, A, B, ...)` → `(ShearForce, BendingMoment)`
- `Calculate_Cantilever_Reactions(...)` → `(Va, Ha, Ma)`
- `Calculate_SF_BM_Cantilever(...)` → `(ShearForce, BendingMoment)`
- `solve_simple_beam(...)` → `(X_Field, SF, BM, Reactions)`
- `solve_cantilever_beam(...)` → `(X_Field, SF, BM_corrected, Reactions)`

---

### 4.4 `src/solver/moi_solver.py` — Moment of Inertia Solver

Handles cross-section input and computation. Each function is interactive (prompts the user).

**Return value of all `inertia_moment_*` functions** (6-tuple):
```python
(Ix, shape_name, c, b_rep, y_array, section_dims)
```

| Return | Type | Description |
|--------|------|-------------|
| `Ix` | float | Second moment of area about neutral axis (m⁴) |
| `shape_name` | str | Canonical shape string (e.g. `"I-beam"`, `"Rectangle"`) |
| `c` | float | Distance from neutral axis to extreme fibre (m) |
| `b_rep` | float | Representative width used in stress calculations (m) |
| `y_array` | ndarray | `np.linspace(-c, c, 10001)` |
| `section_dims` | dict | Shape-specific geometry dict (see Section 5.4) |

Returns `None` on invalid input (caller must check before unpacking).

`get_moi_scale(units_dict)` → `(len_div, i_div, len_unit, i_unit)` — provides display
divisors for the MOI output screen. Does not affect internal SI values.

---

### 4.5 `src/solver/stress_solver.py` — Stress and Deflection

**`width_array_for_section(shape, section_dims, y_array)`** → `np.ndarray`
Builds `b(y)` — the actual material width at every height in the cross-section. Handles all
8 cross-section types. This is the BUG-09 fix — prior versions used a constant width.

**`first_moment_of_area_general(b_array, y_array)`** → `np.ndarray`
Computes `Q(y)` by numerical integration using `scipy.integrate.cumulative_trapezoid`.
Integrates from bottom (`-c`) upward; returns `Q_array` with negatives clamped to 0.

**`calculate_shear_stress(shear_force, Q_array, moment_of_inertia, b)`** → 2D ndarray
`shape = (len(X_Field), len(y_array))`. Uses `τ = VQ/(Ib(y))`.
`b` can be either a scalar or 1D array — if array, it is broadcast correctly.

**`calculate_bending_stress(bending_moment, c, moment_of_inertia)`** → `np.ndarray`
`σ = Mc/I`. Returns 1D array along the beam length.

**`Factor_of_Safety(bending_moment, c, yield_strength, moment_of_inertia)`** → float
`FOS = yield_strength / max(|σ_bending|)`.

**`calculate_beam_deflection(x_field, bending_moment, E, I, beam_type, A, B)`**
→ `(deflection, slope, curvature)`
Double integration via cumulative_trapezoid. Applies exact boundary conditions for Simple
and Cantilever beams. **Currently not called from CLI** — deflection is provided directly
by `indeterminate_solver.py`.

---

### 4.6 `src/database/materials_database.py` — Material Database

**Class**: `MaterialDatabase(filename="materials.Json")`

Resolves `filename` relative to `project_root/data/`. Uses `Path(__file__).resolve()` to
find the project root reliably (navigates up 3 levels from the class file).

Methods:
- `list_all_materials()` → list of material name strings
- `search_by_property(property_name, min_value, max_value)` → filtered list of dicts
- `print_materials(materials_list)` → formatted console output

The `materials` attribute is the raw list of dicts loaded from JSON.

---

### 4.7 `src/ui/Menus.py` — Display Engine and Unit System

Contains all `display_*` and `*_menu()` functions. No business logic — purely I/O.

**Unit constants**:
```python
METRIC_UNITS = {
    'length': 'm', 'length_small': 'mm', 'force': 'N', 'moment': 'N·m',
    'inertia': 'm⁴', 'sec_mod': 'm³', 'modulus': 'GPa',
    'density': 'kg/m³', 'stress': 'MPa'
}

IMPERIAL_UNITS = {
    'length': 'ft', 'length_small': 'in', 'force': 'lbf', 'moment': 'lbf·ft',
    'inertia': 'in⁴', 'sec_mod': 'in³', 'modulus': 'ksi',
    'density': 'lb/ft³', 'stress': 'ksi'
}
```

**`get_divisor(units_dict, quantity)`** → float
The central unit conversion function. Returns the divisor to convert from base SI to the
active display unit. All values stored internally in SI; divide by this before display.

| `quantity` key | Metric divisor | Imperial divisor |
|----------------|----------------|------------------|
| `'length'`     | 1.0            | 0.3048 (m → ft)  |
| `'length_small'` | 0.001 (m → mm) | 0.0254 (m → in) |
| `'force'`      | 1.0            | 4.4482216 (N → lbf) |
| `'moment'`     | 1.0            | 1.3558179 (N·m → lbf·ft) |
| `'stress'`     | 1e6 (Pa → MPa) | 6894757.29 (Pa → ksi) |
| `'modulus'`    | 1e9 (Pa → GPa) | 6894757.29 (Pa → ksi) |
| `'density'`    | 1.0            | 16.01846 (kg/m³ → lb/ft³) |
| `'inertia'`    | 1.0            | (0.0254)⁴ |
| `'sec_mod'`    | 1.0            | (0.0254)³ |

---

### 4.8 `src/ui/inputs.py` — Input Handlers

**`Beam_Classification()`** → str  
Interactive prompt. Returns one of: `"Simple"`, `"Overhanging Beam"`, `"Cantilever"`,
`"Fixed-Fixed"`, `"Propped"`, `"Continuous"`.

**`Beam_Length(unit_system, units)`** → float (SI metres)  
Input is multiplied by `CONVERSION_TO_SI[unit_system]["length"]` before return.

**`Beam_Supports(unit_system, units)`** → `(A, B, A_restraint, B_restraint, A_type, B_type)`  
All positions returned in SI metres.

**`define_continuous_supports(beam_length, unit_system, units)`** → list of dicts  
Each dict: `{"pos": float, "dof": tuple, "ky": None, "kx": None}`
First support gets `dof=(1,1,0)` (pin); all others `dof=(0,1,0)` (roller).

**`manage_loads(unit_system, units)`** → dict  
Interactive loop for adding all load types. Returns the full loads dict (see Section 5.3).
All values returned in SI (N, m, N·m, N/m).

`CONVERSION_TO_SI` multipliers (Imperial → SI):
- length: 0.3048
- force: 4.4482216
- moment: 1.3558179
- distributed: 14.5939 (lbf/ft → N/m)

---

### 4.9 `src/plotting/beam_plot.py` — Schematic Plots

**`plot_beam_schematic(beam_type, beam_length, A, B, continuous_supports, loads, units)`**  
Draws the structural schematic with supports and applied loads in Plotly. Handles all beam
types. `loads` must be in the format produced by `format_loads_for_plotting()` (see 4.10).

**`plot_reaction_diagram(reactions, units)`**  
Draws reaction force arrows. `reactions` must be the list-of-dicts format.

---

### 4.10 `src/plotting/main_plotting.py` — 2D Result Plots

Provides Plotly and Matplotlib versions of all result diagrams.

**Helper**: `format_loads_for_plotting(loads_dict)` → list of tuples  
Converts the `loads` dict into `[("point_load", pos, mag), ("udl", start, end, intensity), ...]`.
Scaling is NOT applied here — that happens in `beam_plot.py`.

**Plotly functions** (open interactive browser window):
- `Plotly_sfd_bmd(X_Field, SF, BM, beam_length, plot_type='Both', units)` — `plot_type`: `'SFD'`, `'BMD'`, `'Both'`
- `Plotly_shear_force(X_Field, SF, beam_length, units)`
- `Plotly_bending_moment(X_Field, BM, beam_length, units)`
- `Plotly_Deflection(X_Field, Deflection, beam_length, units)`
- `Plotly_ShearStress(X_Field, ShearStress, beam_length, units)`
- `Plotly_BendingStress(X_Field, BendingStress, beam_length, units)`
- `Plotly_combined_diagrams(X_Field, SF, BM, beam_length, Deflection=None, ShearStress=None, units)`

**Matplotlib functions** (opens static window):
- `Matplot_sfd_bmd(X_Field, SF, BM, plot_type='Both', units)`
- `Matplot_Deflection(X_Field, Deflection, units)`
- `Matplot_ShearStress(X_Field, Shear_stress, units)`
- `Matplot_BendingStress(X_Field, BendingStress, units)`
- `Matplot_combined(X_Field, SF, BM, Deflection=None, ShearStress=None, units)`

**Internal scale helper**: `_get_scale(units)` → `(units, l_div, ls_div, f_div, m_div, s_div)`

---

### 4.11 `src/plotting/pyvista_plotting.py` — 3D FEA Viewer

Commercial-grade 3D contour visualiser built on PyVista + VTK.

**Key public functions** (all accept same core arguments):
```
PyVista_shear_force(X_Field, Total_ShearForce, beam_length, shape, section_dims, c, b, units)
PyVista_bending_moment(...)
PyVista_shear_stress(X_Field, ShearStress, beam_length, shape, section_dims, c, b, units)
PyVista_bending_stress(X_Field, BendingStress, ...)
PyVista_deflection(X_Field, Deflection, ...)
PyVista_reactions_schematic(beam_length, Reactions, shape, section_dims, c, b, units)
PyVista_combined(X_Field, SF, BM, beam_length, shape, section_dims, c, b,
                 Deflection=None, ShearStress=None, BendingStress=None, Reactions=None, units)
```

**`ProbingPlotter` class** — interactive point-probing overlay:
- Mouse hover: shows scalar value at cursor
- Left click: pins a permanent measurement label
- Key `r`: reset camera, Key `x`: clear pinned labels
- Auto-saves screenshot to `screenshots/` on close

**Mesh building**: `_build_beam_mesh(X_Field, scalar_field, shape, section_dims, c, b, scalar_name)`  
Extrudes the 2D cross-section polygon along X to build a watertight PolyData mesh with
per-point scalar data for the colour map.

**Visual scaling**: `_apply_visual_scaling(plotter, beam_length, section_dim_max)`  
Auto-scales Y and Z when aspect ratio > 10:1 to prevent the beam from appearing as a
flat line.

**Colour maps by result kind**:
- `"stress"` → `"turbo"`
- `"force"`, `"moment"` → `"coolwarm"`
- `"displacement"` → `"viridis"`
- `"safety"` → `"RdYlGn"`

---

## 5. Core Data Structures

### 5.1 Global State Variables in `cli.py`

These are module-level globals. They persist for the duration of the session.

```python
# Session tracking
current_unit_system: str       # "Metric" or "Imperial"
current_labels: dict           # METRIC_LABELS or IMPERIAL_LABELS (active unit dict)
beam_type: str | None          # "Simple", "Cantilever", "Fixed-Fixed", "Propped",
                               # "Continuous", "Overhanging Beam", or None

# Geometry
beam_length: float             # metres (SI)
A: float                       # Pin support position (metres)
B: float                       # Roller support position (metres)
A_restraint: tuple             # DOF tuple, e.g. (1,1,0)
B_restraint: tuple             # DOF tuple, e.g. (0,1,0)
A_type: str                    # "Pin Support"
B_type: str                    # "Roller Support"
supports_list: list            # For Continuous beams: list of support dicts
support_types: tuple           # ("pin","roller") — used by schematic plotter

# Cross-section
Ix: float                      # Moment of inertia (m⁴)
shape: str                     # Canonical shape name
c: float                       # Distance NA to extreme fibre (m)
b: float                       # Representative width (m)
y_array: np.ndarray            # linspace(-c, c, 10001)
section_dims: dict             # Shape geometry (see Section 5.4)

# Material (all in base SI)
selected_material: dict        # Full material dict from JSON
density: float                 # kg/m³
yield_strength: float          # Pa
ultimate_strength: float       # Pa
elastic_modulus: float         # Pa
poisson_ratio: float           # dimensionless
shear_yield_strength: float    # 0.55 * yield_strength (Pa)

# Loads
loads: dict                    # See Section 5.3
pointloads: list
distributedloads: list
momentloads: list
triangleloads: list

# Analysis results (all in base SI)
X_Field: np.ndarray            # Position along beam (m)
Total_ShearForce: np.ndarray   # N
Total_BendingMoment: np.ndarray # N·m
Deflection: np.ndarray         # m (downward is negative)
Slopes: np.ndarray             # rad
Curvatures: np.ndarray         # 1/m
Reactions: list[dict]          # See Section 5.2

# Stress results
Shear_stress: np.ndarray       # 2D (len_X × len_y) Pa — None until calculated
bending_stress: np.ndarray     # 1D (len_X,) Pa — None until calculated
FOS: float | None              # Factor of Safety

# Project
current_project: dict | None
beam_storage: list
project_state: dict            # See Section 5.5
```

---

### 5.2 Reactions Format (Current — List of Dicts)

```python
Reactions = [
    {
        "pos": float,   # Support position along beam (m)
        "Fx":  float,   # Horizontal reaction (N), positive = rightward
        "Fy":  float,   # Vertical reaction (N), positive = upward
        "M":   float,   # Moment reaction (N·m), positive = CCW
    },
    ...
]
```

**Backward compatibility**: The old format was a NumPy array `[Va, Vb, Ha]` (Simple) or
`[Va, Ha, Ma]` (Cantilever). When loading old projects, `load_project()` converts these to
the new dict format.

---

### 5.3 Loads Format

All values stored in base SI (N, m, N·m, N/m). Conversion from user units happens in
`inputs.py` before storage.

```python
loads = {
    "pointloads":       [[pos, Fx, Fy], ...],        # Fx,Fy in N; pos in m
    "distributedloads": [[start, end, w], ...],       # w in N/m (upward positive)
    "momentloads":      [[pos, M], ...],              # M in N·m (CCW positive)
    "triangleloads":    [[start, end, w_start, w_end], ...]  # intensities in N/m
}
```

---

### 5.4 Section Dims Format (by shape)

These dicts are passed to `stress_solver.width_array_for_section()` and all PyVista functions.
All dimensions in metres (SI).

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
    "is_loaded":            bool,  # A project was loaded from disk
    "profile_saved":        bool,  # Ix, shape, c, b, y_array, section_dims are set
    "material_saved":       bool,  # selected_material and properties are set
    "loads_saved":          bool,  # loads dict has been defined
    "supports_saved":       bool,  # Support positions are set
    "analysis_complete":    bool,  # solve_beam() has been run
    "deflection_calculated":bool,  # Deflection array is available
    "stress_calculated":    bool,  # Shear_stress and bending_stress are computed
    "has_unsaved_changes":  bool,  # Triggers save prompt on exit
}
```

**Gate logic**: Menu options `[3]` through `[9]` check `beam_type is not None` before
proceeding. Option `[8]` additionally requires all four flags
(`profile_saved`, `material_saved`, `loads_saved`, `supports_saved`).

---

### 5.6 Project Save Format (`beam_projects.json`)

```json
{
  "name": "string",
  "unit_system": "Metric",
  "beam_type": "Simple",
  "beam_length": 5.0,
  "support_A_pos": 0.0,
  "support_B_pos": 5.0,
  "support_A_restraint": [1, 1, 0],
  "support_B_restraint": [0, 1, 0],
  "support_A_type": "Pin Support",
  "support_B_type": "Roller Support",
  "support_types": ["pin", "roller"],
  "X_Field": [0.0, ...],
  "Total_ShearForce": [0.0, ...],
  "Total_BendingMoment": [0.0, ...],
  "Reactions": [{"pos": 0.0, "Fx": 0.0, "Fy": 5000.0, "M": 0.0}],
  "loads": {
    "pointloads": [[2.5, 0, -10000]],
    "distributedloads": [],
    "momentloads": [],
    "triangleloads": []
  },
  "profile": {
    "Ix": 8.33e-6,
    "shape": "Rectangle",
    "c": 0.1,
    "b": 0.05,
    "y_array": [-0.1, ...],
    "section_dims": {"type": "Rectangle", "width": 0.05, "height": 0.2}
  },
  "material": {
    "material": {
      "Material": "Structural Steel (S275)",
      "Density": 7850,
      "Yield Strength": 275,
      "Elastic Modulus": 210,
      "Poisson Ratio": 0.3,
      ...
    }
  }
}
```

`NumpyEncoder` in `cli.py` handles serialisation of NumPy arrays and scalars to JSON-compatible
Python types.

---

## 6. Beam Types Supported

| Beam Type | Code String | Support Config | Statically |
|-----------|-------------|----------------|------------|
| Simple Supported | `"Simple"` | Pin at A, Roller at B | Determinate |
| Overhanging | `"Overhanging Beam"` | Pin at A, Roller at B (A,B not at ends) | Determinate |
| Cantilever | `"Cantilever"` | Fixed at x=0 | Determinate |
| Fixed-Fixed | `"Fixed-Fixed"` | Fixed at x=0 and x=L | Indeterminate (1× redundant) |
| Propped Cantilever | `"Propped"` | Fixed at x=0, Roller at x=L | Indeterminate (1× redundant) |
| Continuous (n-span) | `"Continuous"` | User-defined positions, Pin+Rollers | Indeterminate |

**DOF tuple convention** (from `indeterminatebeam`): `(x_constraint, y_constraint, moment_constraint)`
- `(1, 1, 0)` = Pin (constrains x and y, free rotation)
- `(0, 1, 0)` = Roller (constrains y only)
- `(1, 1, 1)` = Fixed (constrains all DOF)

**Supports auto-construction in `_build_supports()`**:
- Simple/Overhanging: uses `supports[0]["pos"]` and `supports[1]["pos"]`
- Cantilever: always `Support(0.0, (1,1,1))`
- Fixed-Fixed: `Support(0.0, ...)` and `Support(beam_length, ...)`
- Propped: `Support(0.0, (1,1,1))` and `Support(beam_length, (0,1,0))`
- Continuous: reads each entry in `supports_list`

---

## 7. Cross-Section Types

8 cross-section types, all handled by `moi_solver.py` and `stress_solver.width_array_for_section()`.

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

**T-beam special case**: The neutral axis is not at mid-height. `y_bar` (centroid from bottom)
and `c_top`, `c_bot` are stored in `section_dims`. The governing `c` is `max(c_top, c_bot)`.

**PyVista polygon builders** (in `pyvista_plotting.py`):
- `_rect_polygon(h, w)` — rectangular cross-section
- `_circle_polygon(r, n=24)` — circular approximation
- `_ibeam_polygon(H, bf, tf, tw)` — I-section
- `_tbeam_polygon(H, bf, tf, tw)` — T-section

---

## 8. Load Types and Sign Conventions

### User Input Convention (as shown in menus)

| Direction | Sign |
|-----------|------|
| Force upward ↑ | Positive |
| Force downward ↓ | Negative |
| Force rightward → | Positive |
| Moment CCW ↺ | Positive |
| Moment CW ↻ | Negative |

### Internal Storage Convention

Same as user input. Values are converted from display units to SI on input and stored as-is
in the `loads` dict. No additional sign flip inside `cli.py`.

### Indeterminate Solver Convention

The `indeterminatebeam` library uses upward = positive for vertical loads, matching the
user input convention for `PointLoadV` and `UDLV`.

**Exception**: `TrapezoidalLoadV` is negated inside `_build_loads()`:
```python
TrapezoidalLoadV(force=(-peak, -low), span=(start, end))
```
This is a confirmed quirk of the `indeterminatebeam` API for trapezoidal loads specifically.

---

## 9. Unit System Architecture

### Core Rule

**All values are stored and computed in base SI** (N, m, Pa, kg/m³). Unit conversion
happens only at the display boundary — divide by `get_divisor()` before printing, multiply
by the inverse before storing user input.

### Flow: Input → Storage

```
User types value in display units
    ↓  × CONVERSION_TO_SI multiplier (in inputs.py)
Stored as base SI in loads/geometry globals
```

### Flow: Storage → Display

```
Value in base SI globals
    ↓  ÷ get_divisor(current_labels, quantity) (in Menus.py)
Displayed in active unit system
```

### Materials Database Units (raw JSON values)

The JSON file stores properties in **non-SI mixed units** that must be converted before use:
- `"Density"`: already kg/m³ — use as-is
- `"Yield Strength"`: MPa → multiply × 1e6 to get Pa
- `"Ultimate Strength"`: MPa → multiply × 1e6 to get Pa
- `"Elastic Modulus"`: GPa → multiply × 1e9 to get Pa
- `"Poisson Ratio"`: dimensionless — use as-is
- `"Thermal Expansion"`: already 1/°C — use as-is

This conversion happens explicitly in the `select_material` function and in `load_project`.

### Active Unit Dict (`current_labels`)

Either `METRIC_LABELS` or `IMPERIAL_LABELS` (defined in `cli.py`, mirroring `Menus.py`).
Passed as `units=current_labels` to all display and plotting functions.

---

## 10. Analysis Pipeline (End-to-End)

```
[User selects beam type, length, profile, material, supports, loads]
         ↓
cli.py: builds _supports list of dicts from beam_type
         ↓
indeterminate_solver.solve_beam(
    beam_length, beam_type, supports, pointloads, distributedloads,
    momentloads, triangleloads, E=elastic_modulus, I=Ix
)
         ↓
_build_supports() → indeterminatebeam.Support objects
_build_loads()    → indeterminatebeam load objects
beam.analyse()    → SymPy stiffness solution
X_Field = np.linspace(0, beam_length, 2001)
beam.get_shear_force(x)  → Total_ShearForce
beam.get_bending_moment(x) → Total_BendingMoment
beam.get_deflection(x)   → Deflection
beam.get_reaction(pos)   → Reactions (list of dicts)
         ↓
cli.py: stores results in globals; sets analysis_complete=True
         ↓
[Optional] Stress calculation:
    b_array = width_array_for_section(shape, section_dims, y_array)
    Q_array = first_moment_of_area_general(b_array, y_array)
    Shear_stress = calculate_shear_stress(Total_ShearForce, Q_array, Ix, b_array)
    bending_stress = calculate_bending_stress(Total_BendingMoment, c, Ix)
    FOS = Factor_of_Safety(Total_BendingMoment, c, yield_strength, Ix)
         ↓
[Optional] Plotting:
    Plotly / Matplotlib 2D plots (main_plotting.py)
    PyVista 3D FEA contour viewer (pyvista_plotting.py)
```

---

## 11. Plotting Architecture

### 2D Plots

```
main_plotting.py
├── _get_scale(units)              — extracts divisors for all quantities
├── find_critical_points(X, Y)     — finds peak and zero-crossings for annotation
├── Plotly_* functions             — interactive browser plots (go.Figure.show())
└── Matplot_* functions            — static matplotlib windows (plt.show())
```

### Beam Schematic

```
beam_plot.py
├── plot_beam_schematic()          — draws beam + supports + loads
│   └── uses plotting_helper.py   — draw_beam, draw_support, draw_point_load, etc.
└── plot_reaction_diagram()        — draws reaction force arrows
```

### 3D FEA Viewer

```
pyvista_plotting.py
├── _build_beam_mesh()             — extrudes cross-section into 3D solid
├── _apply_visual_scaling()        — YZ scale correction for slender beams
├── _build_fea_plotter()           — creates ProbingPlotter instance
├── ProbingPlotter                 — full interactive viewer class
│   ├── build()                    — assembles all overlays
│   ├── _add_mesh()                — renders coloured scalar mesh
│   ├── _add_extreme_markers()     — MAX/MIN vtkCaptionActor2D labels
│   ├── _add_probe_system()        — hover probing via vtkCellPicker
│   ├── _pin_point()               — left-click permanent labels
│   └── _add_step_slider()         — optional multi-step load slider
└── PyVista_* public functions     — one per result type
```

---

## 12. Materials Database

Located at: `data/materials.json`

25 materials pre-defined. Schema per entry:

```json
{
  "Material": "string",
  "Density": float,           // kg/m³
  "Yield Strength": float,    // MPa
  "Ultimate Strength": float, // MPa
  "Elastic Modulus": float,   // GPa
  "Poisson Ratio": float,
  "Thermal Expansion": float, // 1/°C (scientific notation in JSON)
  "Description": "string"
}
```

### Material List

| # | Material |
|---|---------|
| 1 | Structural Steel (S235) |
| 2 | Structural Steel (S275) |
| 3 | Structural Steel (S355) |
| 4 | Reinforced Concrete |
| 5 | Aluminum Alloy (6061-T6) |
| 6 | Aluminum Alloy (7075-T6) |
| 7 | Timber (Douglas Fir) |
| 8 | Timber (Oak) |
| 9 | Cast Iron (Gray) |
| 10 | Ductile Iron |
| 11 | High Strength Low Alloy Steel |
| 12 | Stainless Steel (304) |
| 13 | Stainless Steel (316) |
| 14 | Glass Fiber Reinforced Polymer (GFRP) |
| 15 | Carbon Fiber Reinforced Polymer (CFRP) |
| 16 | Titanium Alloy (Ti-6Al-4V) |
| 17 | Brick Masonry |
| 18 | Polyvinyl Chloride (PVC) |
| 19 | Copper (C11000) |
| 20 | Granite |
| 21 | Fiber Reinforced Concrete |
| 22 | Magnesium Alloy (AZ31B) |
| 23 | Tool Steel (A2) |
| 24 | Brass (C26000) |
| 25 | High-Performance Concrete (HPC) |

---

## 13. Dependencies

Listed in `requirements.txt`. Key packages and their roles:

| Package | Role |
|---------|------|
| `indeterminatebeam` | Core structural solver (stiffness method, SymPy-based) |
| `numpy` | All numerical arrays and operations |
| `sympy` | Underlying algebra engine for indeterminatebeam |
| `scipy` | `cumulative_trapezoid` for stress/deflection integration |
| `pyvista` | 3D interactive FEA viewer |
| `vtk` | Required by PyVista (vtkCellPicker, vtkCaptionActor2D, etc.) |
| `plotly` | 2D interactive plots in browser |
| `matplotlib` | 2D static plots |
| `termcolor` | Coloured CLI output |
| `pandas` | Listed in requirements; not heavily used in active code |
| `dash` + ecosystem | Listed in requirements; not currently used in active code |

PyVista is optional — the CLI gracefully handles its absence via:
```python
try:
    from plotting.pyvista_plotting import ...
    _PYVISTA_AVAILABLE = True
except ImportError:
    _PYVISTA_AVAILABLE = False
```

---

## 14. Known Bugs and Applied Fixes

| Bug ID | Description | Status | Fix Location |
|--------|-------------|--------|--------------|
| BUG-05 | `NameError: beam_type not defined` when accessing menu items out of order | Fixed | `cli.py` module-level `beam_type = None` initialisation |
| BUG-07 | `NameError` on post-processing for Deflection, ShearStress etc. if stress not calculated | Fixed | `cli.py` module-level `Deflection = None`, `Shear_stress = None`, etc. |
| BUG-09 | Shear stress incorrect for non-rectangular sections — constant `b` used | Fixed | `stress_solver.width_array_for_section()` replaces constant b with b(y) array |
| BUG-10 | `support_types` not persisted to JSON; loaded projects lost schematic support markers | Fixed | `save_project()` and `load_project()` now include `"support_types"` field |
| — | Cantilever `BendingMoment` sign inversion applied twice (double-negation bug) | Fixed | `main_solver.py` comment: "removes the - inversion bug"; `solve_cantilever_beam` still applies `CorrectedBendingMoment = -BendingMoment` but this path is not used by CLI |
| — | Trapezoidal load centroid formula was incorrect for non-uniform cases | Fixed | `main_solver.py` and `Improved Solver.py` both use `X_res = Xstart + L * (w1 + 2*w2) / (3*(w1+w2))` |
| — | `TrapezoidalLoadV` in indeterminate_solver has opposite sign convention | Fixed/Documented | `_build_loads()` applies negation: `TrapezoidalLoadV(force=(-peak, -low), ...)` |

### Current Rough Edges (not yet bugs, but worth knowing)

- `display_deflection_analysis()` in Menus.py receives `Deflection` in metres but the
  display logic has a branching unit conversion that may not always select the right
  divisor for all unit/magnitude combinations.
- `Plotly_combined_diagrams` hardcodes `step=5` downsampling; for very short beams with
  `num_points=2001` this could cause visible resolution loss.
- `solve_beam()` with `num_points=2001` can be slow for Continuous beams with many supports
  because `indeterminatebeam` evaluates SymPy expressions point-by-point.
- `display_analysis_results()` equilibrium check only sums `Va + Vb` for Simple beam; does
  not work correctly for Continuous or Fixed-Fixed beams where Va/Vb extraction logic uses
  hardcoded `A` and `B`.

---

## 15. Development Conventions

### File Naming
- Snake_case for module files (e.g. `main_plotting.py`, `moi_solver.py`)
- Mixed case for class and function names (CamelCase for classes, snake_case for functions)

### Adding a New Cross-Section
1. Add a function `inertia_moment_<name>(units=None)` in `moi_solver.py` returning the
   6-tuple `(Ix, "Name", c, b_rep, y_array, section_dims)`
2. Add a branch in `choose_profile()` in `Menus.py`
3. Add the corresponding `profile_choice == 'n'` branch in `cli.py` (menu option `'3'`→`'2'`)
4. Add `elif shape == "Name":` handling in `stress_solver.width_array_for_section()`
5. Add `elif shape == "Name":` handling in `pyvista_plotting._build_cross_section_polygon()`

### Adding a New Beam Type
1. Add to `Beam_Classification()` in `inputs.py`
2. Add `_build_supports()` branch in `indeterminate_solver.py`
3. Add `_supports` construction block in `cli.py` solve section
4. Add `support_positions` block in `indeterminate_solver.py` for Reactions extraction
5. Add appropriate support drawing in `beam_plot.plot_beam_schematic()`

### Output Formatting
- All `print` inside `Menus.py` and `moi_solver.py` use `termcolor.colored()` / `cprint()`
- Box-drawing characters use Unicode: `╔ ╗ ╚ ╝ ║ ═ ┌ ┐ └ ┘ │ ─ ┬ ┴`
- All user-facing numbers in display units (not SI) with appropriate `:.3f` or `:.2e` format

### JSON Serialisation
- Always use `NumpyEncoder` when calling `json.dump()` for project files
- `safe_serialize()` converts ndarray → list, tuple → list for project dict values

### Import Order Convention
```python
# 1. Standard library
import os, sys, json, time
import numpy as np

# 2. Path injection block (if needed)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir     = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 3. Third-party
from termcolor import colored, cprint

# 4. Internal modules
from solver.indeterminate_solver import solve_beam
```

### Error Handling Pattern
- User input errors: `print_error(msg)` then `time.sleep(2)` then `continue` in the while loop
- Solver errors: wrapped in `try/except Exception as e`, `print_error(f"...: {e}")`, `continue`
- Missing data: check `project_state` flags before executing; show friendly message

---

## 16. Active Development Notes

### What is Complete and Working
- Full analysis pipeline for all 6 beam types
- All 8 cross-section MOI computations
- Shear and bending stress (section-aware)
- Factor of Safety
- Deflection (via indeterminate solver)
- All 2D plots (Plotly + Matplotlib)
- 3D FEA viewer with interactive probing, MIN/MAX labels, pinned measurements
- Save/Load project to JSON with backward compatibility
- Dual unit system (Metric/Imperial) throughout
- Imperial/Metric input conversion in loads and geometry

### What is Partially Done / Needs Attention
- `src/Temporary/Improved Solver.py` — a refactored legacy solver. It is not integrated.
  No action needed unless migrating back to a custom solver is planned.
- `dash` and related packages in `requirements.txt` are legacy leftovers from an earlier
  web-based version. They are not used. Safe to remove from requirements if desired.
- `display_deflection_analysis()` unit display logic for very small deflections may need
  review — the branching between `length` and `length_small` display units has edge cases.
- Reactions extraction in `display_analysis_results()` and sub-choice `'2'` uses
  `next((r["Fy"] for r in Reactions if r["pos"] == A), 0.0)` — this is an exact float
  comparison which may fail if `A` differs from `r["pos"]` by floating-point epsilon.
  Safer to use `min(Reactions, key=lambda r: abs(r["pos"] - A))`.
- PyVista `_add_extreme_markers()` uses fixed pixel offsets `(80, 80)` and `(-100, 80)`.
  These may overlap on non-standard window sizes.

### Known Intentional Architecture Decisions
- `Deflection` comes from `indeterminate_solver.py` (via `beam.get_deflection()`), NOT from
  `stress_solver.calculate_beam_deflection()`. The latter exists and works but is bypassed.
- `main_solver.py` is kept for reference; it is NOT called from anywhere in the active CLI.
- `pyvista_plotting.py` catches `ImportError` at the top to allow the app to run on systems
  without PyVista (e.g. minimal cloud environments).
- The MOI solver functions are intentionally interactive (they call `input()` internally).
  This is by design — they are not intended to be called programmatically.
- `num_points=2001` is the default resolution for the solver. The comment in the code suggests
  reducing to `501` if the solver is slow — this is relevant for Continuous beams with SymPy.

---