# AltruxIQ — Session Handoff & Continuation Brief

> **Purpose**: One-shot context for a new agent session to resume work without
> re-reading the full history.
> **Last session**: P0 correctness bugs **DONE**; P1 dead-code/stale-reference
> cleanup **DONE** (P1-1/2/3/5, plus bonus dead `import sys` in
> `pyvista_plotting.py`). Branch `fix/p0-correctness-bugs` holds both batches
> (5 commits). Ready to proceed to **P2** (`units.py` API cleanup).
> **Date**: 2026-07-11.

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

#### P2-1 — Collapse `to_si()` / `system_multiplier()` duplication

Both resolve through `_system_key`, which already accepts either a dict or a
string — so the dual API exists for no reason:
```python
def to_si(units_dict, quantity, value):
    return value * _SI_FACTORS[_system_key(units_dict)].get(quantity, 1.0)

def system_multiplier(unit_system, quantity):
    return _SI_FACTORS[_system_key(unit_system)].get(quantity, 1.0)
```
**Fix** — one function, optional `value`:
```python
def to_si(unit_system_or_units, quantity: str, value: float | None = None):
    """SI = value * factor. If value is omitted, returns the bare factor."""
    factor = _SI_FACTORS[_system_key(unit_system_or_units)].get(quantity, 1.0)
    return factor if value is None else value * factor
```
Removes one exported name and the (currently silent) risk of the two functions
drifting apart if `_SI_FACTORS` gains a quantity-specific special case in one but
not the other. Update the handful of `system_multiplier(...)` call sites in
`inputs.py` to `to_si(..., value=None)`-style calls, or keep `system_multiplier`
as a one-line backward-compatible wrapper if churn should be minimized.

#### P2-2 — Optional: `Quantity` enum for typo-safety

Quantity keys are free-form strings (`'length_small'`, `'sec_mod'`). A typo
(`'length-small'`) fails silently — `.get(quantity, 1.0)` returns `1.0` and
produces a plausible-but-wrong number instead of an error.
```python
from enum import Enum
class Quantity(str, Enum):
    LENGTH = "length"; LENGTH_SMALL = "length_small"; FORCE = "force"
    MOMENT = "moment"; AREA = "area"; INERTIA = "inertia"; SEC_MOD = "sec_mod"
    MODULUS = "modulus"; STRESS = "stress"; DENSITY = "density"; DISTRIBUTED = "distributed"
```
`Quantity(str, Enum)` hashes identically to the equivalent string, so this is
opt-in and non-breaking — existing string call sites keep working; new code can
use `get_divisor(units, Quantity.LENGTH)` for autocomplete + typo protection.
Low priority; do only if touching `units.py` for P2-1 anyway.

---

### P3 — Module decomposition (`cli.py` / `Menus.py` / `inputs.py`)

Each of these three files mixes 3–4 unrelated responsibilities. Split by **what
a module knows about**, not by file size — this is what makes the pieces
reusable by a future non-beam calculator. Proposed target structure (moves, not
rewrites — keep signatures stable):

```
src/ui/
├── console/                     # generic, domain-agnostic terminal UI kit
│   ├── prompts.py               # ask_float, ask_int, ask_text, ask_choice, ask_yes_no
│   ├── widgets.py                # ui_banner/ui_open/.../LiveClock
│   └── formatting.py            # fmt_datetime, fmt_duration, fmt_date_compact
├── beam/                         # domain wizards (currently in inputs.py)
│   ├── classification.py        # Beam_Classification
│   ├── geometry.py               # Beam_Length, Beam_Supports, define_continuous_supports, define_custom_supports
│   ├── loads.py                   # manage_loads
│   └── stepped.py                 # define_stepped_segments
├── materials/
│   └── selector.py               # select_material, define_custom_material, display_material_info
│                                    #   (moved OUT of cli.py — permanently fixes P0-1's root cause)
├── reports/                       # domain report renderers (currently in Menus.py)
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
2. **P0 and P1 are done.** Next recommended step is **P2 — `units.py` API
   cleanup** (collapse `to_si`/`system_multiplier` duplication; small,
   non-breaking). Then the larger structural program **P3 → P4 → P5**.
   Confirm with the user which tier to start before proceeding — same
   per-module checkpoint convention as prior phases.
   Open deferred item: **P1-4** (`run.py` entry point) — needs explicit user
   approval since it changes the launch contract.