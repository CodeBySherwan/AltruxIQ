# AltruxIQ — Complete AI Agent Briefing

> **Purpose of this document:** Everything an AI agent needs to understand the project
> architecture, mathematical foundations, data flows, known bugs, constraints, and
> conventions to give accurate, actionable assistance on this codebase.

---

## 1. Project Overview

**Name:** AltruxIQ  app
**Type:** CLI-based structural beam analysis tool  
**Language:** Python 3  
**Entry point:** `cli.py` → `run_extended_menu()` → `init()`  
**Paradigm:** Procedural with global state; menu-driven terminal UI

The tool performs static structural analysis of two beam types:
- **Simply Supported Beam** — pin support at A, roller support at B
- **Cantilever Beam** — fixed at x=0 (left), free at right end

It computes: support reactions, shear force diagram (SFD), bending moment diagram (BMD),
beam deflection, shear stress, bending stress, and factor of safety (FOS).
Results are visualised via both **Matplotlib** and **Plotly**.

---
Architecture:
```
project_root/
├── src/
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── main_solver.py      # Core beam mechanics solver
│   │   ├── stress_solver.py    # Stress, deflection, FOS calculations
│   │   └── moi_solver.py       # Moment of Inertia calculations
│   ├── plotting/
│   │   ├── __init__.py
│   │   ├── main_plotting.py    # Plotly & Matplotlib visualization
│   │   ├── beam_plot.py        # Beam schematic visualization
│   │   └── plotting_helper.py  # Helper functions for plots
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── cli.py              # Main CLI application
│   │   ├── Menus.py            # Menu display functions
│   │   ├── inputs.py           # User input handlers
│   │   └── beam_projects.json  # Saved projects (UI directory)
│   └── data/
│       ├── __init__.py
│       ├── materials.json
…
```
## 2. File Inventory and Responsibilities

| File | Role | Critical |
|------|------|----------|
| `cli.py` | Main controller — global state, menu routing, orchestration | Yes |
| `Solver.py` | Beam mechanics engine — reactions, SF, BM | Yes |
| `Stress_solver.py` | Post-processing — deflection, shear stress, bending stress, FOS | Yes |
| `moi_solver.py` | Cross-section geometry — moment of inertia, neutral axis distance `c`, width `b` | Yes |
| `Plotting.py` | All Matplotlib + Plotly visualisation functions | Yes |
| `beam_plot.py` | Beam schematic + reaction diagram (Plotly) | Yes |
| `plotting_helper.py` | Low-level Plotly trace builders | Yes |
| `inputs.py` | Terminal input handlers for beam, supports, loads | Yes |
| `Menus.py` | Menu display functions + colour-coded print helpers | Supporting |
| `Materials_database.py` | JSON material database wrapper class | Supporting |
| `Materials.Json` | 14-entry material property database | Data |

---

## 3. Global State Architecture (`cli.py`)

The application uses **module-level global variables** exclusively — there are no
class instances or dataclasses. Every subsystem reads and writes these globals.

```python
# Geometry
beam_length: float          # Total beam length in metres
beam_type: str              # "Simple" or "Cantilever"

# Support positions and metadata (Simple beam only)
A: float                    # Pin support position (m)
B: float                    # Roller support position (m)
A_restraint: list           # (1,1,0) — constrained DoFs at A
B_restraint: list           # (0,1,0) — constrained DoFs at B
A_type: str                 # "Pin Support"
B_type: str                 # "Roller Support"
support_types: tuple        # ("pin", "roller")

# Cross-section (from moi_solver)
Ix: float                   # Second moment of area about neutral axis (m⁴)
shape: str                  # Profile name string
c: float                    # Distance: neutral axis → extreme fibre (m)
b: float                    # Representative width at neutral axis (m)
y_array: np.ndarray         # 10001 y-coordinates from -c to +c

# Material properties (converted to SI on selection)
selected_material: dict     # Raw dict from Materials.Json
density: float              # kg/m³
yield_strength: float       # Pa (MPa × 1e6)
ultimate_strength: float    # Pa
elastic_modulus: float      # Pa (GPa × 1e9)
poisson_ratio: float
shear_yield_strength: float # = 0.55 × yield_strength (von Mises approximation)

# Loads (raw input lists, each entry is a sub-list)
pointloads: list            # [[pos, Fx, Fy], ...]
distributedloads: list      # [[x_start, x_end, intensity], ...]
momentloads: list           # [[pos, moment], ...]
triangleloads: list         # [[x_start, x_end, intensity_peak, intensity_low], ...]
loads: dict                 # {"pointloads":[], "distributedloads":[], ...}

# Solver outputs
X_Field: np.ndarray         # Discretised beam positions (10001 points)
Total_ShearForce: np.ndarray
Total_BendingMoment: np.ndarray
Reactions: np.ndarray       # [Va, Vb, Ha] for Simple; [Va, Ha, Ma] for Cantilever

# Post-processing outputs (computed later, not always initialised)
Deflection: np.ndarray
Slope: np.ndarray
Shear_stress: np.ndarray    # 2D matrix: (len(X_Field), len(y_array))
bending_stress: np.ndarray
FOS: float

# Project lifecycle flags
project_state: dict         # See Section 4
beam_storage: list          # All saved projects loaded from disk
current_project: dict       # Currently loaded project dict
Materials: MaterialDatabase # Database object
```

---

## 4. Project State Flags (`project_state`)

```python
project_state = {
    "is_loaded": bool,              # True after loading from disk
    "profile_saved": bool,          # True after Ix/shape/c/b defined
    "material_saved": bool,         # True after material selected
    "loads_saved": bool,            # True after manage_loads() returns
    "supports_saved": bool,         # True after supports defined (auto-True for Cantilever)
    "analysis_complete": bool,      # True after Solver runs successfully
    "deflection_calculated": bool,  # True after calculate_beam_deflection() runs
    "stress_calculated": bool,      # True after stress/FOS run
    "has_unsaved_changes": bool,    # True whenever any data changes
}
```

**Gate logic:** Menu options 8 (Analysis) and 9 (Post-processing) check these flags
before allowing execution. Missing flags produce a `print_error()` and a 2-second delay.

---

## 5. Load Data Structures

All loads are stored as Python lists of lists. When passed to `Solver.py`, they are
converted to `np.ndarray`. Empty input uses `np.empty((0, N))`.

```
pointloads:       [[position_m, Fx_N, Fy_N], ...]
distributedloads: [[x_start_m, x_end_m, intensity_N_per_m], ...]
momentloads:      [[position_m, moment_Nm], ...]
triangleloads:    [[x_start_m, x_end_m, intensity_peak_N_per_m, intensity_low_N_per_m], ...]
```

**Sign convention (Solver):**
- Positive Fy → downward force
- Positive moment → counter-clockwise
- Positive shear → clockwise rotation on section
- Positive bending moment → compression in top fibres (sagging)

---

## 6. Solver Module (`Solver.py`) — Mathematical Detail

### 6.1 Discretisation

```python
Delta = beam_length / 10000
X_Field = np.arange(0, beam_length + Delta, Delta)   # ~10001 points
```

### 6.2 Simple Beam — Reaction Calculation (`calculate_all_reactions`)

Takes moments about A to get Vb, then equilibrium for Va.

```
Point load at Xp with vertical force Fy:
    Vb += Fy * (A - Xp) / (B - A)
    Va += -Fy - Vb_contribution

UDL from Xstart to Xend with intensity Fy:
    Resultant Fy_res = Fy * (Xend - Xstart)
    Acts at X_res = Xstart + 0.5*(Xend - Xstart)
    Same moment-about-A formula

Triangular load (one zero end):
    If Fy_start > 0: Fy_res = 0.5*Fy_start*(Xend-Xstart), X_res = Xstart + (1/3)*(Xend-Xstart)
    If Fy_end   > 0: Fy_res = 0.5*Fy_end*(Xend-Xstart),   X_res = Xstart + (2/3)*(Xend-Xstart)

Point moment at Xm:
    Vb += m / (B - A)
    Va += -m / (B - A)

Horizontal equilibrium:
    Ha = sum of all Fx in pointloads
```

Returns tuple `(Va, Vb, Ha)`.

### 6.3 Simple Beam — SF/BM Calculation (`calculate_sf_bm`)

Iterates over every X_Field point using a **section method from the left**.
At each `x`, it sums all contributions from entities to the LEFT of `x`.

Reactions are treated as upward forces applied at x=A and x=B.

Returns `(ShearForce, -BendingMoment)` — note the sign flip on BM.

### 6.4 Cantilever Beam — Reactions (`Calculate_Cantilever_Reactions`)

Fixed support at x=0. Analyses from right (free end) to fixed end.

```
Va = -sum(Fy of all loads)        [vertical equilibrium]
Ha = -sum(Fx of all loads)        [horizontal equilibrium]
Ma = -sum(Fy*Xp for point loads)  [moment equilibrium about x=0]
    -sum(moments)
    -sum(UDL resultant * centroid)
    -sum(triangular load resultant * centroid)
```

Returns `(Va, Ha, Ma)`.

### 6.5 Cantilever Beam — SF/BM Calculation (`Calculate_SF_BM_Cantilever`)

Uses a **right-to-left section method**: at each position `x`, sums all load
contributions from entities to the RIGHT of `x` (free-end approach).

Then sets `BendingMoment[0] = Ma` to enforce the fixed-end boundary condition.

Returns `(ShearForce, BendingMoment)`.

In `solve_cantilever_beam()` (the high-level wrapper), the returned BM is negated:
```python
CorrectedBendingMoment = -BendingMoment
```

---

## 7. Stress Solver Module (`Stress_solver.py`)

### 7.1 Deflection (`calculate_beam_deflection`)

Uses double numerical integration of the Euler-Bernoulli equation:

```
κ(x) = M(x) / (E·I)          [curvature]
θ(x) = ∫κ dx                  [slope, via cumulative_trapezoid]
v(x) = ∫θ dx                  [deflection, via cumulative_trapezoid]
```

**Boundary condition enforcement (simplified):**
```python
correction = deflection[-1] * (x_field / x_field[-1])
deflection  = deflection - correction
```
This linear correction enforces zero deflection at both ends.
**Limitation:** This only works correctly when supports are at x=0 and x=L.
For overhanging spans or off-end supports, the correction is **wrong**.

### 7.2 First Moment of Area (`first_moment_of_area_rect`)

```python
for each y in y_array:
    A_prime = width * (y_array[-1] - y)    # area above point y
    y_prime = (y_array[-1] + y) / 2 - y   # distance NA → centroid of A'
    Q[i] = A_prime * y_prime
```

**Note:** This formula is specific to rectangular sections. Using it for I-beams,
T-beams, or hollow sections will produce inaccurate shear stress results.

### 7.3 Shear Stress (`calculate_shear_stress`)

```
τ(x, y) = V(x) · Q(y) / (I · b)
```

Implemented via broadcasting:
```python
V = shear_force.reshape(-1, 1)   # (n_x, 1)
Q = first_moment_area.reshape(1, -1)  # (1, n_y)
shear_stress = (V @ Q) / (I * b)  # (n_x, n_y)
```

The result is a 2D matrix. All plotting functions collapse this to 1D by taking
`np.max(np.abs(shear_stress), axis=1)` — the maximum over the cross-section height.

### 7.4 Bending Stress (`calculate_bending_stress`)

```
σ(x) = M(x) · c / I
```

Returns a 1D array — stress at the extreme fibre along the beam length.

### 7.5 Factor of Safety (`Factor_of_Safety`)

```
FOS = yield_strength / max(|σ_bending|)
```

FOS < 1 → unsafe. FOS = 1 → limit state. FOS > 1 → safe.

---

## 8. Moment of Inertia Solver (`moi_solver.py`)

All functions return a 5-tuple: `(Ix, shape_name, c, b_or_width, y_array)`.

| Profile | Function | `b` meaning |
|---------|----------|-------------|
| I-beam | `inertia_moment_ibeam()` | Web thickness `tw` |
| T-beam | `inertia_moment_tbeam()` | Web thickness `tw` |
| Solid Circle | `inertia_moment_circle()` | Diameter |
| Hollow Circle | `inertia_moment_hollow_circle()` | Outer diameter |
| Square | `inertia_moment_square()` | Side length `a` |
| Hollow Square | `inertia_moment_hollow_square()` | Outer side |
| Rectangle | `inertia_moment_rectangle()` | Base width `b` |
| Hollow Rectangle | `inertia_moment_hollow_rectangle()` | Outer base |

**y_array** is always `np.linspace(-c, c, 10001)` — used as cross-section height
coordinates for shear stress distribution.

---

## 9. Visualisation Modules

### 9.1 `plotting_helper.py` — Trace Builders

Produces raw `go.Scatter` trace objects. Not standalone figures.

| Function | Output |
|----------|--------|
| `draw_beam(length)` | Purple horizontal beam line |
| `draw_support(x, type)` | Small circle marker (blue=pin, red=roller) |
| `draw_big_support(x, type)` | Large circle marker |
| `draw_point_load(x, magnitude)` | Vertical arrow with label |
| `draw_udl(x_start, x_end, magnitude)` | Filled rectangle + label (returns list of traces) |
| `draw_moment(x, magnitude)` | Arc + arrowhead + label (returns list of traces) |
| `draw_reaction(x, magnitude)` | Vertical reaction arrow |
| `draw_horizontal_reaction(x, magnitude)` | Horizontal reaction arrow |

### 9.2 `beam_plot.py` — Assembled Figures

| Function | Purpose |
|----------|---------|
| `plot_beam_schematic(beam_length, A, B, support_types, loads)` | Full beam diagram with loads |
| `plot_reaction_diagram(A, B, reactions, support_types)` | Reaction forces visualisation |

`loads` parameter here is a **formatted list** produced by `format_loads_for_plotting()`
from `Plotting.py`, NOT the raw `loads` dict.

### 9.3 `Plotting.py` — Full Diagram Functions

**Plotly functions** (interactive HTML):

| Function | Inputs |
|----------|--------|
| `Plotly_shear_force(X, SF, L)` | SFD only |
| `Plotly_bending_moment(X, BM, L)` | BMD only |
| `Plotly_sfd_bmd(X, SF, BM, L)` | SFD + BMD combined subplot |
| `Plotly_Deflection(X, D, L)` | Deflection only |
| `Plotly_ShearStress(X, SS, L)` | Shear stress (auto-collapses 2D) |
| `Plotly_combined_diagrams(X, SF, BM, L, D=None, SS=None)` | Up to 4 subplots |

**Matplotlib functions** (static PNG):

| Function | Inputs |
|----------|--------|
| `Matplot_shear_force(X, SF)` | SFD only |
| `Matplot_bending_moment(X, BM)` | BMD only |
| `Matplot_sfd_bmd(X, SF, BM)` | SFD + BMD combined |
| `Matplot_Deflection(X, D)` | Deflection only |
| `Matplot_ShearStress(X, SS)` | Shear stress |
| `Matplot_combined(X, SF, BM, D=None, SS=None)` | All in one figure |

**Helper:**
```python
format_loads_for_plotting(loads_dict) -> list
```
Converts the `loads` dict into the `[("point_load", pos, mag), ...]` format
expected by `beam_plot.py`.

---

## 10. Material Database (`Materials.Json` + `Materials_database.py`)

14 materials. All values stored as-is in the JSON:
- Density: kg/m³
- Yield Strength: MPa → converted to Pa in `cli.py` (×1e6)
- Ultimate Strength: MPa → converted to Pa (×1e6)
- Elastic Modulus: GPa → converted to Pa (×1e9)
- Poisson Ratio: dimensionless

Available materials:
Structural Steel, Reinforced Concrete, Aluminum Alloy (6061-T6),
Timber (Douglas Fir), Cast Iron, High Strength Low Alloy Steel,
GFRP, CFRP, Stainless Steel (304), Brick Masonry, PVC, Copper,
Granite, Fiber Reinforced Concrete.

`MaterialDatabase` class methods:
- `list_all_materials()` → list of names
- `search_by_property(name, min, max)` → filtered list
- `print_materials(list)` → formatted console output

---

## 11. Project Persistence (`beam_projects.json`)

Projects are saved as a JSON array. Each project dict structure:

```json
{
  "name": "project_name",
  "beam_length": 5.0,
  "support_A_pos": 0.0,
  "support_B_pos": 5.0,
  "support_A_restraint": [1, 1, 0],
  "support_B_restraint": [0, 1, 0],
  "support_A_type": "Pin Support",
  "support_B_type": "Roller Support",
  "X_Field": [...],
  "Total_ShearForce": [...],
  "Total_BendingMoment": [...],
  "Reactions": [...],
  "loads": {
    "pointloads": [],
    "distributedloads": [],
    "momentloads": [],
    "triangleloads": []
  },
  "profile": {
    "Ix": 0.0,
    "shape": "Rectangle",
    "c": 0.0,
    "b": 0.0,
    "y_array": [...]
  },
  "material": {
    "material": { ...material dict... }
  }
}
```

`numpy.ndarray` and `tuple` objects are serialised via `safe_serialize()` before saving.

---

## 12. Known Bugs and Defects


No known Bugs found yet and all the old bugs have been solved .

## 13. Missing Features and Incomplete Implementations

| Feature | Status | Notes |
|---------|--------|-------|
| Fixed-Fixed Beam | Menu placeholder only | Option 3 commented out in `inputs.py` |
| Continuous Beam | Menu placeholder only | Options 4-5 commented out |
| Overhanging Beam | Menu placeholder only | |
| Bending stress visualisation | Computed but no dedicated plot function exists | `Plotting.py` has no `Plotly_BendingStress()` |
| Reaction schematic for Cantilever | `plot_reaction_diagram()` hardcodes pin+roller symbols | Wrong for cantilever (should show fixed wall) |
| Cross-section stress distribution plot | Not implemented | Would show τ(y) at critical section |
| Export to CSV/PDF | Not implemented | Only JSON project save exists |
| Unit system toggle | Not implemented | App is hard-coded to SI throughout |
| Input validation for load positions | Partial | No check that loads are within beam span |
| `Solver.py` return consistency | Mixed | `solve_simple_beam` calls cantilever solver internally but `solve_cantilever_beam` is the preferred external call |

---

## 14. Dependency List

```
numpy          # Array maths, integration backbone
scipy          # cumulative_trapezoid in Stress_solver.py
plotly         # All interactive plots
matplotlib     # All static plots
termcolor      # Coloured terminal output (colored, cprint)
json           # Project persistence
```

No `requirements.txt` is present in the codebase. These must be installed manually.

---

## 15. Execution Flow — Complete Walkthrough

```
init()
  └─ reset project_state dict

run_extended_menu()
  └─ load_material_database()     # loads Materials.Json into global Materials
  └─ load_projects_from_disk()    # loads beam_projects.json into beam_storage
  └─ while True: main_menu_template()

User path for a fresh analysis:

1. Menu '2' → Beam_Classification() → sets beam_type
2. Menu '3' → Beam_Length() → sets beam_length
            → choose_profile() → moi_solver.* → sets Ix, shape, c, b, y_array
3. Menu '4' → select_material() → sets selected_material, E, ν, σ_y, etc.
4. Menu '5' → Beam_Supports() → sets A, B, A_type, B_type, A_restraint, B_restraint
5. Menu '6' → manage_loads() → sets loads dict + individual load lists
6. Menu '8' → sub-choice '1':
              → solve_simple_beam() or solve_cantilever_beam()
              → sets X_Field, Total_ShearForce, Total_BendingMoment, Reactions
7. Menu '8' → sub-choice '3':
              → calculate_beam_deflection() → sets Deflection, Slope, curv
8. Menu '8' → sub-choice '4':
              → first_moment_of_area_rect() → Q_array
              → calculate_shear_stress() → Shear_stress
              → calculate_bending_stress() → bending_stress
              → Factor_of_Safety() → FOS
9. Menu '9' → various plot functions using all computed arrays
10. Menu '10' → save_project() → save_projects_to_disk()
```

---

## 16. Numerical Conventions and Units

| Quantity | Unit | Notes |
|----------|------|-------|
| Length | m | All positions, beam length |
| Force | N | All point loads and reactions |
| Distributed load | N/m | UDL and triangular |
| Moment | N·m | Applied and reaction moments |
| Stress | Pa | Output of stress functions |
| Elastic Modulus | Pa | Stored internally after GPa→Pa conversion |
| Yield Strength | Pa | Stored internally after MPa→Pa conversion |
| Moment of Inertia | m⁴ | All cross-sections |
| Deflection | m | Output of integration |
| Density | kg/m³ | Not used in calculations, stored only |

---

## 17. Key Design Decisions and Implicit Assumptions

1. **Discretisation is fixed at 10,000 divisions.** Changing beam_length changes
   Δx but not point count. The X_Field always has ~10,001 points.

2. **Simply Supported analysis convention:** Support A is the pin (Fx, Fy fixed),
   Support B is the roller (Fy fixed, Fx free). Ha accounts for all horizontal loads.

3. **No self-weight.** Beam self-weight is never computed or added — only user-defined
   loads are considered, even though `density` is stored.

4. **Cantilever fixed end is always x=0.** There is no option to flip orientation.

5. **The `b` value passed to shear stress is the neutral axis width.** For I-beams
   this is `tw` (web thickness), which is correct at the neutral axis but wrong at
   the flange junction.

6. **Plotly figures use `.show()` directly** — they open in a browser tab or inline
   depending on environment. No figure objects are returned.

7. **The `safe_serialize()` function** converts numpy arrays and tuples to lists
   before JSON serialisation. On load, lists are converted back to numpy arrays.

8. **All monetary/project management** features use a flat list stored in memory
   (`beam_storage`) and synced to a single `beam_projects.json` file.

---

## 18. Code Patterns and Conventions

- **Error handling:** `try/except Exception as e` with `print_error(f"...: {e}")` + `time.sleep(2)` + `continue`
- **Input validation:** Recursive retry pattern (e.g., `Beam_Length()` calls itself on bad input)
- **Colours:** `cyan` = user prompts, `yellow` = menu options, `green` = success, `red` = errors, `white` = data output
- **Section breaks:** `cprint("========...", 'red')` used as visual separators
- **No type hints** anywhere in the codebase
- **No unit tests** exist
- **All plotting functions call `.show()` internally** — no figure is returned to caller

---
## 19. How to Assist With This Project — Agent Instructions

When asked to help with this codebase, apply these rules:

**A. Before suggesting any code change:**
- Identify which global variables are affected.
- Check if `project_state` flags need to be updated.
- Verify the data flow: does the change affect what gets serialised to JSON?

**B. When fixing bugs:**
- Always show the original code, the problem, and the fixed code.
- Check for cascading effects — a reaction order fix in Solver.py
  affects display in cli.py and plotting in beam_plot.py.

**C. When adding new features:**
- Follow the existing menu structure pattern in `Menus.py` + `cli.py`.
- Add the new global variable to the module-level declarations AND to `init()`.
- Add the new state flag to `project_state`.
- Add serialisation/deserialisation in `save_project()` and `load_project()`.

**D. When asked about physics/mechanics:**
- Confirm sign conventions before answering (see Section 5 and 16).
- Clarify whether the question is about the mathematical formulation
  or the numerical implementation — they can differ due to the BM sign flip.

**E. When asked about extending beam types:**
- Fixed-fixed beams require solving a statically indeterminate system
  (stiffness method or moment distribution), which the current deterministic
  solver cannot handle without a rewrite.
- Continuous beams require the three-moment equation or stiffness matrix approach.
- Both represent a significant architecture change to `Solver.py`.

**F. When asked about the deflection calculation:**
- The current method (double numerical integration) is approximate.
- The boundary condition correction is only exact for end-supports at x=0 and x=L.
- For high-precision applications, macaulay's method or virtual work is preferred.

**G. When asked to extend the visualisation:**
- All new Plotly diagrams should follow the pattern in `Plotly_shear_force()`:
  fill with transparency, dotted zero-line, max/min annotations, white background.
- All new Matplotlib diagrams should follow `Matplot_shear_force()`:
  `fill_between` for positive/negative regions, `annotate` with arrowprops,
  remove top/right spines.

---

*End of briefing document. Version 1.0 — reflects codebase as provided.*
