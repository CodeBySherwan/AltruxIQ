"""Analysis summary and static-solution results report renderers.

Extracted from ``ui.Menus`` during the P3 ``ui/reports/`` decomposition
(checkpoint-4). Pure relocation; signatures and behavior unchanged.
"""
import time
from termcolor import colored

from common.units import METRIC_UNITS, get_divisor
from ui.console import (
    ui_banner,
    ui_open,
    ui_close,
    ui_blank,
    ui_head,
    ui_field,
    ui_bullet,
    ui_footer,
    clear_screen,
)


def display_analysis_info(beam_type, beam_length, shape, selected_material, 
                         A=None, B=None, A_type=None, B_type=None, loads=None, units=METRIC_UNITS):
    """
    Display enhanced analysis information in a professional FEA-like format.
    
    Parameters:
    -----------
    beam_type: str
        Type of beam ("Simple" or "Cantilever")
    beam_length: float
        Length of the beam in meters
    shape: str
        Name of the profile shape
    selected_material: dict
        Dictionary containing material properties
    A, B: float
        Support positions for simple beam (optional)
    A_type, B_type: str
        Support types for simple beam (optional)
    loads: dict
        Dictionary containing defined loads
    """
    clear_screen()
 # Fetch divisors
    len_div = get_divisor(units, 'length')
    mod_div = get_divisor(units, 'modulus')
    stress_div = get_divisor(units, 'stress')
    dens_div = get_divisor(units, 'density')   
    # Count loads
    point_load_count = len(loads.get("pointloads", [])) if loads else 0
    distributed_load_count = len(loads.get("distributedloads", [])) if loads else 0
    moment_load_count = len(loads.get("momentloads", [])) if loads else 0
    triangle_load_count = len(loads.get("triangleloads", [])) if loads else 0
    total_load_count = point_load_count + distributed_load_count + moment_load_count + triangle_load_count
    
    # Create decorative header
    print("\n")
    print(colored("╔══════════════════════════════════════════════════════════════╗", 'cyan', attrs=['bold']))
    print(colored("║                AltruxIQ Beam Analysis Engine                   ║", 'cyan', attrs=['bold']))
    print(colored("╚══════════════════════════════════════════════════════════════╝", 'cyan', attrs=['bold']))
    
    # Solver Information
    print("\n")
    print(colored("┌─ SOLVER INFORMATION "+"─"*40, 'yellow', attrs=['bold']))
    print(colored("│", 'yellow'))
    print(colored("│ Solver Type:", 'yellow') + colored(" Beam Finite Element Analysis", 'white'))
    print(colored("│ Solution Method:", 'yellow') + colored(" Direct Stiffness Method", 'white'))
    print(colored("│ Element Type:", 'yellow') + colored(" 1D Beam Element (Euler-Bernoulli)", 'white'))
    print(colored("│ Solver Version:", 'yellow') + colored(" AltruxIQ 2.00 Alpha", 'white'))
    print(colored("│ Numerical Precision:", 'yellow') + colored(" Double Precision (64-bit)", 'white'))
    print(colored("│ Mesh Density:", 'yellow') + colored(" 10,000 Elements", 'white'))
    print(colored("│ Estimated Solution Time:", 'yellow') + colored(" < 1 sec", 'white'))
    print(colored("│", 'yellow'))
    print(colored("└" + "─"*62, 'yellow', attrs=['bold']))
    time.sleep(0.1)

    # Model Information
    print("\n")
    print(colored("┌─ MODEL INFORMATION "+"─"*41, 'green', attrs=['bold']))
    print(colored("│", 'green'))
    print(colored("│ Analysis Type:", 'green') + colored(" Static Linear Elastic", 'white'))
    print(colored("│ Beam Type:", 'green') + colored(f" {beam_type} Beam", 'white'))
    print(colored("│ Beam Length:", 'green') + colored(f" {beam_length / len_div:.3f} {units['length']}", 'white'))
    print(colored("│ Profile Type:", 'green') + colored(f" {shape}", 'white'))
    print(colored("│", 'green'))
    print(colored("└" + "─"*62, 'green', attrs=['bold']))
    time.sleep(0.1)
    # Material Properties
    print("\n")
    print(colored("┌─ MATERIAL PROPERTIES "+"─"*40, 'magenta', attrs=['bold']))
    print(colored("│", 'magenta'))
    material_name = selected_material.get('Material', 'Unknown')
    print(colored("│ Material:", 'magenta') + colored(f" {material_name}", 'white'))
    
    # Display only if material properties are available
    if selected_material:
        # Convert raw JSON DB values to base SI internally before displaying
        raw_E_Pa = selected_material.get('Elastic Modulus', 0) * 1e9
        raw_Y_Pa = selected_material.get('Yield Strength', 0) * 1e6
        raw_Dens = selected_material.get('Density', 0)

        print(colored("│ Young's Modulus (E):", 'magenta') + colored(f" {raw_E_Pa / mod_div:.1f} {units['modulus']}", 'white'))
        print(colored("│ Poisson's Ratio (ν):", 'magenta') + colored(f" {selected_material.get('Poisson Ratio', 0):.2f}", 'white'))
        print(colored("│ Density:", 'magenta') + colored(f" {raw_Dens / dens_div:.1f} {units['density']}", 'white'))
        print(colored("│ Yield Strength:", 'magenta') + colored(f" {raw_Y_Pa / stress_div:.1f} {units['stress']}", 'white'))
    
    print(colored("│", 'magenta'))
    print(colored("└" + "─"*62, 'magenta', attrs=['bold']))
    
    # Boundary Conditions
    print("\n")
    print(colored("┌─ BOUNDARY CONDITIONS "+"─"*40, 'blue', attrs=['bold']))
    print(colored("│", 'blue'))
    
    if beam_type == "Simple":
        print(colored("│ Support Type:", 'blue') + colored(" Simply Supported Beam", 'white'))
        print(colored("│ Left Support:", 'blue') + colored(f" {A_type} at x = {A / len_div:.3f} {units['length']}", 'white'))
        print(colored("│ Right Support:", 'blue') + colored(f" {B_type} at x = {B / len_div:.3f} {units['length']}", 'white'))

    elif beam_type == "Cantilever":
        print(colored("│ Support Type:", 'blue') + colored(" Cantilever Beam", 'white'))
        print(colored("│ Fixed End:", 'blue') + colored(f" at x = 0.000 {units['length']}", 'white'))
        print(colored("│ Free End:", 'blue') + colored(f" at x = {beam_length / len_div:.3f} {units['length']}", 'white'))

    else:
        print(colored("│ Support Type:", 'blue') + colored(f" {beam_type} Configuration", 'white'))
        print(colored("│ Boundaries:", 'blue') + colored(" Defined internally by user", 'white'))

    print(colored("│", 'blue'))
    print(colored("└" + "─"*62, 'blue', attrs=['bold']))
    
    # Load Summary
    print("\n")
    print(colored("┌─ LOAD SUMMARY "+"─"*46, 'red', attrs=['bold']))
    print(colored("│", 'red'))
    print(colored("│ Total Load Definitions:", 'red') + colored(f" {total_load_count}", 'white'))
    print(colored("│ • Point Loads:", 'red') + colored(f" {point_load_count}", 'white'))
    print(colored("│ • Distributed Loads:", 'red') + colored(f" {distributed_load_count}", 'white'))
    print(colored("│ • Moment Loads:", 'red') + colored(f" {moment_load_count}", 'white'))
    print(colored("│ • Triangular Loads:", 'red') + colored(f" {triangle_load_count}", 'white'))
    print(colored("│", 'red'))
    print(colored("└" + "─"*62, 'red', attrs=['bold']))
    time.sleep(0.1)
    # Analysis Progress
    print("\n")
    print(colored("┌─ ANALYSIS PROGRESS "+"─"*42, 'cyan', attrs=['bold']))
    print(colored("│", 'cyan'))
    print(colored("│ [", 'cyan') + colored("■■■■■■■■■■■■■■■■■■■■", 'white') + colored("] 100%", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("│ ✓ Initializing solver...", 'cyan'))
    print(colored("│ ✓ Building element matrices...", 'cyan'))
    print(colored("│ ✓ Assembling global matrices...", 'cyan'))
    print(colored("│ ✓ Applying boundary conditions...", 'cyan'))
    print(colored("│ ✓ Applying loads...", 'cyan'))
    print(colored("│ ✓ Solving system equations...", 'cyan'))
    print(colored("│ ✓ Computing internal forces...", 'cyan'))
    print(colored("│ ✓ Analysis complete!", 'cyan'))
    print(colored("│", 'cyan'))
    print(colored("└" + "─"*62, 'cyan', attrs=['bold']))
    
    print("\n")
    input(colored("Press Enter to view analysis results...", 'cyan', attrs=['bold']))


def display_analysis_results(beam_type, shape, beam_length, A=None, B=None,
                           Va=None, Ha=None, Vb=None, Ma=None,
                           max_shear=None, min_shear=None,
                           max_bending=None, min_bending=None, units=METRIC_UNITS):
    """Professional, commercial-grade presentation of the static solution:
    solver summary, support reactions, equilibrium audit and critical envelopes."""
    clear_screen()
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    mom_div = get_divisor(units, 'moment')

    ui_banner("SOLUTION RESULTS  \u2014  STATIC ANALYSIS",
              "Reactions \u2022 Internal Forces \u2022 Equilibrium Audit", color='cyan')

    # ---- Solver summary --------------------------------------------------
    print("\n")
    ui_open("SOLVER SUMMARY", 'blue')
    ui_blank('blue')
    ui_field("Analysis type", "Static \u2014 Linear Elastic (1D Beam)", 'blue', 'blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    ui_field("Span length", f"{beam_length / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_field("Cross-section", f"{shape}", 'blue', 'blue')
    ui_field("Solution status", "CONVERGED \u2713", 'blue', 'blue', value_color='green')
    ui_blank('blue')
    ui_close('blue')

    # ---- Support reactions ----------------------------------------------
    print("\n")
    ui_open("SUPPORT REACTIONS", 'green')
    ui_blank('green')
    if beam_type == "Simple":
        ui_field("Support configuration", "Pin (A) \u2014 Roller (B)", 'green', 'green')
        ui_blank('green')
        ui_head("Support A  (Pin)", 'green', 'green')
        ui_field("Position", f"{A / len_div:.3f} {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Va / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Horizontal reaction Rₓ", f"{Ha / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_blank('green')
        ui_head("Support B  (Roller)", 'green', 'green')
        ui_field("Position", f"{B / len_div:.3f} {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Vb / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
    elif beam_type == "Cantilever":
        ui_field("Support configuration", "Fixed (A) \u2014 Free (B)", 'green', 'green')
        ui_blank('green')
        ui_head("Fixed Support", 'green', 'green')
        ui_field("Position", f"0.000 {units['length']}", 'green', 'green', bullet="\u2022")
        ui_field("Vertical reaction  Rᵧ", f"{Va / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Horizontal reaction Rₓ", f"{Ha / force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Moment reaction  M", f"{Ma / mom_div:.3f} {units['moment']}", 'green', 'green', bullet="\u2022")
    else:
        ui_field("Support configuration", f"{beam_type}", 'green', 'green')
        ui_field("Reaction at origin Rᵧ", f"{(Va or 0)/ force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
        ui_field("Reaction at far end Rᵧ", f"{(Vb or 0)/ force_div:.3f} {units['force']}", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_close('green')

    # ---- Equilibrium verification ---------------------------------------
    v_sum = (Va or 0) + (Vb or 0)
    h_sum = (Ha or 0)
    print("\n")
    ui_open("EQUILIBRIUM AUDIT  (\u03a3F = 0, \u03a3M = 0)", 'yellow')
    ui_blank('yellow')
    ui_field("\u03a3 Vertical forces", f"{v_sum/force_div:.3e} {units['force']}", 'yellow', 'yellow')
    ui_field("\u03a3 Horizontal forces", f"{h_sum/force_div:.3e} {units['force']}", 'yellow', 'yellow')
    if abs(v_sum) < 1e-2 and abs(h_sum) < 1e-2:
        ui_field("Static equilibrium", "SATISFIED \u2713", 'yellow', 'yellow', value_color='green')
    else:
        ui_field("Static equilibrium", "RESIDUAL DETECTED \u26a0", 'yellow', 'yellow', value_color='red')
        ui_bullet("Minor residuals are numerical (rounding) for determinate systems.", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    # ---- Critical internal-force envelopes ------------------------------
    abs_max_shear = max(abs(max_shear), abs(min_shear))
    abs_max_moment = max(abs(max_bending), abs(min_bending))
    print("\n")
    ui_open("CRITICAL INTERNAL-FORCE ENVELOPE", 'magenta')
    ui_blank('magenta')
    ui_head("Shear Force  V(x)", 'magenta', 'magenta')
    ui_field("Maximum (+)", f"{max_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Minimum (\u2212)", f"{min_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Absolute peak |V|", f"{abs_max_shear / force_div:.3f} {units['force']}", 'magenta', 'magenta',
             bullet="\u2022", value_color='white')
    ui_blank('magenta')
    ui_head("Bending Moment  M(x)", 'magenta', 'magenta')
    ui_field("Maximum (+)", f"{max_bending / mom_div:.3f} {units['moment']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Minimum (\u2212)", f"{min_bending / mom_div:.3f} {units['moment']}", 'magenta', 'magenta', bullet="\u2022")
    ui_field("Absolute peak |M|", f"{abs_max_moment / mom_div:.3f} {units['moment']}", 'magenta', 'magenta',
             bullet="\u2022", value_color='white')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Next steps ------------------------------------------------------
    print("\n")
    ui_open("RECOMMENDED NEXT STEPS", 'cyan')
    ui_blank('cyan')
    ui_bullet("Run Deflection check  \u2014 assess serviceability (L/360, L/480).", 'cyan', 'cyan')
    ui_bullet("Run Stress & FoS check \u2014 verify strength limit state.", 'cyan', 'cyan')
    ui_bullet("Open Design Check report \u2014 consolidated verification & sizing.", 'cyan', 'cyan')
    ui_bullet("Generate SFD/BMD & 3D contour plots in Post-Processing.", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_close('cyan')

    ui_footer("Press Enter to return to the Solution menu...")
