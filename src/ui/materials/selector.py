"""Material selection, info display and custom-material definition.

This module is a **leaf** in the UI dependency graph: it imports only from
``common``, ``database``, ``core.state``, ``ui.console`` and the stdlib. It
has no back-edge into ``ui.cli`` or ``ui.inputs`` — which is what lets
``ui.inputs`` import material helpers eagerly here instead of via the old
lazy ``from ui.cli import ...`` that existed solely to break a circular import
(the root cause of the historical P0-1 crash).

Extracted from ``ui.cli`` (``load_material_database`` / ``select_material`` /
``display_material_info``) and ``ui.inputs`` (``define_custom_material``)
during the P3 ``materials/`` decomposition. Pure relocation; signatures and
behavior unchanged.
"""
import json
import time
from termcolor import colored

from database.materials_database import MaterialDatabase
from core.state import state
from common.units import METRIC_UNITS, default_units, to_json, get_divisor
from ui.console import print_error, print_success, clear_screen
from ui.console.prompts import ask_float, ask_text


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
    if units is None: units = METRIC_UNITS
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


# =============================
# Custom Material Definition
# =============================
def define_custom_material(unit_system="Metric", units=None):
    """Interactive wizard to create a custom material entry."""
    if units is None: units = default_units()
    clear_screen()
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║               DEFINE CUSTOM MATERIAL                         ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    print("\n")
    name = ask_text("Enter material name", required=True, allow_cancel=True, max_len=60)
    if name is None:
        return None

    # Inputs in active units, converted to JSON base schema (kg/m³, MPa, GPa)
    # via common.units.to_json — single source of truth for the storage convention
    dens_val = ask_float("Enter density", unit=units['density'], minimum=0, exclusive_min=True, allow_cancel=True)
    if dens_val is None: return None
    json_dens = to_json(units, 'density', dens_val)

    yield_val = ask_float("Enter yield strength", unit=units['stress'], minimum=0, exclusive_min=True, allow_cancel=True)
    if yield_val is None: return None
    json_yield = to_json(units, 'stress', yield_val)

    ult_val = ask_float("Enter ultimate strength", unit=units['stress'], minimum=0, exclusive_min=True, allow_cancel=True)
    if ult_val is None: return None
    json_ult = to_json(units, 'stress', ult_val)

    if json_yield >= json_ult:
        print_error("Yield Strength must be less than Ultimate Strength.")
        time.sleep(2)
        return None

    mod_val = ask_float("Enter elastic modulus", unit=units['modulus'], minimum=0, exclusive_min=True, allow_cancel=True)
    if mod_val is None: return None
    json_mod = to_json(units, 'modulus', mod_val)

    poisson = ask_float("Enter Poisson's ratio", minimum=0, maximum=0.5, exclusive_min=True, exclusive_max=True, default=0.3, allow_cancel=True)
    if poisson is None: return None

    therm = ask_float("Enter thermal expansion coefficient (1/°C, 0 to skip)", default=0, allow_cancel=True)
    if therm is None: return None
    desc = ask_text("Enter a short description", required=False, allow_cancel=True, max_len=120)
    if desc is None:
        desc = ""

    material_dict = {
        "Material": name,
        "Density": round(json_dens, 2),
        "Yield Strength": round(json_yield, 2),
        "Ultimate Strength": round(json_ult, 2),
        "Elastic Modulus": round(json_mod, 2),
        "Poisson Ratio": round(poisson, 3),
        "Thermal Expansion": therm if therm != 0 else 0,
        "Description": desc
    }

    return material_dict
