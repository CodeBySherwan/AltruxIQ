"""
CLI for AltruxIQ — Structural FEA Suite
===================================
This script provides the command-line interface (CLI) for AltruxIQ, the structural
beam analysis & design-check suite. It handles project management, profile and
material selection, boundary conditions, load definitions, analysis, post-processing,
and project save/load functionality.
"""
# modules


import json
import os
import sys
import datetime
# pyrefly: ignore [missing-import]
import numpy as np
import time
# pyrefly: ignore [missing-import]
from termcolor import colored, cprint
# --- PATH SETUP (entry-point only) ---
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src not in sys.path:
    sys.path.insert(0, _src)
from common.paths import ensure_src_in_path, PROJECTS_FILE
from core.state import state
from common.config import SOLVER
from common.exceptions import (
    AltruxIQError,
    ValidationError,
    SectionGeometryError,
    SingularStiffnessMatrixError,
    PersistenceError,
)
ensure_src_in_path()

    
# Application modules
from database.sections_database import SectionsDatabase
from database.materials_database import MaterialDatabase  # Import MaterialDatabase class
from solver.indeterminate_solver import solve_beam
from solver.stepped_solver import solve_stepped_beam
from solver.area_solver import area_from_section
from solver import moi_solver
from plotting.main_plotting import (Matplot_Deflection, Plotly_Deflection, Plotly_sfd_bmd, Matplot_sfd_bmd, format_loads_for_plotting, Plotly_ShearStress,Matplot_ShearStress,
                      Matplot_BendingStress,Plotly_BendingStress,Plotly_combined_diagrams,Matplot_combined,
                      Plotly_AxialForce, Matplot_AxialForce,
                      Plotly_AxialDisplacement, Matplot_AxialDisplacement,
                      Plotly_CombinedStress, Matplot_CombinedStress)
from plotting.beam_plot import plot_reaction_diagram, plot_beam_schematic
try:
    from plotting.pyvista_plotting import (
        PyVista_reactions_schematic,
        PyVista_shear_force,
        PyVista_bending_moment,
        PyVista_shear_stress,
        PyVista_bending_stress,
        PyVista_deflection,
        PyVista_combined,
        PyVista_animation,
    )
    _PYVISTA_AVAILABLE = True
except ImportError as _pv_err:
    _PYVISTA_AVAILABLE = False
    _pv_import_error   = str(_pv_err)
from solver.stress_solver import (first_moment_of_area_general,
                         width_array_for_section, calculate_shear_stress,
                         calculate_bending_stress, Factor_of_Safety)
from ui.Menus import (main_menu_template, project_management_menu, profile_definition_menu, choose_profile,display_profile_info,display_analysis_info,
                 display_engineering_recommendations,display_stress_analysis,display_deflection_analysis,display_analysis_results,material_selection_menu, boundary_conditions_menu, loads_definition_menu, analysis_simulation_menu,
                 postprocessing_menu, pyvista_menu, print_success, print_error, print_option, print_title, clear_screen,unit_system_menu,get_divisor,resolution_menu,profile_source_menu,display_section_library,
                 ui_banner, ui_open, ui_close, ui_blank, ui_field, ui_text, ui_bullet, ui_head, ui_footer,
                 fmt_datetime, fmt_date_compact, fmt_duration)
from ui.inputs import Beam_Length, Beam_Supports, manage_loads, Beam_Classification, define_stepped_segments, define_continuous_supports, get_solver_resolution, define_custom_material, define_custom_supports


class NumpyEncoder(json.JSONEncoder):
    """Custom encoder that converts NumPy arrays and scalars to standard Python types for JSON."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)
# -----------------------------
# Global Storage Variables
# -----------------------------
# Unit label dictionaries — canonical definitions live in `common.units`.
# Aliased here as METRIC_LABELS / IMPERIAL_LABELS so existing references
# (`current_labels = METRIC_LABELS`, kwargs `units=current_labels`, etc.) keep working.
from common.units import METRIC_UNITS as METRIC_LABELS, IMPERIAL_UNITS as IMPERIAL_LABELS
# BUG-07 FIX: initialise post-processing outputs to None so combined plots never hit NameError

# Stepped beam globals

# -----------------------------

# =============================
# Project Management Functions
# =============================
def New_Project():
    """Start a new project by resetting the current project."""
    state.current_project = None  # Reset current project data
    state.beam_type = None        # BUG-05 FIX: reset beam_type so menu guards work correctly
    state.support_types = ("pin", "roller")  # BUG-10 FIX: reset to safe default
    num_points = SOLVER.DEFAULT_NUM_POINTS
    state.segments = []
    state.AxialForce = None
    state.AxialDisplacement = None
    state.current_unit_system = "Metric"        # <-- RESET UNITS
    state.current_labels = METRIC_LABELS
    # Reset project state flags
    state.project_state = {
        "is_loaded": False,
        "profile_saved": False, 
        "material_saved": False,
        "loads_saved": False,
        "supports_saved": False,
        "has_unsaved_changes": False
    }
    
    print_success("Starting a new project...")
    time.sleep(0.5)

# =============================
def safe_serialize(obj):
    """
    Convert non-JSON serializable objects to JSON-friendly types.
    
    Args:
        obj: Any object (e.g., numpy array, tuple).
    
    Returns:
        A list if object is numpy.ndarray or tuple; otherwise, returns object as is.
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, tuple):
        return list(obj)
    return obj

# =============================
def load_project():
    """Load a project from storage into the current session."""
    
    load_projects_from_disk()

    if not state.beam_storage:
        # Enhanced error message with better styling
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                    ⚠️  NO PROJECTS FOUND ⚠️                    ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print("\n")
        print(colored("No saved projects are available in the storage.", 'yellow'))
        print(colored("You can create a new project using the 'New Project' option.", 'white'))
        print("\n")
        state.current_project = None
        input(colored("Press Enter to return to the Project Management menu...", 'cyan', attrs=['bold']))
        return

    # Only proceed to display projects and ask for selection if projects exist
    clear_screen()
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  AVAILABLE PROJECTS                          ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    print(colored("┌─ SELECT A PROJECT "+"─"*42, 'yellow', attrs=['bold']))
    
    # Display available projects with their save date and key parameters.
    for idx, proj in enumerate(state.beam_storage, 1):
        disp_name = proj.get('base_name') or proj.get('name', 'Untitled')
        saved_lbl = proj.get('saved_display')
        if not saved_lbl and proj.get('saved_at'):
            try:
                saved_lbl = fmt_datetime(datetime.datetime.fromisoformat(proj['saved_at']))
            except (ValueError, TypeError):
                saved_lbl = None
        saved_lbl = saved_lbl or "date not recorded"
        btype = proj.get('beam_type', 'Unknown')
        blen = proj.get('beam_length', 'N/A')
        print(colored(f"│ {idx:2d} │ ", 'yellow')
              + colored(disp_name, 'cyan', attrs=['bold'])
              + colored(f"  ({btype} Beam, L = {blen} m)", 'white'))
        print(colored("│    │   ", 'yellow')
              + colored("💾 saved ", 'green') + colored(saved_lbl, 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print("\n")

    # Get user selection with better handling
    try:
        proj_choice = int(input(colored(f"Enter the number of the project you want to load [1-{len(state.beam_storage)}] ➔ ", 'cyan', attrs=['bold'])))
        
        if proj_choice < 1 or proj_choice > len(state.beam_storage):
            print_error(f"Invalid selection. Please choose a number between 1 and {len(state.beam_storage)}.")
            time.sleep(2)
            return
            
        state.current_project = state.beam_storage[proj_choice - 1]
        print_success(f"Project '{state.current_project['name']}' loaded successfully!")
        
        # ... rest of the function to load project data ...
        time.sleep(1)

        # Load beam type
        state.beam_type = state.current_project.get('beam_type', None)
        

        # Apply loaded project data to current state
        state.current_unit_system = state.current_project.get('unit_system', 'Metric')
        # Update the active dictionary based on loaded save
        if state.current_unit_system == "Imperial":
            state.current_labels = IMPERIAL_LABELS
        else:
            state.current_labels = METRIC_LABELS
            
        state.beam_length = state.current_project.get('beam_length', 0)
        state.beam_length = state.current_project.get('beam_length', 0)
        state.A = state.current_project.get('support_A_pos', 0)
        state.B = state.current_project.get('support_B_pos', 0)
        state.A_restraint = state.current_project.get('support_A_restraint', [])
        state.B_restraint = state.current_project.get('support_B_restraint', [])
        state.A_type = state.current_project.get('support_A_type', '')
        state.B_type = state.current_project.get('support_B_type', '')
        # BUG-10 FIX: restore support_types from saved data; derive from beam_type as fallback
        saved_st = state.current_project.get('support_types', None)
        if saved_st is not None:
            state.support_types = tuple(saved_st)
        elif state.beam_type == "Cantilever":
            state.support_types = ("fixed",)
        else:
            state.support_types = ("pin", "roller")
        state.num_points = state.current_project.get('num_points', SOLVER.DEFAULT_NUM_POINTS)

        # Load analysis data
        state.X_Field = np.array(state.current_project.get('X_Field', []))
        state.Total_ShearForce = np.array(state.current_project.get('Total_ShearForce', []))
        state.Total_BendingMoment = np.array(state.current_project.get('Total_BendingMoment', []))
        
        # Load Reactions natively (list of dicts)
        state.Reactions = state.current_project.get('Reactions', [])
        
        # Backward Compatibility: Convert old array format [Va, Vb, Ha] or [Va, Ha, Ma] to new dict format
        if state.Reactions and not isinstance(state.Reactions[0], dict):
            if state.beam_type == "Simple":
                state.Reactions = [
                    {"pos": state.A, "Fx": float(state.Reactions[2]), "Fy": float(state.Reactions[0]), "M": 0.0},
                    {"pos": state.B, "Fx": 0.0,                 "Fy": float(state.Reactions[1]), "M": 0.0},]
            if state.beam_type == "Overhanging Beam":
                state.Reactions = [
                    {"pos": state.A, "Fx": float(state.Reactions[2]), "Fy": float(state.Reactions[0]), "M": 0.0},
                    {"pos": state.B, "Fx": 0.0,                 "Fy": float(state.Reactions[1]), "M": 0.0},
                ]
            elif state.beam_type == "Cantilever":
                state.Reactions = [
                    {"pos": 0.0, "Fx": float(state.Reactions[1]), "Fy": float(state.Reactions[0]), "M": float(state.Reactions[2])},
                ]
            else:
                state.Reactions = []
        
        # Load and assign loads
        state.loads = state.current_project.get('loads', {})
        state.pointloads = state.loads.get("pointloads", [])
        state.distributedloads = state.loads.get("distributedloads", [])
        state.momentloads = state.loads.get("momentloads", [])
        state.triangleloads = state.loads.get("triangleloads", [])

        # Load profile data
        profile_data = state.current_project.get('profile', {})
        state.Ix = profile_data.get('Ix', 0)
        state.shape = profile_data.get('shape', '')
        state.c = profile_data.get('c', 0)
        state.b = profile_data.get('b', 0)
        state.y_array = np.array(profile_data.get('y_array', []))
        state.section_dims = profile_data.get('section_dims', {})

        # Load material data
        material_data = state.current_project.get('material', {})
        if material_data and 'material' in material_data:
            state.selected_material = material_data.get('material', {})
            if state.selected_material:
                state.density = float(state.selected_material.get("Density", 0))
                state.yield_strength = float(state.selected_material.get("Yield Strength", 0)) * 1e6
                state.ultimate_strength = float(state.selected_material.get("Ultimate Strength", 0)) * 1e6
                state.elastic_modulus = float(state.selected_material.get("Elastic Modulus", 0)) * 1e9
                state.poisson_ratio = float(state.selected_material.get("Poisson Ratio", 0))
                shear_yield_strength = 0.55 * state.yield_strength
        else:
            state.selected_material = {}

        # Load stepped beam segments if present
        state.segments = state.current_project.get('segments', [])
        if state.segments:
            state.project_state["profile_saved"] = True
            state.beam_length = state.segments[-1]["end"] if state.segments else 0.0

        # Load custom supports list if present
        state.supports_list = state.current_project.get('supports_list', [])

        # Update project state flags
        state.project_state["is_loaded"] = True
        state.project_state["profile_saved"] = bool(state.shape) and state.Ix > 0
        state.project_state["material_saved"] = bool(state.selected_material)
        state.project_state["loads_saved"] = bool(state.loads)
        state.project_state["supports_saved"] = (bool(state.A_type) and bool(state.B_type)) or bool(state.supports_list)
        state.project_state["has_unsaved_changes"] = False

        # Optional: Show confirmation summary
        print_loaded_project_summary()

    except (IndexError, ValueError):
        print_error("Invalid choice. Starting a new project instead.")
        state.current_project = None
        time.sleep(1)

# =============================
def print_loaded_project_summary():
    """Display a summary of the loaded project."""
    print(colored(f"\nLoaded Project Summary:", 'green'))
    if state.current_project and (state.current_project.get('saved_display') or state.current_project.get('saved_at')):
        _sv = state.current_project.get('saved_display')
        if not _sv:
            try:
                _sv = fmt_datetime(datetime.datetime.fromisoformat(state.current_project['saved_at']))
            except (ValueError, TypeError):
                _sv = "unknown"
        print(colored(f"Saved: {_sv}", 'green'))
    print(f"Beam Length: {state.beam_length} m")
    print(f"Supports: A : {state.A} m ({state.A_type}), B : {state.B} m ({state.B_type})")
    
    # Enhanced profile information
    if state.shape:
        print(f"Profile: {state.shape} | Ix = {state.Ix:.2e} m⁴")
    else:
        print("Profile: Not defined")
        
    # Enhanced material information
    if state.selected_material:
        print(f"Material: {state.selected_material.get('Material')} | E = {state.elastic_modulus:.2e} Pa")
    else:
        print("Material: Not defined")
        
    # Show load information if available
    if state.loads:
        total_load_count = (len(state.loads.get("pointloads", [])) + 
                          len(state.loads.get("distributedloads", [])) + 
                          len(state.loads.get("momentloads", [])) + 
                          len(state.loads.get("triangleloads", [])))
        print(f"Loads: {total_load_count} total loads defined")
    else:
        print("Loads: None defined")
        
    print("")
    input(colored("Press Enter to continue...", 'cyan'))

# =============================
def modify_loaded_project_data():
    """Allow the user to modify specific aspects of a loaded project."""
    
    if not state.project_state["is_loaded"]:
        print_error("No project is currently loaded.")
        time.sleep(1)
        return
        
    while True:
        clear_screen()
        print_title("Modify Loaded Project Data")
        print_option("1. Edit profile data")
        print_option("2. Edit material selection")
        print_option("3. Edit boundary conditions")
        print_option("4. Edit loads")
        print_option("5. Return to project management")
        print("")
        
        choice = input(colored("Enter your choice ➔ ", 'cyan'))
        
        if choice == '1':
            state.project_state["profile_saved"] = False
            state.project_state["has_unsaved_changes"] = True
            print_success("Profile data can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '2':
            state.project_state["material_saved"] = False
            state.project_state["has_unsaved_changes"] = True
            print_success("Material selection can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '3':
            if state.beam_type not in ("Cantilever", "Fixed-Fixed", "Propped", "Simple"):
                state.project_state["supports_saved"] = False
            state.project_state["has_unsaved_changes"] = True
            print_success("Boundary conditions can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '4':
            state.project_state["loads_saved"] = False
            state.project_state["has_unsaved_changes"] = True
            print_success("Loads can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '5':
            return
            
        else:
            print_error("Invalid selection. Please try again.")
            time.sleep(1)

# =============================
def delete_project():
    """
    Delete an existing project from storage.
    Lists the projects, asks for confirmation, and updates the JSON file.
    """
    load_projects_from_disk()
    
    if not state.beam_storage:
        print_error("No saved projects available to delete.")
        input("Press Enter to return to the Project Management menu...")
        return

    print_title("Delete Project")
    print_option("Select a project to delete:")
    for idx, project in enumerate(state.beam_storage):
        print_option(f"  {idx+1}. {project['name']}")
    print("")
    
    try:
        selection = int(input(colored("Enter the project number you want to delete ➔ ", 'cyan')))
        if selection < 1 or selection > len(state.beam_storage):
            print_error("Invalid project number. Operation cancelled.")
            input("Press Enter to return to the Project Management menu...")
            return
        
        project_to_delete = state.beam_storage[selection - 1]
        confirmation = input(colored(f"Are you sure you want to delete project '{project_to_delete['name']}'? (Y/N): ", 'cyan'))
        if confirmation.lower() == 'y':
            del state.beam_storage[selection - 1]
            try:
                with open(PROJECTS_FILE, 'w') as file:
                    json.dump(state.beam_storage, file, cls=NumpyEncoder, indent=4)
                print_success(f"Project '{project_to_delete['name']}' deleted successfully!")
            except (OSError, PersistenceError) as e:
                print_error(f"Error saving updated project file: {e}")
        else:
            print("Deletion cancelled.")
    except ValueError:
        print_error("Invalid input. Please enter a valid number.")

    print("")
    input("Press Enter to return to the Project Management menu...")

# =============================
# Save/Load Project Functions (To Disk)
# =============================
def save_project():
    """
    Save or update a project in memory, and persist later to disk.
    """
    
    base_name = input(colored("Enter a name for this project ➔ ", 'cyan')).strip()

    if not base_name:
        print_error("Project name cannot be empty.")
        return False

    # Auto-stamp the save with the current local date/time. The visible project
    # name carries the timestamp so the Load menu always shows when it was saved.
    now = datetime.datetime.now().astimezone()
    saved_iso = now.isoformat()
    saved_display = fmt_datetime(now)
    project_name = f"{base_name}  [{fmt_date_compact(now)}]"

    # Create proper profile data structure
    profile_data = {
        'Ix': state.Ix,
        'shape': state.shape,
        'c': state.c,
        'b': state.b,
        'y_array': safe_serialize(state.y_array),
        'section_dims': state.section_dims
    }
    
    # Create proper material data structure
    material_data = {
        'material': state.selected_material
    }
    
    # Create project data dictionary
    project_data = {
        'name': project_name,
        'base_name': base_name,
        'saved_at': saved_iso,
        'saved_display': saved_display,
        'unit_system': state.current_unit_system,
        'beam_type': state.beam_type,
        'beam_length': state.beam_length,
        'support_A_pos': state.A,
        'support_B_pos': state.B,
        'support_A_restraint': list(state.A_restraint),
        'support_B_restraint': list(state.B_restraint),
        'support_A_type': state.A_type,
        'support_B_type': state.B_type,
        'support_types': list(state.support_types),  # BUG-10 FIX: persist support_types to JSON
        'num_points': state.num_points,
        'X_Field': safe_serialize(state.X_Field),
        'Total_ShearForce': safe_serialize(state.Total_ShearForce),
        'Total_BendingMoment': safe_serialize(state.Total_BendingMoment),
        'Reactions': state.Reactions,  # NEW: Already a list of dicts, no serialization needed
        'loads': state.loads if state.loads is not None else {},
        'profile': profile_data,
        'material': material_data,
        'segments': state.segments,  # Stepped beam segments
        'supports_list': state.supports_list,  # Custom/Continuous/Stepped supports
    }


    # Detect an existing project with the same base name (ignoring the date
    # stamp) so re-saving a project updates it in place with a fresh timestamp.
    def _base_of(proj):
        return (proj.get('base_name') or proj.get('name', '')).split('  [')[0]

    for idx, proj in enumerate(state.beam_storage):
        if _base_of(proj).lower() == base_name.lower():
            confirmation = input(colored(f"Project '{base_name}' already exists. Overwrite with a new dated save? (Y/N): ", 'cyan'))
            if confirmation.lower() == 'y':
                state.beam_storage[idx] = project_data
                print_success(f"Project '{project_name}' updated successfully!")
                state.current_project = project_data
                state.project_state["has_unsaved_changes"] = False
                return True
            else:
                print("Save cancelled.")
                return False

    # Add new project
    state.beam_storage.append(project_data)
    print_success(f"Project '{project_name}' saved successfully!")
    state.current_project = project_data
    state.project_state["has_unsaved_changes"] = False
    return True

# =============================
def save_projects_to_disk():
    try:
        with open(PROJECTS_FILE, 'w') as file:
            json.dump(state.beam_storage, file, cls=NumpyEncoder, indent=4)

        print_success("Project saved to disk successfully!") # Only prints if dump succeeds
        
    except (OSError, PersistenceError) as e:
        print_error(f"Error saving projects to disk: {e}")
        # Notice there is no success print statement here

# =============================
def load_projects_from_disk():
    """
    Load projects from the JSON file into the global beam_storage.
    Initializes an empty storage if the file is not found or an error occurs.
    """
    try:
        with open(PROJECTS_FILE, 'r') as file:
            state.beam_storage = json.load(file)
        print_success("Projects loaded from disk successfully!")
    except FileNotFoundError:
        print_error("No saved project file found. Starting with empty storage.")
        state.beam_storage = []
    except json.JSONDecodeError:
        print_error("Error loading projects from disk. Starting with empty storage.")
        state.beam_storage = []

# =============================
# Material Database Functions
# =============================
def load_material_database():
    """
    Load the material database into the global variable.

    No filename argument is needed — MaterialDatabase resolves the path from
    common.paths (MATERIALS_DB_FILE). The old "Materials.json" string relied on
    Windows being case-insensitive (the file is actually "materials.json");
    the centralized default is correct on every platform.
    """
    try:
        state.Materials = MaterialDatabase()
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print_error(f"Error loading the materials database: {e}")
        time.sleep(3)

# =============================
def select_material(unit_system="Metric", units=None):
    """
    List all materials from the loaded database, convert them to the active unit system,
    prompt for a selection, and return key properties.
    """
    if units is None: units = METRIC_LABELS
    if state.Materials is None:
        print_error("Materials database is not loaded.")
        return None

    materials_list = state.Materials.all_materials 
    
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                              MATERIAL SELECTION                                  ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Grab divisors for dynamic UI conversion
    dens_div = get_divisor(units, 'density')
    stress_div = get_divisor(units, 'stress')
    mod_div = get_divisor(units, 'modulus')

    # Dynamic Table Header based on unit system
    header = colored("  # │ Material", 'yellow', attrs=['bold']) + " " * 24 + colored("│ Density │ Yield Str │ Ult Str │ E-Modulus │ Poisson │ Thermal Exp", 'yellow', attrs=['bold'])
    separator = colored("────┼────────────────────────────────────┼─────────┼───────────┼─────────┼───────────┼─────────┼─────────────", 'yellow')
    
    # Dynamic Units Row
    units_str = f"    │                                    │ {units['density']:<7} │ {units['stress']:<9} │ {units['stress']:<7} │ {units['modulus']:<9} │         │ 10⁻⁶/°C"
    print(header)
    print(separator)
    print(colored(units_str, 'white'))
    print(separator)
    
    has_shown_custom_header = False
    # Print each material with dynamically converted properties
    for index, material in enumerate(materials_list):
        is_custom = material.get("is_custom", False)
        
        # Inject the separator before the first custom item
        if is_custom and not has_shown_custom_header:
            print(separator)
            print(colored("    │ ── USER-DEFINED MATERIALS ──────── │", 'yellow', attrs=['bold']))
            print(separator)
            has_shown_custom_header = True

        if is_custom:
            mat_num = colored(f"{index + 1:3d} │", 'yellow', attrs=['bold'])
            mat_name = colored(f" {material['Material']:<28} [CUSTOM] │", 'yellow', attrs=['bold'])
        else:
            mat_num = colored(f"{index + 1:3d} │", 'light_yellow')
            mat_name = colored(f" {material['Material']:<34} │", 'light_yellow')
        
        # 1. Pull raw JSON metric data
        # 2. Multiply to get Base SI (Pa, kg/m³)
        # 3. Divide by divisor to get active display unit (ksi, MPa, etc.)
        disp_dens = material.get('Density', 0) / dens_div
        disp_yield = (material.get('Yield Strength', 0) * 1e6) / stress_div
        disp_ult = (material.get('Ultimate Strength', 0) * 1e6) / stress_div
        disp_mod = (material.get('Elastic Modulus', 0) * 1e9) / mod_div
        poisson = material.get('Poisson Ratio', 0)
        therm_exp = material.get('Thermal Expansion', 0)
        
        # Formatting the columns
        density_col = f" {int(disp_dens):<7d} │"
        yield_col = f" {int(disp_yield):<9d} │"
        ult_col = f" {int(disp_ult):<7d} │"
        mod_col = f" {int(disp_mod):<9d} │"
        poisson_col = f" {poisson:<7.2f} │"
        therm_col = f" {therm_exp:.1e}" if therm_exp else " N/A      "
        
        print(f"{mat_num}{mat_name}{density_col}{yield_col}{ult_col}{mod_col}{poisson_col}{therm_col}")
    
    print(separator)
    print("\n")
    
        # Material descriptions section
    print(colored("┌─ MATERIAL DESCRIPTIONS "+"─"*40, 'green', attrs=['bold']))
    for index, material in enumerate(materials_list):
        if 'Description' in material:
            print(colored(f"│ {index + 1:2d} │ {material['Material']}", 'green') + 
                  colored(f": {material.get('Description', '')}", 'white'))
    print(colored("└───" + "─"*57, 'green', attrs=['bold']))
    print("\n")
    
    # Get user selection
    selection = input(colored("Enter the number of the material you want to select [1-" + str(len(materials_list)) + "] ➔ ", 'cyan', attrs=['bold']))
    try:
        idx = int(selection) - 1
        if idx < 0 or idx >= len(materials_list):
            print_error("Invalid selection.")
            return None
        selected_material = materials_list[idx]
        print_success(f"You selected: {selected_material['Material']}")
        
        state.project_state["material_saved"] = True
        state.project_state["has_unsaved_changes"] = True
        
        return {
            "Material": selected_material.get("Material"),
            "Density": selected_material.get("Density"),
            "Yield Strength": selected_material.get("Yield Strength"),
            "Ultimate Strength": selected_material.get("Ultimate Strength"),
            "Elastic Modulus": selected_material.get("Elastic Modulus"),
            "Poisson Ratio": selected_material.get("Poisson Ratio"),
            "Thermal Expansion": selected_material.get("Thermal Expansion", 0),
            "Description": selected_material.get("Description", "")
        }
    except ValueError:
        print_error("Invalid input. Please enter a valid number.")
        return None

# =============================
def display_material_info(selected_material, density, yield_strength, ultimate_strength, elastic_modulus, poisson_ratio, shear_yield_strength, unit_system, units):
    """
    Display enhanced material information dynamically adjusting to the active unit system.
    """
    clear_screen()
    
    dens_div = get_divisor(units, 'density')
    stress_div = get_divisor(units, 'stress')
    mod_div = get_divisor(units, 'modulus')

    print("\n")
    print(colored("╔═════════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  MATERIAL PROPERTIES                            ║", 'cyan', attrs=['bold']))
    print(colored("╚═════════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    print("\n")
    material_name = selected_material['Material']
    description = selected_material.get('Description', 'No description available')
    
    print(colored("┌─ MATERIAL: ", 'yellow', attrs=['bold']) + colored(f"{material_name}", 'yellow', attrs=['bold']) + colored(" " + "─"*(50 - len(material_name)), 'yellow', attrs=['bold']))
    print(colored("│ ", 'yellow') + colored(f"{description}", 'white'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    print("\n")
    print(colored(f"┌─ ACTIVE UNITS ({unit_system.upper()}) " + "─"*(44 - len(unit_system)), 'green', attrs=['bold']))
    
    # Calculate display values directly from the Base SI variables you passed in
    properties_active = [
        ("Density", f"{density / dens_div:.1f} {units['density']}"),
        ("Yield Strength", f"{yield_strength / stress_div:.1f} {units['stress']}"),
        ("Ultimate Strength", f"{ultimate_strength / stress_div:.1f} {units['stress']}"),
        ("Elastic Modulus", f"{elastic_modulus / mod_div:.1f} {units['modulus']}"),
        ("Poisson Ratio", f"{poisson_ratio}"),
        ("Thermal Expansion", f"{selected_material.get('Thermal Expansion', 'N/A'):.1e} /°C" if 'Thermal Expansion' in selected_material else "N/A")
    ]
    
    for prop, value in properties_active:
        print(colored(f"│ {prop:<20}: ", 'green') + colored(f"{value}", 'white'))
    
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    print("\n")
    print(colored("┌─ INTERNAL SOLVER ENGINE (BASE SI) " + "─"*26, 'blue', attrs=['bold']))
    
    properties_si = [
        ("Density", f"{density} kg/m³"),
        ("Yield Strength", f"{yield_strength:.2e} Pa"),
        ("Ultimate Strength", f"{ultimate_strength:.2e} Pa"),
        ("Elastic Modulus", f"{elastic_modulus:.2e} Pa"),
        ("Shear Modulus*", f"{elastic_modulus/(2*(1+poisson_ratio)):.2e} Pa"),
        ("Shear Yield Strength*", f"{shear_yield_strength:.2e} Pa")
    ]
    
    for prop, value in properties_si:
        print(colored(f"│ {prop:<20}: ", 'blue') + colored(f"{value}", 'white'))
    
    print(colored("│ ", 'blue') + colored("* Calculated parameters", 'white', attrs=['dark']))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Get typical applications based on material type
    applications = "No application information available."
    if "Steel" in material_name:
        applications = "Structural beams, columns, frames, bridges, buildings, and industrial construction."
    elif "Aluminum" in material_name:
        applications = "Lightweight structures, aerospace, transportation, and architectural elements."
    elif "Concrete" in material_name:
        applications = "Building foundations, bridges, dams, floors, and structural members."
    elif "Timber" in material_name:
        applications = "Residential construction, roof trusses, floor systems, and architectural elements."
    elif "Fiber" in material_name or "CFRP" in material_name or "GFRP" in material_name:
        applications = "High-performance applications, retrofitting, reinforcement, and specialized structures."
    
    print(colored(f"│ ", 'magenta') + colored(f"{applications}", 'white'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to return to the Material Selection menu...", 'cyan', attrs=['bold']))

#===============================
def check_unsaved_changes():
    """Check if there are unsaved changes and prompt user to save."""
    
    if state.project_state["has_unsaved_changes"]:
        confirmation = input(colored("You have unsaved changes. Would you like to save them? (Y/N): ", 'cyan'))
        if confirmation.lower() == 'y':
            if save_project():
                save_projects_to_disk()
                return True
    return False

# =============================
def _session_info():
    """Assemble the live status payload shown in the SESSION/PROJECT panels."""
    name = saved = None
    if state.current_project:
        name = state.current_project.get('name') or state.current_project.get('base_name')
        saved = state.current_project.get('saved_display')
        if not saved and state.current_project.get('saved_at'):
            try:
                saved = fmt_datetime(datetime.datetime.fromisoformat(state.current_project['saved_at']))
            except (ValueError, TypeError):
                saved = None
    if state.project_state.get("has_unsaved_changes"):
        saved = None  # force the "unsaved — changes pending" badge
    steps_done = sum(bool(state.project_state.get(k)) for k in
                     ("profile_saved", "material_saved", "supports_saved", "loads_saved"))
    return {
        "name": name,
        "saved_at": saved,
        "unit_system": state.current_unit_system,
        "steps_done": steps_done,
        "steps_total": 4,
        "analysed": bool(state.project_state.get("analysis_complete")),
    }


def run_extended_menu():
    # Analysis result arrays — must be global so save_project()/load_project() and
    # the display_* helpers read the computed values, not the stale module-level
    # empties. Fixes Bug-13 (stale saves) and Bug-12 (UnboundLocalError 'segments').
    state.num_points = SOLVER.DEFAULT_NUM_POINTS
    load_material_database()
    load_projects_from_disk()
    
    state.SectionsDB = SectionsDatabase() # <--- NEW
    
    while True:
        selection = main_menu_template(state.num_points, session_info=_session_info())

        # Validate selection based on beam_type status
        if selection in ['3', '4', '5', '6', '7', '8', '9', '10'] and state.beam_type is None:
            clear_screen()
            print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
            print(colored("║                         ⚠️  WARNING ⚠️                      ║", 'red', attrs=['bold']))
            print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
            print("\n")
            print(colored("You must define a Beam Type before accessing this feature!", 'yellow', attrs=['bold']))
            print(colored("Please select option 2 from the main menu to define a beam type first.", 'yellow'))
            print("\n")
            print(colored("Valid beam types:", 'cyan'))
            print(colored("• Simple Supported Beam", 'white'))
            print(colored("• Cantilever Beam", 'white'))
            print(colored("• Continuous Beam", 'white'))
            print(colored("• Custom Beam", 'white'))  # <--- NEW
            print("\n")
            input(colored("Press Enter to return to the main menu...", 'cyan', attrs=['bold']))
            continue

        if selection == '1':  # Project Management
            while True:
                sub_choice = project_management_menu(session_info=_session_info())
                if sub_choice == '5':  # Back to main menu
                    break
                elif sub_choice == '1':  # New project
                    if state.project_state["has_unsaved_changes"]:
                        check_unsaved_changes()
                    New_Project()
                    state.beam_type = None  # Reset beam_type when starting a new project
                    break
                elif sub_choice == '2':  # Load project
                    if state.project_state["has_unsaved_changes"]:
                        check_unsaved_changes()
                    load_project()
                    # Set beam_type based on loaded project if available
                    if state.current_project and "beam_type" in state.current_project:
                        state.beam_type = state.current_project["beam_type"]
                    break
                elif sub_choice == '3':  # Modify project
                    modify_loaded_project_data()
                elif sub_choice == '4':  # Delete project
                    delete_project()
                else:
                    print_error("Invalid selection. Please try again.")
                    time.sleep(1)

        elif selection == '2':  # Define Beam Type
            while True:
                state.beam_type = Beam_Classification()
                if state.beam_type in ["Simple", "Cantilever", "Fixed-Fixed", "Propped", "Continuous", "Overhanging Beam", "Custom","Stepped Bar"]:
                    # Automatically fulfill the supports gate logic for fixed boundary types
                    if state.beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
                        state.project_state["supports_saved"] = True
                    elif state.beam_type in ("Continuous", "Overhanging Beam", "Custom", "Stepped Bar"):
                        state.project_state["supports_saved"] = False
                   
                    # Update beam_type in current_project if it exists
                    if state.current_project is not None:
                        state.current_project["beam_type"] = state.beam_type
                        state.project_state["has_unsaved_changes"] = True
                    
                    break

                else:
                    print_error("Invalid Beam Classification. Please try again.")
                    time.sleep(1)
                    continue

        # Rest of the function remains the same...
        # ... (other menu options) ...

        elif selection == '3':  # Profile Definition
            while True:
                sub_choice = profile_definition_menu(units=state.current_labels)
                if sub_choice == '4':  # Back to main menu
                    break
                elif sub_choice == '1':  # Define beam length
                    if state.project_state["is_loaded"] and state.project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a beam length defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                            
                    state.beam_length = Beam_Length(state.current_unit_system, state.current_labels)
                    state.project_state["has_unsaved_changes"] = True
                    print("")
                    cprint("==========================================================", 'red')
                    len_div = 0.3048 if state.current_unit_system == "Imperial" else 1.0
                    cprint(f"Beam Length is set to: {state.beam_length / len_div:.3f} {state.current_labels['length']}",'white')
                    cprint("==========================================================", 'red')
                    time.sleep(1)
                    
                    # Auto-define default Simple beam supports if not yet set
                    if state.beam_type == "Simple" and (state.A == 0.0 and state.B == 0.0):
                        state.A = 0.0
                        state.B = state.beam_length
                        state.A_restraint = (1, 1, 0)
                        state.B_restraint = (0, 1, 0)
                        state.A_type = "Pin Support"
                        state.B_type = "Roller Support"
                        state.support_types = ("pin", "roller")
                        state.project_state["supports_saved"] = True
                        state.project_state["has_unsaved_changes"] = True
                    
                elif sub_choice == '2':  # Choose profile
                    if state.project_state["is_loaded"] and state.project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a profile defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                    
                    # Stepped Bar: use segment definition wizard instead of single profile
                    if state.beam_type == "Stepped Bar":
                        seg_result = define_stepped_segments(state.current_unit_system, state.current_labels)
                        if seg_result is not None:
                            state.segments = seg_result
                            state.beam_length = state.segments[-1]["end"] if state.segments else 0.0
                            state.project_state["profile_saved"] = True
                            state.project_state["has_unsaved_changes"] = True
                            print_success("Stepped beam segments defined successfully!")
                            time.sleep(1.5)
                        continue
                        
                    while True:
                        src_choice = profile_source_menu()
                        if src_choice == '6':  # Back
                            break
                            
                        elif src_choice == '1':  # Manual Dimension Entry
                            clear_screen()
                            profile_choice = choose_profile()
                            print("")
                            
                            if state.beam_type is None:
                                cprint("----------------------------------------------", "white")
                                print_error("Please define a beam type first.")
                                cprint("----------------------------------------------", "white")
                                print("")
                                
                            if profile_choice == '1': result = moi_solver.inertia_moment_ibeam(units=state.current_labels)
                            elif profile_choice == '2': result = moi_solver.inertia_moment_tbeam(units=state.current_labels)
                            elif profile_choice == '3': result = moi_solver.inertia_moment_circle(units=state.current_labels)
                            elif profile_choice == '4': result = moi_solver.inertia_moment_hollow_circle(units=state.current_labels)
                            elif profile_choice == '5': result = moi_solver.inertia_moment_square(units=state.current_labels)
                            elif profile_choice == '6': result = moi_solver.inertia_moment_hollow_square(units=state.current_labels)
                            elif profile_choice == '7': result = moi_solver.inertia_moment_rectangle(units=state.current_labels)
                            elif profile_choice == '8': result = moi_solver.inertia_moment_hollow_rectangle(units=state.current_labels)
                            else:
                                print_error("Invalid choice. Please try again.")
                                continue
                                
                            if result is None:
                                print_error("Invalid input. Please try again.")
                                time.sleep(2.5)
                                continue
                                
                            state.Ix, state.shape, state.c, state.b, state.y_array, state.section_dims = result
                            state.project_state["profile_saved"] = True
                            state.project_state["has_unsaved_changes"] = True
                            print_success("Profile defined successfully!")
                            time.sleep(2)
                            break
                            
                        elif src_choice == '2':  # Standard Library
                            families = state.SectionsDB.get_standard_families()
                            if not families:
                                print_error("Standard library is empty or missing.")
                                time.sleep(2)
                                continue
                                
                            clear_screen()
                            print_title("STANDARD SECTION FAMILIES")
                            for i, fam in enumerate(families, 1):
                                print_option(f"  {i}. {fam}")
                            print_option(f"  0. Back")
                            print("")
                            
                            try:
                                fam_idx = int(input(colored("Choose a family ➔ ", 'cyan')))
                                if fam_idx == 0: continue
                                selected_family = families[fam_idx - 1]
                                sections_in_fam = state.SectionsDB.get_sections_in_family(selected_family)
                                
                                sec_idx = display_section_library(sections_in_fam, title=f"{selected_family} Sections", is_custom=False)
                                if sec_idx is not None:
                                    entry = sections_in_fam[sec_idx]
                                    result = moi_solver.load_section_from_library(entry)
                                    if result:
                                        state.Ix, state.shape, state.c, state.b, state.y_array, state.section_dims = result
                                        state.project_state["profile_saved"] = True
                                        state.project_state["has_unsaved_changes"] = True
                                        print_success(f"Loaded {entry['name']} successfully!")
                                        time.sleep(2)
                                        break
                                    else:
                                        print_error("Failed to parse section data.")
                                        time.sleep(2)
                            except (ValueError, IndexError):
                                print_error("Invalid selection.")
                                time.sleep(1)
                                
                        elif src_choice == '3':  # My Saved Sections
                            custom_secs = state.SectionsDB.list_custom_sections()
                            sec_idx = display_section_library(custom_secs, title="MY SAVED SECTIONS", is_custom=True)
                            if sec_idx is not None:
                                entry = custom_secs[sec_idx]
                                result = moi_solver.load_section_from_library(entry)
                                if result:
                                    state.Ix, state.shape, state.c, state.b, state.y_array, state.section_dims = result
                                    state.project_state["profile_saved"] = True
                                    state.project_state["has_unsaved_changes"] = True
                                    print_success(f"Loaded {entry['name']} successfully!")
                                    time.sleep(2)
                                    break
                                else:
                                    print_error("Failed to parse section data.")
                                    time.sleep(2)
                                    
                        elif src_choice == '4':  # Save Current Section
                            if not state.project_state["profile_saved"]:
                                print_error("No active profile to save. Please define one first.")
                                time.sleep(2)
                                continue
                                
                            custom_name = input(colored("Enter a name for this custom section ➔ ", 'cyan')).strip()
                            if not custom_name:
                                print_error("Name cannot be empty.")
                                time.sleep(1)
                                continue
                                
                            sec_dict = {
                                "name": custom_name,
                                "shape": state.shape,
                                "Ix": state.Ix,
                                "c": state.c,
                                "b": state.b,
                                "section_dims": state.section_dims
                            }
                            state.SectionsDB.save_custom_section(sec_dict)
                            print_success(f"Section '{custom_name}' saved successfully!")
                            time.sleep(2)

                                    
                        elif src_choice == '5':  # Delete Custom Section
                            custom_secs = state.SectionsDB.list_custom_sections()
                            if not custom_secs:
                                print_error("No custom sections available to delete.")
                                time.sleep(2)
                                continue
                                
                            sec_idx = display_section_library(custom_secs, title="DELETE CUSTOM SECTION", is_custom=True)
                            if sec_idx is not None:
                                entry = custom_secs[sec_idx]
                                sec_name = entry["name"]
                                confirm = input(colored(f"Are you sure you want to delete '{sec_name}'? (Y/N): ", 'cyan'))
                                if confirm.lower() == 'y':
                                    state.SectionsDB.delete_custom_section(sec_name)
                                    print_success(f"Deleted section '{sec_name}'.")
                                time.sleep(2)


                elif sub_choice == '3':  # View profile info
                    if not state.project_state["profile_saved"] and not state.shape:
                        print_error("No profile defined yet.")
                        time.sleep(2)
                        continue
                        
                    display_profile_info(state.beam_length, state.shape, state.Ix, state.c, state.b, state.y_array, units=state.current_labels, beam_type=state.beam_type, segments=state.segments)

        elif selection == '4':  # Material Selection
            while True:
                sub_choice = material_selection_menu(beam_type=state.beam_type, segments=state.segments, units=state.current_labels)
                if sub_choice == '5':  # Back to main menu
                    break
                elif sub_choice == '1':  # Select material
                    if state.project_state["is_loaded"] and state.project_state["material_saved"]:
                        confirmation = input(colored("Project already has a material defined. Modify? (Y/N): ", 'cyan'))
                        try:
                            if confirmation.lower() != 'y':
                                continue
                        except ValueError:
                                print_error("Invalid input. Please select a valid option.")
                                time.sleep(2)
                                continue    
                    state.selected_material = select_material(state.current_unit_system, state.current_labels)
                    if state.selected_material:
                        # For stepped bars, ask whether to apply to all or specific segment
                        if state.beam_type == "Stepped Bar" and state.segments:
                            print("\n")
                            print(colored("\u250c\u2500 APPLY MATERIAL TO " + "\u2500"*40, 'yellow', attrs=['bold']))
                            print(colored("\u2502 1. All segments", 'yellow'))
                            for idx, seg in enumerate(state.segments, 1):
                                seg_len = seg['end'] - seg['start']
                                print(colored(f"\u2502 {idx+1}. Segment {idx} ({seg['shape']}, L={seg_len:.3f} m)", 'yellow'))
                            print(colored("\u2504" + "\u2500"*57, 'yellow', attrs=['bold']))
                            print("\n")
                            mat_choice = input(colored(f"Enter your choice [1-{len(state.segments)+1}] \u2794 ", 'cyan'))
                            try:
                                mat_idx = int(mat_choice)
                                if mat_idx == 1:
                                    for seg in state.segments:
                                        seg['material_name'] = state.selected_material['Material']
                                        seg['yield_strength'] = float(state.selected_material['Yield Strength']) * 1e6
                                        seg['E'] = float(state.selected_material['Elastic Modulus']) * 1e9
                                    print_success(f"Applied {state.selected_material['Material']} to all segments!")
                                elif 2 <= mat_idx <= len(state.segments) + 1:
                                    seg_idx = mat_idx - 2
                                    state.segments[seg_idx]['material_name'] = state.selected_material['Material']
                                    state.segments[seg_idx]['yield_strength'] = float(state.selected_material['Yield Strength']) * 1e6
                                    state.segments[seg_idx]['E'] = float(state.selected_material['Elastic Modulus']) * 1e9
                                    print_success(f"Applied {state.selected_material['Material']} to Segment {seg_idx+1}!")
                                else:
                                    print_error("Invalid selection.")
                                    time.sleep(1.5)
                                    continue
                            except ValueError:
                                print_error("Invalid input.")
                                time.sleep(1.5)
                                continue
                        else:
                            state.density = float(state.selected_material["Density"])
                            state.yield_strength = float(state.selected_material["Yield Strength"]) * 1e6
                            state.ultimate_strength = float(state.selected_material["Ultimate Strength"]) * 1e6
                            state.elastic_modulus = float(state.selected_material["Elastic Modulus"]) * 1e9
                            state.poisson_ratio = float(state.selected_material["Poisson Ratio"])
                            shear_yield_strength = 0.55 * state.yield_strength
                        
                        state.project_state["material_saved"] = True
                        state.project_state["has_unsaved_changes"] = True
                        
                        cprint("==========================================================", 'red')
                        cprint("       Units Automatically Converted To Metric Units    ",'green')
                        cprint("==========================================================", 'red')
                        time.sleep(1)

                elif sub_choice == '2':  # View material info
                    if not state.project_state["material_saved"] and not state.selected_material:
                        print_error("No material selected yet.")
                        time.sleep(2)
                        continue
                    
                    # For stepped bars, ask which segment to view
                    if state.beam_type == "Stepped Bar" and state.segments:
                        print("\n")
                        print(colored("\u250c\u2500 VIEW MATERIAL FOR SEGMENT " + "\u2500"*37, 'yellow', attrs=['bold']))
                        for idx, seg in enumerate(state.segments, 1):
                            seg_len = seg['end'] - seg['start']
                            mat_name = seg.get('material_name', 'Unknown')
                            print(colored(f"\u2502 {idx}. Segment {idx} ({seg['shape']}, L={seg_len:.3f} m) \u2014 {mat_name}", 'yellow'))
                        print(colored("\u2504" + "\u2500"*57, 'yellow', attrs=['bold']))
                        print("\n")
                        view_choice = input(colored(f"Enter segment number [1-{len(state.segments)}] or 0 to cancel \u2794 ", 'cyan'))
                        try:
                            v_idx = int(view_choice)
                            if v_idx == 0:
                                continue
                            if 1 <= v_idx <= len(state.segments):
                                seg = state.segments[v_idx - 1]
                                seg_material = {
                                    'Material': seg.get('material_name', 'Unknown'),
                                    'Density': 0,
                                    'Yield Strength': seg.get('yield_strength', 0) / 1e6,
                                    'Ultimate Strength': 0,
                                    'Elastic Modulus': seg.get('E', 0) / 1e9,
                                    'Poisson Ratio': 0,
                                }
                                display_material_info(
                                    seg_material, 
                                    0, 
                                    seg.get('yield_strength', 0), 
                                    0, 
                                    seg.get('E', 0), 
                                    0, 
                                    0.55 * seg.get('yield_strength', 0),
                                    state.current_unit_system,
                                    state.current_labels
                                )
                            else:
                                print_error("Invalid selection.")
                                time.sleep(1.5)
                        except ValueError:
                            print_error("Invalid input.")
                            time.sleep(1.5)
                    else:
                        display_material_info(
                            state.selected_material, 
                            state.density, 
                            state.yield_strength, 
                            state.ultimate_strength, 
                            state.elastic_modulus, 
                            state.poisson_ratio, 
                            shear_yield_strength,
                            state.current_unit_system,
                            state.current_labels
                        )

                elif sub_choice == '3':  # Add Custom Material
                    new_mat = define_custom_material(state.current_unit_system, state.current_labels)
                    if new_mat:
                        state.Materials.add_custom_material(new_mat)
                        print_success(f"Custom material '{new_mat['Material']}' added successfully!")
                        time.sleep(2)
                        
                elif sub_choice == '4':  # Delete Custom Material
                    if not state.Materials.custom_materials:
                        print_error("No custom materials available to delete.")
                        time.sleep(2)
                        continue
                    
                    clear_screen()
                    print_title("Delete Custom Material")
                    for idx, mat in enumerate(state.Materials.custom_materials, 1):
                        print_option(f"  {idx}. {mat['Material']}")
                    print("")
                    
                    try:
                        del_idx = int(input(colored("Enter the number to delete (or 0 to cancel) ➔ ", 'cyan')))
                        if del_idx == 0:
                            continue
                        if 1 <= del_idx <= len(state.Materials.custom_materials):
                            mat_name = state.Materials.custom_materials[del_idx-1]["Material"]
                            confirm = input(colored(f"Are you sure you want to delete '{mat_name}'? (Y/N): ", 'cyan'))
                            if confirm.lower() == 'y':
                                state.Materials.delete_custom_material(mat_name)
                                print_success(f"Deleted material '{mat_name}'.")
                                # If active material was deleted, reset it
                                if state.selected_material and state.selected_material.get("Material") == mat_name:
                                    state.selected_material = ''
                                    state.project_state["material_saved"] = False
                                    print(colored("Active material was deleted. Please select a new material.", 'yellow'))
                            time.sleep(2)
                        else:
                            print_error("Invalid selection.")
                            time.sleep(1)
                    except ValueError:
                        print_error("Invalid input.")
                        time.sleep(1)

        elif selection == '5':  # Boundary Conditions
            if state.beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
                print_error(f"{state.beam_type} beams boundary conditions are automatically determined.")
                time.sleep(2)
           
           
           
            elif state.beam_type == "Simple":
                if state.beam_length <= 0:
                    print_error("Please define beam length first (Menu 3) before supports can be auto-defined.")
                    time.sleep(2)
                    continue
                if not state.project_state["supports_saved"] or (state.A == 0.0 and state.B == 0.0):
                    state.A = 0.0
                    state.B = state.beam_length
                    state.A_restraint = (1, 1, 0)
                    state.B_restraint = (0, 1, 0)
                    state.A_type = "Pin Support"
                    state.B_type = "Roller Support"
                    state.support_types = ("pin", "roller")
                    state.project_state["supports_saved"] = True
                    state.project_state["has_unsaved_changes"] = True
                    print_success("Simple beam supports auto-defined: Pin at x=0, Roller at x=L")
                else:
                    print_success("Simple beam supports already defined.")
                time.sleep(2)
                
            elif state.beam_type == "Continuous":
                state.supports_list = define_continuous_supports(state.beam_length, state.current_unit_system, state.current_labels)
                state.project_state["supports_saved"] = True
                state.project_state["has_unsaved_changes"] = True
                state.support_types = tuple(["roller" for _ in state.supports_list])  

            elif state.beam_type == "Custom":
                state.supports_list = define_custom_supports(state.beam_length, state.current_unit_system, state.current_labels)
                state.project_state["supports_saved"] = True
                state.project_state["has_unsaved_changes"] = True
                state.support_types = tuple(
                    "pin" if tuple(s["dof"]) == (1,1,0) 
                    else "fixed" if tuple(s["dof"]) == (1,1,1) 
                    else "roller" for s in state.supports_list
                )

            elif state.beam_type == "Stepped Bar":
                if not state.segments:
                    print_error("Please define stepped beam segments first (Menu 3).")
                    time.sleep(2)
                    continue
                state.supports_list = define_custom_supports(state.beam_length, state.current_unit_system, state.current_labels)
                state.project_state["supports_saved"] = True
                state.project_state["has_unsaved_changes"] = True
                state.support_types = tuple(
                    "pin" if tuple(s["dof"]) == (1,1,0) 
                    else "fixed" if tuple(s["dof"]) == (1,1,1) 
                    else "roller" for s in state.supports_list
                )

            elif state.beam_type == "Overhanging Beam":
                  while True:
                    sub_choice = boundary_conditions_menu()
                    if sub_choice == '3':  # Back to main menu
                        break   
                    elif sub_choice == '1':  # Define supports
                        if state.project_state["is_loaded"] and state.project_state["supports_saved"]:
                            confirmation = input(colored("Project already has supports defined. Modify? (Y/N): ", 'cyan'))
                            if confirmation.lower() != 'y':
                                continue
                            
                        state.A, state.B, state.A_restraint, state.B_restraint, state.A_type, state.B_type = Beam_Supports(state.current_unit_system, state.current_labels)
                        state.project_state["supports_saved"] = True
                        state.project_state["has_unsaved_changes"] = True
                        state.support_types = ("pin", "roller")
                    
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        len_div = get_divisor(state.current_labels, 'length')
                        print(f"Pin Support Position(A): {state.A / len_div:.3f} {state.current_labels['length']}")
                        print(f"Roller Support Position(B): {state.B / len_div:.3f} {state.current_labels['length']}")
                        cprint("==========================================================", 'red')
                        print("")                        
                        input("Press Enter to return to the menu...")
                    
                    elif sub_choice == '2':  # View supports
                        if not state.project_state["supports_saved"] and not state.A_type and not state.B_type:
                            print_error("No supports defined yet.")
                            time.sleep(2)
                            continue
                        
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        len_div = get_divisor(state.current_labels, 'length')
                        cprint(f"Pin Support Position(A): {state.A / len_div:.3f} {state.current_labels['length']}","white")
                        cprint(f"Roller Support Position(B): {state.B / len_div:.3f} {state.current_labels['length']}",'white')
                        cprint("==========================================================", 'red')
                        print("")
                        input("Press Enter to return to the menu...")
            else:
                print_error("Please define a beam classification first.")
                time.sleep(2)
                continue

        elif selection == '6':  # Loads Definition
            if state.beam_type is None:
                print_error("Beam classification is not defined yet.")
                time.sleep(2)
                continue
            else:
                while True:
                    sub_choice = loads_definition_menu()
                    if sub_choice == '4':  # Back to main menu
                        break
                    elif sub_choice == '1':  # Define loads
                        if state.project_state["is_loaded"] and state.project_state["loads_saved"]:
                            confirmation = input(colored("Project already has loads defined. Modify? (Y/N): ", 'cyan'))
                            if confirmation.lower() != 'y':
                                continue
                    
                        print("Define Loads:")
                        loads_dict = manage_loads(state.current_unit_system, state.current_labels, state.beam_type)
                        state.pointloads = loads_dict.get("pointloads", [])
                        state.distributedloads = loads_dict.get("distributedloads", [])
                        state.momentloads = loads_dict.get("momentloads", [])
                        state.triangleloads = loads_dict.get("triangleloads", [])
                        state.loads = loads_dict  # Store the complete dictionary for later use
                    
                        # Update project state
                        state.project_state["loads_saved"] = True
                        state.project_state["has_unsaved_changes"] = True
                    
                        print("")
                        print_success("Loads defined successfully!")
                        time.sleep(1)
                    
                    elif sub_choice == '2':  # View loads
                        if not state.project_state["loads_saved"] and not state.loads:
                            print_error("No loads defined yet.")
                            time.sleep(2)
                            continue
                        
                        clear_screen()
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                    Defined Loads:                        ", 'light_yellow')
                        cprint("==========================================================", 'red')                    
                        print_title("Current Loads:")
                        print(colored(f"\nPoint Loads: {state.loads.get('pointloads', [])}", 'white'))
                        print(colored(f"\nDistributed Loads: {state.loads.get('distributedloads', [])}", 'white'))
                        print(colored(f"\nMoment Loads: {state.loads.get('momentloads', [])}", 'white'))
                        print(colored(f"\nTriangular Loads: {state.loads.get('triangleloads', [])}", 'white'))
                        print("")
                        input("Press Enter to continue...")
                    
                    elif sub_choice == '3':  # Plot beam schematic
                        if not state.project_state["loads_saved"]:
                            print_error("Please review your entered loads.")
                            time.sleep(2)
                            continue
                        elif not state.project_state["supports_saved"]:
                            print_error("Please review your entered supports.")
                            time.sleep(2)
                            continue

                        try:
                            formatted_loads = format_loads_for_plotting(loads_dict)
                            # Single universal call handles all beam types automatically
                            plot_beam_schematic(
                                state.beam_type, state.beam_length, state.A, state.B, 
                                state.supports_list, formatted_loads, units=state.current_labels
                            )
                        except (ValueError, TypeError, OSError) as e:
                            print_error(f"Error plotting beam schematic: {e}")
                            time.sleep(2)
                    
        elif selection == '7':  # Show Beam Schematic (Standalone)
                if not state.project_state["loads_saved"]:
                    print_error("Please review your entered loads.")
                    time.sleep(2)
                    continue
                elif not state.project_state["supports_saved"]:
                    print_error("Please review your entered supports.")
                    time.sleep(2)
                    continue
                
                try:
                    formatted_loads = format_loads_for_plotting(state.loads)
                    # Single universal call handles all beam types automatically
                    plot_beam_schematic(
                        state.beam_type, state.beam_length, state.A, state.B, 
                        state.supports_list, formatted_loads, units=state.current_labels
                    )
                except (ValueError, TypeError, OSError) as e:
                    print_error(f"Error plotting beam schematic: {e}")
                    time.sleep(2)

        elif selection == '8':  # Analysis/Simulation
            while True:
                sub_choice = analysis_simulation_menu()
                if sub_choice == '5':  # Back to main menu
                    break
                    
                # Check if all required data is available for analysis
                if not state.project_state["profile_saved"] or not state.project_state["material_saved"] or \
                   not state.project_state["loads_saved"] or not state.project_state["supports_saved"]:
                    print_error("Analysis requires profile, material, supports and loads to be defined.")
                    time.sleep(2)
                    continue
                
                elif sub_choice == '1':  # Run analysis
                    try:
                        # Check if all required data is available
                        if not state.project_state["profile_saved"] or not state.project_state["material_saved"] or \
                           not state.project_state["loads_saved"] or not state.project_state["supports_saved"]:
                            print_error("Analysis requires profile, material, supports and loads to be defined.")
                            time.sleep(2)
                            continue
        
                        # Display analysis information in FEA-like format
                        display_analysis_info(
                            beam_type=state.beam_type,
                            beam_length=state.beam_length,
                            shape=state.shape,
                            selected_material=state.selected_material,
                            A=state.A,
                            B=state.B,
                            A_type=state.A_type,
                            B_type=state.B_type,
                            loads=state.loads,
                            units=state.current_labels)
                        
        
                        # Perform the analysis with proper arguments
                        # Build internal constraints array for indeterminate package
                        if state.beam_type == "Simple":
                            _supports = [
                                {"pos": state.A, "dof": (1,1,0), "ky": None, "kx": None},
                                {"pos": state.B, "dof": (0,1,0), "ky": None, "kx": None},
                            ]
                        elif state.beam_type == "Overhanging Beam":
                            _supports = [
                                {"pos": state.A, "dof": (1,1,0), "ky": None, "kx": None},
                                {"pos": state.B, "dof": (0,1,0), "ky": None, "kx": None}, 
                            ]                          
                        elif state.beam_type == "Cantilever":
                            _supports = [{"pos": 0.0, "dof": (1,1,1), "ky": None, "kx": None}]
                        elif state.beam_type == "Fixed-Fixed":
                            _supports = [
                                {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
                                {"pos": state.beam_length, "dof": (1,1,1), "ky": None, "kx": None},
                            ]
                        elif state.beam_type == "Propped":
                            _supports = [
                                {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
                                {"pos": state.beam_length, "dof": (0,1,0), "ky": None, "kx": None},
                            ]
                        elif state.beam_type == "Continuous" or state.beam_type == "Custom" or state.beam_type == "Stepped Bar":
                            _supports = state.supports_list

                        # Dispatch to appropriate solver
                        if state.beam_type == "Stepped Bar":
                            result = solve_stepped_beam(
                                segments=state.segments,
                                supports=_supports,
                                pointloads=state.pointloads,
                                distributedloads=state.distributedloads,
                                momentloads=state.momentloads,
                                triangleloads=state.triangleloads,
                                num_points=state.num_points
                            )
                        else:
                            # Invoke unified SymPy solver adapter
                            result = solve_beam(
                                beam_length=state.beam_length,
                                beam_type=state.beam_type,
                                supports=_supports,
                                pointloads=state.pointloads,
                                distributedloads=state.distributedloads,
                                momentloads=state.momentloads,
                                triangleloads=state.triangleloads,
                                E=state.elastic_modulus,
                                I=state.Ix,
                                num_points=state.num_points 
                            )
                        
                        # Populate global response arrays directly
                        state.X_Field = result["X_Field"]
                        state.Total_ShearForce = result["Total_ShearForce"]
                        state.Total_BendingMoment = result["Total_BendingMoment"]
                        state.Deflection = result["Deflection"]
                        state.Reactions = result["Reactions"]
                        state.Slopes = result["Slopes"]
                        state.Curvatures = result["Curvatures"]
                        # Stepped bar extras
                        state.AxialForce = result.get("AxialForce", None)
                        state.AxialDisplacement = result.get("AxialDisplacement", None)
                        # Analysis and deflection calculated in one pass
                        state.project_state["analysis_complete"] = True
                        state.project_state["deflection_calculated"] = True
                        state.project_state["has_unsaved_changes"] = True

                        # Safely unpack dictionary variables for the UI Display payload
                        Va = next((r["Fy"] for r in state.Reactions if r["pos"] == state.A), 0.0) if state.beam_type == "Simple" else next((r["Fy"] for r in state.Reactions if r["pos"] == 0.0), 0.0)
                        Ha = next((r["Fx"] for r in state.Reactions if r["pos"] == state.A), 0.0) if state.beam_type == "Simple" else next((r["Fx"] for r in state.Reactions if r["pos"] == 0.0), 0.0)
                        Vb = next((r["Fy"] for r in state.Reactions if r["pos"] == state.B), 0.0) if state.beam_type == "Simple" else next((r["Fy"] for r in state.Reactions if r["pos"] == state.beam_length), 0.0)
                        Ma = next((r["M"]  for r in state.Reactions if r["pos"] == 0.0), 0.0)

                        max_shear = round(np.max(state.Total_ShearForce), 3)
                        min_shear = round(np.min(state.Total_ShearForce), 3)
                        max_bending = round(np.max(state.Total_BendingMoment), 3)
                        min_bending = round(np.min(state.Total_BendingMoment), 3)
        
                        # Display analysis completion message
                        ui_banner("SOLUTION CONVERGED — ANALYSIS COMPLETE",
                                  "Stage 2 finished • proceed to Stage 3 (Post-Processing)",
                                  color='green')
                        print("\n")
                        ui_open("AVAILABLE NEXT STEPS", 'green')
                        ui_blank('green')
                        ui_bullet("View detailed solution results (reactions & internal forces).", 'white', 'green')
                        ui_bullet("Run the serviceability (deflection) limit-state check.", 'white', 'green')
                        ui_bullet("Run the strength (stress & factor-of-safety) check.", 'white', 'green')
                        ui_bullet("Open the consolidated Design-Check & Recommendations report.", 'white', 'green')
                        ui_bullet("Generate SFD/BMD, stress, deflection & 3D FEA contour plots.", 'white', 'green')
                        ui_blank('green')
                        ui_close('green')
                        ui_footer("Press Enter to return to the Solution menu...")
        
                    except (ValidationError, SingularStiffnessMatrixError, AltruxIQError) as e:
                        print_error(f"Error solving beam: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '2':  # View analysis results
                    if not state.project_state.get("analysis_complete", False):
                        print_error("No analysis results available yet. Please run analysis first.")
                        time.sleep(2)
                        continue
        
                    try:
                        # Extract key results from list of dicts
                        Va = next((r["Fy"] for r in state.Reactions if r["pos"] == state.A), 0.0) if state.beam_type == "Simple" else next((r["Fy"] for r in state.Reactions if r["pos"] == 0.0), 0.0)
                        Ha = next((r["Fx"] for r in state.Reactions if r["pos"] == state.A), 0.0) if state.beam_type == "Simple" else next((r["Fx"] for r in state.Reactions if r["pos"] == 0.0), 0.0)
                        Vb = next((r["Fy"] for r in state.Reactions if r["pos"] == state.B), 0.0) if state.beam_type == "Simple" else next((r["Fy"] for r in state.Reactions if r["pos"] == state.beam_length), 0.0)
                        Ma = next((r["M"]  for r in state.Reactions if r["pos"] == 0.0), 0.0)

                        max_shear = round(np.max(state.Total_ShearForce), 3)
                        min_shear = round(np.min(state.Total_ShearForce), 3)
                        max_bending = round(np.max(state.Total_BendingMoment), 3)
                        min_bending = round(np.min(state.Total_BendingMoment), 3)
        
                        # Display results in professional FEA-like format
                        display_analysis_results(
                            beam_type=state.beam_type,
                            shape=state.shape,
                            beam_length=state.beam_length,
                            A=state.A,
                            B=state.B,
                            Va=Va,
                            Ha=Ha,
                            Vb=Vb,
                            Ma=Ma,
                            max_shear=max_shear,
                            min_shear=min_shear,
                            max_bending=max_bending,
                            min_bending=min_bending,
                            units=state.current_labels
                        )
        
                    except (ValueError, TypeError) as e:
                        print_error(f"Error displaying analysis results: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '3':  # Calculate deflection
                    if not state.project_state.get("analysis_complete", False):
                        print_error("Please run the analysis first.")
                        time.sleep(2)
                        continue
        
                    try:
                        clear_screen()
        
                        # Show calculation in progress
                        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                        print(colored("║                CALCULATING DEFLECTION...                     ║", 'cyan', attrs=['bold']))
                        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                        print("\n")
        
                        print(colored("┌─ DEFLECTION CALCULATION PROGRESS "+"─"*28, 'yellow', attrs=['bold']))
                        print(colored("│", 'yellow'))
                        print(colored("│ ⬤ Applying Euler-Bernoulli beam theory...", 'yellow'))
                        print(colored("│ ⬤ Processing bending moment diagram...", 'yellow'))
                        print(colored("│ ⬤ Calculating beam curvature...", 'yellow'))
                        print(colored("│ ⬤ Performing first numerical integration...", 'yellow'))
                        print(colored("│ ⬤ Calculating slope profile...", 'yellow'))
                        print(colored("│ ⬤ Performing second numerical integration...", 'yellow'))
                        print(colored("│ ⬤ Applying boundary conditions...", 'yellow'))
                        print(colored("│ ⬤ Finalizing deflection profile...", 'yellow'))
                        print(colored("│", 'yellow'))
                        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))

        
                        # Display results in professional format
                        display_deflection_analysis(
                            beam_length=state.beam_length,
                            shape=state.shape,
                            beam_type=state.beam_type,
                            elastic_modulus=state.elastic_modulus,
                            Ix=state.Ix,
                            Deflection=state.Deflection,
                            Slope=state.Slopes,
                            curv=state.Curvatures,
                            units=state.current_labels
                        )
        
                    except (ValueError, TypeError) as e:
                        print_error(f"Error calculating deflection: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '4':  # Calculate stress and FOS
                    if not state.project_state.get("analysis_complete", False):
                        print_error("Please run the analysis first.")
                        time.sleep(2)
                        continue
        
                    try:
                        clear_screen()
        
                        # Show calculation in progress
                        print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
                        print(colored("║             CALCULATING STRESSES & SAFETY FACTOR...          ║", 'cyan', attrs=['bold']))
                        print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
                        print("\n")
        
                        print(colored("┌─ STRESS CALCULATION PROGRESS "+"─"*32, 'yellow', attrs=['bold']))
                        print(colored("│", 'yellow'))
                        print(colored("│ ⬤ Retrieving beam model data...", 'yellow'))
                        print(colored("│ ⬤ Computing first moment of area...", 'yellow'))
                        print(colored("│ ⬤ Calculating shear stress distribution...", 'yellow'))
                        print(colored("│ ⬤ Calculating bending stress distribution...", 'yellow'))
                        print(colored("│ ⬤ Finding maximum stress locations...", 'yellow'))
                        print(colored("│ ⬤ Computing combined stress state...", 'yellow'))
                        print(colored("│ ⬤ Evaluating factor of safety...", 'yellow'))
                        print(colored("│ ⬤ Generating stress assessment...", 'yellow'))
                        print(colored("│", 'yellow'))
                        print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
        
                        # Perform actual calculations
                        if state.beam_type == "Stepped Bar":
                            # Per-segment stress computation for stepped bars
                            # Bug-15 fix: the module-level y_array is empty for any
                            # Stepped workflow (geometry lives in each segment dict).
                            # Size the shear-stress grid from the segment's y_array,
                            # not the global — otherwise the array is (0, N) and the
                            # per-column assignment below raises a broadcast ValueError.
                            n_y = len(state.segments[0]['y_array']) if state.segments else 10001
                            state.Shear_stress = np.zeros((n_y, len(state.X_Field)))
                            state.bending_stress = np.zeros(len(state.X_Field))
                            min_fos = float('inf')
                            for i, x in enumerate(state.X_Field):
                                seg = None
                                for s in state.segments:
                                    if s['start'] <= x <= s['end']:
                                        seg = s
                                        break
                                if seg is None:
                                    continue
                                A_seg = seg['A']
                                I_seg = seg['I']
                                c_seg = seg['c']
                                b_seg = seg['b']
                                y_seg = seg['y_array']
                                shape_seg = seg['shape']
                                dims_seg = seg['section_dims']
                                ys_seg = seg['yield_strength']
                                b_arr = width_array_for_section(shape_seg, dims_seg, y_seg)
                                Q_arr = first_moment_of_area_general(b_arr, y_seg)
                                tau = calculate_shear_stress(state.Total_ShearForce[i], Q_arr, I_seg, b_arr)
                                state.Shear_stress[:, i] = tau
                                sigma = calculate_bending_stress(state.Total_BendingMoment[i], c_seg, I_seg)
                                state.bending_stress[i] = sigma
                                if ys_seg > 0:
                                    fos_pt = ys_seg / max(abs(sigma), 1e-12)
                                    if fos_pt < min_fos:
                                        min_fos = fos_pt
                            Max_Shear_stress = np.max(np.abs(state.Shear_stress))
                            Max_bending_stress = np.max(np.abs(state.bending_stress))
                            state.FOS = min_fos if min_fos != float('inf') else 0.0
                            # Use a composite material dict for display
                            if state.segments:
                                min_yield_seg = min(s.get('yield_strength', 0) for s in state.segments)
                                comp_material = {
                                    'Material': 'Varies (Stepped Bar)',
                                    'Yield Strength': min_yield_seg / 1e6,
                                }
                            else:
                                comp_material = state.selected_material
                        else:
                            #BUG-09 FIX: build section-aware b(y) for correct τ = VQ/(Ib(y))
                            b_array = width_array_for_section(state.shape, state.section_dims, state.y_array)
                            Q_array = first_moment_of_area_general(b_array, state.y_array)
                            state.Shear_stress = calculate_shear_stress(state.Total_ShearForce, Q_array, state.Ix, b_array)
                            Max_Shear_stress = np.max(np.abs(state.Shear_stress))
                            # Calculate bending stress
                            state.bending_stress = calculate_bending_stress(state.Total_BendingMoment, state.c, state.Ix)
                            Max_bending_stress = np.max(np.abs(state.bending_stress))
                            # Calculate factor of safety
                            state.FOS = Factor_of_Safety(state.Total_BendingMoment, state.c, state.yield_strength, state.Ix)
                            comp_material = state.selected_material
                        
                        # Update project state
                        state.project_state["stress_calculated"] = True
                        state.project_state["has_unsaved_changes"] = True
        
                        # Display results in professional format
                        display_stress_analysis(
                            beam_type=state.beam_type,
                            shape=state.shape,
                            selected_material=comp_material,
                            Ix=state.Ix,
                            c=state.c,
                            b=state.b,
                            y_array=state.y_array,
                            Total_ShearForce=state.Total_ShearForce,
                            Total_BendingMoment=state.Total_BendingMoment,
                            Shear_stress=state.Shear_stress,
                            Max_Shear_stress=Max_Shear_stress,
                            bending_stress=state.bending_stress,
                            Max_bending_stress=Max_bending_stress,
                            FOS=state.FOS,
                            units=state.current_labels,
                            segments=state.segments
                        )
        
                    except (ValueError, TypeError, ZeroDivisionError, SectionGeometryError) as e:
                        print_error(f"Error in stress/F.O.S calculations: {e}")
                        time.sleep(2)
                        continue
        elif selection == '9':  # Postprocessing/Visualization
            while True:
                sub_choice = postprocessing_menu(state.beam_type)
                # Menu size depends on beam_type: items 1-8 are always present,
                # items 9/10/11 (axial) exist only for Stepped Bar, then 3D FEA
                # and Back are appended. So their numbers shift by 3 for Stepped.
                # Bug-11 fix: compute these dynamically instead of hardcoding '12'.
                fea_3d_choice = '12' if state.beam_type == "Stepped Bar" else '9'
                back_choice = '13' if state.beam_type == "Stepped Bar" else '10'
                if sub_choice == back_choice:  # Back to main menu
                    break
                    
                # Check if analysis has been completed before allowing visualization
                if not state.project_state.get("analysis_complete", False):
                    print_error("Please complete an analysis before attempting visualization.")
                    time.sleep(2)
                    continue
                    
                if sub_choice == '1':  # Reaction forces schematic
                    try:
                        print_success("Processing reaction-forces schematic (Plotly)…")
                        plot_reaction_diagram(state.Reactions, units=state.current_labels)
                    except (ValueError, TypeError, OSError) as e:
                        print_error(f"Error plotting reaction diagram: {e}")
                        time.sleep(2)
                        continue
                        
                elif sub_choice == '2':  # SFD 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Force Plot (Matplotlib):")
                            Matplot_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment,'SFD',units=state.current_labels)
                        elif style == '2':
                                print_success("Processing shear force plot (Plotly)…")
                                Plotly_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment, state.beam_length,'SFD',units=state.current_labels)
                        
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '3':  # BMD 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Bending Moment Plot (Matplotlib):")
                            Matplot_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment,'BMD',units=state.current_labels)
                        elif style == '2':
                                print_success("Processing bending moment plot (Plotly)…")
                                Plotly_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment, state.beam_length,'BMD',units=state.current_labels)
 
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '4':  # SFD/BMD Combined in one plot 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Force/Bending Moment Plots (Matplotlib):")
                            Matplot_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment,'Both',units=state.current_labels)
                        elif style == '2':
                                print_success("Processing Shear Force/Bending Moment Plots(Plotly):")
                                Plotly_sfd_bmd(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment, state.beam_length,'Both',units=state.current_labels)

                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '5':  # Shear Stress
                  
                    if not state.project_state.get("stress_calculated", False):
                        print_error("Please calculate stresses first (Analysis menu → option 4).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Stress Plot (Matplotlib):")
                            Matplot_ShearStress(state.X_Field, state.Shear_stress,units=state.current_labels)

                        elif style == '2':
                            print_success("Processing Shear Stress Plot(Plotly):")
                            Plotly_ShearStress(state.X_Field, state.Shear_stress, state.beam_length,units=state.current_labels)
                            
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Error plotting Shear-Stress Plot: {e}")
                        time.sleep(2)
                elif sub_choice == '6':  # Bending Stress
                    if not state.project_state.get("stress_calculated", False):
                        print_error("Please calculate stresses first (Analysis menu → option 4).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Bending Stress Plots (Matplotlib):")
                            Matplot_BendingStress(state.X_Field, state.bending_stress, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Bending Stress Plots (Plotly):")
                            Plotly_BendingStress(state.X_Field, state.bending_stress, state.beam_length, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Error plotting Bending-Stress Plot: {e}")
                        time.sleep(2)
                elif sub_choice == '7':  # Deflection
                    if not state.project_state.get("deflection_calculated", False):
                        print_error("Please calculate deflection first (in Analysis menu).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Deflection/Displacement Plots (Matplotlib):")
                            Matplot_Deflection(state.X_Field, state.Deflection, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Deflection/Displacement Plots (Plotly):")
                            Plotly_Deflection(state.X_Field, state.Deflection, state.beam_length, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Error plotting Deflection Plot: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '8':  # Combined plots (Plotly/Matplotlib)
                    try:
                        defl_data = state.Deflection if state.project_state.get("deflection_calculated", False) else None
                        shear_data = state.Shear_stress if state.project_state.get("stress_calculated", False) else None
                        # Stepped Bar extras: include axial force & combined stress when solved
                        axial_data = state.AxialForce if (state.beam_type == "Stepped Bar" and state.AxialForce is not None) else None
                        combo_stress = None
                        if state.beam_type == "Stepped Bar" and state.AxialForce is not None and state.project_state.get("stress_calculated", False):
                            combo_stress = np.zeros_like(state.X_Field)
                            for i, x in enumerate(state.X_Field):
                                seg = next((s for s in state.segments if s["start"] <= x <= s["end"]), None)
                                if seg is None:
                                    continue
                                sigma_axial = state.AxialForce[i] / seg["A"]
                                M_val = state.Total_BendingMoment[i]
                                sigma_bending = abs(M_val) * seg["c"] / seg["I"] if seg["I"] > 0 else 0.0
                                sign = 1.0 if M_val >= 0 else -1.0
                                combo_stress[i] = sigma_axial + sign * sigma_bending

                        if defl_data is None:
                            print(colored("  ℹ  Deflection not yet calculated — will be omitted from combined plot.", 'yellow'))
                        if shear_data is None:
                            print(colored("  ℹ  Shear stress not yet calculated — will be omitted from combined plot.", 'yellow'))

                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))

                        if style == '1':
                            print_success("Processing Combined Plots (Matplotlib):")
                            Matplot_combined(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment,
                                             Deflection=defl_data, ShearStress=shear_data,
                                             AxialForce=axial_data, CombinedStress=combo_stress, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Combined Plots (Plotly):")
                            Plotly_combined_diagrams(state.X_Field, state.Total_ShearForce, state.Total_BendingMoment, state.beam_length,
                                                     Deflection=defl_data, ShearStress=shear_data,
                                                     AxialForce=axial_data, CombinedStress=combo_stress, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue

                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '9' and state.beam_type == "Stepped Bar":  # Axial-Force Plot (Stepped Bar only)
                    if state.AxialForce is None:
                        print_error("Axial Force not available. Run analysis first.")
                        time.sleep(2); continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Axial Force Plot (Matplotlib):")
                            Matplot_AxialForce(state.X_Field, state.AxialForce, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Axial Force Plot (Plotly):")
                            Plotly_AxialForce(state.X_Field, state.AxialForce, state.beam_length, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Error plotting Axial Force Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '10' and state.beam_type == "Stepped Bar":  # Axial-Displacement Plot (Stepped Bar only)
                    if state.AxialDisplacement is None:
                        print_error("Axial Displacement not available. Run analysis first.")
                        time.sleep(2); continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Axial Displacement Plot (Matplotlib):")
                            Matplot_AxialDisplacement(state.X_Field, state.AxialDisplacement, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Axial Displacement Plot (Plotly):")
                            Plotly_AxialDisplacement(state.X_Field, state.AxialDisplacement, state.beam_length, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, OSError, EOFError) as e:
                        print_error(f"Error plotting Axial Displacement Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '11' and state.beam_type == "Stepped Bar":  # Combined Stress (Stepped Bar only)
                    if state.AxialForce is None or not state.project_state.get("stress_calculated", False):
                        print_error("Run analysis and stress calculation first.")
                        time.sleep(2); continue
                    try:
                        # Compute combined stress: sigma_bending + sigma_axial
                        # For each segment, find max axial stress and combine with bending
                        combined_stress = np.zeros_like(state.X_Field)
                        for i, x in enumerate(state.X_Field):
                            # Find which segment this x belongs to
                            seg = None
                            for s in state.segments:
                                if s["start"] <= x <= s["end"]:
                                    seg = s
                                    break
                            if seg is None:
                                continue
                            A_seg = seg["A"]
                            I_seg = seg["I"]
                            c_seg = seg["c"]
                            # Axial stress
                            sigma_axial = state.AxialForce[i] / A_seg if state.AxialForce is not None else 0.0
                            # Bending stress (maximum at extreme fiber)
                            M_val = state.Total_BendingMoment[i]
                            sigma_bending = abs(M_val) * c_seg / I_seg if I_seg > 0 else 0.0
                            # Combined stress (tension positive)
                            sign = 1.0 if M_val >= 0 else -1.0  # simplistic sign handling
                            combined_stress[i] = sigma_axial + sign * sigma_bending

                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Combined Stress Plot (Matplotlib):")
                            Matplot_CombinedStress(state.X_Field, combined_stress, units=state.current_labels)
                        elif style == '2':
                            print_success("Processing Combined Stress Plot (Plotly):")
                            Plotly_CombinedStress(state.X_Field, combined_stress, state.beam_length, units=state.current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except (ValueError, TypeError, ZeroDivisionError, EOFError) as e:
                        print_error(f"Error plotting Combined Stress Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == fea_3d_choice:  # 3D FEA Contour View (PyVista)
                    if not _PYVISTA_AVAILABLE:
                        print_error(f"PyVista is not available: {_pv_import_error}")
                        print_error("Run:  pip install pyvista")
                        time.sleep(3)
                        continue

                    while True:
                        pv_choice = pyvista_menu()

                        if pv_choice == '9':  # Back to postprocessing menu
                            break

                        # Guard: analysis must be done
                        if not state.project_state.get("analysis_complete", False):
                            print_error("Please complete an analysis first.")
                            time.sleep(2)
                            continue

                        try:
                            if pv_choice == '1':  # Reactions
                                if not state.Reactions:
                                    print_error("No reaction data available. Run analysis first.")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Reactions Schematic (PyVista) ...")
                                PyVista_reactions_schematic(
                                    state.beam_length, state.Reactions, state.shape, state.section_dims,
                                    state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '2':  # Shear Force
                                print_success("Opening 3D Shear Force Contour (PyVista) ...")
                                PyVista_shear_force(
                                    state.X_Field, state.Total_ShearForce, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '3':  # Bending Moment
                                print_success("Opening 3D Bending Moment Contour (PyVista) ...")
                                PyVista_bending_moment(
                                    state.X_Field, state.Total_BendingMoment, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '4':  # Shear Stress
                                if not state.project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Shear Stress Contour (PyVista) ...")
                                PyVista_shear_stress(
                                    state.X_Field, state.Shear_stress, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '5':  # Bending Stress
                                if not state.project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Bending Stress Contour (PyVista) ...")
                                PyVista_bending_stress(
                                    state.X_Field, state.bending_stress, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '6':  # Deflection
                                if not state.project_state.get("deflection_calculated", False):
                                    print_error("Please run the analysis first (deflection is auto-calculated).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Deflection Contour (PyVista) ...")
                                PyVista_deflection(
                                    state.X_Field, state.Deflection, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b, units=state.current_labels
                                )

                            elif pv_choice == '7':  # Combined
                                print_success("Starting 3D FEA Combined Sequential Viewer (PyVista) ...")
                                defl_data   = state.Deflection     if state.project_state.get("deflection_calculated", False) else None
                                ss_data     = state.Shear_stress   if state.project_state.get("stress_calculated",     False) else None
                                bs_data     = state.bending_stress if state.project_state.get("stress_calculated",     False) else None
                                reac_data   = state.Reactions      if state.Reactions else None
                                PyVista_combined(
                                    state.X_Field, state.Total_ShearForce, state.Total_BendingMoment, state.beam_length,
                                    state.shape, state.section_dims, state.c, state.b,
                                    Deflection=defl_data,
                                    ShearStress=ss_data,
                                    BendingStress=bs_data,
                                    Reactions=reac_data,
                                    units=state.current_labels
                                )

                            elif pv_choice == '8':  # Load Animation
                                if not state.project_state.get("deflection_calculated", False):
                                    print_error("Please run the analysis first (deflection is auto-calculated).")
                                    time.sleep(2)
                                    continue

                                print(colored("\nSelect scalar to animate:", 'cyan', attrs=['bold']))
                                print(colored("  1 - Shear Force        4 - Bending Stress", 'yellow'))
                                print(colored("  2 - Bending Moment     5 - Deflection only", 'yellow'))
                                print(colored("  3 - Shear Stress       (4 & 3 require stress calc)", 'yellow'))
                                anim_choice = input(colored("Choice [1-5] ➔ ", 'cyan', attrs=['bold'])).strip()

                                result_map = {
                                    '1': "ShearForce", '2': "BendingMoment", '3': "ShearStress",
                                    '4': "BendingStress", '5': "Deflection",
                                }
                                result_key = result_map.get(anim_choice, "ShearForce")

                                if result_key in ("ShearStress", "BendingStress") and \
                                        not state.project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue

                                n_frames_input = input(colored("Number of frames [10-120, default 60] ➔ ", 'cyan')).strip()
                                n_frames = int(n_frames_input) if n_frames_input.isdigit() else 60
                                n_frames = max(10, min(n_frames, 120))

                                ss_anim = state.Shear_stress   if state.project_state.get("stress_calculated", False) else None
                                bs_anim = state.bending_stress if state.project_state.get("stress_calculated", False) else None

                                print_success(f"Opening animation: {result_key} ({n_frames} frames)...")
                                PyVista_animation(
                                    state.X_Field, state.Deflection,
                                    state.Total_ShearForce, state.Total_BendingMoment,
                                    ss_anim, bs_anim,
                                    state.beam_length, state.shape, state.section_dims, state.c, state.b,
                                    result_to_animate=result_key,
                                    n_frames=n_frames,
                                    fps=24,
                                    units=state.current_labels,
                                )

                            else:
                                print_error("Invalid selection.")
                                time.sleep(1)

                        except (ValueError, TypeError, OSError, EOFError, RuntimeError) as e:
                            print_error(f"Error in 3D FEA view: {e}")
                            time.sleep(2)
                            continue




        elif selection == '10':  # Save Project
            if not state.project_state["profile_saved"] or not state.project_state["material_saved"] or \
               not state.project_state["supports_saved"] or not state.project_state["loads_saved"]:
                print_error("You must define profile, material, supports and loads before saving.")
                time.sleep(2)
                continue
                
            try:
                save_decision = input(colored("Do you want to save this project? (Y/N) ➔ ", 'cyan'))
                print("")
                
                if save_decision.lower() == 'y':
                    if save_project():  # Use the new save_project function that takes no arguments
                        save_projects_to_disk()
                        print_success("Project saved to disk successfully!")
                    else:
                        print_error("Failed to save project.")
                else:
                    print(colored("Project not saved. Continuing...", 'yellow'))
                    print("")
                
                time.sleep(2)
                
            except (OSError, PersistenceError, EOFError) as e:
                print_error(f"Error saving project: {e}")
                time.sleep(2)
                
        elif selection == '0':  # Exit
            if state.project_state["has_unsaved_changes"]:
                check_unsaved_changes()
            
            print_success("Thank you for using AltruxIQ.")
            break

        elif selection == '11':  # Recommendations
            # Check if all necessary analyses have been done
            if not state.project_state.get("analysis_complete", False):
                print_error("Please run the basic analysis first before getting recommendations.")
                time.sleep(2)
                continue
    
            try:
                # Extract necessary data for recommendations
                span_ratio = None
                max_stress = None
                max_defl = None
        
                # If deflection has been calculated
                if state.project_state.get("deflection_calculated", False):
                    max_defl_idx = np.argmax(np.abs(state.Deflection))
                    max_defl = state.Deflection[max_defl_idx]
                    span_ratio = abs(max_defl) / state.beam_length
        
                # If stress has been calculated
                if state.project_state.get("stress_calculated", False):
                    max_stress = max(np.max(np.abs(state.bending_stress)), np.max(np.abs(state.Shear_stress)))
        
                # Display recommendations
                display_engineering_recommendations(
                    beam_type=state.beam_type,
                    shape=state.shape,
                    beam_length=state.beam_length,
                    selected_material=state.selected_material,
                    Ix=state.Ix,
                    c=state.c,
                    b=state.b,
                    FOS=state.FOS if state.project_state.get("stress_calculated", False) else None,
                    max_stress=max_stress,
                    max_defl=max_defl,
                    span_ratio=span_ratio,
                    yield_strength=state.yield_strength if 'yield_strength' in globals() else None,
                    segments=state.segments,
                    units=state.current_labels
                )
    
            except (ValueError, TypeError) as e:
                print_error(f"Error generating recommendations: {e}")
                time.sleep(2)
                continue  

        elif selection == '12':  # Unit System
            state.current_unit_system = "Metric"
            while True:
                choice = unit_system_menu(state.current_unit_system)
                if choice == '1':
                    state.current_unit_system = "Metric"
                    state.current_labels = METRIC_LABELS
                    state.project_state["has_unsaved_changes"] = True
                    print_success("Unit system changed to Metric (SI).")
                    time.sleep(1.5)
                    break
                elif choice == '2':
                    state.current_unit_system = "Imperial"
                    state.current_labels = IMPERIAL_LABELS
                    state.project_state["has_unsaved_changes"] = True
                    print_success("Unit system changed to US Customary (Imperial).")
                    time.sleep(1.5)
                    break
                elif choice == '3':
                    break
                else:
                    print_error("Invalid selection.")
                    time.sleep(1)
        elif selection == '13':  # Solver Resolution
            while True:
                res_choice = resolution_menu(state.num_points)
                if res_choice == '1':
                    state.num_points = 501
                    print_success("Resolution set to Fast Draft (501 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '2':
                    state.num_points = 1001
                    print_success("Resolution set to Standard (1001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '3':
                    state.num_points = SOLVER.DEFAULT_NUM_POINTS  # "High" tier
                    print_success("Resolution set to High (2001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '4':
                    state.num_points = 5001
                    print_success("Resolution set to Fine (5001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '5':
                    custom_pts = get_solver_resolution()
                    if custom_pts is not None:
                        state.num_points = custom_pts
                        print_success(f"Resolution set to Custom ({state.num_points} points).")
                        time.sleep(1.5)
                        break
                elif res_choice == '6':
                    break
                else:
                    print_error("Invalid selection.")
                    time.sleep(1)
 
    
        else:
            print_error("Invalid selection. Please try again.")
            time.sleep(1)


def init():
    state.current_unit_system = "Metric"
    state.current_labels = METRIC_LABELS
    num_points = SOLVER.DEFAULT_NUM_POINTS
    state.project_state = {
        "is_loaded": False,
        "profile_saved": False, 
        "material_saved": False,
        "loads_saved": False,
        "supports_saved": False,
        "analysis_complete": False,
        "deflection_calculated": False,
        "stress_calculated": False,
        "has_unsaved_changes": False
    }
# =============================
# Main Program Execution
# =============================
if __name__ == "__main__":
    # Initialize global variables for proper tracking
    init()
    # Start the extended menu-driven application
    run_extended_menu()