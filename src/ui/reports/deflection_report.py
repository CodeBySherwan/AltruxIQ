"""Serviceability (deflection) report renderer with limit-state checks.

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
    ui_field,
    ui_bullet,
    ui_check_row,
    ui_footer,
    clear_screen,
)


def display_deflection_analysis(beam_length, shape, beam_type, elastic_modulus, Ix, Deflection, Slope, curv, units=METRIC_UNITS):
    """Commercial-grade serviceability (deflection) report with limit-state
    demand/capacity bars against L/240, L/360 and L/480 criteria."""
    clear_screen()
    len_div = get_divisor(units, 'length')
    small_len_div = get_divisor(units, 'length_small')

    max_defl_idx = int(np.argmax(np.abs(Deflection)))
    max_defl = Deflection[max_defl_idx]
    max_defl_pos = max_defl_idx * (beam_length / (len(Deflection) - 1))
    max_defl_abs = abs(max_defl)

    max_slope_idx = int(np.argmax(np.abs(Slope)))
    max_slope = Slope[max_slope_idx]
    max_slope_pos = max_slope_idx * (beam_length / (len(Slope) - 1))

    max_curv_idx = int(np.argmax(np.abs(curv)))
    max_curv = curv[max_curv_idx]
    max_curv_pos = max_curv_idx * (beam_length / (len(curv) - 1))

    span_ratio = max_defl_abs / beam_length if beam_length else 0.0
    inv_ratio = (1.0 / span_ratio) if span_ratio > 0 else float('inf')

    ui_banner("SERVICEABILITY  \u2014  DEFLECTION ANALYSIS",
              "Euler\u2013Bernoulli  \u2022  Limit-State Verification", color='cyan')

    # ---- Solution parameters --------------------------------------------
    print("\n")
    ui_open("SOLUTION PARAMETERS", 'blue')
    ui_blank('blue')
    ui_field("Beam theory", "Euler\u2013Bernoulli (small deflection)", 'blue', 'blue')
    ui_field("Integration scheme", "Numerical (double integration of M/EI)", 'blue', 'blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    ui_field("Span length  L", f"{beam_length / len_div:.3f} {units['length']}", 'blue', 'blue')
    if beam_type == "Stepped Bar":
        ui_field("Elastic modulus  E", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
        ui_field("Flexural rigidity  EI", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Elastic modulus  E", f"{elastic_modulus/1e9:.1f} {units['modulus']}", 'blue', 'blue')
        ui_field("Moment of inertia  I", f"{Ix:.4e} {units['inertia']}", 'blue', 'blue')
        ui_field("Flexural rigidity  EI", f"{elastic_modulus*Ix:.3e} N\u00b7m\u00b2", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Deflection results ---------------------------------------------
    if max_defl_abs < 1e-3:
        defl_disp = f"{max_defl / small_len_div:.4f} {units['length_small']}"
    else:
        defl_disp = f"{max_defl / len_div:.6f} {units['length']}"
    arrow = "\u2191 (up)" if max_defl > 0 else "\u2193 (down)"

    print("\n")
    ui_open("DEFLECTION RESULTS", 'green')
    ui_blank('green')
    ui_field("Maximum deflection  \u03b4max", f"{defl_disp}  {arrow}", 'green', 'green')
    ui_field("Location of \u03b4max", f"x = {max_defl_pos / len_div:.3f} {units['length']}", 'green', 'green')
    ui_field("Span/deflection ratio", f"L / {inv_ratio:.0f}", 'green', 'green')
    ui_blank('green')
    ui_close('green')

    # ---- Limit-state serviceability checks ------------------------------
    print("\n")
    ui_open("SERVICEABILITY LIMIT-STATE CHECKS  (demand / capacity)", 'magenta')
    ui_blank('magenta')
    criteria = [
        ("L/240  (roof, no ceiling)", SERVICEABILITY.ROOF_NO_CEILING),
        ("L/360  (general / floors)", SERVICEABILITY.GENERAL_FLOOR),
        ("L/480  (brittle finishes)", SERVICEABILITY.BRITTLE_FINISHES),
    ]
    for label, denom in criteria:
        allow = beam_length / denom
        dc = (max_defl_abs / allow) if allow > 0 else 0.0
        ui_check_row(label, dc)
    ui_blank('magenta')
    ui_text("D/C = actual deflection \u00f7 code deflection limit. \u2264 1.00 passes.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ---- Additional deformation parameters ------------------------------
    print("\n")
    ui_open("ROTATION & CURVATURE", 'blue')
    ui_blank('blue')
    ui_field("Maximum slope  \u03b8max", f"{max_slope:.6f} rad  ({np.degrees(max_slope):.3f}\u00b0)", 'blue', 'blue')
    ui_field("Location of \u03b8max", f"x = {max_slope_pos / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_field("Maximum curvature  \u03ba", f"{max_curv:.4e} 1/{units['length']}", 'blue', 'blue')
    ui_field("Location of \u03bamax", f"x = {max_curv_pos / len_div:.3f} {units['length']}", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ---- Engineering interpretation -------------------------------------
    if span_ratio < 1/SERVICEABILITY.VERY_STIFF_TIER:
        verdict = "Very stiff \u2014 suitable for precision / vibration-sensitive use."
    elif span_ratio < 1/SERVICEABILITY.GENERAL_FLOOR:
        verdict = "Stiff \u2014 satisfies general building serviceability (L/360)."
    elif span_ratio < 1/SERVICEABILITY.ROOF_NO_CEILING:
        verdict = "Moderate \u2014 acceptable for roofs / non-brittle elements only."
    else:
        verdict = "Flexible \u2014 likely exceeds code limits; stiffening advised."

    print("\n")
    ui_open("ENGINEERING INTERPRETATION", 'yellow')
    ui_blank('yellow')
    ui_field("Serviceability verdict", verdict, 'yellow', 'yellow', width=22)
    if beam_type == "Cantilever" and span_ratio > 1/SERVICEABILITY.CANTILEVER_LIMIT:
        ui_bullet("Cantilever exceeds L/180 \u2014 increase section depth / inertia.", 'yellow', 'yellow')
    elif beam_type == "Simple" and span_ratio > 1/SERVICEABILITY.GENERAL_FLOOR:
        ui_bullet("Span exceeds L/360 \u2014 increase I or add intermediate support.", 'yellow', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the Solution menu...")
