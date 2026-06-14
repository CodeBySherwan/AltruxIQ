# AltruxIQ — Complete AI Agent Briefing v2.0

> **Purpose:** Everything an AI agent needs to understand the current architecture,
> mathematics, data flows, state of known bugs, resolved fixes, and conventions
> to give accurate, actionable assistance on this codebase.
> **Based on:** Full source audit of all 19 provided files.
> **Date of audit:** June 2026.

---

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Name** | AltruxIQ |
| **Type** | CLI-based structural beam analysis tool |
| **Language** | Python 3 (no type hints anywhere) |
| **Paradigm** | Procedural with module-level global state; menu-driven terminal UI |
| **Entry point** | `src/ui/cli.py` → `init()` then `run_extended_menu()` |

---

## 2. Directory Layout (Actual, as audited)

```
project_root/
├── data/
│   └── materials.json              ← 25-material property database (root-level)
├── src/
│   ├── database/
│   │   ├── __init__.py
│   │   └── materials_database.py   ← MaterialDatabase class
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── main_solver.py          ← Beam mechanics engine (improved)
│   │   ├── stress_solver.py        ← Post-processing: deflection, stress, FOS
│   │   └── moi_solver.py           ← Cross-section geometry & MOI
│   ├── plotting/
│   │   ├── __init__.py
│   │   ├── main_plotting.py        ← All Matplotlib + Plotly diagrams
│   │   ├── beam_plot.py            ← Beam schematics & reaction diagrams
│   │   └── plotting_helper.py      ← Low-level Plotly trace builders
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── cli.py                  ← Main controller & global state
│   │   ├── Menus.py                ← Menu display + colour-print helpers
│   │   ├── inputs.py               ← User input handlers
│   │   └── beam_projects.json      ← Saved projects (runtime location varies)
│   ├── data/
│   │   └── __init__.py
│   └── Temporary/
│       └── Improved Solver.py      ← Staging copy; identical to main_solver.py
```

**Path resolution note:** `MaterialDatabase.__init__` navigates 3 `.parent` levels from its
own file path to reach the project root, then appends `data/materials.json`. This means the
database file must always be at `<project_root>/data/materials.json`.

**`beam_projects.json` path:** `save_projects_to_disk()` opens `'beam_projects.json'`
with a bare filename (no path prefix), so it reads/writes relative to the **current working
directory** when the interpreter runs — not relative to any source directory. This can cause
confusion if the script is launched from a different directory.

---

## 3. File Inventory and Responsibilities

| File | Role | Critical |
|------|------|----------|
| `cli.py` | Main controller — global state, menu routing, orchestration | **Yes** |
| `main_solver.py` | Beam mechanics engine — reactions, SFD, BMD | **Yes** |
| `stress_solver.py` | Post-processing — deflection, shear stress, bending stress, FOS | **Yes** |
| `moi_solver.py` | Cross-section geometry — Ix, c, b, y_array, **section_dims** | **Yes** |
| `main_plotting.py` | All Matplotlib + Plotly visualisation functions | **Yes** |
| `beam_plot.py` | Beam schematics, reaction diagrams, cantilever schematic | **Yes** |
| `plotting_helper.py` | Low-level Plotly trace builders | **Yes** |
| `inputs.py` | Terminal input handlers: beam type, length, supports, loads | **Yes** |
| `Menus.py` | Menu templates + colour-coded print helpers | Supporting |
| `materials_database.py` | JSON material database wrapper class | Supporting |
| `materials.json` | 25-entry material property database | Data |
| `beam_projects.json` | Saved projects array (runtime) | Data |

---

## 4. Global State Architecture (`cli.py`)

All state is held in **module-level global variables** — no dataclasses, no classes.
Every subsystem reads and writes these globals directly. The full current set:

```python
# ── Geometry ────────────────────────────────────────────────────────────────
beam_length: float          # Total beam length (m)
beam_type: str | None       # "Simple" | "Cantilever" | None (None until set)

# ── Support positions (Simple beam only) ────────────────────────────────────
A: float                    # Pin support position (m)
B: float                    # Roller support position (m)
A_restraint: list           # [1, 1, 0] — constrained DoFs at A
B_restraint: list           # [0, 1, 0] — constrained DoFs at B
A_type: str                 # "Pin Support"
B_type: str                 # "Roller Support"
support_types: tuple        # ("pin", "roller") | ("fixed",) — persisted to JSON

# ── Cross-section (populated from moi_solver 6-tuple) ───────────────────────
Ix: float                   # Second moment of area about NA (m⁴)
shape: str                  # Profile name string
c: float                    # Distance: NA → extreme fibre (m)
b: float                    # Representative width at NA (m)
y_array: np.ndarray         # 10001 y-coordinates from -c to +c
section_dims: dict          # ← NEW: exact geometry dict for shear stress b(y)

# ── Material properties (SI units after conversion) ─────────────────────────
selected_material: dict     # Raw dict from materials.json
density: float              # kg/m³
yield_strength: float       # Pa  (MPa × 1e6)
ultimate_strength: float    # Pa
elastic_modulus: float      # Pa  (GPa × 1e9)
poisson_ratio: float
shear_yield_strength: float # = 0.55 × yield_strength (von Mises approx.)

# ── Loads ────────────────────────────────────────────────────────────────────
pointloads: list            # [[pos, Fx, Fy], ...]
distributedloads: list      # [[x_start, x_end, intensity], ...]
momentloads: list           # [[pos, moment], ...]
triangleloads: list         # [[x_start, x_end, intensity_peak, intensity_low], ...]
loads: dict                 # {"pointloads":[], "distributedloads":[], ...}

# ── Solver outputs ───────────────────────────────────────────────────────────
X_Field: np.ndarray         # ~10001 discretised beam positions
Total_ShearForce: np.ndarray
Total_BendingMoment: np.ndarray
Reactions: np.ndarray       # [Va, Vb, Ha] Simple | [Va, Ha, Ma] Cantilever

# ── Post-processing outputs (None until computed) ────────────────────────────
Deflection: np.ndarray | None   # Initialised to None; set after deflection calc
Slope: np.ndarray | None
Shear_stress: np.ndarray | None # 2D (n_x × n_y); collapsed to 1D for plotting
bending_stress: np.ndarray | None
FOS: float | None

# ── Project lifecycle ────────────────────────────────────────────────────────
project_state: dict         # See Section 5
beam_storage: list          # All projects loaded from disk
current_project: dict       # Currently loaded project dict
Materials: MaterialDatabase # Database object
```

---

## 5. Project State Flags (`project_state`)

```python
project_state = {
    "is_loaded": bool,              # True after load_project() succeeds
    "profile_saved": bool,          # True after moi_solver returns valid result
    "material_saved": bool,         # True after select_material() returns
    "loads_saved": bool,            # True after manage_loads() returns
    "supports_saved": bool,         # True after Beam_Supports() | auto-True for Cantilever
    "analysis_complete": bool,      # True after solve_*_beam() succeeds
    "deflection_calculated": bool,  # True after calculate_beam_deflection() runs
    "stress_calculated": bool,      # True after stress/FOS block runs
    "has_unsaved_changes": bool,    # True whenever any data changes
}
```

**Gate logic:**
- Menu `8` (Analysis) checks: `profile_saved AND material_saved AND loads_saved AND supports_saved`
- Menu `9` (Postprocessing) sub-options individually check `analysis_complete`,
  `deflection_calculated`, and `stress_calculated` before proceeding.

---

## 6. Load Data Structures

All loads are stored as Python lists of lists during input. When passed to the solver,
they are converted to `np.ndarray`. Empty input uses `np.empty((0, N))`.

```
pointloads:       [[position_m, Fx_N, Fy_N], ...]
distributedloads: [[x_start_m, x_end_m, intensity_N_per_m], ...]
momentloads:      [[position_m, moment_Nm], ...]
triangleloads:    [[x_start_m, x_end_m, intensity_peak_N_per_m, intensity_low_N_per_m], ...]
```

**Sign convention (Solver):**
- Positive `Fy` → **downward** force on the beam
- Positive moment → **counter-clockwise** (CCW)
- Positive shear → clockwise rotation on section
- Positive bending moment → compression in top fibres (sagging)

---

## 7. Solver Module (`main_solver.py`) — Mathematical Detail

### 7.1 Discretisation

```python
Delta = beam_length / 10000
X_Field = np.arange(0, beam_length + Delta, Delta)   # ~10001 points
```

### 7.2 Simple Beam — Reactions (`calculate_all_reactions`)

Takes moments about A to get Vb, then equilibrium for Va.

**Point loads:**
```
Vb += Fy * (A - Xp) / (B - A)
Va += -Fy - (Fy * (A - Xp) / (B - A))
Ha += Fx
```

**UDL:**
```
Fy_res = Fy * (Xend - Xstart)
X_res  = Xstart + 0.5*(Xend - Xstart)
(same moment-about-A formula as point load)
```

**Triangular / trapezoidal load (IMPROVED — generic centroid):**
```python
length = Xend - Xstart
Fy_res = 0.5 * (Fy_start + Fy_end) * length

# Guard for zero total load:
if abs(Fy_start + Fy_end) > 1e-9:
    X_res = Xstart + length * (Fy_start + 2*Fy_end) / (3 * (Fy_start + Fy_end))
else:
    X_res = Xstart + length / 2.0
```
> **Key improvement:** Old code handled only triangles with one zero end.
> The new formula is the exact centroid of a trapezoid and is correct for
> purely triangular, trapezoidal, and uniform (UDL, as a degenerate case) loads.

**Point moments (FIXED sign convention — CCW positive):**
```
Vb += -m / (B - A)
Va += +m / (B - A)
```

Returns tuple `(Va, Vb, Ha)`.

### 7.3 Simple Beam — SF/BM (`calculate_sf_bm`)

Left-to-right section method. At each `x`, sums contributions from entities to the **left**.
Reactions at A and B are treated as upward point forces.

**Triangular load — interior cut (IMPROVED):**
```python
# Linearly interpolated intensity at cut position x:
Xbase  = x - Xstart
F_cut  = Fy_start + (Fy_end - Fy_start) * (Xbase / L_load)

# Superposition: uniform part + triangular increment:
R_rect = Fy_start * Xbase
M_rect = R_rect * (Xbase / 2.0)
R_tri  = 0.5 * (F_cut - Fy_start) * Xbase
M_tri  = R_tri * (Xbase / 3.0)         # centroid of triangle at 1/3 from base
```

Returns `(ShearForce, BendingMoment)`.

> **CRITICAL CHANGE from old code:** The old solver returned `(ShearForce, -BendingMoment)`.
> The sign inversion bug has been removed. The returned `BendingMoment` is now the
> mathematically consistent value — sagging positive.

### 7.4 Cantilever — Reactions (`Calculate_Cantilever_Reactions`)

Fixed support at x=0. Global equilibrium:

```
Va = -sum(Fy_all_loads)
Ha = -sum(Fx_all_loads)
Ma = -sum(Fy_i * Xp_i) - sum(moments) - sum(UDL_resultant * centroid) - sum(TRL_resultant * centroid)
```

TRL centroid uses same generic trapezoid formula as above.
Returns `(Va, Ha, Ma)`.

### 7.5 Cantilever — SF/BM (`Calculate_SF_BM_Cantilever`)

Right-to-left section method. At each `x`, sums contributions from entities to the **right**.

**Triangular load — right-to-left cut (IMPROVED):**
```python
if Xend > x:
    start_pos = max(x, Xstart)
    if start_pos == x:   # cut is inside the load region
        t = (x - Xstart) / (Xend - Xstart)
        Fy_at_x = Fy_start + t * (Fy_end - Fy_start)
        remaining_length = Xend - x
        total_force = 0.5 * (Fy_at_x + Fy_end) * remaining_length
        # centroid of trapezoid from x to Xend:
        centroid = x + remaining_length * (Fy_at_x + 2*Fy_end) / (3*(Fy_at_x + Fy_end))
```

After the loop, `BendingMoment[0] = Ma` enforces the fixed-end BC.
Returns `(ShearForce, BendingMoment)`.

### 7.6 High-level wrappers

```python
solve_simple_beam(beam_length, A, B, pointloads_in, distributedloads_in,
                  momentloads_in, triangleloads_in, beam_type="Simple")
    → (X_Field, Total_ShearForce, Total_BendingMoment, Reactions)
    # Reactions = (Va, Vb, Ha)

solve_cantilever_beam(beam_length, pointloads_in, distributedloads_in,
                      momentloads_in, triangleloads_in)
    → (X_Field, ShearForce, CorrectedBendingMoment, Reactions)
    # Reactions = [Va, Ha, Ma]
    # CorrectedBendingMoment = -BendingMoment   ← sign flip ONLY here
```

> **Why the sign flip in `solve_cantilever_beam` only?**
> `Calculate_SF_BM_Cantilever` computes moment by summing forces to the right.
> The raw internal convention gives hogging positive (negative at the fixed end
> under downward loads). The `-` correction at the wrapper level aligns the output
> with the sagging-positive display convention. The simple beam path does NOT
> need this flip because `calculate_sf_bm` already produces sagging-positive values
> from its left-section approach. **Do not add or remove the `-` sign without
> understanding both conventions.**

---

## 8. MOI Solver (`moi_solver.py`) — CRITICAL CHANGE

### 8.1 All functions now return a 6-TUPLE

```python
return Ix, shape_name, c, b_representative, y_array, section_dims
```

Old briefing stated a 5-tuple. This is now incorrect. The 6th element `section_dims`
is a dictionary containing the **exact geometry** needed by `width_array_for_section()`.

**CLI unpacking (required):**
```python
Ix, shape, c, b, y_array, section_dims = result
```

If any code still unpacks only 5 values, it will raise a `ValueError: too many values to unpack`.

### 8.2 `section_dims` dictionary per profile

| Profile | Key fields in `section_dims` |
|---------|-------------------------------|
| I-beam | `type, bf, tf, hw, tw, H` |
| T-beam | `type, bf, tf, hw, tw, y_bar, H, c_top, c_bot` |
| Solid Circle | `type, diameter, radius` |
| Hollow Circle | `type, r_outer, r_inner, diameter_outer, diameter_inner` |
| Rectangle | `type, width, height` |
| Square | `type, side` |
| Hollow Square | `type, outer_width, inner_width, t_wall` |
| Hollow Rectangle | `type, outer_b, outer_h, inner_b, inner_h, t_flange, t_web` |

### 8.3 `b` representative value per profile (4th tuple element)

| Profile | `b` value |
|---------|-----------|
| I-beam | Web thickness `tw` |
| T-beam | Web thickness `tw` |
| Solid Circle | Outer diameter |
| Hollow Circle | Outer diameter |
| Square | Side `a` |
| Hollow Square | Outer side |
| Rectangle | Width `b` |
| Hollow Rectangle | Outer base width |

**Warning:** This scalar `b` is only used for display/reference. All shear stress
calculations now use the full `b_array` produced by `width_array_for_section()`.

---

## 9. Stress Solver (`stress_solver.py`) — Significant Changes

### 9.1 New function: `width_array_for_section(shape, section_dims, y_array)`

Computes the exact cross-section width b(y) at every height y, for **any** profile:

```python
b_array = width_array_for_section(shape, section_dims, y_array)
# Returns: np.ndarray of shape (len(y_array),)
```

Implementation details:
- **I-beam:** `b = tw` in web region, `b = bf` in flange regions. Uses `1e-9` tolerance
  to prevent floating-point boundary misses.
- **T-beam:** `b = bf` in flange, `b = tw` in web. Uses `c_top` and `c_bot` from
  `section_dims` to locate the NA.
- **Solid Circle:** `b(y) = 2 * sqrt(r² - y²)`. Uses `np.maximum(val, 0)` to prevent
  `sqrt` of negative float due to rounding.
- **Hollow Circle:** `b(y) = b_outer(y) - b_inner(y)`.
- **Rectangle / Square:** Constant `b` within height range.
- **Hollow Square / Rectangle:** `b = outer_width - inner_width` in web zone,
  `b = outer_width` in wall zones.
- **Fallback:** Returns `ones * section_dims.get('b', 1.0)` for unknown profiles.

### 9.2 New function: `first_moment_of_area_general(b_array, y_array)`

Computes Q(y) exactly for **any** cross-section via numerical integration:

```python
integrand = b_array * y_array
integral_bottom_up = cumulative_trapezoid(integrand, y_array, initial=0)
Q_array = -integral_bottom_up
Q_array[Q_array < 0] = 0.0   # clip floating-point negatives
```

This replaces the legacy rectangular-only `first_moment_of_area_rect()` for all
non-trivial cross-sections.

### 9.3 Legacy: `first_moment_of_area_rect(b, h, y_array)`

Still exists as a fallback. Uses the closed-form parabolic distribution:
```python
c = h / 2.0
Q = (b / 2.0) * (c**2 - y_array**2)
Q[Q < 0] = 0.0
```
Only accurate for solid rectangular sections. **Do not use for I-beams, circles, etc.**

### 9.4 `calculate_shear_stress(shear_force, Q_array, moment_of_inertia, b)`

```
τ(x, y) = V(x) · Q(y) / (I · b(y))
```

`b` can now be:
- A **scalar** float (legacy path, constant width)
- A **1D numpy array** (new path, exact width at each y)

Broadcasting logic:
```python
V = shear_force.reshape(-1, 1)    # (n_x, 1)
Q = Q_array.reshape(1, -1)        # (1, n_y)
if isinstance(b, np.ndarray):
    b = b.reshape(1, -1)           # (1, n_y)
shear_stress = (V @ Q) / (I * b)  # (n_x, n_y)
# Regions where b == 0 are forced to 0 (material void):
shear_stress = np.where(b == 0, 0.0, shear_stress)
shear_stress = np.nan_to_num(shear_stress)
```

Result is a **2D matrix** `(n_x, n_y)`. All plotting collapses to 1D via
`np.max(np.abs(shear_stress), axis=1)`.

### 9.5 Bending stress — dual function names

```python
# Primary:
def Bending_Stress(bending_moment, c, moment_of_inertia):
    return bending_moment * c / moment_of_inertia

# Wrapper (handles naming variant in cli.py):
def calculate_bending_stress(bending_moment, c, moment_of_inertia):
    return Bending_Stress(bending_moment, c, moment_of_inertia)
```

Both exist and are equivalent. `cli.py` calls `calculate_bending_stress`.

### 9.6 Deflection (`calculate_beam_deflection`)

Double numerical integration of Euler-Bernoulli:
```
κ(x) = M(x) / (E·I)
θ(x) = ∫κ dx   [via cumulative_trapezoid, initial=0]
v(x) = ∫θ dx   [via cumulative_trapezoid, initial=0]
```

Returns `(deflection, slope, curvature)`.

**Known limitation:** No boundary-condition correction is applied. For a simple beam
with supports not exactly at x=0 and x=L, the deflection values will drift. The old
briefing mentioned a linear correction; this has been removed in the current code.
For cantilevers (fixed at x=0), the cumulative integration with `initial=0` naturally
satisfies v(0)=0 and θ(0)=0, so the result is correct.

### 9.7 Factor of Safety (`Factor_of_Safety`)

```
FOS = yield_strength / max(|M(x)| · c / I)
```

FOS < 1 → unsafe. FOS = 1 → limit state. FOS > 1 → safe.

---

## 10. How Stress Calculations Are Called in `cli.py`

The complete stress calculation block (menu 8 → sub-choice 4):

```python
# Step 1: Build exact b(y) array for the actual cross-section geometry
b_array = width_array_for_section(shape, section_dims, y_array)

# Step 2: Compute Q(y) using the exact geometry
Q_array = first_moment_of_area_general(b_array, y_array)

# Step 3: Compute full 2D shear stress matrix
Shear_stress = calculate_shear_stress(Total_ShearForce, Q_array, Ix, b_array)
Max_Shear_stress = np.max(np.abs(Shear_stress))

# Step 4: Bending stress at extreme fibre along beam length
bending_stress = calculate_bending_stress(Total_BendingMoment, c, Ix)
Max_bending_stress = np.max(np.abs(bending_stress))

# Step 5: FOS based on bending
FOS = Factor_of_Safety(Total_BendingMoment, c, yield_strength, Ix)
```

---

## 11. Visualisation Modules

### 11.1 `plotting_helper.py` — Trace Builders (unchanged)

Produces raw `go.Scatter` trace objects for use in assembled figures.

| Function | Output |
|----------|--------|
| `draw_beam(length)` | Purple horizontal beam line |
| `draw_support(x, type)` | Small circle marker (blue=pin, red=roller) |
| `draw_big_support(x, type)` | Large circle marker |
| `draw_point_load(x, magnitude)` | Vertical arrow + label |
| `draw_udl(x_start, x_end, magnitude)` | Filled rectangle + label (returns **list** of traces) |
| `draw_moment(x, magnitude)` | Parametric arc + arrowhead + label (returns **list**) |
| `draw_reaction(x, magnitude)` | Vertical reaction arrow |
| `draw_horizontal_reaction(x, magnitude)` | Horizontal reaction arrow |

### 11.2 `beam_plot.py` — Assembled Figures

| Function | Purpose | New? |
|----------|---------|------|
| `plot_beam_schematic(beam_length, A, B, support_types, loads)` | Full simple beam diagram | No |
| `plot_reaction_diagram(A, B, reactions, support_types)` | Reaction forces diagram | No |
| `plot_cantilever_beam_schematic(beam_length, loads, title)` | **Cantilever** beam schematic | **YES — NEW** |
| `draw_triangular_load(start, end, intensity_start, intensity_end)` | Helper for TRL traces | **YES — NEW** |

**`loads` parameter format** (all beam plot functions): a formatted list produced by
`format_loads_for_plotting()` from `main_plotting.py`, **NOT** the raw `loads` dict.

Format: `[("point_load", pos, mag), ("udl", start, end, intensity), ("moment", pos, moment), ("trl", start, end, i_start, i_end)]`

**Known limitation in `plot_reaction_diagram`:** Function signature accepts `support_types`
but the cantilever reaction diagram is not implemented. Calling it for a cantilever beam
will draw pin+roller symbols instead of a fixed-wall symbol.

### 11.3 `main_plotting.py` — Full Diagram Functions

**Plotly functions (interactive HTML, call `.show()` internally):**

| Function | Inputs | New? |
|----------|--------|------|
| `Plotly_shear_force(X, SF, L)` | SFD only | No |
| `Plotly_bending_moment(X, BM, L)` | BMD only | No |
| `Plotly_sfd_bmd(X, SF, BM, L)` | SFD + BMD combined subplot | No |
| `Plotly_Deflection(X, D, L)` | Deflection only | No |
| `Plotly_ShearStress(X, SS, L)` | Shear stress (auto-collapses 2D) | No |
| `Plotly_BendingStress(X, BS, L)` | Bending stress | **YES — NEW** |
| `Plotly_combined_diagrams(X, SF, BM, L, D=None, SS=None)` | Up to 4 subplots | No |

**Matplotlib functions (static PNG, call `plt.show()` internally):**

| Function | Inputs | New? |
|----------|--------|------|
| `Matplot_shear_force(X, SF)` | SFD only | No |
| `Matplot_bending_moment(X, BM)` | BMD only | No |
| `Matplot_sfd_bmd(X, SF, BM)` | SFD + BMD | No |
| `Matplot_Deflection(X, D)` | Deflection only | No |
| `Matplot_ShearStress(X, SS)` | Shear stress | No |
| `Matplot_BendingStress(X, BS)` | Bending stress | **YES — NEW** |
| `Matplot_combined(X, SF, BM, D=None, SS=None)` | All in one figure | No |

**Helper:**
```python
format_loads_for_plotting(loads_dict) -> list
# Converts raw loads dict → plotting-format list
```

---

## 12. Material Database

### 12.1 25 materials (updated from 14 in old briefing)

All values stored in JSON:
- Density: kg/m³
- Yield / Ultimate Strength: MPa → ×1e6 in `cli.py`
- Elastic Modulus: GPa → ×1e9 in `cli.py`
- Poisson Ratio: dimensionless
- Thermal Expansion: 1/°C (stored but not used in calculations)
- Description: string

**Full material list:**
1. Structural Steel (S235)
2. Structural Steel (S275)
3. Structural Steel (S355)
4. Reinforced Concrete
5. Aluminum Alloy (6061-T6)
6. Aluminum Alloy (7075-T6)
7. Timber (Douglas Fir)
8. Timber (Oak)
9. Cast Iron (Gray)
10. Ductile Iron
11. High Strength Low Alloy Steel
12. Stainless Steel (304)
13. Stainless Steel (316)
14. Glass Fiber Reinforced Polymer
15. Carbon Fiber Reinforced Polymer
16. Titanium Alloy (Ti-6Al-4V)
17. Brick Masonry
18. Polyvinyl Chloride (PVC)
19. Copper (C11000)
20. Granite
21. Fiber Reinforced Concrete
22. Magnesium Alloy (AZ31B)
23. Tool Steel (A2)
24. Brass (C26000)
25. High-Performance Concrete (HPC)

### 12.2 `MaterialDatabase` class methods

```python
MaterialDatabase(filename="Materials.json")   # auto-resolves path via __file__
.list_all_materials()        → list[str]
.search_by_property(name, min_value, max_value) → list[dict]
.print_materials(list)       → None (console output)
.materials                   → list[dict]  (direct attribute access used in cli.py)
```

---

## 13. Project Persistence (`beam_projects.json`) — Updated Format

```json
{
  "name": "project_name",
  "beam_type": "Simple | Cantilever",
  "beam_length": 5.0,
  "support_A_pos": 0.0,
  "support_B_pos": 5.0,
  "support_A_restraint": [1, 1, 0],
  "support_B_restraint": [0, 1, 0],
  "support_A_type": "Pin Support",
  "support_B_type": "Roller Support",
  "support_types": ["pin", "roller"],
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
    "y_array": [...],
    "section_dims": {...}
  },
  "material": {
    "material": { ...full material dict... }
  }
}
```

**New fields vs. old format:**
- `"support_types"` — now persisted explicitly (was missing, causing load errors)
- `"section_dims"` inside `"profile"` — stores exact geometry for stress recalculation after load
- `"beam_type"` — now consistently stored

**Serialisation:** `safe_serialize()` converts `np.ndarray` → `list` and `tuple` → `list`.
On load, lists are converted back to `np.ndarray` via `np.array(...)`.

---

## 14. Known Bugs and Defects (Current State)

The previous briefing listed 10 bugs. As of this audit, the following are **resolved**
and the following are **new issues** found in the current code:

### 14.1 Resolved bugs (previously listed)

| Old ID | Description | Status |
|--------|-------------|--------|
| BUG-01 | Wrong function call for hollow circle | ✅ Fixed |
| BUG-02 | Incorrect cantilever reaction unpacking | ✅ Fixed |
| BUG-03 | NameError in shear stress plot (param name mismatch) | ✅ Fixed |
| BUG-04 | `loads_dict` scoping error | ✅ Fixed |
| BUG-05 | `beam_type` not initialised at module level | ✅ Fixed |
| BUG-06 | MOI 5-tuple vs 6-tuple mismatch | ✅ Fixed (6-tuple throughout) |
| BUG-07 | Combined plots crash if deflection/stress not computed | ✅ Fixed (None guards) |
| BUG-08 | `calculate_sf_bm` BMD sign inversion | ✅ Fixed |
| BUG-09 | Rectangular Q(y) used for non-rectangular sections | ✅ Fixed (width_array_for_section) |
| BUG-10 | `support_types` not persisted to JSON | ✅ Fixed |

### 14.2 Currently present issues

None

## 15. Missing Features and Incomplete Implementations

| Feature | Status | Notes |
|---------|--------|-------|
| Fixed-Fixed Beam | Placeholder only | Requires stiffness method rewrite |
| Continuous Beam | Placeholder only | Requires three-moment equation or matrix approach |
| Overhanging Beam | Returns "Simple" from `Beam_Classification` | No special handling |
| Deflection BC correction | Not applied | Integration drift for off-end supports |
| Reaction schematic for Cantilever | Wrong symbols | `plot_reaction_diagram` shows pin+roller |
| Cross-section stress distribution plot (τ vs y) | Not implemented | Would use y_array + Q_array |
| Export to CSV/PDF | Not implemented | Only JSON project save exists |
| Unit system toggle | Not implemented | Fully SI throughout |
| Load position validation (within span) | Partial | No check that loads lie within [0, L] |
| Self-weight calculation | Not implemented | density is stored but unused |
| Bending stress in `Plotly_combined_diagrams` | Not included | Only SF, BM, Deflection, ShearStress |

---

## 16. Execution Flow — Complete Walkthrough

```
init()
  └─ Resets project_state dict (Note: missing 3 flags — see ISSUE-06)

run_extended_menu()
  └─ load_material_database()     → loads data/materials.json into global Materials
  └─ load_projects_from_disk()    → loads beam_projects.json into beam_storage
  └─ while True: main_menu_template()

User path for a fresh analysis:

1. Menu '2' → Beam_Classification() → sets beam_type
             → If Cantilever: sets project_state["supports_saved"] = True

2. Menu '3' → Beam_Length() → sets beam_length
           → choose_profile() → moi_solver.*() → result unpacked as 6-tuple
           → sets Ix, shape, c, b, y_array, section_dims
           → project_state["profile_saved"] = True

3. Menu '4' → select_material() → sets selected_material + converts to SI
           → density, yield_strength, ultimate_strength, elastic_modulus,
             poisson_ratio, shear_yield_strength
           → project_state["material_saved"] = True

4. Menu '5' → (Simple only) Beam_Supports()
           → sets A, B, A_type, B_type, A_restraint, B_restraint
           → support_types = ("pin", "roller")
           → project_state["supports_saved"] = True

5. Menu '6' → manage_loads()
           → sets loads dict + pointloads, distributedloads, momentloads, triangleloads
           → project_state["loads_saved"] = True

6. Menu '8' → sub '1': solve_simple_beam() | solve_cantilever_beam()
           → sets X_Field, Total_ShearForce, Total_BendingMoment, Reactions
           → project_state["analysis_complete"] = True

7. Menu '8' → sub '3': calculate_beam_deflection()
           → sets Deflection, Slope, curv
           → project_state["deflection_calculated"] = True

8. Menu '8' → sub '4':
           → width_array_for_section() → b_array
           → first_moment_of_area_general() → Q_array
           → calculate_shear_stress() → Shear_stress (2D)
           → calculate_bending_stress() → bending_stress (1D)
           → Factor_of_Safety() → FOS
           → project_state["stress_calculated"] = True

9. Menu '9' → various plot functions using all computed arrays
             → Sub '1': plot_reaction_diagram()
             → Sub '2': Matplot_sfd_bmd() | Plotly_sfd_bmd()  ← ISSUE-01 here
             → Sub '3': Matplot_Deflection() | Plotly_Deflection()
             → Sub '4': Matplot_ShearStress() + Matplot_BendingStress()
                      | Plotly_ShearStress() + Plotly_BendingStress()
             → Sub '5': Matplot_combined() | Plotly_combined_diagrams()  ← ISSUE-02 here

10. Menu '10' → save_project() → save_projects_to_disk()

11. Menu '11' → display_engineering_recommendations()
```

---

## 17. Numerical Conventions and Units

| Quantity | Unit | Notes |
|----------|------|-------|
| Length | m | All positions, beam length, cross-section dims |
| Force | N | All point loads and reactions |
| Distributed load | N/m | UDL and triangular |
| Moment | N·m | Applied and reaction moments |
| Stress | Pa | All stress outputs |
| Elastic Modulus | Pa | After GPa×1e9 conversion |
| Yield Strength | Pa | After MPa×1e6 conversion |
| Moment of Inertia | m⁴ | All cross-sections |
| Deflection | m | Output of double integration |
| Density | kg/m³ | Stored only, unused in calculations |
| Thermal expansion | 1/°C | Stored only, unused in calculations |

---

## 18. Key Design Decisions and Implicit Assumptions

1. **Discretisation is fixed at 10,000 divisions.** Always ~10,001 points.

2. **Simple beam: A is always pin (Fx+Fy), B is always roller (Fy only).**
   `Ha` captures all horizontal force equilibrium.

3. **No self-weight.** Beam density is stored but never applied as a distributed load.

4. **Cantilever fixed end is always at x=0.** No option to flip orientation.

5. **`b` scalar vs `b_array`:** The scalar `b` (4th tuple element from MOI solver)
   is kept for legacy display and saved in JSON. The actual shear stress calculation
   always uses `width_array_for_section()` to get the exact `b_array`.

6. **Plotly figures call `.show()` internally.** No figure object is returned to caller.

7. **`safe_serialize()`** converts numpy arrays and tuples to lists before JSON save.
   On load, lists are re-converted to numpy arrays.

8. **`section_dims` is stored in project JSON** under `profile.section_dims`. If an
   older project (saved before the 6-tuple change) is loaded, `section_dims` will be
   `{}` and `width_array_for_section` will fall into the fallback path.

9. **Triangular load inputs in `inputs.py`:** `intensity` is the peak, `intensityL` is
   the lowest. The storage order is `[start, end, intensity_peak, intensity_low]`.
   In the solver, the parameter is `[Xstart, Xend, Fy_start, Fy_end]`, so the
   calling code in `cli.py` maps `intensity_peak → Fy_start` and `intensity_low → Fy_end`.

10. **`Overhanging Beam` in `Beam_Classification` returns `"Simple"`** — it is treated
    identically to a simply supported beam. No special handling exists.

---

## 19. How to Assist With This Project — Agent Instructions

When asked to help with this codebase, apply these rules:

### A. Before suggesting any code change:
- Identify which global variables are affected.
- Check if `project_state` flags need updating.
- Verify the data flow: does the change affect what gets serialised to JSON?
- Check if `section_dims` needs to be passed alongside `shape` and `y_array`.

### B. When fixing bugs:
- Always show: original code snippet → problem description → fixed code.
- Check cascading effects — a change in solver return order affects cli.py unpacking
  and potentially the JSON save format.
- For any MOI solver change, verify the 6-tuple is correctly unpacked everywhere.

### C. When adding new features:
- Follow the existing menu structure pattern in `Menus.py` + `cli.py`.
- Add new global variable to module-level declarations AND to `init()`.
- Add the new state flag to both the module-level `project_state` AND `init()`.
- Add serialisation/deserialisation in `save_project()` and `load_project()`.
- If the feature uses cross-section geometry, pass `section_dims` to the function.

### D. When asked about physics/mechanics:
- Confirm sign conventions before answering (see Sections 6 and 17).
- Distinguish: mathematical formulation vs. numerical implementation.
- The BM sign flip only occurs once, in `solve_cantilever_beam`. Both internal
  cantilever functions (`Calculate_Cantilever_Reactions` and
  `Calculate_SF_BM_Cantilever`) work with hogging-positive internally.

### E. When asked about extending beam types:
- Fixed-fixed beams: require stiffness matrix method. Current deterministic solver
  cannot handle this without architectural changes to `main_solver.py`.
- Continuous beams: require three-moment equation or direct stiffness. Same limitation.
- Overhanging beams: currently treated as "Simple" — to properly support, the
  deflection BC correction would need to handle off-end support positions.

### F. When asked about deflection:
- Method: double numerical integration (cumulative_trapezoid).
- No BC correction is currently applied. Result is exact for cantilevers.
- For simple beams, the deflection at the supports will not be exactly zero due to
  numerical integration drift. A correction using linear interpolation could be added.

### G. When asked about shear stress:
- Always use `width_array_for_section()` + `first_moment_of_area_general()`.
- The old `first_moment_of_area_rect` is now a legacy fallback — only correct for
  solid rectangular sections.
- The result is 2D `(n_x, n_y)`. Plotting always collapses to 1D by taking
  `np.max(np.abs(shear_stress), axis=1)`.

### H. When asked to extend visualisation:
- All new Plotly diagrams: follow the pattern in `Plotly_shear_force()` —
  fill with transparency, dotted zero-line, `plot_bgcolor='white'`.
- All new Matplotlib diagrams: follow `Matplot_shear_force()` —
  `fill_between` for +/- regions, `annotate` with arrowprops, remove top/right spines.
- Before adding any new function to a combined plot, verify the `num_plots` counting
  logic is correct and that None-guards exist for optional arrays.

### I. When interpreting `Reactions`:
- **Simple beam:** `Reactions = (Va, Vb, Ha)` — index 0=Va, index 1=Vb, index 2=Ha.
- **Cantilever:** `Reactions = [Va, Ha, Ma]` — index 0=Va, index 1=Ha, index 2=Ma.
- `cli.py` extracts these correctly in `sub_choice == '1'` and `sub_choice == '2'`
  of the analysis menu, but the order DIFFERS between beam types — always check `beam_type`
  before unpacking.

---

## 20. Dependency List

```
numpy          # Array maths, integration backbone
scipy          # cumulative_trapezoid in stress_solver.py
plotly         # All interactive plots
matplotlib     # All static plots
termcolor      # Coloured terminal output (colored, cprint)
json           # Project persistence (stdlib)
pathlib        # Path resolution in materials_database.py (stdlib)
os, sys        # Path injection in multiple files (stdlib)
```

**No `requirements.txt` is present.** All packages must be installed manually.

---

## 21. Quick-Reference: Common Change Patterns

### Adding a new cross-section profile

1. Add a new function in `moi_solver.py` that returns the 6-tuple
   `(Ix, "ProfileName", c, b_rep, y_array, section_dims)`.
2. Add a `section_dims` dict with the geometry keys needed.
3. Add a case in `width_array_for_section()` in `stress_solver.py` for the new shape.
4. Add a menu option in `Menus.py` `choose_profile()`.
5. Add an `elif profile_choice == 'N':` in `cli.py` profile section.
6. The `first_moment_of_area_general()` requires no changes — it works with any `b_array`.

### Adding a new material

1. Add a JSON object to `data/materials.json` with all required fields.
2. No code changes needed — `MaterialDatabase` loads all entries dynamically.

### Adding a new load type

1. Add a new key to the `loads` dict in `manage_loads()` in `inputs.py`.
2. Add the new list at module-level in `cli.py`.
3. Update `solve_simple_beam()` and `solve_cantilever_beam()` to accept and convert the new load.
4. Add reaction and SF/BM contributions in the solver functions.
5. Add `format_loads_for_plotting()` handling in `main_plotting.py`.
6. Add a draw function in `plotting_helper.py` if a new trace type is needed.
7. Add serialisation in `save_project()` and deserialisation in `load_project()`.

---

*End of briefing. Version 2.0 — reflects codebase as audited from 19 source files.*
*All section references are internal to this document.*
