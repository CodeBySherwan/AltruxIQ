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
current_unit_system = "Metric"
# Unit label dictionaries — canonical definitions live in `common.units`.
# Aliased here as METRIC_LABELS / IMPERIAL_LABELS so existing references
# (`current_labels = METRIC_LABELS`, kwargs `units=current_labels`, etc.) keep working.
from common.units import METRIC_UNITS as METRIC_LABELS, IMPERIAL_UNITS as IMPERIAL_LABELS
current_labels = METRIC_LABELS  # <-- Tracks active dictionary
beam_storage = []      # List to hold all saved projects
current_project = None # Dictionary holding the currently loaded project
Materials = None       # Placeholder for the materials database object
SectionsDB = None
current_unit_system = 'SI'  # Units System
beam_length = 0.0
A = 0.0
B = 0.0
A_restraint = []
B_restraint = []
A_type = ""
B_type = ""
X_Field = np.array([])
Total_ShearForce = np.array([])
Total_BendingMoment = np.array([])
Reactions = np.array([])
loads = {}
selected_material = ''
Ix = 0.0
shape = ""
c = 0.0
b = 0.0
y_array = np.array([])
section_dims = {}
support_types = ("pin", "roller")  # BUG-10 FIX: module-level default; overwritten on load/save
beam_type = None  # BUG-05 FIX: initialise at module level to prevent NameError
num_points = 2001
supports_list = []  # NEW: Used for Continuous multi-span beams
# BUG-07 FIX: initialise post-processing outputs to None so combined plots never hit NameError
Deflection = None
Slope = None
Shear_stress = None
bending_stress = None
FOS = None

# Stepped beam globals
segments = []          # list of segment dicts for stepped beams
AxialForce = None
AxialDisplacement = None

project_state = {
    "is_loaded": False,
    "profile_saved": False, 
    "material_saved": False,
    "loads_saved": False,
    "supports_saved": False,
    "has_unsaved_changes": False
}
# -----------------------------

# =============================
# Project Management Functions
# =============================
def New_Project():
    """Start a new project by resetting the current project."""
    global current_project, project_state, beam_type, support_types, current_unit_system, current_labels
    global segments, AxialForce, AxialDisplacement
    current_project = None  # Reset current project data
    beam_type = None        # BUG-05 FIX: reset beam_type so menu guards work correctly
    support_types = ("pin", "roller")  # BUG-10 FIX: reset to safe default
    num_points = 2001
    segments = []
    AxialForce = None
    AxialDisplacement = None
    current_unit_system = "Metric"        # <-- RESET UNITS
    current_labels = METRIC_LABELS
    # Reset project state flags
    project_state = {
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
    global current_project, beam_length, A, B, A_restraint, B_restraint, A_type, B_type
    global X_Field, Total_ShearForce, Total_BendingMoment, Reactions, loads
    global Ix, shape, c, b, y_array, section_dims, project_state
    global elastic_modulus, selected_material, density, yield_strength, ultimate_strength, poisson_ratio, shear_yield_strength
    global pointloads, distributedloads, momentloads, triangleloads
    global beam_type, support_types , current_unit_system, supports_list
    global segments, AxialForce, AxialDisplacement
    
    load_projects_from_disk()

    if not beam_storage:
        # Enhanced error message with better styling
        clear_screen()
        print(colored("╔══════════════════════════════════════════════════════════════╗", 'red', attrs=['bold']))
        print(colored("║                    ⚠️  NO PROJECTS FOUND ⚠️                    ║", 'red', attrs=['bold']))
        print(colored("╚══════════════════════════════════════════════════════════════╝", 'red', attrs=['bold']))
        print("\n")
        print(colored("No saved projects are available in the storage.", 'yellow'))
        print(colored("You can create a new project using the 'New Project' option.", 'white'))
        print("\n")
        current_project = None
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
    for idx, proj in enumerate(beam_storage, 1):
        disp_name = proj.get('base_name') or proj.get('name', 'Untitled')
        saved_lbl = proj.get('saved_display')
        if not saved_lbl and proj.get('saved_at'):
            try:
                saved_lbl = fmt_datetime(datetime.datetime.fromisoformat(proj['saved_at']))
            except Exception:
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
        proj_choice = int(input(colored(f"Enter the number of the project you want to load [1-{len(beam_storage)}] ➔ ", 'cyan', attrs=['bold'])))
        
        if proj_choice < 1 or proj_choice > len(beam_storage):
            print_error(f"Invalid selection. Please choose a number between 1 and {len(beam_storage)}.")
            time.sleep(2)
            return
            
        current_project = beam_storage[proj_choice - 1]
        print_success(f"Project '{current_project['name']}' loaded successfully!")
        
        # ... rest of the function to load project data ...
        time.sleep(1)

        # Load beam type
        beam_type = current_project.get('beam_type', None)
        

        # Apply loaded project data to current state
        current_unit_system = current_project.get('unit_system', 'Metric')
        # Update the active dictionary based on loaded save
        global current_labels
        if current_unit_system == "Imperial":
            current_labels = IMPERIAL_LABELS
        else:
            current_labels = METRIC_LABELS
            
        beam_length = current_project.get('beam_length', 0)
        beam_length = current_project.get('beam_length', 0)
        A = current_project.get('support_A_pos', 0)
        B = current_project.get('support_B_pos', 0)
        A_restraint = current_project.get('support_A_restraint', [])
        B_restraint = current_project.get('support_B_restraint', [])
        A_type = current_project.get('support_A_type', '')
        B_type = current_project.get('support_B_type', '')
        # BUG-10 FIX: restore support_types from saved data; derive from beam_type as fallback
        saved_st = current_project.get('support_types', None)
        if saved_st is not None:
            support_types = tuple(saved_st)
        elif beam_type == "Cantilever":
            support_types = ("fixed",)
        else:
            support_types = ("pin", "roller")
        num_points = current_project.get('num_points', 2001)

        # Load analysis data
        X_Field = np.array(current_project.get('X_Field', []))
        Total_ShearForce = np.array(current_project.get('Total_ShearForce', []))
        Total_BendingMoment = np.array(current_project.get('Total_BendingMoment', []))
        
        # Load Reactions natively (list of dicts)
        Reactions = current_project.get('Reactions', [])
        
        # Backward Compatibility: Convert old array format [Va, Vb, Ha] or [Va, Ha, Ma] to new dict format
        if Reactions and not isinstance(Reactions[0], dict):
            if beam_type == "Simple":
                Reactions = [
                    {"pos": A, "Fx": float(Reactions[2]), "Fy": float(Reactions[0]), "M": 0.0},
                    {"pos": B, "Fx": 0.0,                 "Fy": float(Reactions[1]), "M": 0.0},]
            if beam_type == "Overhanging Beam":
                Reactions = [
                    {"pos": A, "Fx": float(Reactions[2]), "Fy": float(Reactions[0]), "M": 0.0},
                    {"pos": B, "Fx": 0.0,                 "Fy": float(Reactions[1]), "M": 0.0},
                ]
            elif beam_type == "Cantilever":
                Reactions = [
                    {"pos": 0.0, "Fx": float(Reactions[1]), "Fy": float(Reactions[0]), "M": float(Reactions[2])},
                ]
            else:
                Reactions = []
        
        # Load and assign loads
        loads = current_project.get('loads', {})
        pointloads = loads.get("pointloads", [])
        distributedloads = loads.get("distributedloads", [])
        momentloads = loads.get("momentloads", [])
        triangleloads = loads.get("triangleloads", [])

        # Load profile data
        profile_data = current_project.get('profile', {})
        Ix = profile_data.get('Ix', 0)
        shape = profile_data.get('shape', '')
        c = profile_data.get('c', 0)
        b = profile_data.get('b', 0)
        y_array = np.array(profile_data.get('y_array', []))
        section_dims = profile_data.get('section_dims', {})

        # Load material data
        material_data = current_project.get('material', {})
        if material_data and 'material' in material_data:
            selected_material = material_data.get('material', {})
            if selected_material:
                density = float(selected_material.get("Density", 0))
                yield_strength = float(selected_material.get("Yield Strength", 0)) * 1e6
                ultimate_strength = float(selected_material.get("Ultimate Strength", 0)) * 1e6
                elastic_modulus = float(selected_material.get("Elastic Modulus", 0)) * 1e9
                poisson_ratio = float(selected_material.get("Poisson Ratio", 0))
                shear_yield_strength = 0.55 * yield_strength
        else:
            selected_material = {}

        # Load stepped beam segments if present
        segments = current_project.get('segments', [])
        if segments:
            project_state["profile_saved"] = True
            beam_length = segments[-1]["end"] if segments else 0.0

        # Load custom supports list if present
        supports_list = current_project.get('supports_list', [])

        # Update project state flags
        project_state["is_loaded"] = True
        project_state["profile_saved"] = bool(shape) and Ix > 0
        project_state["material_saved"] = bool(selected_material)
        project_state["loads_saved"] = bool(loads)
        project_state["supports_saved"] = (bool(A_type) and bool(B_type)) or bool(supports_list)
        project_state["has_unsaved_changes"] = False

        # Optional: Show confirmation summary
        print_loaded_project_summary()

    except (IndexError, ValueError):
        print_error("Invalid choice. Starting a new project instead.")
        current_project = None
        time.sleep(1)

# =============================
def print_loaded_project_summary():
    """Display a summary of the loaded project."""
    print(colored(f"\nLoaded Project Summary:", 'green'))
    if current_project and (current_project.get('saved_display') or current_project.get('saved_at')):
        _sv = current_project.get('saved_display')
        if not _sv:
            try:
                _sv = fmt_datetime(datetime.datetime.fromisoformat(current_project['saved_at']))
            except Exception:
                _sv = "unknown"
        print(colored(f"Saved: {_sv}", 'green'))
    print(f"Beam Length: {beam_length} m")
    print(f"Supports: A : {A} m ({A_type}), B : {B} m ({B_type})")
    
    # Enhanced profile information
    if shape:
        print(f"Profile: {shape} | Ix = {Ix:.2e} m⁴")
    else:
        print("Profile: Not defined")
        
    # Enhanced material information
    if selected_material:
        print(f"Material: {selected_material.get('Material')} | E = {elastic_modulus:.2e} Pa")
    else:
        print("Material: Not defined")
        
    # Show load information if available
    if loads:
        total_load_count = (len(loads.get("pointloads", [])) + 
                          len(loads.get("distributedloads", [])) + 
                          len(loads.get("momentloads", [])) + 
                          len(loads.get("triangleloads", [])))
        print(f"Loads: {total_load_count} total loads defined")
    else:
        print("Loads: None defined")
        
    print("")
    input(colored("Press Enter to continue...", 'cyan'))

# =============================
def modify_loaded_project_data():
    """Allow the user to modify specific aspects of a loaded project."""
    global project_state
    
    if not project_state["is_loaded"]:
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
            project_state["profile_saved"] = False
            project_state["has_unsaved_changes"] = True
            print_success("Profile data can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '2':
            project_state["material_saved"] = False
            project_state["has_unsaved_changes"] = True
            print_success("Material selection can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '3':
            if beam_type not in ("Cantilever", "Fixed-Fixed", "Propped", "Simple"):
                project_state["supports_saved"] = False
            project_state["has_unsaved_changes"] = True
            print_success("Boundary conditions can now be modified.")
            time.sleep(1)
            return
            
        elif choice == '4':
            project_state["loads_saved"] = False
            project_state["has_unsaved_changes"] = True
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
    global beam_storage
    load_projects_from_disk()
    
    if not beam_storage:
        print_error("No saved projects available to delete.")
        input("Press Enter to return to the Project Management menu...")
        return

    print_title("Delete Project")
    print_option("Select a project to delete:")
    for idx, project in enumerate(beam_storage):
        print_option(f"  {idx+1}. {project['name']}")
    print("")
    
    try:
        selection = int(input(colored("Enter the project number you want to delete ➔ ", 'cyan')))
        if selection < 1 or selection > len(beam_storage):
            print_error("Invalid project number. Operation cancelled.")
            input("Press Enter to return to the Project Management menu...")
            return
        
        project_to_delete = beam_storage[selection - 1]
        confirmation = input(colored(f"Are you sure you want to delete project '{project_to_delete['name']}'? (Y/N): ", 'cyan'))
        if confirmation.lower() == 'y':
            del beam_storage[selection - 1]
            try:
                with open(PROJECTS_FILE, 'w') as file:
                    json.dump(beam_storage, file, cls=NumpyEncoder, indent=4)
                print_success(f"Project '{project_to_delete['name']}' deleted successfully!")
            except Exception as e:
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
    global beam_storage, current_project, project_state, beam_type, support_types
    
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
        'Ix': Ix,
        'shape': shape,
        'c': c,
        'b': b,
        'y_array': safe_serialize(y_array),
        'section_dims': section_dims
    }
    
    # Create proper material data structure
    material_data = {
        'material': selected_material
    }
    
    # Create project data dictionary
    project_data = {
        'name': project_name,
        'base_name': base_name,
        'saved_at': saved_iso,
        'saved_display': saved_display,
        'unit_system': current_unit_system,
        'beam_type': beam_type,
        'beam_length': beam_length,
        'support_A_pos': A,
        'support_B_pos': B,
        'support_A_restraint': list(A_restraint),
        'support_B_restraint': list(B_restraint),
        'support_A_type': A_type,
        'support_B_type': B_type,
        'support_types': list(support_types),  # BUG-10 FIX: persist support_types to JSON
        'num_points': num_points,
        'X_Field': safe_serialize(X_Field),
        'Total_ShearForce': safe_serialize(Total_ShearForce),
        'Total_BendingMoment': safe_serialize(Total_BendingMoment),
        'Reactions': Reactions,  # NEW: Already a list of dicts, no serialization needed
        'loads': loads if loads is not None else {},
        'profile': profile_data,
        'material': material_data,
        'segments': segments,  # Stepped beam segments
        'supports_list': supports_list,  # Custom/Continuous/Stepped supports
    }


    # Detect an existing project with the same base name (ignoring the date
    # stamp) so re-saving a project updates it in place with a fresh timestamp.
    def _base_of(proj):
        return (proj.get('base_name') or proj.get('name', '')).split('  [')[0]

    for idx, proj in enumerate(beam_storage):
        if _base_of(proj).lower() == base_name.lower():
            confirmation = input(colored(f"Project '{base_name}' already exists. Overwrite with a new dated save? (Y/N): ", 'cyan'))
            if confirmation.lower() == 'y':
                beam_storage[idx] = project_data
                print_success(f"Project '{project_name}' updated successfully!")
                current_project = project_data
                project_state["has_unsaved_changes"] = False
                return True
            else:
                print("Save cancelled.")
                return False

    # Add new project
    beam_storage.append(project_data)
    print_success(f"Project '{project_name}' saved successfully!")
    current_project = project_data
    project_state["has_unsaved_changes"] = False
    return True

# =============================
def save_projects_to_disk():
    try:
        with open(PROJECTS_FILE, 'w') as file:
            json.dump(beam_storage, file, cls=NumpyEncoder, indent=4)

        print_success("Project saved to disk successfully!") # Only prints if dump succeeds
        
    except Exception as e:
        print_error(f"Error saving projects to disk: {e}")
        # Notice there is no success print statement here

# =============================
def load_projects_from_disk():
    """
    Load projects from the JSON file into the global beam_storage.
    Initializes an empty storage if the file is not found or an error occurs.
    """
    global beam_storage
    try:
        with open(PROJECTS_FILE, 'r') as file:
            beam_storage = json.load(file)
        print_success("Projects loaded from disk successfully!")
    except FileNotFoundError:
        print_error("No saved project file found. Starting with empty storage.")
        beam_storage = []
    except json.JSONDecodeError:
        print_error("Error loading projects from disk. Starting with empty storage.")
        beam_storage = []

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
    global Materials
    try:
        Materials = MaterialDatabase()
    except Exception as e:
        print_error(f"Error loading the materials database: {e}")
        time.sleep(3)

# =============================
def select_material(unit_system="Metric", units=None):
    """
    List all materials from the loaded database, convert them to the active unit system,
    prompt for a selection, and return key properties.
    """
    global Materials, project_state
    if units is None: units = METRIC_LABELS
    if Materials is None:
        print_error("Materials database is not loaded.")
        return None

    materials_list = Materials.all_materials 
    
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
        
        project_state["material_saved"] = True
        project_state["has_unsaved_changes"] = True
        
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
    global project_state
    
    if project_state["has_unsaved_changes"]:
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
    if current_project:
        name = current_project.get('name') or current_project.get('base_name')
        saved = current_project.get('saved_display')
        if not saved and current_project.get('saved_at'):
            try:
                saved = fmt_datetime(datetime.datetime.fromisoformat(current_project['saved_at']))
            except Exception:
                saved = None
    if project_state.get("has_unsaved_changes"):
        saved = None  # force the "unsaved — changes pending" badge
    steps_done = sum(bool(project_state.get(k)) for k in
                     ("profile_saved", "material_saved", "supports_saved", "loads_saved"))
    return {
        "name": name,
        "saved_at": saved,
        "unit_system": current_unit_system,
        "steps_done": steps_done,
        "steps_total": 4,
        "analysed": bool(project_state.get("analysis_complete")),
    }


def run_extended_menu():
    global current_unit_system, current_labels
    global current_project, project_state
    global beam_length, A, B, A_restraint, B_restraint, A_type, B_type
    global Ix, shape, c, b, y_array, section_dims
    global selected_material, density, yield_strength, ultimate_strength, elastic_modulus, poisson_ratio, shear_yield_strength
    global pointloads, distributedloads, momentloads, triangleloads, loads
    global support_types, supports_list
    global beam_type  # Ensure we can access the beam_type variable
    # Analysis result arrays — must be global so save_project()/load_project() and
    # the display_* helpers read the computed values, not the stale module-level
    # empties. Fixes Bug-13 (stale saves) and Bug-12 (UnboundLocalError 'segments').
    global num_points
    global X_Field, Total_ShearForce, Total_BendingMoment
    global Deflection, Slopes, Curvatures, Reactions
    global Shear_stress, bending_stress, FOS
    global segments, AxialForce, AxialDisplacement
    num_points = 2001
    load_material_database()
    load_projects_from_disk()
    
    global SectionsDB           # <--- NEW
    SectionsDB = SectionsDatabase() # <--- NEW
    
    while True:
        selection = main_menu_template(num_points, session_info=_session_info())

        # Validate selection based on beam_type status
        if selection in ['3', '4', '5', '6', '7', '8', '9', '10'] and beam_type is None:
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
                    if project_state["has_unsaved_changes"]:
                        check_unsaved_changes()
                    New_Project()
                    beam_type = None  # Reset beam_type when starting a new project
                    break
                elif sub_choice == '2':  # Load project
                    if project_state["has_unsaved_changes"]:
                        check_unsaved_changes()
                    load_project()
                    # Set beam_type based on loaded project if available
                    if current_project and "beam_type" in current_project:
                        beam_type = current_project["beam_type"]
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
                beam_type = Beam_Classification()
                if beam_type in ["Simple", "Cantilever", "Fixed-Fixed", "Propped", "Continuous", "Overhanging Beam", "Custom","Stepped Bar"]:
                    # Automatically fulfill the supports gate logic for fixed boundary types
                    if beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
                        project_state["supports_saved"] = True
                    elif beam_type in ("Continuous", "Overhanging Beam", "Custom", "Stepped Bar"):
                        project_state["supports_saved"] = False
                   
                    # Update beam_type in current_project if it exists
                    if current_project is not None:
                        current_project["beam_type"] = beam_type
                        project_state["has_unsaved_changes"] = True
                    
                    break

                else:
                    print_error("Invalid Beam Classification. Please try again.")
                    time.sleep(1)
                    continue

        # Rest of the function remains the same...
        # ... (other menu options) ...

        elif selection == '3':  # Profile Definition
            while True:
                sub_choice = profile_definition_menu(units=current_labels)
                if sub_choice == '4':  # Back to main menu
                    break
                elif sub_choice == '1':  # Define beam length
                    if project_state["is_loaded"] and project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a beam length defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                            
                    beam_length = Beam_Length(current_unit_system, current_labels)
                    project_state["has_unsaved_changes"] = True
                    print("")
                    cprint("==========================================================", 'red')
                    len_div = 0.3048 if current_unit_system == "Imperial" else 1.0
                    cprint(f"Beam Length is set to: {beam_length / len_div:.3f} {current_labels['length']}",'white')
                    cprint("==========================================================", 'red')
                    time.sleep(1)
                    
                    # Auto-define default Simple beam supports if not yet set
                    if beam_type == "Simple" and (A == 0.0 and B == 0.0):
                        A = 0.0
                        B = beam_length
                        A_restraint = (1, 1, 0)
                        B_restraint = (0, 1, 0)
                        A_type = "Pin Support"
                        B_type = "Roller Support"
                        support_types = ("pin", "roller")
                        project_state["supports_saved"] = True
                        project_state["has_unsaved_changes"] = True
                    
                elif sub_choice == '2':  # Choose profile
                    if project_state["is_loaded"] and project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a profile defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                    
                    # Stepped Bar: use segment definition wizard instead of single profile
                    if beam_type == "Stepped Bar":
                        seg_result = define_stepped_segments(current_unit_system, current_labels)
                        if seg_result is not None:
                            segments = seg_result
                            beam_length = segments[-1]["end"] if segments else 0.0
                            project_state["profile_saved"] = True
                            project_state["has_unsaved_changes"] = True
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
                            
                            if beam_type is None:
                                cprint("----------------------------------------------", "white")
                                print_error("Please define a beam type first.")
                                cprint("----------------------------------------------", "white")
                                print("")
                                
                            if profile_choice == '1': result = moi_solver.inertia_moment_ibeam(units=current_labels)
                            elif profile_choice == '2': result = moi_solver.inertia_moment_tbeam(units=current_labels)
                            elif profile_choice == '3': result = moi_solver.inertia_moment_circle(units=current_labels)
                            elif profile_choice == '4': result = moi_solver.inertia_moment_hollow_circle(units=current_labels)
                            elif profile_choice == '5': result = moi_solver.inertia_moment_square(units=current_labels)
                            elif profile_choice == '6': result = moi_solver.inertia_moment_hollow_square(units=current_labels)
                            elif profile_choice == '7': result = moi_solver.inertia_moment_rectangle(units=current_labels)
                            elif profile_choice == '8': result = moi_solver.inertia_moment_hollow_rectangle(units=current_labels)
                            else:
                                print_error("Invalid choice. Please try again.")
                                continue
                                
                            if result is None:
                                print_error("Invalid input. Please try again.")
                                time.sleep(2.5)
                                continue
                                
                            Ix, shape, c, b, y_array, section_dims = result
                            project_state["profile_saved"] = True
                            project_state["has_unsaved_changes"] = True
                            print_success("Profile defined successfully!")
                            time.sleep(2)
                            break
                            
                        elif src_choice == '2':  # Standard Library
                            families = SectionsDB.get_standard_families()
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
                                sections_in_fam = SectionsDB.get_sections_in_family(selected_family)
                                
                                sec_idx = display_section_library(sections_in_fam, title=f"{selected_family} Sections", is_custom=False)
                                if sec_idx is not None:
                                    entry = sections_in_fam[sec_idx]
                                    result = moi_solver.load_section_from_library(entry)
                                    if result:
                                        Ix, shape, c, b, y_array, section_dims = result
                                        project_state["profile_saved"] = True
                                        project_state["has_unsaved_changes"] = True
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
                            custom_secs = SectionsDB.list_custom_sections()
                            sec_idx = display_section_library(custom_secs, title="MY SAVED SECTIONS", is_custom=True)
                            if sec_idx is not None:
                                entry = custom_secs[sec_idx]
                                result = moi_solver.load_section_from_library(entry)
                                if result:
                                    Ix, shape, c, b, y_array, section_dims = result
                                    project_state["profile_saved"] = True
                                    project_state["has_unsaved_changes"] = True
                                    print_success(f"Loaded {entry['name']} successfully!")
                                    time.sleep(2)
                                    break
                                else:
                                    print_error("Failed to parse section data.")
                                    time.sleep(2)
                                    
                        elif src_choice == '4':  # Save Current Section
                            if not project_state["profile_saved"]:
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
                                "shape": shape,
                                "Ix": Ix,
                                "c": c,
                                "b": b,
                                "section_dims": section_dims
                            }
                            SectionsDB.save_custom_section(sec_dict)
                            print_success(f"Section '{custom_name}' saved successfully!")
                            time.sleep(2)

                                    
                        elif src_choice == '5':  # Delete Custom Section
                            custom_secs = SectionsDB.list_custom_sections()
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
                                    SectionsDB.delete_custom_section(sec_name)
                                    print_success(f"Deleted section '{sec_name}'.")
                                time.sleep(2)


                elif sub_choice == '3':  # View profile info
                    if not project_state["profile_saved"] and not shape:
                        print_error("No profile defined yet.")
                        time.sleep(2)
                        continue
                        
                    display_profile_info(beam_length, shape, Ix, c, b, y_array, units=current_labels, beam_type=beam_type, segments=segments)

        elif selection == '4':  # Material Selection
            while True:
                sub_choice = material_selection_menu(beam_type=beam_type, segments=segments, units=current_labels)
                if sub_choice == '5':  # Back to main menu
                    break
                elif sub_choice == '1':  # Select material
                    if project_state["is_loaded"] and project_state["material_saved"]:
                        confirmation = input(colored("Project already has a material defined. Modify? (Y/N): ", 'cyan'))
                        try:
                            if confirmation.lower() != 'y':
                                continue
                        except ValueError:
                                print_error("Invalid input. Please select a valid option.")
                                time.sleep(2)
                                continue    
                    selected_material = select_material(current_unit_system, current_labels)
                    if selected_material:
                        # For stepped bars, ask whether to apply to all or specific segment
                        if beam_type == "Stepped Bar" and segments:
                            print("\n")
                            print(colored("\u250c\u2500 APPLY MATERIAL TO " + "\u2500"*40, 'yellow', attrs=['bold']))
                            print(colored("\u2502 1. All segments", 'yellow'))
                            for idx, seg in enumerate(segments, 1):
                                seg_len = seg['end'] - seg['start']
                                print(colored(f"\u2502 {idx+1}. Segment {idx} ({seg['shape']}, L={seg_len:.3f} m)", 'yellow'))
                            print(colored("\u2504" + "\u2500"*57, 'yellow', attrs=['bold']))
                            print("\n")
                            mat_choice = input(colored(f"Enter your choice [1-{len(segments)+1}] \u2794 ", 'cyan'))
                            try:
                                mat_idx = int(mat_choice)
                                if mat_idx == 1:
                                    for seg in segments:
                                        seg['material_name'] = selected_material['Material']
                                        seg['yield_strength'] = float(selected_material['Yield Strength']) * 1e6
                                        seg['E'] = float(selected_material['Elastic Modulus']) * 1e9
                                    print_success(f"Applied {selected_material['Material']} to all segments!")
                                elif 2 <= mat_idx <= len(segments) + 1:
                                    seg_idx = mat_idx - 2
                                    segments[seg_idx]['material_name'] = selected_material['Material']
                                    segments[seg_idx]['yield_strength'] = float(selected_material['Yield Strength']) * 1e6
                                    segments[seg_idx]['E'] = float(selected_material['Elastic Modulus']) * 1e9
                                    print_success(f"Applied {selected_material['Material']} to Segment {seg_idx+1}!")
                                else:
                                    print_error("Invalid selection.")
                                    time.sleep(1.5)
                                    continue
                            except ValueError:
                                print_error("Invalid input.")
                                time.sleep(1.5)
                                continue
                        else:
                            density = float(selected_material["Density"])
                            yield_strength = float(selected_material["Yield Strength"]) * 1e6
                            ultimate_strength = float(selected_material["Ultimate Strength"]) * 1e6
                            elastic_modulus = float(selected_material["Elastic Modulus"]) * 1e9
                            poisson_ratio = float(selected_material["Poisson Ratio"])
                            shear_yield_strength = 0.55 * yield_strength
                        
                        project_state["material_saved"] = True
                        project_state["has_unsaved_changes"] = True
                        
                        cprint("==========================================================", 'red')
                        cprint("       Units Automatically Converted To Metric Units    ",'green')
                        cprint("==========================================================", 'red')
                        time.sleep(1)

                elif sub_choice == '2':  # View material info
                    if not project_state["material_saved"] and not selected_material:
                        print_error("No material selected yet.")
                        time.sleep(2)
                        continue
                    
                    # For stepped bars, ask which segment to view
                    if beam_type == "Stepped Bar" and segments:
                        print("\n")
                        print(colored("\u250c\u2500 VIEW MATERIAL FOR SEGMENT " + "\u2500"*37, 'yellow', attrs=['bold']))
                        for idx, seg in enumerate(segments, 1):
                            seg_len = seg['end'] - seg['start']
                            mat_name = seg.get('material_name', 'Unknown')
                            print(colored(f"\u2502 {idx}. Segment {idx} ({seg['shape']}, L={seg_len:.3f} m) \u2014 {mat_name}", 'yellow'))
                        print(colored("\u2504" + "\u2500"*57, 'yellow', attrs=['bold']))
                        print("\n")
                        view_choice = input(colored(f"Enter segment number [1-{len(segments)}] or 0 to cancel \u2794 ", 'cyan'))
                        try:
                            v_idx = int(view_choice)
                            if v_idx == 0:
                                continue
                            if 1 <= v_idx <= len(segments):
                                seg = segments[v_idx - 1]
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
                                    current_unit_system,
                                    current_labels
                                )
                            else:
                                print_error("Invalid selection.")
                                time.sleep(1.5)
                        except ValueError:
                            print_error("Invalid input.")
                            time.sleep(1.5)
                    else:
                        display_material_info(
                            selected_material, 
                            density, 
                            yield_strength, 
                            ultimate_strength, 
                            elastic_modulus, 
                            poisson_ratio, 
                            shear_yield_strength,
                            current_unit_system,
                            current_labels
                        )

                elif sub_choice == '3':  # Add Custom Material
                    new_mat = define_custom_material(current_unit_system, current_labels)
                    if new_mat:
                        Materials.add_custom_material(new_mat)
                        print_success(f"Custom material '{new_mat['Material']}' added successfully!")
                        time.sleep(2)
                        
                elif sub_choice == '4':  # Delete Custom Material
                    if not Materials.custom_materials:
                        print_error("No custom materials available to delete.")
                        time.sleep(2)
                        continue
                    
                    clear_screen()
                    print_title("Delete Custom Material")
                    for idx, mat in enumerate(Materials.custom_materials, 1):
                        print_option(f"  {idx}. {mat['Material']}")
                    print("")
                    
                    try:
                        del_idx = int(input(colored("Enter the number to delete (or 0 to cancel) ➔ ", 'cyan')))
                        if del_idx == 0:
                            continue
                        if 1 <= del_idx <= len(Materials.custom_materials):
                            mat_name = Materials.custom_materials[del_idx-1]["Material"]
                            confirm = input(colored(f"Are you sure you want to delete '{mat_name}'? (Y/N): ", 'cyan'))
                            if confirm.lower() == 'y':
                                Materials.delete_custom_material(mat_name)
                                print_success(f"Deleted material '{mat_name}'.")
                                # If active material was deleted, reset it
                                if selected_material and selected_material.get("Material") == mat_name:
                                    selected_material = ''
                                    project_state["material_saved"] = False
                                    print(colored("Active material was deleted. Please select a new material.", 'yellow'))
                            time.sleep(2)
                        else:
                            print_error("Invalid selection.")
                            time.sleep(1)
                    except ValueError:
                        print_error("Invalid input.")
                        time.sleep(1)

        elif selection == '5':  # Boundary Conditions
            if beam_type in ("Cantilever", "Fixed-Fixed", "Propped"):
                print_error(f"{beam_type} beams boundary conditions are automatically determined.")
                time.sleep(2)
           
           
           
            elif beam_type == "Simple":
                if beam_length <= 0:
                    print_error("Please define beam length first (Menu 3) before supports can be auto-defined.")
                    time.sleep(2)
                    continue
                if not project_state["supports_saved"] or (A == 0.0 and B == 0.0):
                    A = 0.0
                    B = beam_length
                    A_restraint = (1, 1, 0)
                    B_restraint = (0, 1, 0)
                    A_type = "Pin Support"
                    B_type = "Roller Support"
                    support_types = ("pin", "roller")
                    project_state["supports_saved"] = True
                    project_state["has_unsaved_changes"] = True
                    print_success("Simple beam supports auto-defined: Pin at x=0, Roller at x=L")
                else:
                    print_success("Simple beam supports already defined.")
                time.sleep(2)
                
            elif beam_type == "Continuous":
                supports_list = define_continuous_supports(beam_length, current_unit_system, current_labels)
                project_state["supports_saved"] = True
                project_state["has_unsaved_changes"] = True
                support_types = tuple(["roller" for _ in supports_list])  

            elif beam_type == "Custom":
                supports_list = define_custom_supports(beam_length, current_unit_system, current_labels)
                project_state["supports_saved"] = True
                project_state["has_unsaved_changes"] = True
                support_types = tuple(
                    "pin" if tuple(s["dof"]) == (1,1,0) 
                    else "fixed" if tuple(s["dof"]) == (1,1,1) 
                    else "roller" for s in supports_list
                )

            elif beam_type == "Stepped Bar":
                if not segments:
                    print_error("Please define stepped beam segments first (Menu 3).")
                    time.sleep(2)
                    continue
                supports_list = define_custom_supports(beam_length, current_unit_system, current_labels)
                project_state["supports_saved"] = True
                project_state["has_unsaved_changes"] = True
                support_types = tuple(
                    "pin" if tuple(s["dof"]) == (1,1,0) 
                    else "fixed" if tuple(s["dof"]) == (1,1,1) 
                    else "roller" for s in supports_list
                )

            elif beam_type == "Overhanging Beam":
                  while True:
                    sub_choice = boundary_conditions_menu()
                    if sub_choice == '3':  # Back to main menu
                        break   
                    elif sub_choice == '1':  # Define supports
                        if project_state["is_loaded"] and project_state["supports_saved"]:
                            confirmation = input(colored("Project already has supports defined. Modify? (Y/N): ", 'cyan'))
                            if confirmation.lower() != 'y':
                                continue
                            
                        A, B, A_restraint, B_restraint, A_type, B_type = Beam_Supports(current_unit_system, current_labels)
                        project_state["supports_saved"] = True
                        project_state["has_unsaved_changes"] = True
                        support_types = ("pin", "roller")
                    
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        len_div = get_divisor(current_labels, 'length')
                        print(f"Pin Support Position(A): {A / len_div:.3f} {current_labels['length']}")
                        print(f"Roller Support Position(B): {B / len_div:.3f} {current_labels['length']}")
                        cprint("==========================================================", 'red')
                        print("")                        
                        input("Press Enter to return to the menu...")
                    
                    elif sub_choice == '2':  # View supports
                        if not project_state["supports_saved"] and not A_type and not B_type:
                            print_error("No supports defined yet.")
                            time.sleep(2)
                            continue
                        
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        len_div = get_divisor(current_labels, 'length')
                        cprint(f"Pin Support Position(A): {A / len_div:.3f} {current_labels['length']}","white")
                        cprint(f"Roller Support Position(B): {B / len_div:.3f} {current_labels['length']}",'white')
                        cprint("==========================================================", 'red')
                        print("")
                        input("Press Enter to return to the menu...")
            else:
                print_error("Please define a beam classification first.")
                time.sleep(2)
                continue

        elif selection == '6':  # Loads Definition
            if beam_type is None:
                print_error("Beam classification is not defined yet.")
                time.sleep(2)
                continue
            else:
                while True:
                    sub_choice = loads_definition_menu()
                    if sub_choice == '4':  # Back to main menu
                        break
                    elif sub_choice == '1':  # Define loads
                        if project_state["is_loaded"] and project_state["loads_saved"]:
                            confirmation = input(colored("Project already has loads defined. Modify? (Y/N): ", 'cyan'))
                            if confirmation.lower() != 'y':
                                continue
                    
                        print("Define Loads:")
                        loads_dict = manage_loads(current_unit_system, current_labels, beam_type)
                        pointloads = loads_dict.get("pointloads", [])
                        distributedloads = loads_dict.get("distributedloads", [])
                        momentloads = loads_dict.get("momentloads", [])
                        triangleloads = loads_dict.get("triangleloads", [])
                        loads = loads_dict  # Store the complete dictionary for later use
                    
                        # Update project state
                        project_state["loads_saved"] = True
                        project_state["has_unsaved_changes"] = True
                    
                        print("")
                        print_success("Loads defined successfully!")
                        time.sleep(1)
                    
                    elif sub_choice == '2':  # View loads
                        if not project_state["loads_saved"] and not loads:
                            print_error("No loads defined yet.")
                            time.sleep(2)
                            continue
                        
                        clear_screen()
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                    Defined Loads:                        ", 'light_yellow')
                        cprint("==========================================================", 'red')                    
                        print_title("Current Loads:")
                        print(colored(f"\nPoint Loads: {loads.get('pointloads', [])}", 'white'))
                        print(colored(f"\nDistributed Loads: {loads.get('distributedloads', [])}", 'white'))
                        print(colored(f"\nMoment Loads: {loads.get('momentloads', [])}", 'white'))
                        print(colored(f"\nTriangular Loads: {loads.get('triangleloads', [])}", 'white'))
                        print("")
                        input("Press Enter to continue...")
                    
                    elif sub_choice == '3':  # Plot beam schematic
                        if not project_state["loads_saved"]:
                            print_error("Please review your entered loads.")
                            time.sleep(2)
                            continue
                        elif not project_state["supports_saved"]:
                            print_error("Please review your entered supports.")
                            time.sleep(2)
                            continue

                        try:
                            formatted_loads = format_loads_for_plotting(loads_dict)
                            # Single universal call handles all beam types automatically
                            plot_beam_schematic(
                                beam_type, beam_length, A, B, 
                                supports_list, formatted_loads, units=current_labels
                            )
                        except Exception as e:
                            print_error(f"Error plotting beam schematic: {e}")
                            time.sleep(2)
                    
        elif selection == '7':  # Show Beam Schematic (Standalone)
                if not project_state["loads_saved"]:
                    print_error("Please review your entered loads.")
                    time.sleep(2)
                    continue
                elif not project_state["supports_saved"]:
                    print_error("Please review your entered supports.")
                    time.sleep(2)
                    continue
                
                try:
                    formatted_loads = format_loads_for_plotting(loads)
                    # Single universal call handles all beam types automatically
                    plot_beam_schematic(
                        beam_type, beam_length, A, B, 
                        supports_list, formatted_loads, units=current_labels
                    )
                except Exception as e:
                    print_error(f"Error plotting beam schematic: {e}")
                    time.sleep(2)

        elif selection == '8':  # Analysis/Simulation
            while True:
                sub_choice = analysis_simulation_menu()
                if sub_choice == '5':  # Back to main menu
                    break
                    
                # Check if all required data is available for analysis
                if not project_state["profile_saved"] or not project_state["material_saved"] or \
                   not project_state["loads_saved"] or not project_state["supports_saved"]:
                    print_error("Analysis requires profile, material, supports and loads to be defined.")
                    time.sleep(2)
                    continue
                
                elif sub_choice == '1':  # Run analysis
                    try:
                        # Check if all required data is available
                        if not project_state["profile_saved"] or not project_state["material_saved"] or \
                           not project_state["loads_saved"] or not project_state["supports_saved"]:
                            print_error("Analysis requires profile, material, supports and loads to be defined.")
                            time.sleep(2)
                            continue
        
                        # Display analysis information in FEA-like format
                        display_analysis_info(
                            beam_type=beam_type,
                            beam_length=beam_length,
                            shape=shape,
                            selected_material=selected_material,
                            A=A,
                            B=B,
                            A_type=A_type,
                            B_type=B_type,
                            loads=loads,
                            units=current_labels)
                        
        
                        # Perform the analysis with proper arguments
                        # Build internal constraints array for indeterminate package
                        if beam_type == "Simple":
                            _supports = [
                                {"pos": A, "dof": (1,1,0), "ky": None, "kx": None},
                                {"pos": B, "dof": (0,1,0), "ky": None, "kx": None},
                            ]
                        elif beam_type == "Overhanging Beam":
                            _supports = [
                                {"pos": A, "dof": (1,1,0), "ky": None, "kx": None},
                                {"pos": B, "dof": (0,1,0), "ky": None, "kx": None}, 
                            ]                          
                        elif beam_type == "Cantilever":
                            _supports = [{"pos": 0.0, "dof": (1,1,1), "ky": None, "kx": None}]
                        elif beam_type == "Fixed-Fixed":
                            _supports = [
                                {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
                                {"pos": beam_length, "dof": (1,1,1), "ky": None, "kx": None},
                            ]
                        elif beam_type == "Propped":
                            _supports = [
                                {"pos": 0.0,         "dof": (1,1,1), "ky": None, "kx": None},
                                {"pos": beam_length, "dof": (0,1,0), "ky": None, "kx": None},
                            ]
                        elif beam_type == "Continuous" or beam_type == "Custom" or beam_type == "Stepped Bar":
                            _supports = supports_list

                        # Dispatch to appropriate solver
                        if beam_type == "Stepped Bar":
                            result = solve_stepped_beam(
                                segments=segments,
                                supports=_supports,
                                pointloads=pointloads,
                                distributedloads=distributedloads,
                                momentloads=momentloads,
                                triangleloads=triangleloads,
                                num_points=num_points
                            )
                        else:
                            # Invoke unified SymPy solver adapter
                            result = solve_beam(
                                beam_length=beam_length,
                                beam_type=beam_type,
                                supports=_supports,
                                pointloads=pointloads,
                                distributedloads=distributedloads,
                                momentloads=momentloads,
                                triangleloads=triangleloads,
                                E=elastic_modulus,
                                I=Ix,
                                num_points=num_points 
                            )
                        
                        # Populate global response arrays directly
                        X_Field = result["X_Field"]
                        Total_ShearForce = result["Total_ShearForce"]
                        Total_BendingMoment = result["Total_BendingMoment"]
                        Deflection = result["Deflection"]
                        Reactions = result["Reactions"]
                        Slopes = result["Slopes"]
                        Curvatures = result["Curvatures"]
                        # Stepped bar extras
                        AxialForce = result.get("AxialForce", None)
                        AxialDisplacement = result.get("AxialDisplacement", None)
                        # Analysis and deflection calculated in one pass
                        project_state["analysis_complete"] = True
                        project_state["deflection_calculated"] = True
                        project_state["has_unsaved_changes"] = True

                        # Safely unpack dictionary variables for the UI Display payload
                        Va = next((r["Fy"] for r in Reactions if r["pos"] == A), 0.0) if beam_type == "Simple" else next((r["Fy"] for r in Reactions if r["pos"] == 0.0), 0.0)
                        Ha = next((r["Fx"] for r in Reactions if r["pos"] == A), 0.0) if beam_type == "Simple" else next((r["Fx"] for r in Reactions if r["pos"] == 0.0), 0.0)
                        Vb = next((r["Fy"] for r in Reactions if r["pos"] == B), 0.0) if beam_type == "Simple" else next((r["Fy"] for r in Reactions if r["pos"] == beam_length), 0.0)
                        Ma = next((r["M"]  for r in Reactions if r["pos"] == 0.0), 0.0)

                        max_shear = round(np.max(Total_ShearForce), 3)
                        min_shear = round(np.min(Total_ShearForce), 3)
                        max_bending = round(np.max(Total_BendingMoment), 3)
                        min_bending = round(np.min(Total_BendingMoment), 3)
        
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
        
                    except Exception as e:
                        print_error(f"Error solving beam: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '2':  # View analysis results
                    if not project_state.get("analysis_complete", False):
                        print_error("No analysis results available yet. Please run analysis first.")
                        time.sleep(2)
                        continue
        
                    try:
                        # Extract key results from list of dicts
                        Va = next((r["Fy"] for r in Reactions if r["pos"] == A), 0.0) if beam_type == "Simple" else next((r["Fy"] for r in Reactions if r["pos"] == 0.0), 0.0)
                        Ha = next((r["Fx"] for r in Reactions if r["pos"] == A), 0.0) if beam_type == "Simple" else next((r["Fx"] for r in Reactions if r["pos"] == 0.0), 0.0)
                        Vb = next((r["Fy"] for r in Reactions if r["pos"] == B), 0.0) if beam_type == "Simple" else next((r["Fy"] for r in Reactions if r["pos"] == beam_length), 0.0)
                        Ma = next((r["M"]  for r in Reactions if r["pos"] == 0.0), 0.0)

                        max_shear = round(np.max(Total_ShearForce), 3)
                        min_shear = round(np.min(Total_ShearForce), 3)
                        max_bending = round(np.max(Total_BendingMoment), 3)
                        min_bending = round(np.min(Total_BendingMoment), 3)
        
                        # Display results in professional FEA-like format
                        display_analysis_results(
                            beam_type=beam_type,
                            shape=shape,
                            beam_length=beam_length,
                            A=A,
                            B=B,
                            Va=Va,
                            Ha=Ha,
                            Vb=Vb,
                            Ma=Ma,
                            max_shear=max_shear,
                            min_shear=min_shear,
                            max_bending=max_bending,
                            min_bending=min_bending,
                            units=current_labels
                        )
        
                    except Exception as e:
                        print_error(f"Error displaying analysis results: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '3':  # Calculate deflection
                    if not project_state.get("analysis_complete", False):
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
                            beam_length=beam_length,
                            shape=shape,
                            beam_type=beam_type,
                            elastic_modulus=elastic_modulus,
                            Ix=Ix,
                            Deflection=Deflection,
                            Slope=Slopes,
                            curv=Curvatures,
                            units=current_labels
                        )
        
                    except Exception as e:
                        print_error(f"Error calculating deflection: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '4':  # Calculate stress and FOS
                    if not project_state.get("analysis_complete", False):
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
                        if beam_type == "Stepped Bar":
                            # Per-segment stress computation for stepped bars
                            # Bug-15 fix: the module-level y_array is empty for any
                            # Stepped workflow (geometry lives in each segment dict).
                            # Size the shear-stress grid from the segment's y_array,
                            # not the global — otherwise the array is (0, N) and the
                            # per-column assignment below raises a broadcast ValueError.
                            n_y = len(segments[0]['y_array']) if segments else 10001
                            Shear_stress = np.zeros((n_y, len(X_Field)))
                            bending_stress = np.zeros(len(X_Field))
                            min_fos = float('inf')
                            for i, x in enumerate(X_Field):
                                seg = None
                                for s in segments:
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
                                tau = calculate_shear_stress(Total_ShearForce[i], Q_arr, I_seg, b_arr)
                                Shear_stress[:, i] = tau
                                sigma = calculate_bending_stress(Total_BendingMoment[i], c_seg, I_seg)
                                bending_stress[i] = sigma
                                if ys_seg > 0:
                                    fos_pt = ys_seg / max(abs(sigma), 1e-12)
                                    if fos_pt < min_fos:
                                        min_fos = fos_pt
                            Max_Shear_stress = np.max(np.abs(Shear_stress))
                            Max_bending_stress = np.max(np.abs(bending_stress))
                            FOS = min_fos if min_fos != float('inf') else 0.0
                            # Use a composite material dict for display
                            if segments:
                                min_yield_seg = min(s.get('yield_strength', 0) for s in segments)
                                comp_material = {
                                    'Material': 'Varies (Stepped Bar)',
                                    'Yield Strength': min_yield_seg / 1e6,
                                }
                            else:
                                comp_material = selected_material
                        else:
                            #BUG-09 FIX: build section-aware b(y) for correct τ = VQ/(Ib(y))
                            b_array = width_array_for_section(shape, section_dims, y_array)
                            Q_array = first_moment_of_area_general(b_array, y_array)
                            Shear_stress = calculate_shear_stress(Total_ShearForce, Q_array, Ix, b_array)
                            Max_Shear_stress = np.max(np.abs(Shear_stress))
                            # Calculate bending stress
                            bending_stress = calculate_bending_stress(Total_BendingMoment, c, Ix)
                            Max_bending_stress = np.max(np.abs(bending_stress))
                            # Calculate factor of safety
                            FOS = Factor_of_Safety(Total_BendingMoment, c, yield_strength, Ix)
                            comp_material = selected_material
                        
                        # Update project state
                        project_state["stress_calculated"] = True
                        project_state["has_unsaved_changes"] = True
        
                        # Display results in professional format
                        display_stress_analysis(
                            beam_type=beam_type,
                            shape=shape,
                            selected_material=comp_material,
                            Ix=Ix,
                            c=c,
                            b=b,
                            y_array=y_array,
                            Total_ShearForce=Total_ShearForce,
                            Total_BendingMoment=Total_BendingMoment,
                            Shear_stress=Shear_stress,
                            Max_Shear_stress=Max_Shear_stress,
                            bending_stress=bending_stress,
                            Max_bending_stress=Max_bending_stress,
                            FOS=FOS,
                            units=current_labels,
                            segments=segments
                        )
        
                    except Exception as e:
                        print_error(f"Error in stress/F.O.S calculations: {e}")
                        time.sleep(2)
                        continue
        elif selection == '9':  # Postprocessing/Visualization
            while True:
                sub_choice = postprocessing_menu(beam_type)
                # Menu size depends on beam_type: items 1-8 are always present,
                # items 9/10/11 (axial) exist only for Stepped Bar, then 3D FEA
                # and Back are appended. So their numbers shift by 3 for Stepped.
                # Bug-11 fix: compute these dynamically instead of hardcoding '12'.
                fea_3d_choice = '12' if beam_type == "Stepped Bar" else '9'
                back_choice = '13' if beam_type == "Stepped Bar" else '10'
                if sub_choice == back_choice:  # Back to main menu
                    break
                    
                # Check if analysis has been completed before allowing visualization
                if not project_state.get("analysis_complete", False):
                    print_error("Please complete an analysis before attempting visualization.")
                    time.sleep(2)
                    continue
                    
                if sub_choice == '1':  # Reaction forces schematic
                    try:
                        print_success("Processing reaction-forces schematic (Plotly)…")
                        plot_reaction_diagram(Reactions, units=current_labels)
                    except Exception as e:
                        print_error(f"Error plotting reaction diagram: {e}")
                        time.sleep(2)
                        continue
                        
                elif sub_choice == '2':  # SFD 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Force Plot (Matplotlib):")
                            Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment,'SFD',units=current_labels)
                        elif style == '2':
                                print_success("Processing shear force plot (Plotly)…")
                                Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,'SFD',units=current_labels)
                        
                    except Exception as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '3':  # BMD 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Bending Moment Plot (Matplotlib):")
                            Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment,'BMD',units=current_labels)
                        elif style == '2':
                                print_success("Processing bending moment plot (Plotly)…")
                                Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,'BMD',units=current_labels)
 
                    except Exception as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '4':  # SFD/BMD Combined in one plot 
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Force/Bending Moment Plots (Matplotlib):")
                            Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment,'Both',units=current_labels)
                        elif style == '2':
                                print_success("Processing Shear Force/Bending Moment Plots(Plotly):")
                                Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,'Both',units=current_labels)

                    except Exception as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '5':  # Shear Stress
                  
                    if not project_state.get("stress_calculated", False):
                        print_error("Please calculate stresses first (Analysis menu → option 4).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Stress Plot (Matplotlib):")
                            Matplot_ShearStress(X_Field, Shear_stress,units=current_labels)

                        elif style == '2':
                            print_success("Processing Shear Stress Plot(Plotly):")
                            Plotly_ShearStress(X_Field, Shear_stress, beam_length,units=current_labels)
                            
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Shear-Stress Plot: {e}")
                        time.sleep(2)
                elif sub_choice == '6':  # Bending Stress
                    if not project_state.get("stress_calculated", False):
                        print_error("Please calculate stresses first (Analysis menu → option 4).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Bending Stress Plots (Matplotlib):")
                            Matplot_BendingStress(X_Field, bending_stress, units=current_labels)
                        elif style == '2':
                            print_success("Processing Bending Stress Plots (Plotly):")
                            Plotly_BendingStress(X_Field, bending_stress, beam_length, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Bending-Stress Plot: {e}")
                        time.sleep(2)
                elif sub_choice == '7':  # Deflection
                    if not project_state.get("deflection_calculated", False):
                        print_error("Please calculate deflection first (in Analysis menu).")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Deflection/Displacement Plots (Matplotlib):")
                            Matplot_Deflection(X_Field, Deflection, units=current_labels)
                        elif style == '2':
                            print_success("Processing Deflection/Displacement Plots (Plotly):")
                            Plotly_Deflection(X_Field, Deflection, beam_length, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Deflection Plot: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '8':  # Combined plots (Plotly/Matplotlib)
                    try:
                        defl_data = Deflection if project_state.get("deflection_calculated", False) else None
                        shear_data = Shear_stress if project_state.get("stress_calculated", False) else None
                        # Stepped Bar extras: include axial force & combined stress when solved
                        axial_data = AxialForce if (beam_type == "Stepped Bar" and AxialForce is not None) else None
                        combo_stress = None
                        if beam_type == "Stepped Bar" and AxialForce is not None and project_state.get("stress_calculated", False):
                            combo_stress = np.zeros_like(X_Field)
                            for i, x in enumerate(X_Field):
                                seg = next((s for s in segments if s["start"] <= x <= s["end"]), None)
                                if seg is None:
                                    continue
                                sigma_axial = AxialForce[i] / seg["A"]
                                M_val = Total_BendingMoment[i]
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
                            Matplot_combined(X_Field, Total_ShearForce, Total_BendingMoment,
                                             Deflection=defl_data, ShearStress=shear_data,
                                             AxialForce=axial_data, CombinedStress=combo_stress, units=current_labels)
                        elif style == '2':
                            print_success("Processing Combined Plots (Plotly):")
                            Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
                                                     Deflection=defl_data, ShearStress=shear_data,
                                                     AxialForce=axial_data, CombinedStress=combo_stress, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue

                    except Exception as e:
                        print_error(f"Plotting error: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '9' and beam_type == "Stepped Bar":  # Axial-Force Plot (Stepped Bar only)
                    if AxialForce is None:
                        print_error("Axial Force not available. Run analysis first.")
                        time.sleep(2); continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Axial Force Plot (Matplotlib):")
                            Matplot_AxialForce(X_Field, AxialForce, units=current_labels)
                        elif style == '2':
                            print_success("Processing Axial Force Plot (Plotly):")
                            Plotly_AxialForce(X_Field, AxialForce, beam_length, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Axial Force Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '10' and beam_type == "Stepped Bar":  # Axial-Displacement Plot (Stepped Bar only)
                    if AxialDisplacement is None:
                        print_error("Axial Displacement not available. Run analysis first.")
                        time.sleep(2); continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Axial Displacement Plot (Matplotlib):")
                            Matplot_AxialDisplacement(X_Field, AxialDisplacement, units=current_labels)
                        elif style == '2':
                            print_success("Processing Axial Displacement Plot (Plotly):")
                            Plotly_AxialDisplacement(X_Field, AxialDisplacement, beam_length, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Axial Displacement Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '11' and beam_type == "Stepped Bar":  # Combined Stress (Stepped Bar only)
                    if AxialForce is None or not project_state.get("stress_calculated", False):
                        print_error("Run analysis and stress calculation first.")
                        time.sleep(2); continue
                    try:
                        # Compute combined stress: sigma_bending + sigma_axial
                        # For each segment, find max axial stress and combine with bending
                        combined_stress = np.zeros_like(X_Field)
                        for i, x in enumerate(X_Field):
                            # Find which segment this x belongs to
                            seg = None
                            for s in segments:
                                if s["start"] <= x <= s["end"]:
                                    seg = s
                                    break
                            if seg is None:
                                continue
                            A_seg = seg["A"]
                            I_seg = seg["I"]
                            c_seg = seg["c"]
                            # Axial stress
                            sigma_axial = AxialForce[i] / A_seg if AxialForce is not None else 0.0
                            # Bending stress (maximum at extreme fiber)
                            M_val = Total_BendingMoment[i]
                            sigma_bending = abs(M_val) * c_seg / I_seg if I_seg > 0 else 0.0
                            # Combined stress (tension positive)
                            sign = 1.0 if M_val >= 0 else -1.0  # simplistic sign handling
                            combined_stress[i] = sigma_axial + sign * sigma_bending

                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Combined Stress Plot (Matplotlib):")
                            Matplot_CombinedStress(X_Field, combined_stress, units=current_labels)
                        elif style == '2':
                            print_success("Processing Combined Stress Plot (Plotly):")
                            Plotly_CombinedStress(X_Field, combined_stress, beam_length, units=current_labels)
                        else:
                            print_error("Invalid style selection.")
                            time.sleep(2)
                            continue
                    except Exception as e:
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
                        if not project_state.get("analysis_complete", False):
                            print_error("Please complete an analysis first.")
                            time.sleep(2)
                            continue

                        try:
                            if pv_choice == '1':  # Reactions
                                if not Reactions:
                                    print_error("No reaction data available. Run analysis first.")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Reactions Schematic (PyVista) ...")
                                PyVista_reactions_schematic(
                                    beam_length, Reactions, shape, section_dims,
                                    c, b, units=current_labels
                                )

                            elif pv_choice == '2':  # Shear Force
                                print_success("Opening 3D Shear Force Contour (PyVista) ...")
                                PyVista_shear_force(
                                    X_Field, Total_ShearForce, beam_length,
                                    shape, section_dims, c, b, units=current_labels
                                )

                            elif pv_choice == '3':  # Bending Moment
                                print_success("Opening 3D Bending Moment Contour (PyVista) ...")
                                PyVista_bending_moment(
                                    X_Field, Total_BendingMoment, beam_length,
                                    shape, section_dims, c, b, units=current_labels
                                )

                            elif pv_choice == '4':  # Shear Stress
                                if not project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Shear Stress Contour (PyVista) ...")
                                PyVista_shear_stress(
                                    X_Field, Shear_stress, beam_length,
                                    shape, section_dims, c, b, units=current_labels
                                )

                            elif pv_choice == '5':  # Bending Stress
                                if not project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Bending Stress Contour (PyVista) ...")
                                PyVista_bending_stress(
                                    X_Field, bending_stress, beam_length,
                                    shape, section_dims, c, b, units=current_labels
                                )

                            elif pv_choice == '6':  # Deflection
                                if not project_state.get("deflection_calculated", False):
                                    print_error("Please run the analysis first (deflection is auto-calculated).")
                                    time.sleep(2)
                                    continue
                                print_success("Opening 3D Deflection Contour (PyVista) ...")
                                PyVista_deflection(
                                    X_Field, Deflection, beam_length,
                                    shape, section_dims, c, b, units=current_labels
                                )

                            elif pv_choice == '7':  # Combined
                                print_success("Starting 3D FEA Combined Sequential Viewer (PyVista) ...")
                                defl_data   = Deflection     if project_state.get("deflection_calculated", False) else None
                                ss_data     = Shear_stress   if project_state.get("stress_calculated",     False) else None
                                bs_data     = bending_stress if project_state.get("stress_calculated",     False) else None
                                reac_data   = Reactions      if Reactions else None
                                PyVista_combined(
                                    X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
                                    shape, section_dims, c, b,
                                    Deflection=defl_data,
                                    ShearStress=ss_data,
                                    BendingStress=bs_data,
                                    Reactions=reac_data,
                                    units=current_labels
                                )

                            elif pv_choice == '8':  # Load Animation
                                if not project_state.get("deflection_calculated", False):
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
                                        not project_state.get("stress_calculated", False):
                                    print_error("Please calculate stresses first (Analysis → option 4).")
                                    time.sleep(2)
                                    continue

                                n_frames_input = input(colored("Number of frames [10-120, default 60] ➔ ", 'cyan')).strip()
                                n_frames = int(n_frames_input) if n_frames_input.isdigit() else 60
                                n_frames = max(10, min(n_frames, 120))

                                ss_anim = Shear_stress   if project_state.get("stress_calculated", False) else None
                                bs_anim = bending_stress if project_state.get("stress_calculated", False) else None

                                print_success(f"Opening animation: {result_key} ({n_frames} frames)...")
                                PyVista_animation(
                                    X_Field, Deflection,
                                    Total_ShearForce, Total_BendingMoment,
                                    ss_anim, bs_anim,
                                    beam_length, shape, section_dims, c, b,
                                    result_to_animate=result_key,
                                    n_frames=n_frames,
                                    fps=24,
                                    units=current_labels,
                                )

                            else:
                                print_error("Invalid selection.")
                                time.sleep(1)

                        except Exception as e:
                            print_error(f"Error in 3D FEA view: {e}")
                            time.sleep(2)
                            continue




        elif selection == '10':  # Save Project
            if not project_state["profile_saved"] or not project_state["material_saved"] or \
               not project_state["supports_saved"] or not project_state["loads_saved"]:
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
                
            except Exception as e:
                print_error(f"Error saving project: {e}")
                time.sleep(2)
                
        elif selection == '0':  # Exit
            if project_state["has_unsaved_changes"]:
                check_unsaved_changes()
            
            print_success("Thank you for using AltruxIQ.")
            break

        elif selection == '11':  # Recommendations
            # Check if all necessary analyses have been done
            if not project_state.get("analysis_complete", False):
                print_error("Please run the basic analysis first before getting recommendations.")
                time.sleep(2)
                continue
    
            try:
                # Extract necessary data for recommendations
                span_ratio = None
                max_stress = None
                max_defl = None
        
                # If deflection has been calculated
                if project_state.get("deflection_calculated", False):
                    max_defl_idx = np.argmax(np.abs(Deflection))
                    max_defl = Deflection[max_defl_idx]
                    span_ratio = abs(max_defl) / beam_length
        
                # If stress has been calculated
                if project_state.get("stress_calculated", False):
                    max_stress = max(np.max(np.abs(bending_stress)), np.max(np.abs(Shear_stress)))
        
                # Display recommendations
                display_engineering_recommendations(
                    beam_type=beam_type,
                    shape=shape,
                    beam_length=beam_length,
                    selected_material=selected_material,
                    Ix=Ix,
                    c=c,
                    b=b,
                    FOS=FOS if project_state.get("stress_calculated", False) else None,
                    max_stress=max_stress,
                    max_defl=max_defl,
                    span_ratio=span_ratio,
                    yield_strength=yield_strength if 'yield_strength' in globals() else None,
                    segments=segments
                )
    
            except Exception as e:
                print_error(f"Error generating recommendations: {e}")
                time.sleep(2)
                continue  

        elif selection == '12':  # Unit System
            current_unit_system = "Metric"
            while True:
                choice = unit_system_menu(current_unit_system)
                if choice == '1':
                    current_unit_system = "Metric"
                    current_labels = METRIC_LABELS
                    project_state["has_unsaved_changes"] = True
                    print_success("Unit system changed to Metric (SI).")
                    time.sleep(1.5)
                    break
                elif choice == '2':
                    current_unit_system = "Imperial"
                    current_labels = IMPERIAL_LABELS
                    project_state["has_unsaved_changes"] = True
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
                res_choice = resolution_menu(num_points)
                if res_choice == '1':
                    num_points = 501
                    print_success("Resolution set to Fast Draft (501 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '2':
                    num_points = 1001
                    print_success("Resolution set to Standard (1001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '3':
                    num_points = 2001
                    print_success("Resolution set to High (2001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '4':
                    num_points = 5001
                    print_success("Resolution set to Fine (5001 points).")
                    time.sleep(1.5)
                    break
                elif res_choice == '5':
                    custom_pts = get_solver_resolution()
                    if custom_pts is not None:
                        num_points = custom_pts
                        print_success(f"Resolution set to Custom ({num_points} points).")
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
    global project_state, current_unit_system, current_labels
    current_unit_system = "Metric"
    current_labels = METRIC_LABELS
    num_points = 2001
    project_state = {
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