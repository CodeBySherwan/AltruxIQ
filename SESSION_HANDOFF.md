# AltruxIQ — Session Handoff & Continuation Brief

> **Purpose**: One-shot context for a new agent session to resume work without
> re-reading the full history.
> **Last session**: Phase 2-B exceptions adoption (pass 2) — narrowed 27 bare
> `except Exception` blocks across 5 modules + cli.py (78 → 53 remaining).
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

### Phase 2-B — exceptions.py adoption (pass 2, COMPLETE this session)

Narrowed 27 bare `except Exception` blocks so genuine programming bugs
(`AttributeError`/`KeyError`/`NameError`) propagate instead of being masked as user errors.
Total across `src/`: **78 → 53**. Per-commit:

| Commit | What |
|--------|------|
| `8ace76b` | **Prerequisite migrations + cli.py solve handler.** `indeterminate_solver.py:75` unknown-beam-type `ValueError` → `ValidationError`; `area_solver.py` 10 section-dimension `ValueError` → `SectionGeometryError` (found to be reachable via stepped_solver inside the solve try-block — migrating first avoided a regression). cli.py solve handler (~1676) → `(ValidationError, SingularStiffnessMatrixError, AltruxIQError)`; first `PersistenceError` adoption at `save_projects_to_disk` (~602) → `(OSError, PersistenceError)`. AST-only (cli.py). |
| `3ecf7ff` | **inputs.py** fully cleared (5 → 0): 4 `manage_loads` float-parsing guards → `(ValueError, EOFError)`; `area_from_section` guard → `(SectionGeometryError,)` — the end-to-end payoff of the area_solver migration. AST + runtime hierarchy verified. |
| `0a41a89` | **Persistence branch complete + date guards.** `delete_project` (~506) → `(OSError, PersistenceError)` (PersistenceError now at both write sites); `load_project:232` + `print_loaded_project_summary:382` → `(ValueError, TypeError)` (these guard `datetime.fromisoformat`, not persistence — honest narrowing rather than forcing PersistenceError). `load_projects_from_disk` was already well-narrowed, left alone. cli.py 24 → 21. AST-only. |
| `4091624` | **Quick-wins bundle** — cleared 3 modules: `export_helper.py` (3 → 0: import→`ImportError`, HTML/PNG writes→`OSError`), `main_plotting.py` (2 → 0: import fallbacks→`ImportError`), `Menus.py` (2 → 0: `isatty()`→`AttributeError`, ANSI writes→`(OSError, ValueError)`). Menus.py runtime-tested (isatty AttributeError path returns False as before). |

---

## 3. What REMAINS to do

### Phase 2-B — exceptions.py adoption (COMPLETE except for PyVista)

Pass 3 cleared all 21 remaining blocks in `cli.py` across 3 commits (`fe4003a`, `ea402dd`, `f03c5ad`).
- **Added `SectionGeometryError` to cli.py imports** — payoff of the pass 2 `area_solver` migration.
- **Added `EOFError`** — all postprocessing handlers that prompt for style choice now catch `EOFError` for piped/closed stdin.
- **Added `RuntimeError` on PyVista wrapper** — VTK/GPU windowing failures surface as `RuntimeError`.
- **Added `PersistenceError` on save handler** — completes the adoption at all 3 persistence-related sites in cli.py.

Pass 4 cleared the final quick wins in `beam_plot.py` and `plotting_helper.py` (both were import fallbacks narrowed to `ImportError`).

Total across `src/`: **53 → 30**. 

**Recommended next steps:**

1. **pyvista_plotting.py** — 28 blocks remain. **NOTE:** These remaining blocks are entirely intentional VTK-callback defense (e.g. `_log.debug` handlers inside VTK events, or bare `pass`/default-value logic to prevent the C++ event loop from crashing on bad data). Do not touch them. The two genuine targets (GIF/PNG export blocks) were cleared in pass 4. Phase 2-B is now 100% complete for all actionable blocks.
2. **Phase 3 — known-issue fixes.** See "Known-issue fixes" below.
3. **Phase 3 — `ProjectState` dataclass refactor.** See "ProjectState dataclass refactor" below.

**Lessons from pass 2 (carry forward):**
- Before narrowing a handler, **trace what's reachable inside its try-block** — pass 2 found
  `area_solver.py` `ValueError`s reachable via `stepped_solver` inside the solve handler;
  migrating them first avoided a regression.
- The handoff's line-number pointers are approximate; always read in context. Pass 2 found
  the "~184 PersistenceError" pointer actually pointed at `fromisoformat` guards (a `ValueError`
  class), not persistence.
- After every Edit, re-read the changed lines before verifying — pass 2 caught an accidental
  f-string prefix drop (`f"...{e}"` → `"...{e}"`) that would have silently broken error
  display; `git show HEAD:file` confirms originals when in doubt.

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
   > "Phase 2-B pass 2 is complete (78 → 53 bare `except Exception`). Where next?
   > - **(B-pass3) Continue cli.py** *(Recommended — 21 blocks remain, the largest remaining
   >   module. AST-only verification. Triage each nested menu handler in context first.)*
   > - **(B-pass3) beam_plot.py + plotting_helper.py** *(1 block each, runtime-testable quick
   >   wins — clears two more modules)*
   > - **(B-pass3) pyvista_plotting.py GIF/PNG export handlers** *(the 2 real candidates among
   >   its 30 defensive VTK-callback blocks, ~lines 1516/1522)*
   > - **(Phase 3) ProjectState dataclass** *(large cli.py rewrite — needs explicit approval)*
   > - **Known-issue fix** *(num_points persistence, equilibrium check, indeterminate_solver
   >     if/if/elif)*"
3. Proceed per-module with checkpoints, same as Phase 1 & 2.
