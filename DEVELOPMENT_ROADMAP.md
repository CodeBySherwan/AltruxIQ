# AltruxIQ — Development Roadmap & Implementation Guide

> This document describes six planned development steps for AltruxIQ. Each step explains
> **what** needs to be built, **why** it matters, **which files are affected**, and
> **exactly how** it should integrate with the existing codebase. Any AI agent or developer
> picking this up should be able to implement each step independently without ambiguity.

---

## Table of Contents

1. [Custom Beam Classification](#step-1--custom-beam-classification)
2. [Cross-Section Standard Library with Custom Saves](#step-2--cross-section-standard-library-with-custom-saves)
3. [User-Selectable Solver Resolution](#step-3--user-selectable-solver-resolution)
4. [Custom Material Creation and Persistence](#step-4--custom-material-creation-and-persistence)
5. [Deflected Beam Animation in PyVista](#step-5--deflected-beam-animation-in-pyvista)
6. [Restructured Project Layout for Multi-Analysis Expansion](#step-6--restructured-project-layout-for-multi-analysis-expansion)

---

## Step 1 — Custom Beam Classification

### What It Is

Currently AltruxIQ supports six fixed beam types: Simple, Overhanging, Cantilever,
Fixed-Fixed, Propped, and Continuous. Each type has hardcoded support DOF tuples that
are passed to `indeterminate_solver._build_supports()`. There is no way for a user to
define an arbitrary combination — for example, a beam fixed at the left end with a roller
at mid-span (which is neither a Propped Cantilever nor a Continuous beam in the current
classification).

This step adds a **seventh option** — "Custom" — that lets the user define any number of
supports at any position, each with a manually chosen DOF tuple and optionally an elastic
spring constant. The output is structurally equivalent to what the Continuous beam type
already produces internally, but exposed through a guided UI that makes the DOF concept
understandable to the user.

### Why It Matters

The existing fixed classifications cover the most common academic cases but are too
rigid for real engineering problems. A pharmaceutical equipment support frame, for
example, might have a beam on three supports where one is a spring-mounted anti-vibration
pad — none of the existing six types covers this cleanly. Custom classification unlocks
the full power of the `indeterminatebeam` backend, which already supports elastic springs
via `ky` and `kx` parameters on `Support()`.

### Which Files Are Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `src/ui/inputs.py` | Modify | Add `'7'` branch in `Beam_Classification()` returning `"Custom"` |
| `src/ui/inputs.py` | Add new function | `define_custom_supports(beam_length, unit_system, units)` |
| `src/solver/indeterminate_solver.py` | Modify | Add `"Custom"` branch in `_build_supports()` |
| `src/solver/indeterminate_solver.py` | Modify | Add `"Custom"` to `support_positions` extraction block |
| `src/ui/cli.py` | Modify | Add `"Custom"` to the valid beam types list; route to new support definition |
| `src/plotting/beam_plot.py` | Modify | Handle `beam_type == "Custom"` in `plot_beam_schematic()` |
| `src/ui/Menus.py` | Modify | `display_analysis_info()` — add Custom branch for boundary conditions display |

### How to Implement It

#### 1.1 — Extend `Beam_Classification()` in `inputs.py`

Add option `7` at the end of the existing menu:

```python
elif classification == '7':
    return "Custom"
```

Add a descriptive visual for the custom option:
```
│ 7 - Custom Beam (User-Defined Supports)
│    Visual:  ? ─────── ? ─────── ? ─────── ?
│    Define support positions and DOF manually
```

#### 1.2 — Add `define_custom_supports()` in `inputs.py`

This function is the core of this feature. It must:

1. Ask how many supports the user wants (minimum 1; warn if only 1 — beam may be
   unstable unless it's a fixed support with moment reaction).
2. For each support, ask: position (in display units, converted to SI on input).
3. For each support, show a clear DOF table and ask which type:

```
Support Types:
  [1] Pin          — DOF (1,1,0) — restrains X and Y, free rotation
  [2] Roller       — DOF (0,1,0) — restrains Y only
  [3] Fixed        — DOF (1,1,1) — restrains all three DOF
  [4] Vertical Spring — DOF (0,1,0) with ky = ? N/m
  [5] Horizontal Spring — DOF (1,0,0) with kx = ? N/m
```

4. For spring types, prompt the spring stiffness in display units (N/m or lbf/ft),
   convert to SI before storing.
5. Validate that at least one support restrains the vertical DOF (y=1) — otherwise the
   beam has no vertical equilibrium and the solver will fail.
6. Validate that at least one support restrains the horizontal DOF (x=1) — otherwise
   the solver matrix is singular.
7. Return a `supports_list` in the same format as `define_continuous_supports()`:
   `[{"pos": float, "dof": tuple, "ky": float|None, "kx": float|None}, ...]`

```python
def define_custom_supports(beam_length, unit_system="Metric", units=None):
    """
    Interactive wizard for defining arbitrary support configurations.
    Returns a list of support dicts compatible with indeterminate_solver.solve_beam().
    """
    ...
```

#### 1.3 — Extend `_build_supports()` in `indeterminate_solver.py`

Add a `"Custom"` branch that reuses the same logic as `"Continuous"`:

```python
elif beam_type == "Custom":
    result = []
    for s in supports:
        dof = tuple(s["dof"])
        ky  = s.get("ky", None)
        kx  = s.get("kx", None)
        if ky is not None or kx is not None:
            result.append(Support(s["pos"], dof, ky=ky, kx=kx))
        else:
            result.append(Support(s["pos"], dof))
    return result
```

Also add the `support_positions` extraction:
```python
elif beam_type == "Custom":
    support_positions = [s["pos"] for s in supports]
```

#### 1.4 — Route in `cli.py`

In `run_extended_menu()`, add `"Custom"` to the valid beam types list:

```python
if beam_type in ["Simple", "Cantilever", "Fixed-Fixed", "Propped",
                 "Continuous", "Overhanging Beam", "Custom"]:
```

In the `selection == '5'` (Boundary Conditions) block, add a branch:
```python
elif beam_type == "Custom":
    supports_list = define_custom_supports(beam_length, current_unit_system, current_labels)
    project_state["supports_saved"] = True
    project_state["has_unsaved_changes"] = True
    support_types = tuple(
        "pin" if tuple(s["dof"]) == (1,1,0)
        else "roller" if tuple(s["dof"]) == (0,1,0)
        else "fixed"
        for s in supports_list
    )
```

In the solve block (`selection == '8'`, `sub_choice == '1'`), add:
```python
elif beam_type == "Custom":
    _supports = supports_list
```

#### 1.5 — Schematic Plot Support

In `beam_plot.py` → `plot_beam_schematic()`, add a `"Custom"` branch that iterates
the `continuous_supports` list (same variable passed for Continuous beams):

```python
elif beam_type == "Custom":
    for s in continuous_supports:
        dof = tuple(s.get("dof", (0, 1, 0)))
        s_type = "pin" if dof == (1,1,0) else "roller" if dof == (0,1,0) else "roller"
        traces.append(draw_support(s["pos"] / len_div, s_type))
```

### Validation Rules to Enforce

- At least 2 supports total (1 support with only vertical DOF leaves the beam
  horizontally free — valid only with a moment-releasing analysis, but let the solver
  handle that).
- At least one support must have `dof[0] == 1` (horizontal restraint) OR the user must
  accept a warning that the beam may be horizontally unstable.
- No two supports at the same position.
- All positions must be within `[0, beam_length]`.

---

## Step 2 — Cross-Section Standard Library with Custom Saves

### What It Is

Currently, every cross-section profile requires the user to manually type all dimensions
every time, with no way to reuse a previous definition or select from standard engineering
tables. This step adds a **section library** with two tiers:

**Standard Library** — Pre-populated from real engineering standards:
- European sections: IPE, HEA, HEB, HEM (I-beams)
- European hollow sections: SHS, RHS, CHS (square, rectangular, circular hollow)
- American W-sections (wide flange beams)
- Common round bars and pipes

**Custom Library** — Sections the user has defined and saved. Displayed in a different
colour (e.g., yellow vs. white) and stored in a separate JSON file that persists between
sessions.

### Why It Matters

In real-world structural work, engineers choose from catalogue sections rather than
inventing arbitrary dimensions. A structural engineer at a pharmaceutical facility in Syria
would reference DIN or EN 10034 sections for steel beams. Having a one-click lookup
eliminates repetitive data entry, reduces input errors, and makes the workflow feel
professional rather than academic.

### Which Files Are Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `data/standard_sections.json` | New file | Pre-populated section catalogue |
| `data/custom_sections.json` | New file (auto-created) | User-saved sections |
| `src/database/sections_database.py` | New file | `SectionsDatabase` class |
| `src/solver/moi_solver.py` | Modify | Add `load_section_from_library()` function |
| `src/ui/inputs.py` | Modify | Extend `choose_profile()` flow with library option |
| `src/ui/Menus.py` | Modify | Add `section_library_menu()` display function |
| `src/ui/cli.py` | Modify | Add library lookup branch in profile definition block |

### Data Format — `data/standard_sections.json`

```json
{
  "IPE": [
    {
      "name": "IPE 100",
      "shape": "I-beam",
      "bf": 0.055, "tf": 0.0057, "hw": 0.0806, "tw": 0.0041,
      "H": 0.1,
      "Ix": 1.71e-6, "c": 0.05,
      "A": 1.032e-3,
      "source": "EN 10034"
    },
    ...
  ],
  "HEA": [...],
  "HEB": [...],
  "SHS": [...],
  "RHS": [...],
  "CHS": [...]
}
```

Each entry must contain all fields needed to fully populate the 6-tuple that
`inertia_moment_*` functions return: `Ix`, `shape`, `c`, `b_rep` (web thickness `tw`
for I/T beams, outer diameter for circles, outer width for rectangulars), `y_array`
(generated at load time via `np.linspace(-c, c, 10001)`), and `section_dims`.

### Data Format — `data/custom_sections.json`

```json
[
  {
    "name": "My Factory Beam 250x120",
    "shape": "I-beam",
    "bf": 0.12, "tf": 0.010, "hw": 0.230, "tw": 0.007,
    "H": 0.250,
    "Ix": 6.54e-5, "c": 0.125,
    "section_dims": { "type": "I-beam", "bf": 0.12, ... },
    "created_at": "2026-06-20T14:30:00"
  }
]
```

### New Class — `src/database/sections_database.py`

```python
class SectionsDatabase:
    def __init__(self):
        # Loads both standard and custom sections
        self._load_standard()
        self._load_custom()

    def get_standard_families(self) -> list[str]:
        # Returns ["IPE", "HEA", "HEB", "SHS", "RHS", "CHS", "W-Sections", ...]

    def get_sections_in_family(self, family: str) -> list[dict]:
        # Returns all entries for a given family

    def search_by_name(self, name: str) -> dict | None:
        # Case-insensitive exact or partial match

    def save_custom_section(self, section_dict: dict):
        # Appends to custom_sections.json, adds timestamp

    def delete_custom_section(self, name: str) -> bool:
        # Removes by name from custom_sections.json

    def list_custom_sections(self) -> list[dict]:
        # Returns all entries from custom_sections.json
```

### UI Flow — `section_library_menu()` in `Menus.py`

When the user selects `[2] Define Profile` in the Profile Definition menu, they now first
see:

```
┌─ PROFILE SOURCE ─────────────────────────────────────────────
│  1  │ Enter Custom Dimensions   - Type in dimensions manually
│  2  │ Standard Section Library  - Browse IPE, HEA, W-Sections...
│  3  │ My Saved Sections         - Retrieve a saved custom section
│  4  │ Save Current Section      - Save the active section for reuse
└─────────────────────────────────────────────────────────────
```

When browsing the Standard Library, sections are displayed in **white**. When browsing
custom sections, each entry is displayed in **yellow** with a `[CUSTOM]` tag:

```
  1  │ IPE 100          — Ix = 1.71e-06 m⁴  | H = 100mm | bf = 55mm
  2  │ IPE 120          — Ix = 3.18e-06 m⁴  | H = 120mm | bf = 64mm
  ...
[CUSTOM]
  C1 │ My Factory Beam  — Ix = 6.54e-05 m⁴  | Saved: 2026-06-20   ← yellow text
  C2 │ Warehouse Rafter — Ix = 2.10e-05 m⁴  | Saved: 2026-06-19   ← yellow text
```

### Loading a Section from Library — `moi_solver.py`

Add a function that converts a library dict into the standard 6-tuple without
prompting the user for anything:

```python
def load_section_from_library(entry: dict) -> tuple:
    """
    Convert a sections_database entry into the standard MOI 6-tuple.
    Returns (Ix, shape_name, c, b_rep, y_array, section_dims) or None on error.
    """
    import numpy as np
    try:
        Ix    = float(entry["Ix"])
        shape = entry["shape"]
        c     = float(entry["c"])
        b_rep = float(entry.get("tw", entry.get("outer_b", entry.get("diameter", c*2))))
        y_array = np.linspace(-c, c, 10001)
        section_dims = entry.get("section_dims", {})
        return Ix, shape, c, b_rep, y_array, section_dims
    except (KeyError, TypeError, ValueError):
        return None
```

### Saving the Current Active Section

In `cli.py`, when the user selects `[4] Save Current Section` from the library menu:
1. Check that `project_state["profile_saved"]` is `True` (i.e., a profile is active).
2. Prompt for a custom name.
3. Assemble a dict from the active globals (`Ix`, `shape`, `c`, `b`, `section_dims`).
4. Call `sections_db.save_custom_section(dict)`.

---

## Step 3 — User-Selectable Solver Resolution

### What It Is

The number of evaluation points along the beam (`num_points`) is currently hardcoded at
`2001` inside the `solve_beam()` call in `cli.py`. This controls the resolution of all
output arrays (`X_Field`, `Total_ShearForce`, `Total_BendingMoment`, `Deflection`) and
directly determines both the precision of results and the time the SymPy solver takes to
evaluate each expression point-by-point.

This step exposes `num_points` as a user-selectable setting with a sensible allowed range
and a clear explanation of the tradeoff.

### Why It Matters

For a simple 5m beam, 2001 points resolves in under a second. For a 10-span continuous
beam where `indeterminatebeam` evaluates a complex SymPy piecewise function at every
point, 2001 evaluations can take 30–90 seconds. Reducing to 501 cuts that to 8–20 seconds
at a small cost in plot smoothness. Conversely, for publication-quality reports, 5001
points produces smoother curves with more accurate contraflexure detection.

### Which Files Are Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `src/ui/cli.py` | Modify | Add `num_points` global; expose via new menu option |
| `src/ui/Menus.py` | Add function | `resolution_menu(current_points)` display function |
| `src/ui/inputs.py` | Add function | `get_solver_resolution()` input handler |
| `src/solver/indeterminate_solver.py` | No change needed | Already accepts `num_points` as parameter |

### Allowed Range and Presets

The acceptable range is `201` to `10001`. Below 201, plots appear jagged and
contraflexure detection becomes unreliable. Above 10001, SymPy evaluation time becomes
impractical for interactive use even on a fast machine.

Offer four named presets plus a custom entry:

| Preset | `num_points` | Use Case |
|--------|-------------|----------|
| Fast (Draft) | 501 | Complex continuous beams, quick iteration |
| Standard | 1001 | Good balance for most beam types |
| High (Default) | 2001 | Default; sufficient for all standard cases |
| Fine (Report) | 5001 | Publication-quality smooth curves |
| Custom | user input | Any integer between 201 and 10001 |

### Implementation

#### 3.1 — Add Global in `cli.py`

At the module level (alongside `beam_length`, `Ix`, etc.):

```python
num_points = 2001   # Default solver resolution — user-modifiable
```

Also include `num_points` in the `init()` function reset and in `save_project()` /
`load_project()` so that saved projects restore the resolution used to generate them.

#### 3.2 — Add to `project_data` dict in `save_project()`

```python
project_data = {
    ...
    'num_points': num_points,
    ...
}
```

And in `load_project()`:
```python
num_points = current_project.get('num_points', 2001)
```

#### 3.3 — Add Menu Option

Add option `13` to the main menu:
```
│ 13 │ ⚙️  Solver Resolution  - Set analysis point count (current: 2001)
```

The status line in the main menu should dynamically show the active value so the user
always knows what resolution is set.

#### 3.4 — New function `resolution_menu()` in `Menus.py`

```
┌─ SOLVER RESOLUTION ─────────────────────────────────────────
│  Current setting: 2001 points
│
│  1  │ Fast Draft   (501)    — Best for multi-span beams
│  2  │ Standard    (1001)    — Balanced speed and accuracy
│  3  │ High         (2001)   — Default [current]
│  4  │ Fine         (5001)   — Report-quality smooth curves
│  5  │ Custom               — Enter a value (201 – 10001)
│  6  │ Back to Main Menu
│
│  ⚠ Higher values significantly increase solve time for
│     Continuous and indeterminate beams (SymPy evaluation).
└─────────────────────────────────────────────────────────────
```

#### 3.5 — Propagate to `solve_beam()` call in `cli.py`

Replace the hardcoded value:
```python
# Before
result = solve_beam(..., num_points=2001)

# After
result = solve_beam(..., num_points=num_points)
```

#### 3.6 — Also Expose the Legacy Solver Divisions (if reactivated)

The legacy `main_solver.py` uses `divisions=10000` in `initialize_solver()`. If the
legacy solver path is ever reactivated, the same `num_points` global should control
`divisions` proportionally (e.g., `divisions = num_points * 5`).

---

## Step 4 — Custom Material Creation and Persistence

### What It Is

Currently the materials database is a read-only list of 25 pre-defined materials loaded
from `data/materials.json`. Users cannot add new materials, and any material property
needed (e.g., a specific pharmaceutical-grade stainless steel or a proprietary composite)
must be hacked in by editing the JSON file directly.

This step adds a full **custom material workflow**: create, view, edit, and delete
user-defined materials, stored in a separate `data/custom_materials.json` file that
persists between sessions. In the material selection table, custom materials appear at
the bottom under a visible separator, displayed in **yellow** text with a `[CUSTOM]` tag
to distinguish them from the standard database.

### Why It Matters

In pharmaceutical manufacturing (Rama Pharma's context), the actual materials used —
specific grades of SS316L tubing, HDPE supports, or specialized polymer gasket beams —
often don't map exactly to the standard database entries. The closest standard entry may
have the right yield strength but the wrong density, which directly affects self-weight
calculations if that feature is ever added. Custom materials also allow engineers to
encode vendor-specific data that otherwise exists only in procurement sheets.

### Which Files Are Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `data/custom_materials.json` | New file (auto-created) | User-defined material storage |
| `src/database/materials_database.py` | Modify | Extend `MaterialDatabase` to merge standard + custom |
| `src/ui/cli.py` | Modify | Add material creation/deletion flow |
| `src/ui/inputs.py` | Add function | `define_custom_material()` interactive wizard |
| `src/ui/Menus.py` | Modify | `select_material()` display — highlight custom entries |
| `src/ui/Menus.py` | Modify | `material_selection_menu()` — add "Manage Custom Materials" option |

### Data Format — `data/custom_materials.json`

The schema is identical to `data/materials.json` entries, with two extra fields:

```json
[
  {
    "Material": "SS316L Pharma Grade",
    "Density": 7980,
    "Yield Strength": 220,
    "Ultimate Strength": 520,
    "Elastic Modulus": 193,
    "Poisson Ratio": 0.28,
    "Thermal Expansion": 16e-6,
    "Description": "Pharmaceutical-grade austenitic stainless steel per ASTM A270",
    "is_custom": true,
    "created_at": "2026-06-20T14:30:00"
  }
]
```

The `is_custom: true` flag allows the display layer to render these entries differently.
`created_at` is an ISO 8601 timestamp added automatically on save.

### Extending `MaterialDatabase` in `materials_database.py`

Modify the `__init__` to also load `custom_materials.json`, then expose a merged view:

```python
class MaterialDatabase:
    def __init__(self, filename="materials.json"):
        # ... existing load logic for standard materials ...
        self._load_custom_materials()

    def _load_custom_materials(self):
        custom_path = self.db_path.parent / "custom_materials.json"
        try:
            with open(custom_path, 'r') as f:
                self.custom_materials = json.load(f)
        except FileNotFoundError:
            self.custom_materials = []

    @property
    def all_materials(self):
        """Returns standard + custom materials in one list."""
        return self.materials + self.custom_materials

    def add_custom_material(self, material_dict: dict):
        """Appends a new custom material and persists to disk."""
        material_dict["is_custom"] = True
        material_dict["created_at"] = datetime.now().isoformat()
        self.custom_materials.append(material_dict)
        self._save_custom_materials()

    def delete_custom_material(self, name: str) -> bool:
        """Removes a custom material by exact name match."""
        original_count = len(self.custom_materials)
        self.custom_materials = [
            m for m in self.custom_materials if m["Material"] != name
        ]
        if len(self.custom_materials) < original_count:
            self._save_custom_materials()
            return True
        return False

    def _save_custom_materials(self):
        custom_path = self.db_path.parent / "custom_materials.json"
        with open(custom_path, 'w') as f:
            json.dump(self.custom_materials, f, indent=2)
```

### Display Rules in `select_material()` / `Menus.py`

The material table now iterates `Materials.all_materials` instead of `Materials.materials`.
The rendering logic checks `material.get("is_custom", False)`:

```python
for index, material in enumerate(all_materials):
    is_custom = material.get("is_custom", False)

    if is_custom:
        # Yellow row with [CUSTOM] tag
        mat_num  = colored(f"{index + 1:3d} │", 'yellow', attrs=['bold'])
        mat_name = colored(f" {material['Material']:<28} [CUSTOM] │", 'yellow', attrs=['bold'])
    else:
        # Standard white row
        mat_num  = colored(f"{index + 1:3d} │", 'light_yellow')
        mat_name = colored(f" {material['Material']:<34} │", 'light_yellow')
```

A visual separator is printed between the last standard material and the first custom
material:

```
────┼────────────────────────────────────┼─── ... (separator) ───
    │ ── USER-DEFINED MATERIALS ──────── │
────┼────────────────────────────────────┼─── ...
```

### New Function `define_custom_material()` in `inputs.py`

This is a guided wizard that walks through each required property, validates ranges
(e.g., density must be positive, yield strength must be < ultimate strength, elastic
modulus must be > 0), and returns a complete material dict:

```python
def define_custom_material(unit_system="Metric", units=None) -> dict | None:
    """
    Interactive wizard to create a custom material entry.
    Returns a dict in materials.json format, or None on abort.

    Validates:
    - All numeric fields are positive
    - Yield Strength < Ultimate Strength
    - Elastic Modulus > 0
    - Poisson Ratio in (0, 0.5)
    """
```

All input values are shown in the active unit system (MPa, GPa, kg/m³ or ksi, lb/ft³)
but stored internally in the same mixed-unit format as the standard JSON database
(MPa for strengths, GPa for modulus, kg/m³ for density — matching the existing schema).

### New Menu Option in `material_selection_menu()`

Add option `4` — "Manage Custom Materials":

```
│  1  │ 🔍 Select Material          — Choose from database
│  2  │ 📋 View Current Material    — Display active material properties
│  3  │ ➕ Add Custom Material      — Define and save a new material
│  4  │ 🗑️  Delete Custom Material  — Remove a user-defined material
│  5  │ ⬅️  Return to Main Menu
```

---

## Step 5 — Deflected Beam Animation in PyVista

### What It Is

Currently the PyVista 3D viewer (`pyvista_plotting.py`) shows a single static result:
either the deflected shape coloured by displacement magnitude, or a force/stress contour
on the undeflected mesh. This step adds a **load-step animation** that shows the beam
transitioning from its unloaded (straight) state to its fully loaded (deflected) state,
while simultaneously mapping the corresponding intermediate scalar field (shear force,
bending moment, stress, or deflection magnitude) as a colour contour.

The animation includes a **Play / Stop** button widget and a **scrubber slider** so the
user can manually step through frames. A **load factor** label (0% → 100%) updates at
each frame. Screenshots of the animation can be exported as a PNG sequence or a GIF.

### Why It Matters

Static contour plots are technically correct but hard to communicate to non-engineers.
Watching the beam physically bow under increasing load while the colour map shifts from
blue to red at the critical section is immediately intuitive. In a pharmaceutical plant
context, showing equipment support beams progressively loading under a pharmaceutical
vessel filling with liquid is far more compelling in an engineering report than a static
snapshot.

### Which Files Are Affected

| File | Change Type | Description |
|------|-------------|-------------|
| `src/plotting/pyvista_plotting.py` | Add new function | `PyVista_animation()` |
| `src/plotting/pyvista_plotting.py` | Add new class | `AnimationPlotter` |
| `src/ui/Menus.py` | Modify | `pyvista_menu()` — add option `9` for Animation |
| `src/ui/cli.py` | Modify | Add `pv_choice == '9'` branch in the PyVista submenu |

### How the Animation Works

The animation is frame-based. `N_FRAMES = 60` is the default (configurable). For frame
`k` (where `k` goes from `0` to `N_FRAMES - 1`):

- **Load factor** `α = k / (N_FRAMES - 1)` — ranges from `0.0` to `1.0`
- **Deflected Y-position** at each point = `polygon_y + α × defl_visual[i]`
  (linearly interpolating between the straight beam and the fully deflected shape)
- **Scalar field value** at each point = `α × scalar_at_point`
  (the colour map scales proportionally with the load factor)

This linear interpolation is physically correct for linear-elastic analysis (which
AltruxIQ exclusively performs), where all responses scale linearly with load.

### New Class `AnimationPlotter`

```python
class AnimationPlotter:
    """
    Extends ProbingPlotter to add frame-by-frame animation of load application.

    Parameters
    ----------
    mesh_frames : list[pv.PolyData]
        N_FRAMES meshes with progressively scaled geometry and scalars.
    scalar_name : str
        The point data key to colour the mesh by.
    title : str
        Result name shown in the overlay.
    units : str
        Display unit label (e.g., "N", "MPa").
    result_kind : str
        Colour map selector — "stress", "force", "moment", "displacement".
    fps : int
        Target playback speed in frames per second (default: 24).
    """

    def build(self):
        # 1. Creates the plotter (_make_plotter)
        # 2. Adds the first frame mesh
        # 3. Adds VTK slider widget for scrubbing (0 to N_FRAMES-1)
        # 4. Adds Play/Stop button using vtkButtonWidget
        # 5. Adds load factor text overlay (e.g., "Load: 0%")
        # 6. Registers a timer callback for playback
        # 7. Adds MAX/MIN caption actors (updates each frame)

    def _on_play_stop(self, obj, event):
        # Toggles self._playing flag
        # Starts/stops vtkRenderWindowInteractor timer

    def _on_timer(self, obj, event):
        # Advances self._current_frame
        # Swaps the mesh point coordinates and scalars
        # Updates load factor label
        # Calls plotter.render()

    def _update_frame(self, frame_idx: int):
        # Core update: swap geometry and scalars from self.mesh_frames[frame_idx]
        # Updates the scalar bar range
        # Refreshes MAX/MIN caption positions

    def export_gif(self, filepath: str, fps: int = 24):
        # Renders each frame offscreen and writes to GIF using imageio
```

### Frame Generation — `_build_animation_frames()`

This is a standalone helper function (not a method) that pre-builds all `N_FRAMES` meshes
before the plotter opens. This avoids stuttering during playback.

```python
def _build_animation_frames(
    X_Field, Deflection, beam_length, shape, section_dims, c, b,
    scalar_field, scalar_name, n_frames=60, units=None
) -> list[pv.PolyData]:
    """
    Pre-computes N_FRAMES PyVista meshes for animation.
    Each frame applies load_factor = k/(n_frames-1) to both geometry and scalars.
    """
    frames = []
    l_div = get_divisor(units, "length")
    X_vis, defl_vis = _downsample_for_visuals(X_Field / l_div, Deflection, target_fraction=0.1)
    _, scalar_vis  = _downsample_for_visuals(X_Field / l_div, scalar_field, target_fraction=0.1)

    max_defl = float(np.max(np.abs(defl_vis)))
    visual_scale = min(((c / l_div) * 6.0) / max_defl, 50.0) if max_defl > 0 else 1.0
    defl_visual = defl_vis * visual_scale

    polygon = _build_cross_section_polygon(shape, section_dims, c / l_div, b / l_div)

    for k in range(n_frames):
        alpha = k / (n_frames - 1)
        # Scale geometry
        pts_k, scalars_k = _build_deflected_frame_mesh(
            X_vis, polygon, defl_visual, scalar_vis, scalar_name, alpha
        )
        mesh_k = pv.PolyData(pts_k, ...)   # same face topology every frame
        mesh_k.point_data[scalar_name] = scalars_k * alpha
        frames.append(mesh_k)

    return frames
```

### New Public API Function `PyVista_animation()`

```python
def PyVista_animation(
    X_Field, Deflection, Total_ShearForce, Total_BendingMoment,
    ShearStress, BendingStress, beam_length, shape, section_dims,
    c, b, result_to_animate="ShearForce", n_frames=60, fps=24, units=None
):
    """
    Opens an interactive animation of load application on the 3D beam model.

    Parameters
    ----------
    result_to_animate : str
        Which scalar field to animate: "ShearForce", "BendingMoment",
        "ShearStress", "BendingStress", or "Deflection".
    n_frames : int
        Number of interpolation steps from zero to full load. Default: 60.
    fps : int
        Playback target speed. Default: 24.
    """
```

### Menu Changes

In `pyvista_menu()` (`Menus.py`), add:

```
│  9  │ 🎬 Load Animation     — Watch beam deflect under increasing load
│ 10  │ ⬅️  Return to Postprocessing Menu
```

Before opening the animation, prompt which scalar to animate alongside the deflection:

```
┌─ SELECT ANIMATION SCALAR ──────────────────────────────────
│  1  │ Shear Force     — SFD colour mapping during load
│  2  │ Bending Moment  — BMD colour mapping during load
│  3  │ Shear Stress    — Stress contour during load (requires stress calc)
│  4  │ Bending Stress  — Stress contour during load (requires stress calc)
│  5  │ Deflection Only — Magnitude of displacement only
└────────────────────────────────────────────────────────────
```

### Export Option

After the animation closes (window is shut), ask:
```
Export animation as GIF? (Y/N):
→ Enter filename (without extension):
```

GIF export uses `imageio` (add to `requirements.txt`). The output goes to a new
`exports/` folder alongside `screenshots/`.

---

## Step 6 — Restructured Project Layout for Multi-Analysis Expansion

### What It Is

The current `src/` directory structure groups everything by technical layer (solver,
plotting, ui, database) rather than by analysis type. This works well when there is only
one analysis type (beams), but becomes unmanageable when truss analysis, 2D frame
analysis, or plate elements are added later — all these types would share the same
`plotting/` and `ui/` folders, turning them into monolithic files with hundreds of
conditionals.

This step defines a **new directory structure** that organises code first by analysis
domain, with a `common/` layer for genuinely shared infrastructure, and a `visualization/`
layer that is shared across all domains. The existing beam code migrates into a `beam/`
sub-package with minimal changes to internal logic.

### Why It Matters

Adding truss analysis in a flat structure means either adding more branches to `cli.py`
(which is already 1,000+ lines) or creating a separate `truss_cli.py` that duplicates
the project management, unit system, and save/load infrastructure. Neither is sustainable.
The proposed structure makes each analysis domain self-contained while sharing common
infrastructure, exactly the same architectural pattern used by major FEA packages like
OpenSees and FEniCS.

### Proposed Directory Structure

```
altruxiq/                        ← project root (rename from src/)
│
├── main.py                      ← Entry point; routes to beam/truss/frame CLI
│
├── common/                      ← Shared across ALL analysis domains
│   ├── __init__.py
│   ├── units.py                 ← get_divisor(), METRIC_LABELS, IMPERIAL_LABELS
│   │                               (extracted from Menus.py)
│   ├── materials.py             ← MaterialDatabase class + custom material logic
│   │                               (extracted from database/materials_database.py)
│   ├── sections.py              ← SectionsDatabase class (new — Step 2)
│   ├── project_io.py            ← save_project(), load_project(), NumpyEncoder
│   │                               (extracted from cli.py)
│   └── utils.py                 ← safe_serialize(), path helpers, termcolor wrappers
│
├── beam/                        ← All beam-specific code
│   ├── __init__.py
│   ├── beam_cli.py              ← run_beam_menu() — the existing run_extended_menu()
│   │                               stripped of common infrastructure
│   ├── beam_inputs.py           ← Beam_Classification(), Beam_Length(), Beam_Supports(),
│   │                               define_continuous_supports(), define_custom_supports()
│   │                               manage_loads() (from inputs.py)
│   ├── beam_menus.py            ← All display_* and *_menu() functions specific to beam
│   │                               (from Menus.py, beam-specific portions)
│   ├── solver/
│   │   ├── __init__.py
│   │   ├── indeterminate.py     ← renamed from indeterminate_solver.py
│   │   ├── legacy.py            ← renamed from main_solver.py (kept for reference)
│   │   ├── moi.py               ← renamed from moi_solver.py
│   │   └── stress.py            ← renamed from stress_solver.py
│   └── sections/                ← Cross-section standard library data (Step 2)
│       ├── IPE.json
│       ├── HEA.json
│       ├── HEB.json
│       ├── SHS.json
│       ├── RHS.json
│       └── W_sections.json
│
├── truss/                       ← Future: 2D/3D truss analysis (stub)
│   ├── __init__.py
│   ├── truss_cli.py             ← run_truss_menu() — not yet implemented
│   ├── truss_inputs.py
│   └── solver/
│       ├── __init__.py
│       └── direct_stiffness.py  ← Truss direct stiffness method
│
├── frame/                       ← Future: 2D frame analysis (stub)
│   ├── __init__.py
│   ├── frame_cli.py             ← run_frame_menu() — not yet implemented
│   ├── frame_inputs.py
│   └── solver/
│       ├── __init__.py
│       └── frame_stiffness.py   ← 2D frame stiffness method
│
├── visualization/               ← Shared visualization for all analysis types
│   ├── __init__.py
│   ├── plotly/
│   │   ├── __init__.py
│   │   ├── beam_plots.py        ← All Plotly_* functions (from main_plotting.py)
│   │   └── schematic.py        ← plot_beam_schematic, plot_reaction_diagram
│   │                               (from beam_plot.py)
│   ├── matplotlib/
│   │   ├── __init__.py
│   │   └── beam_plots.py        ← All Matplot_* functions (from main_plotting.py)
│   ├── pyvista/
│   │   ├── __init__.py
│   │   ├── beam_3d.py           ← All PyVista_* functions (from pyvista_plotting.py)
│   │   ├── probing.py           ← ProbingPlotter class
│   │   └── animation.py         ← AnimationPlotter class (Step 5)
│   └── helpers/
│       ├── __init__.py
│       ├── plotly_shapes.py     ← draw_beam, draw_support, etc. (from plotting_helper.py)
│       └── formatting.py        ← format_plotly_sci, format_matplot_sci, find_critical_points
│
├── database/                    ← All persistent data files
│   ├── materials/
│   │   ├── standard.json        ← renamed from data/materials.json
│   │   └── custom.json          ← auto-created for Step 4
│   ├── sections/
│   │   ├── standard/            ← IPE.json, HEA.json, etc. for Step 2
│   │   └── custom.json          ← auto-created for Step 2
│   └── projects/
│       └── beam_projects.json   ← moved from project root
│
└── ui/                          ← Top-level UI: main menu and domain routing
    ├── __init__.py
    ├── main_menu.py             ← Top-level domain selector (Beam / Truss / Frame)
    └── shared_menus.py          ← Unit system menu, project management menus
                                    shared across all domains
```

### Migration Plan — What Moves Where

The goal is zero change to internal logic during the migration. Only imports and file
locations change. The following table maps each current file to its new location:

| Current File | New Location | Notes |
|---|---|---|
| `src/ui/cli.py` | `altruxiq/beam/beam_cli.py` | Rename `run_extended_menu` → `run_beam_menu` |
| `src/ui/Menus.py` (beam-specific functions) | `altruxiq/beam/beam_menus.py` | `display_analysis_results`, `display_stress_analysis`, etc. |
| `src/ui/Menus.py` (unit helpers) | `altruxiq/common/units.py` | `get_divisor`, `get_inverse_multiplier`, unit dicts |
| `src/ui/Menus.py` (print helpers) | `altruxiq/common/utils.py` | `print_error`, `print_success`, `clear_screen` |
| `src/ui/inputs.py` | `altruxiq/beam/beam_inputs.py` | All input functions |
| `src/solver/indeterminate_solver.py` | `altruxiq/beam/solver/indeterminate.py` | Internal logic unchanged |
| `src/solver/main_solver.py` | `altruxiq/beam/solver/legacy.py` | Internal logic unchanged |
| `src/solver/moi_solver.py` | `altruxiq/beam/solver/moi.py` | Internal logic unchanged |
| `src/solver/stress_solver.py` | `altruxiq/beam/solver/stress.py` | Internal logic unchanged |
| `src/database/materials_database.py` | `altruxiq/common/materials.py` | Extended per Step 4 |
| `src/plotting/main_plotting.py` | Split: `altruxiq/visualization/plotly/beam_plots.py` + `altruxiq/visualization/matplotlib/beam_plots.py` | |
| `src/plotting/beam_plot.py` | `altruxiq/visualization/plotly/schematic.py` | |
| `src/plotting/plotting_helper.py` | `altruxiq/visualization/helpers/plotly_shapes.py` | |
| `src/plotting/pyvista_plotting.py` | `altruxiq/visualization/pyvista/beam_3d.py` + `probing.py` | |
| `data/materials.json` | `altruxiq/database/materials/standard.json` | |
| `beam_projects.json` (project root) | `altruxiq/database/projects/beam_projects.json` | Update path resolution |

### `main.py` — Top-Level Entry Point

```python
#!/usr/bin/env python3
"""
AltruxIQ — Structural Analysis Suite
Entry point. Routes to the appropriate analysis domain.
"""
from ui.main_menu import run_main_menu

if __name__ == "__main__":
    run_main_menu()
```

`run_main_menu()` displays:

```
╔══════════════════════════════════════════════════════════════╗
║               AltruxIQ — Structural Analysis                 ║
╚══════════════════════════════════════════════════════════════╝

┌─ SELECT ANALYSIS TYPE ──────────────────────────────────────
│  1  │ 🏗️  Beam Analysis      — 1D beam FEA (active)
│  2  │ 🔩  Truss Analysis     — 2D/3D pin-jointed trusses (coming soon)
│  3  │ 🏢  Frame Analysis     — 2D rigid frame analysis (coming soon)
│  0  │ 🚪  Exit
└─────────────────────────────────────────────────────────────
```

Options 2 and 3 display a "Feature not yet available" message rather than crashing,
so the structure is in place before the implementation is complete.

### Path Resolution After Migration

The `Path(__file__).resolve()` navigation pattern used in `MaterialDatabase` will need
updating. After migration, `standard.json` is at `altruxiq/database/materials/standard.json`.
The new resolution from `altruxiq/common/materials.py`:

```python
project_root = Path(__file__).resolve().parent.parent  # altruxiq/ root
db_path = project_root / "database" / "materials" / "standard.json"
```

The same pattern applies to `sections_database.py`, custom materials, and projects.

### Import Path Convention After Migration

All cross-module imports use absolute paths from the `altruxiq/` root, enabled by adding
`altruxiq/` to `sys.path` in `main.py`. The path injection blocks currently scattered
across every file (`sys.path.insert(0, src_dir)`) are eliminated — they are replaced by
a single path setup in `main.py`:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
```

Every module then imports cleanly:
```python
from common.units import get_divisor, METRIC_LABELS
from beam.solver.indeterminate import solve_beam
from visualization.pyvista.beam_3d import PyVista_shear_force
```

### Backward Compatibility for Saved Projects

The `beam_projects.json` file moves to `altruxiq/database/projects/`. The new
`project_io.py` module resolves this path via the same `Path(__file__)` pattern.
Old project files at the project root are automatically detected and migrated on first
run, with a one-time notice to the user.

---

## Implementation Priority

Based on development effort, user impact, and dependency between steps:

| Priority | Step | Effort | Impact | Depends On |
|----------|------|--------|--------|------------|
| 1 | Step 3 — Solver Resolution | Low | High (immediate UX) | Nothing |
| 2 | Step 4 — Custom Materials | Medium | High (daily use) | Nothing |
| 3 | Step 1 — Custom Beam Classification | Medium | High (engineering flexibility) | Nothing |
| 4 | Step 2 — Section Library | High | High (professional workflow) | Step 4 patterns |
| 5 | Step 5 — PyVista Animation | High | Medium (presentation quality) | Nothing |
| 6 | Step 6 — Restructure | High | Critical (long-term) | All steps done |

Steps 1, 3, and 4 are independent and can be developed in parallel. Step 6
(restructuring) should be the **last** step because it changes import paths across
every file — doing it after all features are stable minimises merge conflicts.

---

*This roadmap reflects the codebase state as documented in `AGENT_BRIEFING.md`. Any
agent implementing a step should re-read the relevant sections of the briefing before
writing code, particularly the Data Structures (Section 5), the Analysis Pipeline
(Section 10), and the Known Bugs (Section 14).*
