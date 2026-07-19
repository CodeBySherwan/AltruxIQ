# AltruxIQ — Session Handoff & Continuation Brief

> **Purpose**: One-shot context for a new agent session to resume work without
> re-reading the full history.
> **Last session**: P0 (correctness) **DONE**, P1 (dead-code cleanup) **DONE**,
> P2 (`units.py` API cleanup — both P2-1 and P2-2) **DONE**,
> **P3-checkpoints 1–4 DONE**: `console/` kit, `materials/selector.py`,
> `beam/` wizards (all merged — PRs #2, #3, #4), and `reports/` renderers
> (branch `refactor/p3-reports`, pending merge). **`ui/inputs.py` no longer
> exists**; `Menus.py` is down to navigation menus + `display_profile_info`
> (1677→843 lines). The **`cli ↔ inputs` circular-import cycle is
> permanently eliminated** (zero `from ui.cli import` statements in `src/`).
> **Bonus fix in checkpoint-4**: latent `NameError: get_divisor` (introduced
> by checkpoint-1's shim drop) found & repaired — see §P3-checkpoint-4.
> **P6 — unified stage-driven Stepped Bar APPROVED** (2026-07-19, see §P6):
> the `define_stepped_segments` monolith retires; Stepped Bar flows through
> the same main-menu stages as every other beam type. Queued after
> P3-checkpoint-5, before P4.
> Ready for **P3-checkpoint-5** (`menus/` + thin `cli.py`).
> **Date**: 2026-07-19.

---

## 1. Project context (read first)

AltruxIQ is a Python CLI structural beam FEA tool. Authoritative references:

- **`AGENT_BRIEFING.md`** — full technical reference (v3). Read sections 1–5, 9, 14, 16.
- Entry point: `python src/ui/cli.py`. Session state now lives in `core/state.py`
  (`ProjectState` dataclass, singleton `state`) — the ~30-globals problem from
  earlier phases is resolved.

**Key architectural facts that catch agents out:**
- `cli.py` cannot be `import`ed in a bare environment: it depends on `indeterminatebeam`
  (external FEA package), **not installed** in the agent's sandbox Python. Verify
  `cli.py` changes via **AST checks** (`ast.parse` + walk), not runtime imports. All
  other modules *are* runtime-testable (numpy/scipy/plotly/matplotlib/termcolor present).
- Everything is stored in base SI; conversion happens only at display boundaries via
  `common.units.get_divisor()` / `to_si()`, and at the JSON-persistence boundary via
  `common.units.to_json()` / `from_json()`.
- `common/` is the foundation layer: `paths.py`, `config.py`, `units.py`,
  `exceptions.py`. Any new magic number, unit factor, or domain exception belongs
  there — never inline.
- **Verification standard, unchanged**: every fix gets (1) `ast.parse` syntax check,
  (2) a runtime or AST test proving the fix, (3) a stale-literal/reference audit
  (grep for the old pattern).

---

## 2. Audit summary (this session)

A full pass was made over `paths.py`/`units.py` adoption, module cohesion in
`cli.py`/`Menus.py`/`inputs.py`, and future-proofing gaps (plugin points, solver
registry, settings vs. engineering constants). Headline result: **the path and
unit centralization is real and correctly adopted almost everywhere** — no
duplicate conversion tables or raw path arithmetic remain outside the items
listed below. The open items are integration debt (one live crash, one silent
wrong-output bug, several dead imports) plus a cohesion/scalability plan for the
three oversized UI modules.

---

## 3. Priority-ordered action list

Work top-to-bottom. **P0 items are correctness bugs — fix these before any
structural refactor**, since refactor plans should not be built on top of broken
code paths. P1 is fast cleanup. P2+ are the structural/scalability program.

### P0 — Correctness bugs  ✅ DONE & VERIFIED (2026-07-11)

#### P0-1 — CRASH: `ui/inputs.py` imports a global that no longer exists  ✅ FIXED

**File**: `src/ui/inputs.py`, inside `define_stepped_segments()`.

**Fix applied** (`src/ui/inputs.py`, material-selection block): replaced
`from ui.cli import select_material, load_material_database, Materials` with
`from core.state import state` + `from ui.cli import select_material,
load_material_database`, and changed the guard from `if Materials is None:` to
`if state.Materials is None:`. `select_material`/`load_material_database` stay
imported from `ui.cli` for now (structural move deferred to P3
`ui/materials/selector.py`, which closes the root cause permanently).

**Verified**: AST-walk confirms no `from ui.cli import ... Materials` remains;
`ProjectState.Materials` exists and defaults to `None`; `MaterialDatabase()`
constructs and loads 73 entries; the `state.Materials = MaterialDatabase()`
assignment the guard performs works. `test_stepped_solver.py` regression suite
still green (8/8).

#### P0-2 — SILENT WRONG OUTPUT: `display_engineering_recommendations` ignores unit system  ✅ FIXED

**File**: `src/ui/Menus.py::display_engineering_recommendations` + `src/ui/cli.py` call site.

**Scope note (expanded at fix time)**: the audit listed 4 hardcoded SI literals
(span length, I, S, depth in the "MODEL & SECTION SUMMARY" block). Two more of
the **same bug class** were found in the "PRIORITISED RECOMMENDED ACTIONS" block:
the `s_req` (section-modulus target) and `i_req` (inertia target) recommendation
strings also printed raw SI with hardcoded `m³`/`m⁴`. All 7 literals were fixed
together — leaving the 2 recommendation-target strings in SI would have meant an
Imperial user still gets wrong sizing targets.

**Fix applied**:
- Added `units=METRIC_UNITS` kwarg to the signature.
- Added three divisors at function entry: `len_div`, `inertia_div`, `sec_mod_div`
  via `get_divisor(units, ...)`.
- Converted all 7 literals to `/div` + `units[...]` label (both the Stepped Bar
  `beam_length` line and the non-stepped branch).
- `cli.py` call site (`selection == '11'`) now passes `units=state.current_labels`.

**Verified**: runtime test proves a 6.0 m beam prints `6.000 m` in Metric and
`19.685 ft` in Imperial (previously both printed `6.000 m`); section modulus
`3e-5 m³` prints `3.00e-05 m³` vs `1.83 in³`. AST audit confirms zero remaining
hardcoded SI length/inertia/sec-mod literals in the function body.

---

### P1 — Dead code / stale references (fast, no behavior change)  ✅ DONE & VERIFIED (2026-07-11)

**Completed**: P1-1, P1-2, P1-3, P1-5. **Deferred**: P1-4 (the `run.py`
entry-point refactor — handoff flagged it as "needs explicit approval, changes
the launch contract"; revisit when the user is ready). Commit group on
`fix/p0-correctness-bugs`: `chore(cleanup): remove dead imports + adopt
pathlib in pyvista_plotting` and `refactor(units): standardize on
METRIC_UNITS/IMPERIAL_UNITS everywhere`.

**Bonus**: `pyvista_plotting.py` also had an unused `import sys` (separate
from P1-1's files) — removed during P1-3.

#### P1-1 — Unused pre-centralization imports

- `src/solver/area_solver.py`: `import os`, `import sys` — unused anywhere in
  file, leftover from the pre-`paths.py` sys.path-injection pattern.
- `src/solver/stepped_solver.py`: same — `import os`, `import sys`, unused.

**Fix**: delete both import lines from each file. **Verify**: `ast.parse` +
confirm no `os.`/`sys.` usage remains in either file body.

#### P1-2 — Stale comment referencing removed code

`src/ui/inputs.py`, inside `define_stepped_segments()`:
```python
# Import needed modules (path injection is already done at top of inputs.py)
```
No path injection exists anywhere in `inputs.py`. Misleading for the next agent.
**Fix**: delete the comment (or replace with an accurate one noting imports are
local to avoid the P0-1-adjacent circular-import risk).

#### P1-3 — Two path idioms coexist in `pyvista_plotting.py`

`paths.py` constants (`Path` objects) are immediately stringified and rebuilt
with `os.path.join`/`os.makedirs`:
```python
_SCREENSHOT_DIR = str(SCREENSHOTS_DIR)
...
def _ensure_screenshot_dir() -> str:
    path = os.path.normpath(_SCREENSHOT_DIR)
    os.makedirs(path, exist_ok=True)
    return path
```
**Fix** — stay in `pathlib` throughout, since `paths.py` already committed to it:
```python
def _make_screenshot_path(name: str) -> Path:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    return SCREENSHOTS_DIR / f"{name}_{_timestamp()}.png"
```
Apply the same treatment to `_ensure_export_dir()` / `_EXPORT_DIR`.

#### P1-4 — Redundant `sys.path` bootstrap in `cli.py`

```python
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src not in sys.path:
    sys.path.insert(0, _src)
from common.paths import ensure_src_in_path, PROJECTS_FILE
...
ensure_src_in_path()   # no-op: the manual block above already did this
```
**Deferred fix (needs explicit approval — changes launch contract)**: add a
project-root `run.py` entry point so `cli.py` never needs manual `sys.path`
surgery:
```python
# project_root/run.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from ui.cli import init, run_extended_menu
if __name__ == "__main__":
    init()
    run_extended_menu()
```
Then `cli.py` drops the manual bootstrap block and just does
`from common.paths import PROJECTS_FILE`.

#### P1-5 — Naming inconsistency: `METRIC_UNITS`/`IMPERIAL_UNITS` vs. `METRIC_LABELS`/`IMPERIAL_LABELS`

`Menus.py` defines/re-exports the dicts as `METRIC_UNITS`/`IMPERIAL_UNITS`;
`cli.py` re-imports the same objects under `METRIC_LABELS`/`IMPERIAL_LABELS`.
Same objects, two vocabularies across the codebase.
**Fix**: standardize on `UNITS` (more accurate than "labels" — these are
conversion-divisor dicts, not just display strings). Delete the alias in `cli.py`
once all call sites are updated. Mechanical, but touches many call sites —
grep-and-replace with a full-file re-view afterward.

---

### P2 — `units.py` API cleanup (small, non-breaking)

#### P2-1 — Collapse `to_si()` / `system_multiplier()` duplication  ✅ DONE & VERIFIED (2026-07-12)

**Fix applied**: `to_si(unit_system_or_units, quantity, value=None)` — when
`value` is omitted, returns the bare factor (replaces `system_multiplier`);
when given, returns `value * factor` (original `to_si`). Accepts either a
units dict or a system string, unchanged.

`system_multiplier` removed entirely (no back-compat wrapper — only 10 call
sites in `inputs.py`, none elsewhere). `Menus.py` re-export dropped.
Commit `refactor(units): collapse to_si and system_multiplier into one
function` on `refactor/p2-units-api-cleanup`.

**Verified**: AST parse clean; zero `system_multiplier` references remain;
runtime tests pass (bare-factor mode, value mode, string+dict keys,
round-trip symmetry with `get_divisor` for every quantity, `1.0` fallback
preserved); stepped-solver regression 8/8.

#### P2-2 — Optional: `Quantity` enum for typo-safety  ✅ DONE & VERIFIED (2026-07-12)

**Fix applied**: added `Quantity(str, Enum)` covering all 11 quantities in
`common/units.py`. Subclassing `str` keeps it backward-compatible — members
hash and compare equal to the underlying string, so existing free-form call
sites (`to_si(units, 'length')`) keep working unchanged. New code can opt in
to `to_si(units, Quantity.LENGTH)` for autocomplete + typo protection.

**Bonus over the original spec**: added a drift guard at module bottom that
asserts `Quantity` members match `_SI_FACTORS` keys exactly — a future factor
addition without a matching enum member (or vice versa) now fails loudly at
import time, instead of re-introducing the silent-typo risk the enum exists
to prevent. Verified the guard fires correctly on a synthetic mismatch.

**Verified**: AST parse clean; 6 runtime tests pass (enum members exist,
`str` equality/hash contract, string call sites unaffected, enum works
through `to_si`/`get_divisor`, enum as dict key, drift guard in sync);
all units-dependent modules import cleanly; stepped-solver regression 8/8.

---

---

### P3 — Module decomposition (`cli.py` / `Menus.py` / `inputs.py`)

Each of these three files mixes 3–4 unrelated responsibilities. Split by **what
a module knows about**, not by file size — this is what makes the pieces
reusable by a future non-beam calculator. Proposed target structure (moves, not
rewrites — keep signatures stable):

#### P3-checkpoint-1 — Extract `ui/console/` (generic terminal kit)  ✅ DONE & VERIFIED (2026-07-13)

**Scope**: moved the domain-agnostic terminal kit (prompts, widgets,
formatters, session clock, `print_*`/`clear_screen`) out of `Menus.py` and
`inputs.py` into a new `ui/console/` package. Pure relocation, no logic
changes. Decision locked at plan time: **update all importers, no re-export
shims**.

**New package** `src/ui/console/`:
- `formatting.py` — `fmt_datetime`, `fmt_date_compact`, `fmt_duration`.
- `widgets.py` — `SESSION_START`, `UI_W`, session clock (`session_uptime`,
  `input_with_live_clock`, `_live_clock_supported`), all `ui_*` widgets
  (`ui_banner`/`ui_open`/`ui_close`/`ui_blank`/`ui_text`/`ui_head`/`ui_field`/
  `ui_bullet`/`ui_bar`/`ui_check_row`/`ui_verdict_badge`/`ui_footer`/
  `ui_menu_stage`), and `clear_screen`/`print_title`/`print_option`/
  `print_error`/`print_success`. Deps: stdlib + `termcolor` only.
- `prompts.py` — `PROMPT_CARET`, `_CANCEL_TOKENS`, `_dim`, `_format_prompt`,
  `_range_hint`, `ask_float`/`ask_int`/`ask_text`/`ask_choice`/`ask_yes_no`.
  Depends on `ui.console.widgets` (for `print_error`).
- `__init__.py` — single re-export hub so consumers write one
  `from ui.console import ...` line.
- Intra-package dep direction is acyclic: `prompts → widgets`; `formatting`
  standalone.

**Consumer rewrites** (6 files, all importers updated):
- `ui/Menus.py` — kit now from `ui.console`; dropped dead `cprint` import;
  dropped the `common.units` re-export shim (its only real consumer was
  `cli.py:get_divisor`, redirected to `common.units`). Kept
  `from common.units import METRIC_UNITS` (real usage as default-arg value in
  7 renderer signatures) and `SERVICEABILITY` (DOMAIN). Shrunk 1914→1677 lines.
- `ui/inputs.py` — kit from `ui.console`; dropped 4 dead `ui_*` imports
  (`ui_field`/`ui_text`/`ui_bullet`/`ui_head`); trimmed prompt import to the 3
  actually used (`ask_float`/`ask_int`/`ask_text`). Lazy import in
  `define_stepped_segments` split: kit removed (already module-level), DOMAIN
  (`choose_profile`/`display_section_library`) stays from `ui.Menus`. Shrunk
  1062→933 lines.
- `ui/cli.py` — the big `from ui.Menus import (...)` split into
  `ui.console` (13 kit symbols) + `ui.Menus` (20 DOMAIN symbols);
  `get_divisor` moved to the existing `common.units` import; dropped 4 dead
  kit imports (`ui_field`/`ui_text`/`ui_head`/`fmt_duration`). **AST-verified
  only** (can't runtime-import — `indeterminatebeam` transitive).
- `plotting/export_helper.py` + `plotting/pyvista_plotting.py` — kit + `ask_*`
  now from `ui.console` (collapsed 2 import lines → 1).

**Verified**: `ast.parse` clean on all 9 files; runtime import of `ui.console`
+ stripped `ui.Menus` (20 domain symbols) + `ui.inputs` (9 wizards) +
`plotting.export_helper` all clean; cli.py AST audit confirms zero kit symbols
leak from the `ui.Menus` import and `get_divisor` now comes from
`common.units`; stale-reference grep across `src/` returns zero matches;
integration test imports all 8 of cli.py's ui/plotting deps together; stepped-
solver regression **8/8 PASS**. Commit `refactor(ui): extract generic terminal
kit into ui/console/ package` on `refactor/p3-console-kit`.

**Carry-forward notes from checkpoint-1**:
- ~~The `cli ↔ inputs` cycle still exists~~ → **RESOLVED by checkpoint-2**.
- `LiveClock` class encapsulation (P4-2) deferred — `SESSION_START` + clock
  funcs moved verbatim into `widgets.py`; P4-2 will class-ify them and retire
  the module global.
- Deferred cleanups still open (not in this checkpoint's touched lines):
  `inputs.py:1-2` unused `sys`/`os`; `inputs.py:12` unused `UNIT_SYSTEMS`;
  `cli.py` possibly-dead `area_from_section` import (verify call sites before
  removing).

#### P3-checkpoint-2 — Extract `ui/materials/selector.py`  ✅ DONE & VERIFIED (2026-07-13)

**Scope**: moved all four material-handling functions out of `cli.py` (3
functions) and `inputs.py` (1 function) into a new leaf module
`ui/materials/selector.py`. Pure relocation; signatures and behavior unchanged.

**The key result**: the `cli ↔ inputs` circular-import cycle — the root cause
of the historical P0-1 crash — is **permanently eliminated**. Zero `from
ui.cli import` statements remain anywhere in `src/`.

**New module** `src/ui/materials/selector.py`:
- `load_material_database()` ← `cli.py` — writes `state.Materials`.
- `select_material(unit_system, units)` ← `cli.py` — reads
  `state.Materials.all_materials`, writes `state.project_state` flags, returns
  material dict.
- `display_material_info(...)` ← `cli.py` — pure-presentational (params only,
  no `state`).
- `define_custom_material(unit_system, units)` ← `inputs.py` — uses
  `ask_float`/`ask_text` + `to_json`, returns material dict.

**Leaf module proof**: the new module imports only from `common.units`,
`common.state`, `database.materials_database`, `ui.console`, and stdlib. Zero
back-edges into `ui.cli` or `ui.inputs`. Verified by import-graph inspection
after loading `ui.materials.selector` + `ui.inputs` — `ui.cli` is never pulled
into `sys.modules`.

**Consumer rewrites**:
- `ui/cli.py` — removed the 3 function defs (lines 589–795, ~207 lines).
  Added `from ui.materials.selector import load_material_database,
  select_material, display_material_info, define_custom_material`. Dropped
  `define_custom_material` from the `ui.inputs` import. Shrunk 2409→2201
  lines.
- `ui/inputs.py` — removed `define_custom_material` (lines 665–720, ~56
  lines). Converted the lazy import block at `define_stepped_segments` from
  `from ui.cli import select_material, load_material_database` (in-function,
  the cycle-break point) to a top-level eager `from ui.materials.selector
  import select_material, load_material_database`. Added `from core.state
  import state` at module top (needed for the `state.Materials` guard that
  was previously served by the lazy import). Shrunk 933→876 lines.

**Bonus cleanup**: the misleading comment in `inputs.py` ("still live in
ui.cli, to be moved in P3") deleted — the move it predicted is now done.

**Verified**: `ast.parse` clean on all 4 files; runtime import of
`ui.materials.selector` (4 functions) + `ui.inputs` (8 wizards) clean; cycle
elimination grep (`from ui.cli import` across `src/`) returns zero matches
(the single hit is a docstring comment, not an import); cli.py AST audit
confirms `ui.materials.selector` import present and `define_custom_material`
absent from `ui.inputs` import; integration test imports all 9 of cli.py's
ui/plotting deps together; stepped-solver regression **8/8 PASS**. Commit
`refactor(ui): extract material functions into ui/materials/selector.py` on
`refactor/p3-materials-selector` (stacks on checkpoint-1).

#### P3-checkpoint-3 — Extract `ui/beam/` wizards  ✅ DONE & VERIFIED (2026-07-19)

**Scope**: moved all 8 beam-domain input wizards out of `inputs.py` into a
new `ui/beam/` package. Pure relocation; signatures and behavior unchanged.
**`ui/inputs.py` no longer exists** — deleted per the locked
update-all-importers/no-shim convention.

**New package** `src/ui/beam/`:
- `classification.py` — `Beam_Classification`, `get_solver_resolution`.
  (`get_solver_resolution` was absent from the original P3 plan; placed
  here because both are small "define the analysis problem" wizards —
  placement decision recorded in the module docstring.)
- `geometry.py` — `Beam_Length`, `Beam_Supports`,
  `define_continuous_supports`, `define_custom_supports`.
- `loads.py` — `manage_loads`.
- `stepped.py` — `define_stepped_segments`. Function-local imports
  (`solver`, `ui.Menus`, `database`) kept function-local; one stale comment
  (citing the since-eliminated ui.cli import cycle) replaced with an
  accurate rationale — the only non-verbatim hunk in the move.
- `__init__.py` — single re-export hub (ui/console pattern).

**Consumer rewrite**: `cli.py`'s lone `from ui.inputs import (...)` (8
names) repointed to `ui.beam`. No other importer of `ui.inputs` existed
anywhere in the repo.

**Verified**: pure-relocation diff vs `HEAD:src/ui/inputs.py` — 7/8
functions byte-identical, `define_stepped_segments` differs only in the
approved comment swap; `ast.parse` clean on all 6 files; `ui.beam`
runtime-imports with all 8 names and does NOT pull `ui.cli` into
`sys.modules` (import-time deps are only `ui.console` +
`ui.materials.selector` + foundation — no solver layer); cli.py AST audit
(`ui.beam` import with all 8 names, zero `ui.inputs` refs, all 8 names
used); zero `from ui.inputs`/`import ui.inputs` matches repo-wide;
integration test — all 6 unguarded ui/plotting deps of cli.py import
together (`plotting.pyvista_plotting` stays try/except-guarded; pyvista
absent in the sandbox is pre-existing, unchanged); stepped-solver
regression **8/8 PASS**. Commit `refactor(ui): extract beam-domain wizards
into ui/beam/ package` on `refactor/p3-beam-wizards`. Git detected
`inputs.py → beam/loads.py` as a 50%-similarity rename, independently
confirming the move's fidelity.

**Deferred-item dispositions**: checkpoint-1's open cleanups
"`inputs.py:1-2` unused `sys`/`os`" and "`inputs.py:12` unused
`UNIT_SYSTEMS`" are **resolved by elimination** — the file is gone and the
dead imports were not carried into the new modules (per-module
minimal-import discipline). The "`cli.py` possibly-dead `area_from_section`
import" item remains open (untouched by this checkpoint).

#### P3-checkpoint-4 — Extract `ui/reports/` renderers  ✅ DONE & VERIFIED (2026-07-19)

**Scope**: moved the 5 post-solution report renderers out of `Menus.py`
(1677→843 lines) into a new `ui/reports/` package. Pure relocation —
byte-identical function bodies. `display_profile_info` deliberately stays
in `ui.Menus` (post-profile-confirmation screen, not an analysis report).

**New package** `src/ui/reports/`:
- `analysis_report.py` — `display_analysis_info`, `display_analysis_results`.
- `deflection_report.py` — `display_deflection_analysis`.
- `stress_report.py` — `display_stress_analysis`.
- `recommendations_report.py` — `display_engineering_recommendations`.
- `__init__.py` — re-export hub (ui/console pattern).

**Consumer rewrite**: `cli.py` — the 5 renderer names moved from the
`from ui.Menus import (...)` group (now 15 names) to a new
`from ui.reports import (...)` line. Call sites untouched.

**Menus.py trim**: dropped the imports only the renderers used
(`SERVICEABILITY`, `ui_text`, `ui_head`, `ui_bullet`, `ui_check_row`,
`ui_verdict_badge`, `ui_footer`); AST-verified every retained import has a
live usage; header comment rewritten for what remains.

**⚠ Bonus correctness fix (P0-class, latent)**: checkpoint-1 (`a2db0eb`)
dropped `get_divisor` from `Menus.py`'s imports when the `common.units`
re-export shim was removed, but `display_profile_info` and all 5 renderers
call `get_divisor` in their bodies — 18 call sites with no import. Every
renderer call would have raised `NameError: name 'get_divisor' is not
defined`. Never caught before because the sandbox can't runtime-drive
cli.py and the regression suite exercises the solver, not the UI
renderers. Found by runtime-probing during this checkpoint; fixed by
importing `get_divisor` from `common.units` in the 4 new modules and in
trimmed `Menus.py`. Function bodies byte-identical — wiring restored, no
logic change.

**Verified** (independently re-run by the parent agent, not just the
executor): relocation diff vs `HEAD~1:src/ui/Menus.py` — 5/5 functions
byte-identical; `ast.parse` clean on 7 files; `ui.reports` runtime-imports
(leaf: no `ui.cli`, no `solver.*`, no `ui.Menus` pulled in); trimmed
`ui.Menus` keeps exactly 15 callables (14 menus + `display_profile_info`);
cli.py AST audit (5 names from `ui.reports`, zero in the `ui.Menus` group,
all 5 used); zero stale `from ui.Menus import ... display_*` matches
repo-wide; 7 unguarded ui/plotting deps co-import cleanly;
stepped-solver regression **8/8 PASS**. Commit
`refactor(ui): extract domain report renderers into ui/reports/ package`
on `refactor/p3-reports`.

```
src/ui/
├── console/                     # generic, domain-agnostic terminal UI kit
│   ├── prompts.py               # ask_float, ask_int, ask_text, ask_choice, ask_yes_no
│   ├── widgets.py                # ui_banner/ui_open/.../LiveClock
│   └── formatting.py            # fmt_datetime, fmt_duration, fmt_date_compact
├── beam/                         # domain wizards (DONE — checkpoint-3)
│   ├── classification.py        # Beam_Classification, get_solver_resolution
│   ├── geometry.py               # Beam_Length, Beam_Supports, define_continuous_supports, define_custom_supports
│   ├── loads.py                   # manage_loads
│   └── stepped.py                 # define_stepped_segments
├── materials/
│   └── selector.py               # select_material, define_custom_material, display_material_info
│                                    #   (moved OUT of cli.py — permanently fixes P0-1's root cause)
├── reports/                       # domain report renderers (DONE — checkpoint-4)
│   ├── analysis_report.py        # display_analysis_results, display_analysis_info
│   ├── deflection_report.py      # display_deflection_analysis
│   ├── stress_report.py          # display_stress_analysis
│   └── recommendations_report.py # display_engineering_recommendations
├── menus/                         # pure navigation menus (main_menu_template, *_menu functions)
├── project/
│   ├── repository.py             # ProjectRepository (see P4-1)
│   └── serializers.py            # to_project_dict / apply_project_dict for ProjectState
└── cli.py                         # thin orchestrator only: menu loop + dispatch
```

**Rationale, concretely**: `ask_float`/`ask_int` etc. have zero beam-domain
knowledge and are already well-factored internally (shared `_format_prompt`,
`PROMPT_CARET`, consistent retry semantics) — the problem is purely *location*,
sitting in the same file as `manage_loads()`, a 250-line beam-specific wizard.
Same for `Menus.py`: `ui_banner`/`ui_field`/`ui_bar` are a generic terminal
design system with no idea what a beam is; `display_stress_analysis` is 100%
beam-domain and *uses* that design system. Welded into one file today, so
extending to a truss calculator currently means importing beam-report code just
to get a progress bar.

**Sequencing**: do this per-module with checkpoints (established convention).
Suggested order: `console/` first (zero domain coupling, safest), then
`materials/selector.py` (closes P0-1 permanently), then `beam/`, then
`reports/`, then thin out `cli.py` last once everything it used to contain has
somewhere else to live.

---

### P6 — Unified stage-driven Stepped Bar (APPROVED 2026-07-19)

> **Sequencing**: runs **after P3-checkpoint-5, before P4**. Numbered P6
> because it was identified after P4/P5 were drafted; execution order is
> P3 → P6 → P4 → P5. Approved by the user in conversation: "make the stepped
> bar work like any other beam type but taking into account segments number."

**Problem (3 classes, user-reported & confirmed)**:
1. *Silent conflicts* — with segments defined, main-menu `[4] Material
   Selection` still writes `state.elastic_modulus` / `material_saved`, which
   the stepped solver ignores (segments carry their own `E`). The user
   believes the material changed; it didn't. Same bug family as P0-2.
2. *Dead/misleading menu items* — for Stepped Bar, "Enter Beam Length" and
   "Select Material" do nothing meaningful; `state.beam_length` / `state.Ix` /
   `state.shape` stay empty, forcing `!= "Stepped Bar"` guards across
   display/save/solve code.
3. *All-or-nothing editing* — changing one segment's material/section means
   re-running the entire `define_stepped_segments()` monolith.

**Goal**: one stage-driven flow for ALL beam types. Stepped Bar makes some
stages multi-valued instead of bypassing them. The `define_stepped_segments`
monolith retires; `ui/beam/stepped.py` shrinks to per-stage helpers +
assembly/validation.

**Stage behavior for Stepped Bar** (standard beams unchanged):
- `[2] Classification`: unchanged (returns "Stepped Bar"; no segment count
  here — count is geometry, lives in Profile).
- `[3] Profile`: "Define Segments" — segment count X + lengths (default:
  equal split of a total length; option: custom per-segment, enforced
  contiguous from 0). Then "Define Cross-Sections" — loops X times through
  the EXISTING profile flow (`choose_profile` → custom dims / standard
  library / saved sections) with "same as previous segment" and "apply to
  all remaining" shortcuts.
- `[4] Material`: shows the per-segment material list; prominent default
  "apply one material to all segments" (the common case — stepped bars
  usually vary section, not material) plus "edit material for segment i".
  Reuses `ui/materials/selector.select_material` per segment — zero changes
  there.
- `[5] Boundary` / `[6] Loads`: already shared (`define_custom_supports`,
  `manage_loads` — the latter already stepped-aware for axial/angled
  loads). No changes.
- `[8] Solve`: NEW pre-solve validation — lengths contiguous from 0, X
  sections defined, X materials assigned; failures name the incomplete
  stage. Then existing dispatch to `solve_stepped_beam()`, unchanged.

**State changes**:
- `state.segments` schema UNCHANGED (§5.6 save format untouched;
  `test_stepped_solver.py` unaffected — it tests the solver, not wizards).
- `state.beam_length = Σ segment lengths` ALWAYS populated, including
  Stepped Bar (kills a class of `!= "Stepped Bar"` guards in
  schematic/reports/save).
- Segments are ASSEMBLED from stage data (lengths + sections + materials)
  by one `assemble_segments(...)` function; `project_state` flags
  (`profile_saved`, `material_saved`) become uniform across beam types.
- Menu labels become beam-type-aware in the Profile/Material slots (same
  pattern as the existing dynamic `fea_3d_choice` computation) — no
  separate menu trees.

**Migration**: `load_project` back-fills stage data (per-segment
sections/materials, `beam_length`) from saved `segments` for old Stepped
Bar projects so they stay editable in the new flow.

**Out of scope**: solver changes (none needed); postprocessing items
9/10/11 (legitimate domain difference — stays); PyVista stepped meshes
(still §4.13's open enhancement).

**Verification**: `ast.parse`; runtime wizard-flow tests with scripted
stdin (the wizards are runtime-testable — feed `input()`); validation +
assembly unit tests (assembled segments match the old monolith's output
shape); stale-reference grep; stepped-solver regression 8/8.

---

### P4 — Reusable common modules

#### P4-1 — Save/load: Repository pattern

`save_project`/`load_project`/`save_projects_to_disk`/`load_projects_from_disk`
are free functions in `cli.py` mixing three concerns: file I/O, `ProjectState`↔dict
serialization, and UI prompts ("Overwrite? Y/N"). Separate them:

```python
# ui/project/repository.py
import json
from pathlib import Path
from common.paths import PROJECTS_FILE
from common.exceptions import PersistenceError

class ProjectRepository:
    """Pure persistence — no UI, no ProjectState knowledge."""
    def __init__(self, path: Path = PROJECTS_FILE):
        self._path = path

    def load_all(self) -> list[dict]:
        try:
            return json.loads(self._path.read_text())
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as e:
            raise PersistenceError(f"Corrupt project file {self._path}: {e}") from e

    def save_all(self, projects: list[dict]) -> None:
        try:
            self._path.write_text(json.dumps(projects, cls=NumpyEncoder, indent=4))
        except OSError as e:
            raise PersistenceError(f"Could not write {self._path}: {e}") from e
```

Add `to_project_dict(state)` / `apply_project_dict(state, data)` to
`core/state.py`. `cli.py::save_project()` shrinks to: build dict, ask overwrite
question, call `repo.save_all(...)`. Each concern becomes independently
testable — `ProjectRepository` can be unit-tested with a tmp path and zero
terminal I/O, which is impossible with the current procedural version.

#### P4-2 — Live clock widget

```python
# ui/console/widgets.py
import datetime, sys

class LiveClock:
    """Encapsulates the SESSION_START global + input_with_live_clock ANSI trick."""
    def __init__(self):
        self.start = datetime.datetime.now().astimezone()

    def uptime_seconds(self) -> float:
        return (datetime.datetime.now().astimezone() - self.start).total_seconds()

    def prompt(self, prompt_text: str, render_line) -> str:
        if not self._tty_supported():
            print(render_line()); return input(prompt_text)
        return self._ticking_prompt(prompt_text, render_line)

    @staticmethod
    def _tty_supported() -> bool:
        try:
            return sys.stdout.isatty()
        except AttributeError:
            return False
    # _ticking_prompt = existing input_with_live_clock body, unchanged
```
`main_menu_template` holds a `LiveClock` instance instead of a module-level
`SESSION_START` global — also removes global mutable state that currently makes
the clock impossible to reset between test runs.

#### P4-3 — Prompt toolkit: move only, no redesign

`ask_float`/`ask_int`/`ask_text`/`ask_choice`/`ask_yes_no` are already
well-designed. Relocate to `ui/console/prompts.py` per P3; no logic changes.

#### P4-4 — Logging

No logging currently exists outside `print_error`/`print_success` (user-facing
only, not diagnostic). Add:
```python
# common/logging_config.py
import logging
from common.paths import PROJECT_ROOT

def configure_logging(level=logging.WARNING) -> None:
    logging.basicConfig(
        filename=PROJECT_ROOT / "altruxiq.log",
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
```
Call once from the entry point (`init()` or the future `run.py`). Lets solver
modules `logging.getLogger(__name__).debug(...)` without polluting the CLI
output stream — useful once the solver registry (P5-1) and plugin surface
(P5-2) exist and failures need attribution to a specific module.

---

### P5 — Future-proofing

#### P5-1 — Solver registry (replaces `if beam_type ==` chains)

Directly targets the Open/Closed Principle gap: adding a new beam/frame/truss
type today means editing the dispatch chain in three places (`cli.py` solve
block, `indeterminate_solver._build_supports`, plotting dispatch).

```python
# solver/registry.py
from typing import Callable, Protocol
from common.exceptions import ValidationError

class BeamSolver(Protocol):
    def __call__(self, **kwargs) -> dict: ...

_REGISTRY: dict[str, BeamSolver] = {}

def register_solver(*beam_types: str):
    def _decorator(fn: BeamSolver) -> BeamSolver:
        for bt in beam_types:
            _REGISTRY[bt] = fn
        return fn
    return _decorator

def get_solver(beam_type: str) -> BeamSolver:
    try:
        return _REGISTRY[beam_type]
    except KeyError:
        raise ValidationError(
            f"No solver registered for beam_type={beam_type!r}. "
            f"Known types: {sorted(_REGISTRY)}"
        )
```
```python
# indeterminate_solver.py
@register_solver("Simple", "Cantilever", "Fixed-Fixed", "Propped",
                  "Continuous", "Custom", "Overhanging Beam")
def solve_beam(...) -> dict: ...

# stepped_solver.py
@register_solver("Stepped Bar")
def solve_stepped_beam(...) -> dict: ...
```
`cli.py`'s solve block collapses from a 20-line `if/elif` to:
```python
solver_fn = get_solver(state.beam_type)
result = solver_fn(**_build_solver_kwargs(state))
```
A future `frame2d`/`truss2d` module — the explicit generalization target named
in `stepped_solver.py`'s own docstring — registers itself with **zero** changes
to `cli.py`.

#### P5-2 — Plugin/extension contract

Define the extension contract now, before retrofitting becomes necessary:
```python
# common/plugin.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class EngineeringModule(Protocol):
    """Contract every calculator (beam, frame, truss, ...) must satisfy."""
    module_id: str
    display_name: str
    def solve(self, **kwargs) -> dict: ...
    def build_menu(self) -> "ModuleMenu": ...
```
This is what makes "additional engineering calculators" and a future GUI
version tractable — the menu/CLI layer becomes a generic host that discovers
`EngineeringModule` implementations rather than hardcoding beam-specific menu
item numbers (the same bug class as the historical Bug-11: hardcoded
`sub_choice == '12'`).

#### P5-3 — Split engineering constants from user preferences

`common/config.py` currently holds only engineering constants
(`SolverDefaults`, `ServiceabilityLimits` — L/360, target FoS) which must stay
frozen/non-user-editable. "User preferences" (task requirement) needs a
**separate** module so a future "reset to defaults" UI action can't conflate
"reset my UI prefs" with "reset the L/360 deflection limit" — mixing them is
the kind of bug that ships wrong structural results, not a style issue.
```python
# common/settings.py
from dataclasses import dataclass, asdict
import json
from common.paths import PROJECT_ROOT

SETTINGS_FILE = PROJECT_ROOT / "user_settings.json"

@dataclass
class UserSettings:
    default_unit_system: str = "Metric"
    default_num_points: int = 2001
    locale: str = "en_US"

    @classmethod
    def load(cls) -> "UserSettings":
        try:
            return cls(**json.loads(SETTINGS_FILE.read_text()))
        except FileNotFoundError:
            return cls()

    def save(self) -> None:
        SETTINGS_FILE.write_text(json.dumps(asdict(self), indent=2))
```

---

## 4. Principle-to-finding map (for quick reference)

| Principle | Already satisfied | Violated (this audit) |
|---|---|---|
| SRP | `common/paths.py`, `common/units.py`, `common/exceptions.py` | `cli.py` (menu + orchestration + persistence + material selection), `Menus.py` (generic UI kit + domain reports) |
| OCP | — | Beam-type `if/elif` chains — fixed by P5-1 |
| DIP | `ProjectState` as a shared object | `save_project()` depends directly on filesystem/json, not an abstraction — fixed by P4-1 |
| DRY | `units.py`, `config.py` — no duplicate conversion tables found | `to_si`/`system_multiplier` duplicate lookup logic — P2-1 |
| KISS | `ask_*` prompt toolkit | `display_engineering_recommendations` silently wrong output is not "simple," it's a hidden bug — P0-2 |
| Correctness (prerequisite to all of the above) | — | P0-1 live crash, P0-2 silent wrong output — **fix before any structural refactor** |

---

## 5. Working conventions (unchanged)

- **Per-module checkpoints**: user reviews after each module. Ask before
  starting each step.
- **Verification standard**: every change gets (1) `ast.parse` syntax check,
  (2) a runtime or AST test proving the fix, (3) a stale-literal/reference
  audit (grep for the old pattern).
- **`cli.py` verification caveat**: cannot runtime-import (missing
  `indeterminatebeam` in sandbox). Use AST walks to verify imports/calls
  instead. All other modules are runtime-testable.
- **`common/` is the foundation layer**: new magic numbers → `common/config.py`;
  new unit factors → `common/units.py`; new domain exceptions →
  `common/exceptions.py`; new paths → `common/paths.py`; new user-editable
  settings → `common/settings.py` (P5-3) — never inline these.
- **Always present options + recommendation** before starting a step, per
  standing user request.
- Commit message style: conventional commits (`fix(inputs):`, `fix(menus):`,
  `refactor(ui):`, `feat(solver):`, `chore(cleanup):`).

---

## 6. Resume instruction for the new session

1. Read this file + `AGENT_BRIEFING.md` §1–5, 9, 14.
2. **P0, P1, P2, and P3-checkpoints 1–4 are fully done.** The
   `cli ↔ inputs` circular-import cycle is permanently eliminated,
   `ui/inputs.py` no longer exists, and the 5 report renderers now live in
   `ui/reports/` (`Menus.py` keeps only navigation menus +
   `display_profile_info`). Checkpoint-4 also repaired a latent
   `NameError: get_divisor` from checkpoint-1 (see §P3-checkpoint-4).
   Next is **P3-checkpoint-5 — `menus/` + thin `cli.py`**: move the 14
   navigation menu functions out of `Menus.py` into `ui/menus/`, then thin
   `cli.py` to a pure orchestrator (menu loop + dispatch; project save/load
   moves to `ui/project/` under P4-1).
   Then **P6** (unified stage-driven Stepped Bar — APPROVED, see §P6;
   retires the `define_stepped_segments` monolith), then **P4**
   (`ProjectRepository`, `LiveClock`, logging) and **P5**
   (solver registry, plugin contract, settings/config split — needed before
   frame2d/truss2d or a GUI).
   Open deferred item: **P1-4** (`run.py` entry point) — needs explicit user
   approval since it changes the launch contract.
3. **Key constraint unchanged**: `cli.py` cannot be runtime-imported in the
   sandbox (transitive `indeterminatebeam`). Verify its changes via AST.
   `Menus.py`, `ui/beam/*`, `ui/console/*`, `ui/reports/*`, and the plotting
   modules ARE runtime-testable (pyvista absent — its import stays
   try/except-guarded in cli.py). Regression suite is
   `test_stepped_solver.py` (run directly with `PYTHONPATH=src py -3
   test_stepped_solver.py` — 8/8; `python` is not on PATH in this shell,
   use the `py -3` launcher; pytest is not installed in the sandbox
   Python).