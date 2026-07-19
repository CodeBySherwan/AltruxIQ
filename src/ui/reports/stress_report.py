"""Strength limit-state (stress & factor-of-safety) report renderer.

Extracted from ``ui.Menus`` during the P3 ``ui/reports/`` decomposition
(checkpoint-4). Pure relocation; signatures and behavior unchanged.
"""
import numpy as np

from common.units import METRIC_UNITS, get_divisor
from common.config import SERVICEABILITY
from ui.console import (
    ui_banner,
    ui_open,
    ui_close,
    ui_blank,
    ui_text,
    ui_head,
    ui_field,
    ui_bullet,
    ui_check_row,
    ui_footer,
    clear_screen,
)


def display_stress_analysis(beam_type, shape, selected_material, Ix, c, b,
                          y_array, Total_ShearForce, Total_BendingMoment,
                          Shear_stress, Max_Shear_stress, bending_stress,
                          Max_bending_stress, FOS, units=METRIC_UNITS, segments=None):
    """Commercial-grade strength limit-state report: bending, shear, von Mises
    combined stress, demand/capacity bars and factor-of-safety verdict."""
    clear_screen()
    stress_div = get_divisor(units, 'stress')
    sec_mod_div = get_divisor(units, 'sec_mod')
    inertia_div = get_divisor(units, 'inertia')

    yield_strength = selected_material.get('Yield Strength', 0) * 1e6  # MPa -> Pa
    section_modulus = Ix / c if c else 0.0
    allowable_stress = (yield_strength / FOS) if FOS else 0.0

    tau_max = Max_Shear_stress
    sigma_max = Max_bending_stress
    von_mises = np.sqrt(sigma_max**2 + 3 * tau_max**2)

    n = len(Total_BendingMoment)
    bm_frac = int(np.argmax(np.abs(Total_BendingMoment))) / max(1, (n - 1))
    sf_frac = int(np.argmax(np.abs(Total_ShearForce))) / max(1, (n - 1))

    # demand/capacity ratios
    dc_bending = (sigma_max / yield_strength) if yield_strength else 0.0
    dc_shear = (tau_max / (0.577 * yield_strength)) if yield_strength else 0.0  # von Mises shear yield
    dc_vm = (von_mises / yield_strength) if yield_strength else 0.0

    ui_banner("STRENGTH  \u2014  STRESS & FACTOR OF SAFETY",
              "\u03c3 = My/I  \u2022  \u03c4 = VQ/Ib  \u2022  von Mises", color='cyan')

    # ---- Analysis parameters --------------------------------------------
    print("\n")
    ui_open("ANALYSIS PARAMETERS", 'blue')
    ui_blank('blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    if beam_type == "Stepped Bar" and segments:
        ui_field("Cross-section", "Varies along length", 'blue', 'blue')
        ui_field("Material", "Varies along length", 'blue', 'blue')
        ui_field("Yield strength  Fy", "Varies along length", 'blue', 'blue')
        ui_field("Section modulus  S", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Cross-section", f"{shape}", 'blue', 'blue')
        ui_field("Material", f"{selected_material.get('Material', 'Unknown')}", 'blue', 'blue')
        ui_field("Yield strength  Fy", f"{yield_strength / stress_div:.2f} {units['stress']}", 'blue', 'blue')
        ui_field("Section modulus  S", f"{section_modulus / sec_mod_div:.4e} {units['sec_mod']}", 'blue', 'blue')
        ui_field("Moment of inertia  I", f"{Ix / inertia_div:.4e} {units['inertia']}", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Computed stress state ------------------------------------------
    print("\n")
    ui_open("COMPUTED STRESS STATE", 'green')
    ui_blank('green')
    ui_head("Bending (normal) stress  \u03c3", 'green', 'green')
    ui_field("Maximum |\u03c3|", f"{sigma_max / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Location", f"x \u2248 {bm_frac:.2f}\u00b7L", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_head("Transverse shear stress  \u03c4", 'green', 'green')
    ui_field("Maximum |\u03c4|", f"{tau_max / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Location", f"x \u2248 {sf_frac:.2f}\u00b7L", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_head("Combined stress  (von Mises)  \u03c3ᵥ", 'green', 'green')
    ui_field("Maximum \u03c3ᵥ", f"{von_mises / stress_div:.2f} {units['stress']}", 'green', 'green', bullet="\u2022")
    ui_field("Fraction of yield", f"{dc_vm*100:.1f}% of Fy", 'green', 'green', bullet="\u2022")
    ui_blank('green')
    ui_close('green')

    # ---- Strength limit-state checks ------------------------------------
    print("\n")
    ui_open("STRENGTH LIMIT-STATE CHECKS  (demand / capacity)", 'magenta')
    ui_blank('magenta')
    ui_check_row("Bending  \u03c3 / Fy", dc_bending)
    ui_check_row("Shear  \u03c4 / 0.577Fy", dc_shear)
    ui_check_row("von Mises  \u03c3ᵥ / Fy", dc_vm)
    ui_blank('magenta')
    ui_text("Capacity = material yield (Fy). D/C \u2264 1.00 means no yielding.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Factor of safety ------------------------------------------------
    if FOS >= 2.0:
        s_status, s_col, s_msg = "EXCELLENT \u2713", 'green', "High margin of safety."
    elif FOS >= SERVICEABILITY.TARGET_FACTOR_OF_SAFETY:
        s_status, s_col, s_msg = "GOOD \u2713", 'green', "Meets standard structural requirements."
    elif FOS >= 1.0:
        s_status, s_col, s_msg = "MARGINAL \u26a0", 'yellow', "Safe but limited reserve \u2014 review loads."
    else:
        s_status, s_col, s_msg = "UNSAFE \u2717", 'red', "Predicted yielding under design loads."

    print("\n")
    ui_open("FACTOR OF SAFETY", 'magenta')
    ui_blank('magenta')
    ui_field("Factor of safety  (Fy/\u03c3)", f"{FOS:.2f}", 'magenta', 'magenta', value_color=s_col)
    ui_field("Allowable stress", f"{allowable_stress / stress_div:.2f} {units['stress']}", 'magenta', 'magenta')
    ui_field("Safety status", s_status, 'magenta', 'magenta', value_color=s_col)
    ui_field("Assessment", s_msg, 'magenta', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Design guidance -------------------------------------------------
    print("\n")
    ui_open("DESIGN GUIDANCE", 'yellow')
    ui_blank('yellow')
    ui_head("Recommended FoS by application:", 'yellow', 'yellow')
    ui_bullet("1.25 \u2013 1.50 : routine static structural members", 'yellow', 'yellow')
    ui_bullet("1.50 \u2013 2.00 : critical / primary load paths", 'yellow', 'yellow')
    ui_bullet("2.00 \u2013 3.00 : dynamic, impact or cyclic loading", 'yellow', 'yellow')
    ui_bullet("3.00+         : life-safety / high-uncertainty cases", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_head("Action:", 'yellow', 'yellow')
    if FOS < 1.0:
        ui_bullet("CRITICAL \u2014 increase section size or upgrade material.", 'yellow', 'yellow', mark="\u2717")
    elif FOS < SERVICEABILITY.TARGET_FACTOR_OF_SAFETY:
        ui_bullet("Improve section if member is critical; verify load model.", 'yellow', 'yellow', mark="\u26a0")
    elif FOS > 2.5:
        ui_bullet("Over-designed \u2014 consider lighter section to save weight/cost.", 'yellow', 'yellow', mark="\u2193")
    else:
        ui_bullet("Design meets strength requirements with appropriate reserve.", 'yellow', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the Solution menu...")
