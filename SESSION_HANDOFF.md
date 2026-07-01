# AltruxIQ — Session Handoff & Continuation Brief

> **Purpose**: One-shot context for a new agent session to resume Phase 2 of the
> stabilization/foundation work without re-reading the full history.
> **Last session**: Bug stabilization (Phase 1) + paths.py centralization (Phase 2 start).
> **Date**: 2026-07-01.

---

## 1. Project context (read first)

AltruxIQ is a Python CLI structural beam FEA tool. Authoritative references:

- **`AGENT_BRIEFING.md`** — full technical reference (v3). Read sections 1–5, 9, 14, 16.
- **`AltruxIQ Architecture Audit.md`** *(on Desktop)* — root-cause analysis with concrete
  code deliverables in §4. This is the roadmap for Phase 2.
- Entry point: `python src/ui/cli.py`. The entire session state is ~30 module-level
  globals in `cli.py::run_extended_menu()` — there is no session object yet.

**Key architectural facts that catch agents out:**
- `cli.py` cannot be `import`ed in a bare environment: it depends on `indeterminatebeam`
  (external FEA package) which is **not installed in the agent's sandbox Python**. To verify
  `cli.py` changes, use **AST checks** (`ast.parse` + walk for imports/calls), not runtime
  imports. Plotting/database code *can* be runtime-tested (numpy/scipy/plotly/matplotlib present).
- The codebase stores everything in base SI; conversion happens only at display boundaries
  via `common.units.get_divisor()` / `to_si()`.
- `units.py` centralization is DONE (recent "new Units engine" commit). `paths.py`
  centralization is DONE (last commit this session).

---

## 2. What was accomplished in the last session

### Phase 1 — Bug Stabilization (COMPLETE, all committed)

All 7 confirmed bugs from the briefing §14.2 are fixed. Per-bug commits:

| Commit | Bug | Fix |
|--------|-----|-----|
| `ea12618` | **Bug-13/12** — `run_extended_menu()` globals | Added `global` declarations for `num_points`, `X_Field`, `Total_ShearForce`, `Total_BendingMoment`, `Deflection`, `Slopes`, `Curvatures`, `Reactions`, `Shear_stress`, `bending_stress`, `FOS`, `segments`, `AxialForce`, `AxialDisplacement`. Fixed stale saves + `UnboundLocalError`. |
| `bd48e3c` | **export_helper NameError** | `_export_dir()` referenced undefined `project_root` → every Plotly export crashed. Fixed (now uses `DIAGRAM_EXPORT_DIR`). |
| `189cd05` | **Bug-11** — 3D FEA unreachable for non-Stepped | Added dynamic `fea_3d_choice`/`back_choice`; lifted `beam_type` guards into axial `elif`s. |
| `2d44759` | **Bug-14** + side-finding | `len_div` NameError in Overhanging BC; hardcoded "m" in View supports. Both use `get_divisor(current_labels, 'length')`. |
| `9d56bf9` | **Bug-15** — Shear_stress wrong shape | `n_y = len(segments[0]['y_array'])` instead of empty module-level `y_array`. |
| `f5e25d2` | **Bug-16** — Combined Stress TypeError | Removed extra `beam_length` positional arg from `Matplot_BendingStress` call. |
| `38a2a1f` | **Bug-17** — Axial plotting (full) | Added 3 SERIES keys + 6 plotting functions + extended `combined` funcs + cli dispatch. |

### Phase 2 — paths.py centralization (COMPLETE, committed `e1da67e`)

`common/paths.py` is now the single source of truth. Migrated 5 files off duplicated
`__file__`/`dirname` arithmetic. Fixed two side-effect bugs:
- "Run from wrong CWD" — `beam_projects.json` was CWD-relative; now `PROJECTS_FILE` (absolute).
- Cross-platform filename casing — `load_material_database()` passed `"Materials.json"`
  (relied on Windows case-insensitivity); now uses centralized lowercase default.

---

## 3. What REMAINS to do (Phase 2 + beyond)

### Phase 2 — Foundation modules (3 items left)

These are the root-cause fixes from audit §4. Do them in this order:

#### (A) `common/config.py` — magic-number constants  [RECOMMENDED NEXT]
Audit §4.4. Create `common/config.py` with two frozen dataclasses:
- `SolverDefaults`: `DEFAULT_NUM_POINTS=2001`, `MIN/MAX_NUM_POINTS`, `MIN_LOAD_SUBDIVISIONS=100`
  (bare literal in `stepped_solver.py`), `FALLBACK_STEEL_E_PA=210e9`, `FALLBACK_STEEL_I_M4=8.33e-6`
- `ServiceabilityLimits`: `ROOF_NO_CEILING=240.0`, `GENERAL_FLOOR=360.0`, `BRITTLE_FINISHES=480.0`,
  `TARGET_FACTOR_OF_SAFETY=1.50`
- The `240/360/480` denominators are **duplicated independently** in two `Menus.py` functions
  (`display_deflection_analysis` and `display_engineering_recommendations`) — this is the DRY
  violation to fix. Grep: `240\|360\|480` in `src/ui/Menus.py`.
- **Scope**: small, isolated, zero-risk pure extraction.

#### (B) `common/exceptions.py` — fail-fast hierarchy  [after config.py]
Audit §4.3. Create:
```python
class AltruxIQError(Exception): ...
class ValidationError(AltruxIQError): ...
class SectionGeometryError(ValidationError): ...
class SolverError(AltruxIQError): ...
class SingularStiffnessMatrixError(SolverError): ...
class PersistenceError(AltruxIQError): ...
```
Then:
- `stepped_solver.py` raises bare `ValueError` for singular matrix → `SingularStiffnessMatrixError`.
- Start narrowing the **~30 bare `except Exception as e:`** blocks in `cli.py` (grep:
  `except Exception` in `src/ui/cli.py`) that currently mask programming errors
  (`AttributeError`/`KeyError`) as user errors. This is the highest-value but largest-scope
  item — do it incrementally, don't try to fix all 30 at once.

#### (C) Units adoption cleanup  [last]
Audit §2. Three DRY violations:
- Delete `moi_solver.get_moi_scale()` (lines ~14–28) — parallel, incompatible unit engine.
  Replace its callers with `units.get_divisor(units, 'length')` / `'inertia'`.
- Fix `inputs.py::define_custom_material` hardcoded `16.01846`/`6.894757`/`0.006894757`
  (lines ~808–825) — add a storage-schema factor table to `units.py` per audit §4.2.
- Add `'area'` quantity to `units.py` `_SI_FACTORS` (audit §2.2 — `moi_solver.inertia_moment_tbeam`
  hand-rolls area/sec_mod divisors inconsistently: area in ft², modulus in in³).
- Delete deprecated `get_inverse_multiplier()` in `Menus.py` (zero callers).

### Phase 3 — Large refactors (DEFERRED, do NOT start without explicit approval)

- **`core/state.py` — ProjectState dataclass** (audit §4.5): replaces cli.py's ~30 globals.
  Audit calls this the "single highest-leverage change" but it's a large `cli.py` rewrite.
  Only attempt after Phase 2 + a test harness exists.
- **Module decomposition** (audit §3): split `Menus.py`/`inputs.py`/`cli.py` into
  `ui/console/` + `ui/beam/` packages. Mechanical but large.
- **Solver registry** (audit §5): replace `if beam_type ==` chains with a `@register` decorator.
- **Self-defeating sys.path bootstrap** in `cli.py:21-25`: fix by adding a project-root
  `run.py` entry point (changes launch contract — get approval first).
- **PyVista Stepped Bar**: `_build_beam_mesh()` uses single shape/section_dims; per-segment
  step-changes not rendered. Needs per-segment mesh stitching.

### Known minor issues (not crashes, low priority)
- `display_analysis_results()` equilibrium check only sums Va+Vb for Simple beams.
- `indeterminate_solver._build_supports()` uses `if`/`if`/`elif` (not `if`/`elif`/`elif`)
  for Simple vs Overhanging — works by coincidence, latent risk.
- `num_points` not persisted to saved projects despite the Bug-13 globals fix (separate issue).

---

## 4. Working conventions established this session

- **Per-bug checkpoints**: user reviews after each bug fix. Ask before starting each step.
- **Verification standard**: every change gets (1) `ast.parse` syntax check, (2) a runtime
  or AST test proving the fix, (3) a stale-literal audit (grep for the old pattern).
- **`cli.py` verification caveat**: cannot runtime-import (missing `indeterminatebeam` in
  sandbox). Use AST walks to verify imports/calls instead.
- **Always present options + recommendation** before starting a step, per user's standing request.
- Commit message style: conventional commits (`fix(cli):`, `feat(plotting):`, `refactor(paths):`).

---

## 5. Resume instruction for the new session

1. Read this file + `AGENT_BRIEFING.md` §1–5,9,14.
2. **At the start, ask the user this exact question** (they requested it):
   > "Which foundation module should Phase 2 continue with?
   > - **(A) `config.py` constants** *(Recommended — small, isolated, zero-risk extraction
   >   of the 240/360/480 deflection limits duplicated in Menus.py + solver defaults)*
   > - **(B) `exceptions.py` + fail-fast** *(create hierarchy, start narrowing ~30 bare
   >   `except Exception` blocks in cli.py — higher value, larger scope)*
   > - **(C) units adoption cleanup** *(delete moi_solver parallel engine, fix
   >   define_custom_material hardcoded conversions, add 'area' quantity)*"
3. Proceed per-bug/per-module with checkpoints, same as Phase 1.
