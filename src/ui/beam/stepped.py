"""Stepped-bar segment-definition wizards (decomposed for the unified
stage-driven Stepped Bar flow — P6).

Historically the whole Stepped Bar definition lived in one ~200-line
monolith (``define_stepped_segments``). P6 splits it into per-stage
helpers that mirror how every other beam type already flows through the
main-menu stages:

* Stage [3] Profile → :func:`define_segment_lengths` + :func:`define_segment_section`
  (looped), assembled by :func:`assemble_segments`.
* Stage [4] Material → :func:`define_segment_material` (looped per segment).
* Stage [8] Solve → :func:`validate_segments_for_solve` (pre-solve gate).

The 12-key segment dict schema consumed by ``solver.stepped_solver`` is
**unchanged** — the helpers only change how that dict is *produced*, not
its shape. ``assemble_segments`` output is byte-compatible with the legacy
monolith's output (verified by ``test_stepped_assembly.py``).

Heavy dependencies (``solver``, ``ui.menus``, ``database``) are imported
function-locally so that importing this module stays cheap and free of
solver-layer side effects.

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3); decomposed for P6.
"""
import time
import numpy as np
from termcolor import colored

from common.units import to_si, default_units
from common.exceptions import SectionGeometryError
from core.state import state
from ui.console import (print_error, print_success, print_title, print_option,
                        clear_screen)
from ui.console.prompts import ask_float
from ui.materials.selector import select_material, load_material_database

#==================================================================================
# Stage [3] helpers — geometry
#==================================================================================

def define_segment_lengths(num_segs, unit_system="Metric", units=None,
                           *, total_hint=None):
    """Define the length of each segment.

    Total-first flow (P6 decision, 2026-07-24): the user gives the overall
    bar length, then chooses either an equal split (the common case) or a
    custom per-segment length. Custom lengths are enforced contiguous from
    0 — the running total must reach the stated total length.

    Parameters
    ----------
    num_segs : int
        Number of segments (>= 1).
    unit_system, units : str, dict
        Active unit system + divisor dict.
    total_hint : float, optional
        SI total length to pre-fill / suggest. If None the user is prompted.

    Returns
    -------
    list[float] | None
        SI lengths, one per segment (sums to the total length), or ``None``
        if the user cancels.
    """
    if units is None:
        units = default_units()
    l_mult = to_si(unit_system, "length")
    inv_len = 1.0 / l_mult

    if num_segs < 1:
        print_error("At least 1 segment required.")
        return None

    # --- Total length -------------------------------------------------------
    if total_hint is not None and total_hint > 0:
        total_len = float(total_hint)
    else:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║            STEPPED BAR — TOTAL LENGTH                        ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        seg_word = "segment" if num_segs == 1 else "segments"
        total_raw = ask_float(f"Total bar length ({num_segs} {seg_word})", unit=units['length'],
                              minimum=0, exclusive_min=True, allow_cancel=True)
        if total_raw is None:
            return None
        total_len = total_raw * l_mult

    # --- Single segment: trivial -------------------------------------------
    if num_segs == 1:
        return [total_len]

    # --- Equal split vs custom ---------------------------------------------
    clear_screen()
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║            SEGMENT LENGTH DISTRIBUTION                       ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("")
    print(colored(f"  Total length: {total_len * inv_len:.3f} {units['length']}  •  {num_segs} segments", 'white'))
    print("")
    print_option("  1. Equal split  — each segment "
                 f"{total_len / num_segs * inv_len:.3f} {units['length']}  (recommended)")
    print_option("  2. Custom per-segment lengths (must sum to total)")
    print("")
    choice = input(colored("Choose option [1-2] ➔ ", 'cyan')).strip()

    if choice == '2':
        # Custom per-segment, enforced contiguous from 0 and summing to total.
        lengths = []
        remaining = total_len
        for i in range(num_segs):
            is_last = (i == num_segs - 1)
            if is_last:
                # Final segment absorbs any rounding residual so the total is exact.
                lengths.append(remaining)
                break
            max_next = remaining if False else remaining  # informational
            seg_raw = ask_float(
                f"Segment {i + 1} length",
                unit=units['length'],
                minimum=0,
                exclusive_min=True,
                maximum=remaining * inv_len,
                allow_cancel=True,
            )
            if seg_raw is None:
                return None
            seg_si = seg_raw * l_mult
            if seg_si >= remaining - 1e-12 and not is_last:
                print_error("That would consume the whole remaining length before the last segment.")
                time.sleep(1.5)
                # Re-prompt this segment
                while True:
                    seg_raw = ask_float(
                        f"Segment {i + 1} length",
                        unit=units['length'],
                        minimum=0,
                        exclusive_min=True,
                        maximum=remaining * inv_len,
                        allow_cancel=True,
                    )
                    if seg_raw is None:
                        return None
                    seg_si = seg_raw * l_mult
                    if seg_si < remaining - 1e-12:
                        break
                    print_error("That would consume the whole remaining length before the last segment.")
                    time.sleep(1.5)
            lengths.append(seg_si)
            remaining -= seg_si
        return lengths

    # Equal split (default + fallback for any unrecognised input).
    each = total_len / num_segs
    return [each for _ in range(num_segs)]


def define_segment_section(seg_index, num_segs, units=None, *, prev_result=None,
                            unit_system="Metric"):
    """Define the cross-section for one segment.

    Reuses the EXISTING profile flow (``choose_profile`` → custom dims /
    standard library / saved sections). When ``prev_result`` is given (the
    previous segment's result tuple), offers "same as previous segment" and
    "apply same section to all remaining segments" shortcuts so the common
    case of a stepped bar that varies only *some* segments is fast.

    Parameters
    ----------
    seg_index, num_segs : int
        0-based index + total count, for labelling.
    units : dict
        Active divisor dict.
    prev_result : tuple, optional
        The ``(Ix, shape, c, b, y_array, section_dims)`` tuple returned for
        the previous segment, enabling the shortcut options.
    unit_system : str
        Active unit system (forwarded to the section solvers).

    Returns
    -------
    tuple | str | None
        * ``(Ix, shape, c, b, y_array, section_dims)`` on success.
        * ``"SAME"`` if the user chose "same as previous segment".
        * ``"ALL"`` if the user chose "apply to all remaining segments".
        * ``None`` on cancel.
    """
    if units is None:
        units = default_units()

    # Function-local imports keep this module's import-time surface minimal:
    # the solver/Menus layers are only loaded when the wizard actually runs.
    from solver import moi_solver

    clear_screen()
    print(colored(f"╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored(f"║        DEFINING SEGMENT {seg_index + 1} OF {num_segs}                          ║", 'cyan', attrs=['bold']))
    print(colored(f"╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("")

    # --- Shortcuts (only when there is a previous result to reuse) ---------
    if prev_result is not None:
        prev_shape = prev_result[1]
        remaining = num_segs - seg_index
        print(colored("┌─ SHORTCUTS ─" + "─"*47, 'green', attrs=['bold']))
        print_option(f"  0. Same as previous segment ({prev_shape})")
        if remaining > 1:
            print_option(f"  S. Apply '{prev_shape}' to all {remaining} remaining segments")
        print(colored("└" + "─"*62, 'green', attrs=['bold']))
        print("")

    print(colored("┌─ SELECT CROSS-SECTION FOR THIS SEGMENT ─" + "─"*20, 'yellow', attrs=['bold']))
    print_option("  1. ✍️  Enter Custom Dimensions (Manual)")
    print_option("  2. 📚 Standard Section Library")
    print_option("  3. 💾 My Saved Sections")
    print("")
    src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()

    # Shortcut handling -----------------------------------------------------
    if src_choice == '0' and prev_result is not None:
        return "SAME"
    if src_choice.upper() == 'S' and prev_result is not None and (num_segs - seg_index) > 1:
        return "ALL"

    from database.sections_database import SectionsDatabase
    sections_db = SectionsDatabase()

    while True:
        result = None
        if src_choice == '1':
            from ui.menus import choose_profile
            profile_choice = choose_profile()
            if profile_choice in ('1', '2', '3', '4', '5', '6', '7', '8'):
                if profile_choice == '1': result = moi_solver.inertia_moment_ibeam(units=units)
                elif profile_choice == '2': result = moi_solver.inertia_moment_tbeam(units=units)
                elif profile_choice == '3': result = moi_solver.inertia_moment_circle(units=units)
                elif profile_choice == '4': result = moi_solver.inertia_moment_hollow_circle(units=units)
                elif profile_choice == '5': result = moi_solver.inertia_moment_square(units=units)
                elif profile_choice == '6': result = moi_solver.inertia_moment_hollow_square(units=units)
                elif profile_choice == '7': result = moi_solver.inertia_moment_rectangle(units=units)
                elif profile_choice == '8': result = moi_solver.inertia_moment_hollow_rectangle(units=units)
            else:
                print_error("Invalid profile selection.")
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue
            if result is None:
                print_error("Invalid dimensions entered. Try again.")
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue
            break

        elif src_choice == '2':
            from ui.menus import display_section_library
            families = sections_db.get_standard_families()
            if not families:
                print_error("Standard library is empty or missing.")
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue
            clear_screen()
            print_title("STANDARD SECTION FAMILIES")
            for j, fam in enumerate(families, 1):
                print_option(f"  {j}. {fam}")
            print_option(f"  0. Back")
            print("")
            try:
                fam_idx = int(input(colored("Choose a family ➔ ", 'cyan')))
                if fam_idx == 0:
                    src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                    continue
                selected_family = families[fam_idx - 1]
                sections_in_fam = sections_db.get_sections_in_family(selected_family)
                sec_idx = display_section_library(sections_in_fam, title=f"{selected_family} Sections", is_custom=False)
                if sec_idx is not None:
                    entry = sections_in_fam[sec_idx]
                    result = moi_solver.load_section_from_library(entry)
                    if result:
                        break
                    print_error("Failed to parse section data.")
                    src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                    continue
            except (ValueError, IndexError):
                print_error("Invalid selection.")
                time.sleep(1)
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue

        elif src_choice == '3':
            from ui.menus import display_section_library
            custom_secs = sections_db.list_custom_sections()
            if not custom_secs:
                print_error("No saved custom sections found.")
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue
            sec_idx = display_section_library(custom_secs, title="MY SAVED SECTIONS", is_custom=True)
            if sec_idx is not None:
                entry = custom_secs[sec_idx]
                result = moi_solver.load_section_from_library(entry)
                if result:
                    break
                print_error("Failed to parse section data.")
                src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()
                continue
        else:
            print_error("Invalid choice. Please enter 0/1/2/3 (or S for the shortcut).")
            src_choice = input(colored("Choose option ➔ ", 'cyan')).strip()

    return result


#==================================================================================
# Stage [4] helper — material
#==================================================================================

def define_segment_material(seg_index, num_segs, unit_system="Metric", units=None):
    """Select a material for one segment.

    Thin wrapper over :func:`ui.materials.selector.select_material` — it
    ensures the materials database is loaded, then delegates. Returns the
    raw material dict that ``select_material`` returns (keys: ``Material``,
    ``Elastic Modulus`` in GPa, ``Yield Strength`` in MPa, ...), or ``None``
    on cancel.
    """
    if units is None:
        units = default_units()

    clear_screen()
    print(colored(f"╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored(f"║      MATERIAL FOR SEGMENT {seg_index + 1} OF {num_segs}                      ║", 'cyan', attrs=['bold']))
    print(colored(f"╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("")

    if state.Materials is None:
        load_material_database()

    return select_material(unit_system, units)


#==================================================================================
# Assembly — pure function producing the 12-key segment dicts
#==================================================================================

def assemble_segments(lengths, sections, materials, unit_system="Metric", units=None):
    """Combine per-stage lists into the solver's segment dict list.

    This is the single place that builds the 12-key segment schema consumed
    by ``solver.stepped_solver.solve_stepped_beam``. All three lists must be
    the same length (one entry per segment).

    Parameters
    ----------
    lengths : list[float]
        SI length of each segment.
    sections : list[tuple]
        ``(Ix, shape, c, b, y_array, section_dims)`` per segment.
    materials : list[dict]
        Material dict per segment (as returned by ``select_material``).
    unit_system, units : str, dict
        Active unit context (unused by the assembly itself today, but kept
        in the signature so callers can pass it uniformly with the other
        stage helpers).

    Returns
    -------
    list[dict] | None
        Segment dicts with cumulative ``start``/``end`` coordinates and
        the material/section fields resolved to SI, or ``None`` if the
        inputs are inconsistent (length mismatch / missing entries).
    """
    from solver.area_solver import area_from_section

    n = len(lengths) if lengths is not None else 0
    if not lengths or not sections or not materials:
        return None
    if not (len(sections) == n and len(materials) == n):
        return None

    segments = []
    cursor = 0.0
    for i in range(n):
        Ix, shape, c, b, y_array, section_dims = sections[i]
        mat = materials[i]
        if mat is None:
            return None
        try:
            A = area_from_section(shape, section_dims)
        except SectionGeometryError as e:
            print_error(f"Error computing area for segment {i + 1}: {e}")
            return None

        seg_len = float(lengths[i])
        start = cursor
        end = cursor + seg_len
        cursor = end

        segments.append({
            "start": start,
            "end": end,
            "length": seg_len,
            "E": float(mat["Elastic Modulus"]) * 1e9,
            "A": A,
            "I": Ix,
            "shape": shape,
            "section_dims": section_dims,
            "c": c,
            "b": b,
            "y_array": y_array,
            "material_name": mat["Material"],
            "yield_strength": float(mat["Yield Strength"]) * 1e6,
        })
    return segments


#==================================================================================
# Stage [8] helper — pre-solve validation
#==================================================================================

def validate_segments_for_solve(state_obj):
    """Return a list of human-readable problems that block solving.

    Called from the Solve stage before dispatching to
    ``solve_stepped_beam``. An empty return value means the stepped model
    is complete enough to solve.

    Checks (each adds a message on failure):
      * no segments defined
      * lengths not contiguous from 0 (gaps / overlaps / first start != 0)
      * section/material fields missing on any segment
      * ``state.beam_length`` disagrees with ``segments[-1]["end"]``

    Parameters
    ----------
    state_obj : ProjectState
        The session state (passed in explicitly so this is unit-testable
        without the module singleton).

    Returns
    -------
    list[str]
        Empty list if OK; otherwise one message per problem found.
    """
    problems = []
    segs = getattr(state_obj, "segments", None) or []
    if not segs:
        problems.append("No segments defined — define geometry, sections and materials in Stage 3/4 first.")
        return problems

    # Contiguity from 0
    if abs(float(segs[0]["start"])) > 1e-6:
        problems.append("First segment does not start at x = 0 (gaps would make the model discontinuous).")
    for i in range(len(segs) - 1):
        gap = abs(float(segs[i]["end"]) - float(segs[i + 1]["start"]))
        if gap > 1e-6:
            problems.append(f"Gap/overlap between segment {i + 1} and segment {i + 2} "
                            f"(end {segs[i]['end']:.6f} vs start {segs[i + 1]['start']:.6f}).")

    # Per-segment completeness
    for i, seg in enumerate(segs, 1):
        if not seg.get("shape"):
            problems.append(f"Segment {i} has no cross-section defined.")
        if not seg.get("material_name"):
            problems.append(f"Segment {i} has no material assigned.")
        if not seg.get("E") or float(seg["E"]) <= 0:
            problems.append(f"Segment {i} has an invalid elastic modulus.")
        if not seg.get("A") or float(seg["A"]) <= 0:
            problems.append(f"Segment {i} has an invalid cross-sectional area.")

    # beam_length consistency (now always populated for Stepped Bar under P6)
    expected_len = float(segs[-1]["end"])
    actual_len = float(getattr(state_obj, "beam_length", 0.0) or 0.0)
    if abs(actual_len - expected_len) > 1e-6:
        problems.append(f"Stored beam_length ({actual_len:.6f} m) does not match "
                        f"the segments' total length ({expected_len:.6f} m).")

    return problems


#==================================================================================
# Legacy orchestrator — kept for back-compat during P6 rollout
# (rewritten as a thin assembler of the per-stage helpers above; deleted in
#  checkpoint-B once cli.py dispatches to the helpers directly.)
#==================================================================================

def define_stepped_segments(unit_system="Metric", units=None):
    """Interactive wizard for defining stepped beam segments end-to-end.

    Legacy entry point. P6 Checkpoint-A keeps the public signature and
    behaviour but reimplements the body as an orchestrator over
    :func:`define_segment_lengths`, :func:`define_segment_section`,
    :func:`define_segment_material` and :func:`assemble_segments`.

    Returns a list of segment dicts (see module docstring for the schema),
    or ``None`` if the user cancels.
    """
    if units is None:
        units = default_units()
    l_mult = to_si(unit_system, "length")
    inv_len = 1.0 / l_mult

    # --- Segment count -----------------------------------------------------
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║              STEPPED BEAM SEGMENT DEFINITION                 ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        try:
            num_segs = int(input(colored("Enter number of segments: ➔ ", 'cyan')))
            if num_segs < 1:
                print_error("At least 1 segment required.")
                time.sleep(1.5)
                continue
            break
        except ValueError:
            print_error("Please enter a valid number.")
            time.sleep(1.5)

    # --- Lengths (total-first) ---------------------------------------------
    lengths = define_segment_lengths(num_segs, unit_system, units)
    if lengths is None:
        return None

    # --- Sections (loop with shortcuts) ------------------------------------
    sections = []
    prev = None
    i = 0
    while i < num_segs:
        result = define_segment_section(i, num_segs, units=units, prev_result=prev,
                                         unit_system=unit_system)
        if result is None:
            return None
        if result == "SAME" and prev is not None:
            sections.append(prev)
        elif result == "ALL" and prev is not None:
            # Apply previous section to this and all remaining segments.
            while i < num_segs:
                sections.append(prev)
                i += 1
            break
        else:
            sections.append(result)
            prev = result
        i += 1

    if len(sections) != num_segs:
        return None

    # --- Materials (loop) --------------------------------------------------
    materials = []
    for i in range(num_segs):
        mat = define_segment_material(i, num_segs, unit_system, units)
        if mat is None:
            print_error(f"Material selection is required for segment {i + 1}.")
            time.sleep(1.5)
            return None
        materials.append(mat)

    # --- Assemble ----------------------------------------------------------
    segments = assemble_segments(lengths, sections, materials, unit_system, units)
    if segments is None:
        return None

    total_length = segments[-1]["end"]
    print_success(f"All {num_segs} segments defined. Total length = {total_length * inv_len:.3f} {units['length']}")
    time.sleep(1.5)
    return segments
