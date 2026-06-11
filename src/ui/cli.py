#!/usr/bin/env python3
"""
CLI for Zylo-X Beam Calculator
===================================
This script provides a command-line interface (CLI) for the Zylo-X Beam Calculator.
It handles project management, profile and material selection, boundary conditions,
load definitions, analysis, postprocessing, and project save/load functionalities.
"""
# modules
import json
import os
import sys
# pyrefly: ignore [missing-import]
import numpy as np
import time
# pyrefly: ignore [missing-import]
from termcolor import colored, cprint
# --- PATH INJECTION (The Fix) ---
# 1. Get the directory of cli.py (ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent directory (src folder)
src_dir = os.path.dirname(current_dir)
# 3. Add the src folder to Python's search path if it's not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
# Application modules
from database.materials_database import MaterialDatabase  # Import MaterialDatabase class
from solver.main_solver import solve_simple_beam,solve_cantilever_beam
from solver import moi_solver
from plotting.main_plotting import (Matplot_Deflection, Plotly_Deflection, Plotly_sfd_bmd, Matplot_sfd_bmd, format_loads_for_plotting, Plotly_ShearStress,Matplot_ShearStress,
                      Matplot_BendingStress,Plotly_BendingStress,Plotly_combined_diagrams,Matplot_combined)
from plotting.beam_plot import plot_reaction_diagram, plot_beam_schematic,plot_cantilever_beam_schematic
from solver.stress_solver import (calculate_beam_deflection,
                         first_moment_of_area_rect, first_moment_of_area_general,
                         width_array_for_section, calculate_shear_stress,
                         calculate_bending_stress, Factor_of_Safety)
from ui.Menus import (main_menu_template, project_management_menu, profile_definition_menu, choose_profile,display_profile_info,display_analysis_info,
                 display_engineering_recommendations,display_stress_analysis,display_deflection_analysis,display_analysis_results,material_selection_menu, boundary_conditions_menu, loads_definition_menu, analysis_simulation_menu,
                 postprocessing_menu, print_success, print_error, print_option, print_title, clear_screen)
from ui.inputs import Beam_Length, Beam_Supports, manage_loads,Beam_Classification

# -----------------------------
# Global Storage Variables
# -----------------------------
beam_storage = []      # List to hold all saved projects
current_project = None # Dictionary holding the currently loaded project
Materials = None       # Placeholder for the materials database object
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
support_types = ("pin", "roller")  # BUG-10 FIX: module-level default; overwritten on load/save
beam_type = None  # BUG-05 FIX: initialise at module level to prevent NameError
# BUG-07 FIX: initialise post-processing outputs to None so combined plots never hit NameError
Deflection = None
Slope = None
Shear_stress = None
bending_stress = None
FOS = None
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
    global current_project, project_state, beam_type, support_types
    current_project = None  # Reset current project data
    beam_type = None        # BUG-05 FIX: reset beam_type so menu guards work correctly
    support_types = ("pin", "roller")  # BUG-10 FIX: reset to safe default
    
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
    global Ix, shape, c, b, y_array, project_state
    global elastic_modulus, selected_material, density, yield_strength, ultimate_strength, poisson_ratio, shear_yield_strength
    global pointloads, distributedloads, momentloads, triangleloads
    global beam_type, support_types  # BUG-10 FIX: support_types must be a global

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
    
    # Display available projects in a nicer format
    for idx, proj in enumerate(beam_storage, 1):
        print(colored(f"│ {idx:2d} │ {proj['name']}", 'yellow') + 
              colored(f" ({proj.get('beam_type', 'Unknown')} Beam, Length: {proj.get('beam_length', 'N/A')} m)", 'white'))
    
    print(colored("└───" + "─"*57, 'yellow', attrs=['bold']))
    print("\n")

    # Get user selection with better handling
    try:
        proj_choice = int(input(colored(f"Enter the number of the project you want to load [1-{len(beam_storage)}] ➔ ", 'cyan', attrs=['bold'])))
        
        if proj_choice < 1 or proj_choice > len(beam_storage):
            print_error(f"Invalid selection! Please choose a number between 1 and {len(beam_storage)}.")
            time.sleep(2)
            return
            
        current_project = beam_storage[proj_choice - 1]
        print_success(f"Project '{current_project['name']}' loaded successfully!")
        
        # ... rest of the function to load project data ...
        time.sleep(1)

        # Load beam type
        beam_type = current_project.get('beam_type', None)
        

        # Apply loaded project data to current state
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

        # Load analysis data
        X_Field = np.array(current_project.get('X_Field', []))
        Total_ShearForce = np.array(current_project.get('Total_ShearForce', []))
        Total_BendingMoment = np.array(current_project.get('Total_BendingMoment', []))
        Reactions = np.array(current_project.get('Reactions', []))
        
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

        # Update project state flags
        project_state["is_loaded"] = True
        project_state["profile_saved"] = bool(shape) and Ix > 0
        project_state["material_saved"] = bool(selected_material)
        project_state["loads_saved"] = bool(loads)
        project_state["supports_saved"] = bool(A_type) and bool(B_type)
        project_state["has_unsaved_changes"] = False

        # Optional: Show confirmation summary
        print_loaded_project_summary()

    except (IndexError, ValueError):
        print_error("Invalid choice! Starting a new project instead.")
        current_project = None
        time.sleep(1)

# =============================
def print_loaded_project_summary():
    """Display a summary of the loaded project."""
    print(colored(f"\nLoaded Project Summary:", 'green'))
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
        print_error("No project is currently loaded!")
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
            print_error("Invalid selection! Please try again.")
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
        print_error("No saved projects available to delete!")
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
                with open('beam_projects.json', 'w') as file:
                    json.dump(beam_storage, file, indent=4)
                print_success(f"Project '{project_to_delete['name']}' deleted successfully!")
            except Exception as e:
                print_error(f"Error saving updated project file: {e}")
        else:
            print("Deletion cancelled.")
    except ValueError:
        print_error("Invalid input! Please enter a valid number.")

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
    
    project_name = input(colored("Enter a name for this project ➔ ", 'cyan')).strip()
    
    if not project_name:
        print_error("Project name cannot be empty!")
        return False

    # Create proper profile data structure
    profile_data = {
        'Ix': Ix,
        'shape': shape,
        'c': c,
        'b': b,
        'y_array': safe_serialize(y_array)
    }
    
    # Create proper material data structure
    material_data = {
        'material': selected_material
    }
    
    # Create project data dictionary
    project_data = {
        'name': project_name,
        'beam_type': beam_type,
        'beam_length': beam_length,
        'support_A_pos': A,
        'support_B_pos': B,
        'support_A_restraint': list(A_restraint),
        'support_B_restraint': list(B_restraint),
        'support_A_type': A_type,
        'support_B_type': B_type,
        'support_types': list(support_types),  # BUG-10 FIX: persist support_types to JSON
        'X_Field': safe_serialize(X_Field),
        'Total_ShearForce': safe_serialize(Total_ShearForce),
        'Total_BendingMoment': safe_serialize(Total_BendingMoment),
        'Reactions': safe_serialize(Reactions),
        'loads': loads if loads is not None else {},
        'profile': profile_data,
        'material': material_data
    }


    # Check if project with this name already exists
    for idx, proj in enumerate(beam_storage):
        if proj['name'].lower() == project_name.lower():
            confirmation = input(colored(f"Project '{project_name}' already exists. Overwrite? (Y/N): ", 'cyan'))
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
    """
    Save all global projects to disk as a JSON file.
    Uses indentation for human readability.
    """
    global beam_storage
    try:
        with open('beam_projects.json', 'w') as file:
            json.dump(beam_storage, file, indent=4)
        print_success("All projects saved to disk successfully!")
        return True
    except Exception as e:
        print_error(f"Error saving projects to disk: {e}")
        return False

# =============================
def load_projects_from_disk():
    """
    Load projects from the JSON file into the global beam_storage.
    Initializes an empty storage if the file is not found or an error occurs.
    """
    global beam_storage
    try:
        with open('beam_projects.json', 'r') as file:
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
    Load the material database from 'Materials.json' into the global variable.
    """
    global Materials
    json_filename = "Materials.json"
    try:
        Materials = MaterialDatabase(json_filename)
    except Exception as e:
        print_error(f"Error loading the materials database: {e}")
        time.sleep(3)

# =============================
def select_material():
    """
    List all materials from the loaded database in an enhanced visual format,
    prompt for a selection, and return key properties of the selected material.
    
    Returns:
        dict: Selected material properties or None if input is invalid.
    """
    global Materials, project_state
    if Materials is None:
        print_error("Materials database is not loaded!")
        return None

    materials_list = Materials.materials
    
    # Create a decorative header
    clear_screen()
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                              MATERIAL SELECTION                                  ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    
    # Header for materials table
    header = colored("  # │ Material", 'yellow', attrs=['bold']) + " " * 24 + colored("│ Density │ Yield Str │ Ult Str │ E-Modulus │ Poisson │ Thermal Exp", 'yellow', attrs=['bold'])
    separator = colored("────┼────────────────────────────────────┼─────────┼───────────┼─────────┼───────────┼─────────┼─────────────", 'yellow')
    units =    colored("    │                                    │ kg/m³   │ MPa       │ MPa     │ GPa       │         │ 10⁻⁶/°C", 'white')
    
    print(header)
    print(separator)
    print(units)
    print(separator)
    
    # Print each material with properties in a table format
    for index, material in enumerate(materials_list):
        # Material number and name
        mat_num = colored(f"{index + 1:3d} │", 'light_yellow')
        mat_name = colored(f" {material['Material']:<34} │", 'light_yellow')
        
        # Properties with appropriate formatting
        density = f" {material.get('Density', 'N/A'):<7d} │"
        yield_str = f" {material.get('Yield Strength', 'N/A'):<9d} │"
        ult_str = f" {material.get('Ultimate Strength', 'N/A'):<7d} │"
        e_mod = f" {material.get('Elastic Modulus', 'N/A'):<9d} │"
        poisson = f" {material.get('Poisson Ratio', 'N/A'):<7.2f} │"
        
        # New property - Thermal Expansion
        therm_exp = f" {material.get('Thermal Expansion', 'N/A'):.1e}" if 'Thermal Expansion' in material else " N/A      "
        
        # Combine all parts of the row
        print(f"{mat_num}{mat_name}{density}{yield_str}{ult_str}{e_mod}{poisson}{therm_exp}")
    
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
            print_error("Invalid selection!")
            return None
        selected_material = materials_list[idx]
        print_success(f"You selected: {selected_material['Material']}")
        
        # Mark material as changed
        project_state["material_saved"] = True
        project_state["has_unsaved_changes"] = True
        
        # Return key properties including the new ones
        key_props = {
            "Material": selected_material.get("Material"),
            "Density": selected_material.get("Density"),
            "Yield Strength": selected_material.get("Yield Strength"),
            "Ultimate Strength": selected_material.get("Ultimate Strength"),
            "Elastic Modulus": selected_material.get("Elastic Modulus"),
            "Poisson Ratio": selected_material.get("Poisson Ratio"),
            "Thermal Expansion": selected_material.get("Thermal Expansion", 0),
            "Description": selected_material.get("Description", "")
        }
        return key_props
    except ValueError:
        print_error("Invalid input. Please enter a valid number.")
        return None

# =============================
def display_material_info(selected_material, density, yield_strength, ultimate_strength, elastic_modulus, poisson_ratio, shear_yield_strength):
    """
    Display enhanced material information in a visually appealing format.
    
    Parameters:
    -----------
    selected_material : dict
        Dictionary containing material properties
    density, yield_strength, etc. : float
        Converted material properties in SI units
    """
    clear_screen()
    
    # Create decorative header
    print("\n")
    print(colored("╔═════════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                  MATERIAL PROPERTIES                            ║", 'cyan', attrs=['bold']))
    print(colored("╚═════════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Material name and description
    print("\n")
    material_name = selected_material['Material']
    description = selected_material.get('Description', 'No description available')
    
    # Display material name with decoration
    print(colored("┌─ MATERIAL: ", 'yellow', attrs=['bold']) + colored(f"{material_name}", 'yellow', attrs=['bold']) + colored(" " + "─"*(50 - len(material_name)), 'yellow', attrs=['bold']))
    print(colored("│ ", 'yellow') + colored(f"{description}", 'white'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    
    # Properties section with decorative box
    print("\n")
    print(colored("┌─ STANDARD UNITS "+"─"*45, 'green', attrs=['bold']))
    
    # Create a table for properties in standard units
    properties_std = [
        ("Density", f"{selected_material['Density']} kg/m³"),
        ("Yield Strength", f"{selected_material['Yield Strength']} MPa"),
        ("Ultimate Strength", f"{selected_material['Ultimate Strength']} MPa"),
        ("Elastic Modulus", f"{selected_material['Elastic Modulus']} GPa"),
        ("Poisson Ratio", f"{selected_material['Poisson Ratio']}"),
        ("Thermal Expansion", f"{selected_material.get('Thermal Expansion', 'N/A'):.1e} /°C" if 'Thermal Expansion' in selected_material else "N/A")
    ]
    
    # Display properties in standard units
    for prop, value in properties_std:
        print(colored(f"│ {prop:<20}: ", 'green') + colored(f"{value}", 'white'))
    
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    
    # SI Units section with converted values
    print("\n")
    print(colored("┌─ SI UNITS (FOR CALCULATIONS) "+"─"*34, 'blue', attrs=['bold']))
    
    # Create a table for properties in SI units
    properties_si = [
        ("Density", f"{density} kg/m³"),
        ("Yield Strength", f"{yield_strength:.2e} Pa"),
        ("Ultimate Strength", f"{ultimate_strength:.2e} Pa"),
        ("Elastic Modulus", f"{elastic_modulus:.2e} Pa"),
        ("Poisson Ratio", f"{poisson_ratio}"),
        ("Shear Modulus*", f"{elastic_modulus/(2*(1+poisson_ratio)):.2e} Pa"),
        ("Shear Yield Strength*", f"{shear_yield_strength:.2e} Pa")
    ]
    
    # Display properties in SI units
    for prop, value in properties_si:
        print(colored(f"│ {prop:<20}: ", 'blue') + colored(f"{value}", 'white'))
    
    print(colored("│ ", 'blue') + colored("* Calculated values", 'white', attrs=['dark']))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Application information section
    print("\n")
    print(colored("┌─ TYPICAL APPLICATIONS "+"─"*41, 'magenta', attrs=['bold']))
    
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
def run_extended_menu():
    global current_project, project_state
    global beam_length, A, B, A_restraint, B_restraint, A_type, B_type
    global Ix, shape, c, b, y_array
    global selected_material, density, yield_strength, ultimate_strength, elastic_modulus, poisson_ratio, shear_yield_strength
    global pointloads, distributedloads, momentloads, triangleloads, loads
    global support_types
    global beam_type  # Ensure we can access the beam_type variable

    load_material_database()
    load_projects_from_disk()

    while True:
        selection = main_menu_template()

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
            print("\n")
            input(colored("Press Enter to return to the main menu...", 'cyan', attrs=['bold']))
            continue

        if selection == '1':  # Project Management
            while True:
                sub_choice = project_management_menu()
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
                    print_error("Invalid selection! Please try again.")
                    time.sleep(1)

        elif selection == '2':  # Define Beam Type
            while True:
                beam_type = Beam_Classification()
                if beam_type == "Simple" or beam_type == "Cantilever":
                    if beam_type == "Cantilever":
                        project_state["supports_saved"] = True
                    
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
                sub_choice = profile_definition_menu()
                if sub_choice == '4':  # Back to main menu
                    break
                elif sub_choice == '1':  # Define beam length
                    if project_state["is_loaded"] and project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a beam length defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                            
                    beam_length = Beam_Length()
                    project_state["has_unsaved_changes"] = True
                    print("")
                    cprint("==========================================================", 'red')
                    cprint(f"Beam Length is set to: {beam_length} m",'white')
                    cprint("==========================================================", 'red')
                    time.sleep(1)
                    
                elif sub_choice == '2':  # Choose profile
                    if project_state["is_loaded"] and project_state["profile_saved"]:
                        confirmation = input(colored("Project already has a profile defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                            
                    clear_screen()
                    profile_choice = choose_profile()
                    print("")
                    
                    # Moment of Inertia (MOI) Solver
                    if beam_type is None:
                        cprint("----------------------------------------------","white")
                        print_error("Note: Please define beam type !!!!")
                        cprint("----------------------------------------------","white")
                        print("")
                    if profile_choice == '1':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_ibeam()
                    elif profile_choice == '2':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_tbeam()
                    elif profile_choice == '3':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_circle()
                    elif profile_choice == '4':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_hollow_circle()
                    elif profile_choice == '5':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_square()
                    elif profile_choice == '6':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_hollow_square()
                    elif profile_choice == '7':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_rectangle()
                    elif profile_choice == '8':
                        Ix, shape, c, b, y_array = moi_solver.inertia_moment_hollow_rectangle()
                    else:
                        print_error("Invalid choice! Please try again.")
                        continue
                        
                    project_state["profile_saved"] = True
                    project_state["has_unsaved_changes"] = True
                    print_success("Profile defined successfully!")
                    time.sleep(2)
                    
                elif sub_choice == '3':  # View profile info
                    if not project_state["profile_saved"] and not shape:
                        print_error("No profile defined yet!")
                        time.sleep(2)
                        continue
                        
                    display_profile_info(beam_length, shape, Ix, c, b, y_array)

        elif selection == '4':  # Material Selection
            while True:
                sub_choice = material_selection_menu()
                if sub_choice == '3':  # Back to main menu
                    break
                elif sub_choice == '1':  # Select material
                    if project_state["is_loaded"] and project_state["material_saved"]:
                        confirmation = input(colored("Project already has a material defined. Modify? (Y/N): ", 'cyan'))
                        if confirmation.lower() != 'y':
                            continue
                            
                    selected_material = select_material()
                    if selected_material:
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
        
                    display_material_info(
                        selected_material, 
                        density, 
                        yield_strength, 
                        ultimate_strength, 
                        elastic_modulus, 
                        poisson_ratio, 
                        shear_yield_strength
                    )


        elif selection == '5':  # Boundary Conditions

            if beam_type == "Cantilever":
                print_error("Cantilever beams Boundary Conditions Already Defined !!!!")
                time.sleep(2)
                

            elif beam_type == "Simple":
                while True:
                    sub_choice = boundary_conditions_menu()
                    if sub_choice == '3':  # Back to main menu
                        break   
                    elif sub_choice == '1':  # Define supports
                        if project_state["is_loaded"] and project_state["supports_saved"]:
                            confirmation = input(colored("Project already has supports defined. Modify? (Y/N): ", 'cyan'))
                            if confirmation.lower() != 'y':
                                continue
                            
                        A, B, A_restraint, B_restraint, A_type, B_type = Beam_Supports()
                        project_state["supports_saved"] = True
                        project_state["has_unsaved_changes"] = True
                        support_types = ("pin", "roller")
                    
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        print(f"Pin Support Position(A): {A} m")
                        print("")
                        print(f"Roller Support Position(B): {B} m")
                        cprint("==========================================================", 'red')
                        print("")                        
                        input("Press Enter to return to the menu...")
                    
                    elif sub_choice == '2':  # View supports
                        if not project_state["supports_saved"] and not A_type and not B_type:
                            print_error("No supports defined yet!")
                            time.sleep(2)
                            continue
                        
                        print("")
                        cprint("==========================================================", 'red')
                        cprint("                Selected Support Positions                                 ", 'light_yellow')
                        cprint("==========================================================", 'red')
                        cprint(f"Pin Support Position(A): {A} m","white")
                        print("")
                        cprint(f"Roller Support Position(B): {B} m",'white')
                        cprint("==========================================================", 'red')
                        print("")
                        input("Press Enter to return to the menu...")
            else:
                print_error("Please define Beam Classification first !!!! ")
                time.sleep(2)
                continue

        elif selection == '6':  # Loads Definition
            if beam_type is None:
                print_error("Beam Classificatione is not defined yet!")
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
                        loads_dict = manage_loads()
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
                            print_error("No loads defined yet!")
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
                            print_error("Please Check your Entered Loads!")
                            time.sleep(2)
                            continue
                        elif not project_state["supports_saved"]:
                            print_error("Please Check your Entered Supports!")
                            time.sleep(2)
                            continue

                        try:
                            formatted_loads = format_loads_for_plotting(loads_dict)
                            if beam_type=="Simple":
                                formatted_loads = format_loads_for_plotting(loads_dict)
                                plot_beam_schematic(beam_length, A, B, support_types, formatted_loads)
                            elif beam_type=="Cantilever":
                                 fig = plot_cantilever_beam_schematic(beam_length, formatted_loads, "Cantilever Beam Analysis")
                                 fig.show()
                        except Exception as e:
                            print_error(f"Error plotting beam schematic: {e}")
                            time.sleep(2)
                    else:
                        print_error("Invalid selection! Please try again.")
                        time.sleep(2)
                    
        elif selection == '7':  # Show Beam Schematic (Standalone)
                if not project_state["loads_saved"]:
                    print_error("Please Check your Entered Loads!")
                    time.sleep(2)
                    continue
                elif not project_state["supports_saved"]:
                    print_error("Please Check your Entered Supports!")
                    time.sleep(2)
                    continue

                try:
                    formatted_loads = format_loads_for_plotting(loads)
                    if beam_type=="Simple":
                        plot_beam_schematic(beam_length, A, B, support_types, formatted_loads)
                    elif beam_type=="Cantilever":
                         fig = plot_cantilever_beam_schematic(beam_length, formatted_loads, "Cantilever Beam Analysis")
                         fig.show()
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
                    print_error("Analysis requires profile, material, supports and loads to be defined!")
                    time.sleep(2)
                    continue
                
                elif sub_choice == '1':  # Run analysis
                    try:
                        # Check if all required data is available
                        if not project_state["profile_saved"] or not project_state["material_saved"] or \
                           not project_state["loads_saved"] or not project_state["supports_saved"]:
                            print_error("Analysis requires profile, material, supports and loads to be defined!")
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
                            loads=loads
                        )
        
                        # Perform the analysis with proper arguments
                        if beam_type == "Simple":
                            X_Field, Total_ShearForce, Total_BendingMoment, Reactions = solve_simple_beam(
                                beam_length, A=A, B=B,
                                pointloads_in=pointloads, 
                                distributedloads_in=distributedloads,
                                momentloads_in=momentloads, 
                                triangleloads_in=triangleloads,
                                beam_type=beam_type
                            )
                        elif beam_type == "Cantilever":
                             X_Field, Total_ShearForce, Total_BendingMoment, Reactions = solve_cantilever_beam(
                                 beam_length, 
                                 pointloads_in=pointloads,
                                 distributedloads_in=distributedloads,
                                 momentloads_in=momentloads, 
                                 triangleloads_in=triangleloads
                             )
        
                        # Mark results as available for use in other menus
                        project_state["analysis_complete"] = True
                        project_state["has_unsaved_changes"] = True
        
                        # Extract and display key results
                        if beam_type == "Simple":
                            Va = Reactions[0]
                            Ha = Reactions[2]
                            Vb = Reactions[1]
                        else:
                            Va = Reactions[0]
                            Ha = Reactions[1]
                            Ma = Reactions[2]

                        max_shear = round(np.max(Total_ShearForce), 3)
                        min_shear = round(np.min(Total_ShearForce), 3)
                        max_bending = round(np.max(Total_BendingMoment), 3)
                        min_bending = round(np.min(Total_BendingMoment), 3)
        
                        # Display analysis completion message
                        print("")
                        print(colored("╔══════════════════════════════════════════════════════════════╗", 'green', attrs=['bold']))
                        print(colored("║           BEAM ANALYSIS COMPLETED SUCCESSFULLY!              ║", 'green', attrs=['bold']))
                        print(colored("╚══════════════════════════════════════════════════════════════╝", 'green', attrs=['bold']))
                        print("")
                        print(colored("You can now:", 'white'))
                        print(colored("• View detailed analysis results", 'white'))
                        print(colored("• Calculate deflection", 'white'))
                        print(colored("• Calculate stress and factor of safety", 'white'))
                        print(colored("• Visualize results through plots", 'white'))
                        print("")
                        input(colored("Press Enter to return to the Analysis/Simulation menu...", 'cyan', attrs=['bold']))
        
                    except Exception as e:
                        print_error(f"Error solving beam: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '2':  # View analysis results
                    if not project_state.get("analysis_complete", False):
                        print_error("No analysis results available yet! Please run analysis first.")
                        time.sleep(2)
                        continue
        
                    try:
                        # Extract key results
                        if beam_type == "Simple":
                            Va = Reactions[0]
                            Ha = Reactions[2]
                            Vb = Reactions[1]
                            Ma = None
                        else:  # Cantilever
                            Va = Reactions[0]
                            Ha = Reactions[1]
                            Ma = Reactions[2]
                            Vb = None

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
                            min_bending=min_bending
                        )
        
                    except Exception as e:
                        print_error(f"Error displaying analysis results: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '3':  # Calculate deflection
                    if not project_state.get("analysis_complete", False):
                        print_error("Please run the analysis first!")
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
        
                        # Perform actual calculation
                        Deflection, Slope, curv = calculate_beam_deflection(
                            X_Field, Total_BendingMoment, elastic_modulus, Ix)
        
                        # Update project state
                        project_state["deflection_calculated"] = True
                        project_state["has_unsaved_changes"] = True
        
                        # Display results in professional format
                        display_deflection_analysis(
                            beam_length=beam_length,
                            shape=shape,
                            beam_type=beam_type,
                            elastic_modulus=elastic_modulus,
                            Ix=Ix,
                            Deflection=Deflection,
                            Slope=Slope,
                            curv=curv
                        )
        
                    except Exception as e:
                        print_error(f"Error calculating deflection: {e}")
                        time.sleep(2)
                        continue
                elif sub_choice == '4':  # Calculate stress and FOS
                    if not project_state.get("analysis_complete", False):
                        print_error("Please run the analysis first!")
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
                        # BUG-09 FIX: build section-aware b(y) for correct τ = VQ/(Ib(y))
                        b_array = width_array_for_section(shape, c, b, y_array)
                        Q_array = first_moment_of_area_general(b_array, y_array)
                        Shear_stress = calculate_shear_stress(Total_ShearForce, Q_array, Ix, b_array)
                        Max_Shear_stress = np.max(np.abs(Shear_stress))

                        # Calculate bending stress
                        bending_stress = calculate_bending_stress(Total_BendingMoment, c, Ix)
                        Max_bending_stress = np.max(np.abs(bending_stress))
        
                        # Calculate factor of safety
                        FOS = Factor_of_Safety(Total_BendingMoment, c, yield_strength, Ix)
        
                        # Update project state
                        project_state["stress_calculated"] = True
                        project_state["has_unsaved_changes"] = True
        
                        # Display results in professional format
                        display_stress_analysis(
                            beam_type=beam_type,
                            shape=shape,
                            selected_material=selected_material,
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
                            FOS=FOS
                        )
        
                    except Exception as e:
                        print_error(f"Error in stress/F.O.S calculations: {e}")
                        time.sleep(2)
                        continue
        elif selection == '9':  # Postprocessing/Visualization
            while True:
                sub_choice = postprocessing_menu()
                if sub_choice == '6':  # Back to main menu
                    break
                    
                # Check if analysis has been completed before allowing visualization
                if not project_state.get("analysis_complete", False):
                    print_error("Please complete an analysis before attempting visualization!")
                    time.sleep(2)
                    continue
                    
                if sub_choice == '1':  # Reaction forces schematic
                    try:
                        print_success("Processing Reactions Forces Schematic Plots (Plotly-only):")
                        plot_reaction_diagram(A, B, Reactions, support_types)
                    except Exception as e:
                        print_error(f"Error plotting reaction diagram: {e}")
                        time.sleep(2)
                        continue
                        
                elif sub_choice == '2':  # SFD/BMD (Matplotlib)
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Shear Force/Bending Moment Plots (Matplotlib):")
                            Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment)
                        elif style == '2':
                                print_success("Processing Shear Force/Bending Moment Plots (Plotly):")
                                Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length)
                        
                    except Exception as e:
                        print_error(f"Error in Plotting !!! : {e}")
                        time.sleep(2)
                        continue
                        
                elif sub_choice == '5':  # Combined plots
                    try:
                        # BUG-07 FIX: only pass arrays that have actually been computed
                        defl_data = Deflection if project_state.get("deflection_calculated", False) else None
                        shear_data = Shear_stress if project_state.get("stress_calculated", False) else None

                        if defl_data is None:
                            print(colored("  ℹ  Deflection not yet calculated — will be omitted from combined plot.", 'yellow'))
                        if shear_data is None:
                            print(colored("  ℹ  Shear stress not yet calculated — will be omitted from combined plot.", 'yellow'))

                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Combined Plots (Matplotlib):")
                            Matplot_combined(X_Field, Total_ShearForce, Total_BendingMoment, Deflection=defl_data, ShearStress=shear_data)
                        elif style == '2':
                            print_success("Processing Combined Plots (Plotly):")
                            Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, Deflection=defl_data, ShearStress=shear_data)
                        else:
                            print_error("Invalid style selection!")
                            time.sleep(2)
                            continue

                    except Exception as e:
                        print_error(f"Error in Plotting !!! : {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '3':  # Deflection plot
                    if not project_state.get("deflection_calculated", False):
                        print_error("Please calculate deflection first (in Analysis menu)!")
                        time.sleep(2)
                        continue

                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing Deflection/Displacement Plots (Matplotlib):")
                            Matplot_Deflection(X_Field, Deflection)
                        elif style == '2':
                            print_success("Processing Deflection/Displacement Plots (Plotly):")
                            Plotly_Deflection(X_Field, Deflection, beam_length)
                        else:
                            print_error("Invalid style selection!")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting Deflection Plot: {e}")
                        time.sleep(2)
                        continue

                elif sub_choice == '4':  # Stress contours
                    # BUG-07 FIX: guard against accessing Shear_stress/bending_stress before computed
                    if not project_state.get("stress_calculated", False):
                        print_error("Please calculate stresses first (Analysis menu → option 4)!")
                        time.sleep(2)
                        continue
                    try:
                        style = input(colored("Choose a style (1 for Matplotlib, 2 for Plotly) ➔ ", 'cyan'))
                        if style == '1':
                            print_success("Processing shear/Bending Stress Plots (Matplotlib):")
                            Matplot_ShearStress(X_Field, Shear_stress)
                            Matplot_BendingStress(X_Field, bending_stress)
                        elif style == '2':
                            print_success("Processing shear/Bending Plots (Plotly):")
                            Plotly_ShearStress(X_Field, Shear_stress, beam_length)
                            Plotly_BendingStress(X_Field, bending_stress, beam_length)
                        else:
                            print_error("Invalid style selection!")
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print_error(f"Error plotting shear-Stress Plot: {e}")
                        time.sleep(2)

        elif selection == '10':  # Save Project
            if not project_state["profile_saved"] or not project_state["material_saved"] or \
               not project_state["supports_saved"] or not project_state["loads_saved"]:
                print_error("You must define profile, material, supports and loads before saving!")
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
                        print_error("Failed to save project!")
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
            
            print_success("Thank you for using the Zylo-X Beam Calculator!")
            break

        elif selection == '11':  # Recommendations
            # Check if all necessary analyses have been done
            if not project_state.get("analysis_complete", False):
                print_error("Please run the basic analysis first before getting recommendations!")
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
                    yield_strength=yield_strength if 'yield_strength' in globals() else None
                )
    
            except Exception as e:
                print_error(f"Error generating recommendations: {e}")
                time.sleep(2)
                continue  
    
        else:
            print_error("Invalid selection! Please try again.")
            time.sleep(1)

display_engineering_recommendations

def init():
    global project_state

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