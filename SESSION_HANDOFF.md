# AltruxIQ — Session Handoff & Continuation Brief

> **Purpose**: One-shot context for a new agent session to resume work without
> re-reading the full history.
> **Last session**: Phase 2 foundation modules (A config, B exceptions pass 1,
> C units cleanup) — **Phase 2 COMPLETE**.
> **Date**: 2026-07-09.

---

## 1. Project context (read first)

AltruxIQ is a Python CLI structural beam FEA tool. Authoritative references:

- **`AGENT_BRIEFING.md`** — full technical reference (v3). Read sections 1–5, 9, 14, 16.
- **`AltruxIQ Architecture Audit.md`** *(on Desktop)* — root-cause analysis with concrete
  code deliverables in §4. This is the roadmap for refactoring.
- Entry point: `python src/ui/cli.py`. The entire session state is ~30 module-level
  globals in `cli.py::run_extended_menu()` — there is no session object yet.

**Key architectural facts that catch agents out:**
- `cli.py` cannot be `import`ed in a bare environment: it depends on `indeterminatebeam`
  (external FEA package) which is **not installed in the agent's sandbox Python**. To verify
  `cli.py` changes, use **AST checks** (`ast.parse` + walk for imports/calls), not runtime
  imports. All other modules *can* be runtime-tested (numpy/scipy/plotly/matplotlib/termcolor present).
- The codebase stores everything in base SI; conversion happens only at display boundaries
  via `common.units.get_divisor()` / `to_si()`, and at the JSON-persistence boundary via
  `common.units.to_json()` / `from_json()` (materials JSON stores MPa/GPa, not base-SI Pa).
- The **`common/` package** is the foundation layer. Three single-source-of-truth modules
  live there now: `paths.py`, `config.py`, `units.py`, `exceptions.py`. Any new magic number,
  unit factor, or domain exception belongs here — never inline.

---

## 2. What was accomplished

### Phase 1 — Bug Stabilization (COMPLETE, all committed in an earlier session)

All 7 confirmed bugs from the briefing §14.2 are fixed. Per-bug commits: `ea12618`, `bd48e3c`,
`189cd05`, `2d44759`, `9d56bf9`, `f5e25d2`, `38a2a1f`. See git log / briefing §14 for detail.

### Phase 2 — Foundation modules (COMPLETE this session)

All three root-cause foundation modules from audit §4 are done. Per-module commits:

| Commit | Module | What |
|--------|--------|------|
| `dc21a2f` | **(A) `common/config.py`** | Two frozen dataclasses: `SolverDefaults` (`DEFAULT/MIN/MAX_NUM_POINTS`, `MIN_LOAD_SUBDIVISIONS`, `FALLBACK_STEEL_E_PA/I_M4`) and `ServiceabilityLimits` (L/180, L/240, L/360, L/480, L/500 denominators + `TARGET_FACTOR_OF_SAFETY`). Exposed as `SOLVER` / `SERVICEABILITY` singletons. Migrated all duplicated literals across `indeterminate_solver.py`, `stepped_solver.py`, `inputs.py`, `cli.py`, `Menus.py` (the 240/360/480 DRY violation in two Menus.py functions was the core fix). |
| `d4ff036` | **(B) `common/exceptions.py` — pass 1** | 6-class `AltruxIQError` hierarchy per audit §4.3. Migrated moi_solver (8 raise sites → `SectionGeometryError`; 8 `except Exception` narrowed to `(SectionGeometryError, ValueError, TypeError, EOFError)`) and stepped_solver (7 structural raises → `ValidationError`; singular-matrix raise → `SingularStiffnessMatrixError`). **cli.py narrowing deferred — see §3.** |
| `66f5e52` | **(C) units adoption cleanup** | Deleted `moi_solver.get_moi_scale()` parallel engine (8 callers → `get_divisor`). Added `'area'` quantity to `units.py`. Added `_JSON_FACTORS` dict + `to_json`/`from_json` helpers; replaced `inputs.py::define_custom_material` hardcoded `16.01846`/`6.894757`/`0.006894757` (fixed a truncation bug: old literals were 7-digit roundings of `6.89475729`/`0.00689475729`). Deleted dead `get_inverse_multiplier()` from `Menus.py`. |

**Verification standard used throughout**: every change got (1) `ast.parse`, (2) a runtime
or AST test proving the fix, (3) a stale-literal audit (grep for the old pattern). All
Phase 2 commits passed this bar.

---

## 3. What REMAINS to do

### Phase 2-B — exceptions.py adoption (pass 2+ of N, IN PROGRESS)

Pass 1 (above) established the hierarchy and migrated the two solver clusters. The broader
goal is narrowing the **78 bare `except Exception` blocks** across `src/` so genuine
programming bugs (`AttributeError`/`KeyError`/`NameError`) stop being masked as user errors.
Distribution: `pyvista_plotting.py` 30 · `cli.py` 26 · `moi_solver.py` 0 (done) ·
`inputs.py` 5 · `export_helper.py` 3 · `main_plotting.py` 2 · `Menus.py` 2 · others.

**Recommended next passes (in order):**

1. **cli.py solve handler** (`src/ui/cli.py:~1676`, "Error solving beam"). Narrow from
   `except Exception` to `(ValidationError, SingularStiffnessMatrixError, AltruxIQError)`
   so the new hierarchy from pass 1 actually starts filtering at the CLI layer. AST-only
   verification (cli.py can't runtime-import). This is the single highest-value handler.
2. **inputs.py** — 5 blocks: 4 `manage_loads` float-parsing (`float(input())` → catch
   `ValueError` specifically) at lines ~537/584/624/675, plus 1 `area_from_section` call
   at ~1006. Runtime-testable.
3. **pyvista_plotting.py** — 30 blocks but mostly intentional VTK-callback defense (17 are
   `_log.debug`, 11 are bare `pass`/default-value). Low priority; leave alone unless explicitly
   asked. Only the 2 `print_error` GIF/PNG export blocks (~1516/1522) are real candidates.
4. **PersistenceError adoption** — `exceptions.py` defines `PersistenceError` but no code
   raises it yet. Add it to the save/load paths in `cli.py` (`save_projects_to_disk` ~602,
   `load_project` ~184, `delete_project` ~466) when those handlers are narrowed.

### Phase 3 — Large refactors (DEFERRED, do NOT start without explicit approval)

- **`core/state.py` — ProjectState dataclass** (audit §4.5): replaces cli.py's ~30 globals.
  Audit calls this the "single highest-leverage change" but it's a large `cli.py` rewrite.
  Only attempt after Phase 2-B is further along + a test harness exists.
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
- `moi_solver.print_derived_properties()` (non-tbeam path) still hardcodes "m²"/"m³" strings
  and ignores its `units` param — pre-existing display inconsistency, left intentionally in 2-C.

---

## 4. Working conventions established

- **Per-module checkpoints**: user reviews after each module. Ask before starting each step.
- **Verification standard**: every change gets (1) `ast.parse` syntax check, (2) a runtime
  or AST test proving the fix, (3) a stale-literal audit (grep for the old pattern).
- **`cli.py` verification caveat**: cannot runtime-import (missing `indeterminatebeam` in
  sandbox). Use AST walks to verify imports/calls instead. All other modules are runtime-testable.
- **`common/` is the foundation layer**: new magic numbers → `common/config.py`; new unit
  factors → `common/units.py`; new domain exceptions → `common/exceptions.py`; new paths →
  `common/paths.py`. Never inline these.
- **Always present options + recommendation** before starting a step, per user's standing request.
- Commit message style: conventional commits (`refactor(config):`, `refactor(exceptions):`,
  `refactor(units):`, `fix(cli):`, `feat(plotting):`).

---

## 5. Resume instruction for the new session

1. Read this file + `AGENT_BRIEFING.md` §1–5,9,14.
2. **At the start, ask the user this exact question** (they requested it):
   > "Phase 2 (foundation modules) is complete. Where should we continue?
   > - **(B-pass2) cli.py solve-handler narrowing** *(Recommended — single highest-value
   >   `except Exception` block; makes the Phase 2-B exception hierarchy actually filter
   >   bugs at the CLI layer. AST-only verification.)*
   > - **(B-pass2) inputs.py block narrowing** *(5 blocks, runtime-testable: 4 manage_loads
   >   float-parsing + 1 area_from_section call)*
   > - **(Phase 3) ProjectState dataclass** *(large cli.py rewrite — needs explicit approval;
   >   audit calls it highest-leverage but biggest scope)*
   > - **Known-issue fix** *(e.g. num_points persistence, equilibrium check, indeterminate_solver
   >   if/if/elif)*"
3. Proceed per-module with checkpoints, same as Phase 1 & 2.
