"""Stepped-bar segment-definition wizard.

Interactive wizard for defining stepped beam segments, each with its own
cross-section (custom dimensions, standard library, or saved sections),
material and length. Heavy dependencies (``solver``, ``ui.menus``,
``database``) are imported function-locally so that importing this module
stays cheap and free of solver-layer side effects.

Extracted from ``ui.inputs`` during the P3 ``ui/beam/`` decomposition
(checkpoint-3). Pure relocation; signatures and behavior unchanged.
"""
import time
from termcolor import colored

from common.units import to_si, default_units
from common.exceptions import SectionGeometryError
from core.state import state
from ui.console import (print_error, print_success, print_title, print_option,
                        clear_screen)
from ui.console.prompts import ask_float
from ui.materials.selector import select_material, load_material_database

#==================================================================================

def define_stepped_segments(unit_system="Metric", units=None):
    """
    Interactive wizard for defining stepped beam segments.
    Each segment has its own cross-section, material, and length.
    
    Returns a list of segment dicts:
        [
            {
                "start": float, "end": float,
                "E": float, "A": float, "I": float,
                "shape": str, "section_dims": dict,
                "c": float, "b": float, "y_array": np.ndarray,
                "material_name": str,
            }, ...
        ]
    """
    import numpy as np

    if units is None:
        units = default_units()
    
    l_mult = to_si(unit_system, "length")
    inv_len = 1.0 / l_mult
    
    # Function-local imports keep this module's import-time surface minimal:
    # the solver/Menus layers are only loaded when the wizard actually runs.
    # No sys.path surgery needed — common.paths.ensure_src_in_path handles that.
    from solver import moi_solver
    from solver.area_solver import area_from_section
    from ui.menus import choose_profile, display_section_library
    # Kit helpers (print_*/clear_screen) come from the module top.

    segments = []
    
    while True:
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored("║              STEPPED BEAM SEGMENT DEFINITION                 ║", 'cyan', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        
        if segments:
            print(colored("┌─ DEFINED SEGMENTS ─" + "─"*43, 'green', attrs=['bold']))
            for i, seg in enumerate(segments, 1):
                print(colored(f"│ {i}. {seg['shape']:15s}  L={seg['length']*inv_len:.3f} {units['length']}  E={seg['E']/1e9:.1f} GPa  A={seg['A']*1e6:.2f} mm²  I={seg['I']*1e12:.2e} mm⁴", 'white'))
            print(colored("└" + "─"*62, 'green', attrs=['bold']))
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
    
    total_length = 0.0
    
    for i in range(num_segs):
        clear_screen()
        print(colored(f"╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
        print(colored(f"║           DEFINING SEGMENT {i+1} OF {num_segs}                             ║", 'cyan', attrs=['bold']))
        print(colored(f"╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
        print("")
        
        # Segment length
        seg_len_raw = ask_float(f"Segment {i+1} length", unit=units['length'], minimum=0, exclusive_min=True, allow_cancel=True)
        if seg_len_raw is None:
            return None
        seg_len = seg_len_raw * l_mult
        
        # Cross-section selection
        print("")
        print(colored("┌─ SELECT CROSS-SECTION FOR THIS SEGMENT ─" + "─"*20, 'yellow', attrs=['bold']))
        
        from database.sections_database import SectionsDatabase
        sections_db = SectionsDatabase()
        
        while True:
            print_option("  1. ✍️  Enter Custom Dimensions (Manual)")
            print_option("  2. 📚 Standard Section Library")
            print_option("  3. 💾 My Saved Sections")
            print("")
            src_choice = input(colored("Choose option [1-3] ➔ ", 'cyan')).strip()
            
            result = None
            if src_choice == '1':
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
                    continue
                if result is None:
                    print_error("Invalid dimensions entered. Try again.")
                    continue
                break
                
            elif src_choice == '2':
                families = sections_db.get_standard_families()
                if not families:
                    print_error("Standard library is empty or missing.")
                    continue
                clear_screen()
                print_title("STANDARD SECTION FAMILIES")
                for j, fam in enumerate(families, 1):
                    print_option(f"  {j}. {fam}")
                print_option(f"  0. Back")
                print("")
                try:
                    fam_idx = int(input(colored("Choose a family ➔ ", 'cyan')))
                    if fam_idx == 0: continue
                    selected_family = families[fam_idx - 1]
                    sections_in_fam = sections_db.get_sections_in_family(selected_family)
                    sec_idx = display_section_library(sections_in_fam, title=f"{selected_family} Sections", is_custom=False)
                    if sec_idx is not None:
                        entry = sections_in_fam[sec_idx]
                        result = moi_solver.load_section_from_library(entry)
                        if result:
                            break
                        else:
                            print_error("Failed to parse section data.")
                except (ValueError, IndexError):
                    print_error("Invalid selection.")
                    time.sleep(1)
                    continue
                    
            elif src_choice == '3':
                custom_secs = sections_db.list_custom_sections()
                if not custom_secs:
                    print_error("No saved custom sections found.")
                    continue
                sec_idx = display_section_library(custom_secs, title="MY SAVED SECTIONS", is_custom=True)
                if sec_idx is not None:
                    entry = custom_secs[sec_idx]
                    result = moi_solver.load_section_from_library(entry)
                    if result:
                        break
                    else:
                        print_error("Failed to parse section data.")
            else:
                print_error("Invalid choice. Please enter 1, 2, or 3.")
        
        Ix, shape, c, b, y_array, section_dims = result
        
        # Compute cross-sectional area
        try:
            A = area_from_section(shape, section_dims)
        except SectionGeometryError as e:
            print_error(f"Error computing area: {e}")
            time.sleep(2)
            return None
        
        # Material selection from library
        print("")
        print(colored("┌─ SELECT MATERIAL FOR THIS SEGMENT ─" + "─"*20, 'magenta', attrs=['bold']))

        # select_material / load_material_database imported eagerly at module
        # top from ui.materials.selector (leaf module — no circular import).
        if state.Materials is None:
            load_material_database()

        selected_mat = select_material(unit_system, units)
        if selected_mat is None:
            print_error("Material selection is required for segment.")
            time.sleep(1.5)
            return None
            
        E = float(selected_mat["Elastic Modulus"]) * 1e9
        E_gpa = float(selected_mat["Elastic Modulus"])
        yield_mpa = float(selected_mat["Yield Strength"])
        material_name = selected_mat["Material"]
        
        seg_start = total_length
        seg_end = total_length + seg_len
        total_length = seg_end
        
        segments.append({
            "start": seg_start,
            "end": seg_end,
            "length": seg_len,
            "E": E,
            "A": A,
            "I": Ix,
            "shape": shape,
            "section_dims": section_dims,
            "c": c,
            "b": b,
            "y_array": y_array,
            "material_name": material_name,
            "yield_strength": yield_mpa * 1e6,
        })
        
        print_success(f"Segment {i+1} defined: {shape}, L={seg_len*inv_len:.3f} {units['length']}")
        time.sleep(1)
    
    print_success(f"All {num_segs} segments defined. Total length = {total_length*inv_len:.3f} {units['length']}")
    time.sleep(1.5)
    return segments
