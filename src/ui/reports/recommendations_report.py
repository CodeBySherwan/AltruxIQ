"""Engineering design-check & recommendations report renderer.

Extracted from ``ui.Menus`` during the P3 ``ui/reports/`` decomposition
(checkpoint-4). Pure relocation; signatures and behavior unchanged.
"""
from termcolor import colored

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
    ui_verdict_badge,
    ui_footer,
    clear_screen,
)


def display_engineering_recommendations(beam_type, shape, beam_length, selected_material,
                                      Ix, c, b, FOS=None, max_stress=None, max_defl=None,
                                      span_ratio=None, yield_strength=None, segments=None,
                                      units=METRIC_UNITS):
    """Commercial-grade structural design-check & recommendation report.

    Consolidates the strength and serviceability limit states into a single
    verification dossier: executive verdict, demand/capacity matrix, governing
    limit state, prioritised remediation with quantitative sizing targets,
    section optimisation, stability/secondary effects, and applicable codes.

    Units (SI): beam_length [m], Ix [m^4], c,b [m], max_stress/yield_strength [Pa],
    max_defl [m], span_ratio [-], FOS [-]. Display values are divided by the
    active ``units`` divisors so Imperial users see ft/in/ksi numbers.
    """
    clear_screen()

    # Divisors for display conversion (single source: common.units.get_divisor)
    len_div = get_divisor(units, 'length')
    inertia_div = get_divisor(units, 'inertia')
    sec_mod_div = get_divisor(units, 'sec_mod')

    # ------------------------------------------------------------------ #
    #  DERIVED ENGINEERING QUANTITIES
    # ------------------------------------------------------------------ #
    TARGET_FOS = SERVICEABILITY.TARGET_FACTOR_OF_SAFETY  # target strength reserve
    DEFL_LIMIT_DENOM = SERVICEABILITY.GENERAL_FLOOR      # governing criterion (L/360)

    section_modulus = (Ix / c) if c else 0.0
    depth = 2.0 * c if c else 0.0
    mat_name = selected_material.get('Material', 'Unknown') if selected_material else 'Unknown'
    yield_MPa = (yield_strength / 1e6) if yield_strength else None

    # --- Demand / capacity ratios (None where data unavailable) -------- #
    dc_strength = (max_stress / yield_strength) if (max_stress and yield_strength) else None
    allow_defl = (beam_length / DEFL_LIMIT_DENOM) if beam_length else None
    dc_defl = (abs(max_defl) / allow_defl) if (max_defl is not None and allow_defl) else None
    dc_fos = (TARGET_FOS / FOS) if FOS else None   # >1.0 => below target reserve
    inv_span = (1.0 / span_ratio) if span_ratio else None

    have_data = any(v is not None for v in (dc_strength, dc_defl, FOS))

    # --- Overall verdict ---------------------------------------------- #
    governing_name, governing_dc = None, 0.0
    for nm, dc in (("Strength (yield)", dc_strength),
                   ("Serviceability (L/360)", dc_defl),
                   ("Strength reserve (FoS)", dc_fos)):
        if dc is not None and dc > governing_dc:
            governing_name, governing_dc = nm, dc

    if not have_data:
        verdict = 'INCOMPLETE'
    elif (dc_strength is not None and dc_strength > 1.0) or \
         (dc_defl is not None and dc_defl > 1.0) or (FOS is not None and FOS < 1.0):
        verdict = 'FAIL'
    elif governing_dc > 0.90 or (FOS is not None and FOS < TARGET_FOS):
        verdict = 'REVIEW'
    else:
        verdict = 'PASS'

    ui_banner("ENGINEERING DESIGN-CHECK REPORT",
              "Limit-State Verification \u2022 Optimisation \u2022 Code Compliance",
              color='cyan')

    # ================================================================== #
    #  0. EXECUTIVE VERDICT
    # ================================================================== #
    label, vcol = ui_verdict_badge(verdict)
    print("\n")
    ui_open("EXECUTIVE VERDICT", vcol)
    ui_blank(vcol)
    print(colored("\u2502   ", vcol) + colored(f" {label} ", vcol, attrs=['bold', 'reverse']))
    ui_blank(vcol)
    if governing_name:
        ui_field("Governing limit state", governing_name, vcol, vcol, value_color='white')
        ui_field("Controlling utilisation", f"{governing_dc*100:.1f}%  (D/C = {governing_dc:.2f})",
                 vcol, vcol, value_color='white')
        reserve = (1.0 - governing_dc) * 100.0
        ui_field("Remaining reserve", f"{reserve:+.1f}%", vcol, vcol, value_color='white')
    else:
        ui_text("Run Stress (FoS) and Deflection checks for a full verdict.", 'white', vcol)
    ui_blank(vcol)
    ui_close(vcol)

    # ================================================================== #
    #  1. MODEL & SECTION SUMMARY
    # ================================================================== #
    print("\n")
    ui_open("MODEL & SECTION SUMMARY", 'blue')
    ui_blank('blue')
    ui_field("Structural system", f"{beam_type} Beam", 'blue', 'blue')
    if beam_type == "Stepped Bar" and segments:
        ui_field("Cross-section", "Varies along length", 'blue', 'blue')
        ui_field("Span length  L", f"{beam_length/len_div:.3f} {units['length']}", 'blue', 'blue')
        ui_field("Material", "Varies along length", 'blue', 'blue')
        ui_field("Moment of inertia  I", "Varies along length", 'blue', 'blue')
        ui_field("Section modulus  S", "Varies along length", 'blue', 'blue')
        ui_field("Section depth  (2c)", "Varies along length", 'blue', 'blue')
    else:
        ui_field("Cross-section", f"{shape}", 'blue', 'blue')
        ui_field("Span length  L", f"{beam_length/len_div:.3f} {units['length']}", 'blue', 'blue')
        ui_field("Material", f"{mat_name}" + (f"  (Fy = {yield_MPa:.0f} MPa)" if yield_MPa else ""), 'blue', 'blue')
        if Ix is not None:
            ui_field("Moment of inertia  I", f"{Ix/inertia_div:.4e} {units['inertia']}", 'blue', 'blue')
        if section_modulus:
            ui_field("Section modulus  S", f"{section_modulus/sec_mod_div:.4e} {units['sec_mod']}", 'blue', 'blue')
        if depth:
            ui_field("Section depth  (2c)", f"{depth/len_div:.4f} {units['length']}", 'blue', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ================================================================== #
    #  2. LIMIT-STATE VERIFICATION MATRIX
    # ================================================================== #
    print("\n")
    ui_open("LIMIT-STATE VERIFICATION MATRIX", 'magenta')
    ui_blank('magenta')
    if dc_strength is not None:
        ui_check_row("Strength  \u03c3/Fy", dc_strength)
    if dc_defl is not None:
        ui_check_row("Service  \u03b4/(L/360)", dc_defl)
    if dc_fos is not None:
        # show FoS adequacy: PASS when FOS>=target  (dc_fos<=1)
        ui_check_row("FoS  (1.5/FoS)", dc_fos,
                     status_text=("PASS \u2713" if FOS >= TARGET_FOS else
                                  ("MARGINAL \u26a0" if FOS >= 1.0 else "FAIL \u2717")))
    if dc_strength is None and dc_defl is None and dc_fos is None:
        ui_text("No quantitative results yet \u2014 complete the Solution checks.", 'white', 'magenta')
    ui_blank('magenta')
    ui_text("Bar fill = utilisation. Green \u2264 75%, Amber \u2264 95%, Red > 95%.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ================================================================== #
    #  3. DESIGN ASSESSMENT (strengths / concerns)
    # ================================================================== #
    strengths, concerns = [], []
    if FOS is not None:
        if FOS < 1.0:
            concerns.append(f"Factor of safety critically low (FoS = {FOS:.2f}) \u2014 yielding predicted")
        elif FOS < TARGET_FOS:
            concerns.append(f"Factor of safety {FOS:.2f} is below the {TARGET_FOS:.2f} target")
        else:
            strengths.append(f"Adequate strength reserve (FoS = {FOS:.2f})")
    if span_ratio is not None and inv_span:
        if span_ratio > 1/SERVICEABILITY.CANTILEVER_LIMIT:
            concerns.append(f"Excessive deflection (L/{inv_span:.0f}) \u2014 serviceability at risk")
        elif span_ratio > 1/SERVICEABILITY.GENERAL_FLOOR:
            concerns.append(f"Deflection L/{inv_span:.0f} exceeds the L/360 floor criterion")
        else:
            strengths.append(f"Deflection within limits (L/{inv_span:.0f})")
    if dc_strength is not None:
        if dc_strength > 0.90:
            concerns.append(f"Bending stress at {dc_strength*100:.0f}% of yield \u2014 little margin")
        elif dc_strength > 0.67:
            concerns.append(f"Moderately high bending stress ({dc_strength*100:.0f}% of yield)")
        else:
            strengths.append(f"Comfortable bending stress level ({dc_strength*100:.0f}% of yield)")
    # section morphology
    if shape in ("I-beam", "T-beam"):
        strengths.append("Efficient section for major-axis bending (high I per unit mass)")
    elif "Circle" in shape:
        strengths.append("Isotropic / good torsional resistance")
        if beam_type == "Cantilever":
            concerns.append("Circular sections are sub-optimal for cantilever bending")
    elif ("Rectangle" in shape or "Square" in shape):
        if "Hollow" in shape:
            strengths.append("Hollow box \u2014 good combined bending + torsion efficiency")
        else:
            concerns.append("Solid rectangular/square \u2014 inefficient material utilisation")
    if beam_type == "Cantilever" and beam_length > 10 and "Hollow" not in shape:
        concerns.append("Long cantilever \u2014 consider hollow section for weight control")

    print("\n")
    ui_open("DESIGN ASSESSMENT", 'green')
    ui_blank('green')
    if strengths:
        ui_head("Strengths", 'green', 'green')
        for s in strengths:
            ui_bullet(s, 'green', 'green', mark="\u2713")
        ui_blank('green')
    if concerns:
        ui_head("Concerns", 'yellow', 'green')
        for c_ in concerns:
            ui_bullet(c_, 'yellow', 'green', mark="\u26a0")
        ui_blank('green')
    if not strengths and not concerns:
        ui_text("Complete all analyses to populate the design assessment.", 'white', 'green')
        ui_blank('green')
    ui_close('green')

    # ================================================================== #
    #  4. PRIORITISED RECOMMENDED ACTIONS  (with quantitative targets)
    # ================================================================== #
    p1, p2, p3 = [], [], []   # P1 critical/strength, P2 serviceability, P3 optimisation

    # ---- P1: strength -------------------------------------------------
    if FOS is not None and FOS < TARGET_FOS and section_modulus:
        s_req = section_modulus * (TARGET_FOS / FOS)
        inc = (s_req / section_modulus - 1.0) * 100.0
        p1.append(f"Raise section modulus to S \u2265 {s_req/sec_mod_div:.3e} {units['sec_mod']} "
                  f"(+{inc:.0f}%) to reach FoS = {TARGET_FOS:.2f}")
        if shape in ("I-beam", "T-beam"):
            p1.append("Increase web height (most effective) or flange area")
        elif "Circle" in shape:
            p1.append("Increase diameter / wall thickness")
        elif "Hollow" in shape:
            p1.append("Increase overall depth or wall thickness")
        else:
            p1.append("Switch to an I-section or hollow box for higher S per mass")
        if yield_MPa:
            p1.append(f"Alternative: upgrade material (current Fy = {yield_MPa:.0f} MPa)")

    # ---- P2: serviceability ------------------------------------------
    if dc_defl is not None and dc_defl > 1.0 and Ix:
        i_req = Ix * dc_defl
        inc = (dc_defl - 1.0) * 100.0
        p2.append(f"Raise moment of inertia to I \u2265 {i_req/inertia_div:.3e} {units['inertia']} "
                  f"(+{inc:.0f}%) to satisfy L/360")
        if beam_type == "Simple":
            p2.append("Or add an intermediate support to roughly quarter the deflection")
        elif beam_type == "Cantilever":
            p2.append("Or shorten the cantilever / add a back-span prop")
    elif span_ratio is not None and span_ratio > 1/SERVICEABILITY.BRITTLE_FINISHES:
        p2.append("Deflection acceptable for general use; verify L/480 if brittle finishes apply")

    # ---- P3: optimisation --------------------------------------------
    if FOS is not None and FOS > 2.5:
        if "Hollow" not in shape:
            p3.append("Over-designed \u2014 convert to a hollow section (~30\u201340% mass saving)")
        else:
            p3.append("Over-designed \u2014 reduce wall thickness / depth while keeping FoS \u2265 1.5")
    if shape == "Rectangle" and "Hollow" not in shape:
        p3.append("Re-orient so depth > width to maximise I about the bending axis")
    if not p3:
        p3.append("Round selected dimensions up to the nearest standard mill size")

    print("\n")
    ui_open("PRIORITISED RECOMMENDED ACTIONS", 'yellow')
    ui_blank('yellow')
    ui_head("P1 \u2014 Strength (address first)", 'red', 'yellow')
    if p1:
        for a in p1:
            ui_bullet(a, 'white', 'yellow', mark="\u2776")
    else:
        ui_bullet("No strength deficiency detected.", 'green', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_head("P2 \u2014 Serviceability", 'yellow', 'yellow')
    if p2:
        for a in p2:
            ui_bullet(a, 'white', 'yellow', mark="\u2777")
    else:
        ui_bullet("No serviceability deficiency detected.", 'green', 'yellow', mark="\u2713")
    ui_blank('yellow')
    ui_head("P3 \u2014 Optimisation & detailing", 'cyan', 'yellow')
    for a in p3:
        ui_bullet(a, 'white', 'yellow', mark="\u2778")
    ui_blank('yellow')
    ui_close('yellow')

    # ================================================================== #
    #  5. STABILITY & SECONDARY EFFECTS
    # ================================================================== #
    print("\n")
    ui_open("STABILITY & SECONDARY EFFECTS", 'blue')
    ui_blank('blue')
    if shape in ("I-beam", "T-beam"):
        ui_bullet("Check lateral-torsional buckling (LTB) \u2014 provide compression-flange bracing.", 'white', 'blue')
        ui_bullet("Verify flange/web local buckling (section compactness, b/t & h/tw).", 'white', 'blue')
    if "Hollow" in shape:
        ui_bullet("HSS/box: check wall slenderness for local buckling under bending.", 'white', 'blue')
    if beam_type == "Cantilever":
        ui_bullet("Cantilever tip is unbraced \u2014 LTB and tip rotation often govern.", 'white', 'blue')
    ui_bullet("Confirm web shear capacity and bearing/crippling at supports & point loads.", 'white', 'blue')
    ui_bullet("Where applicable include P-\u0394 / second-order effects for slender members.", 'white', 'blue')
    ui_blank('blue')
    ui_close('blue')

    # ================================================================== #
    #  6. FATIGUE, DYNAMICS & DURABILITY
    # ================================================================== #
    print("\n")
    ui_open("FATIGUE, DYNAMICS & DURABILITY", 'magenta')
    ui_blank('magenta')
    if beam_type == "Simple" and beam_length > 3:
        ui_bullet("Span > 3 m \u2014 check natural frequency / walking vibration (target f\u2081 > 3\u20134 Hz).", 'white', 'magenta')
    if beam_type == "Cantilever":
        ui_bullet("If cyclically loaded, perform fatigue assessment of the fixed-end detail.", 'white', 'magenta')
    ui_bullet("Apply corrosion allowance / protective coating per exposure category.", 'white', 'magenta')
    ui_bullet("Account for temperature effects & thermal movement at connections.", 'white', 'magenta')
    ui_blank('magenta')
    ui_close('magenta')

    # ================================================================== #
    #  7. APPLICABLE CODES & STANDARDS
    # ================================================================== #
    print("\n")
    ui_open("APPLICABLE CODES & STANDARDS", 'cyan')
    ui_blank('cyan')
    ui_head("Member design", 'cyan', 'cyan')
    if "Steel" in mat_name:
        ui_bullet("AISC 360 \u2014 Specification for Structural Steel Buildings (US)", 'cyan', 'cyan')
        ui_bullet("EN 1993 (Eurocode 3) \u2014 Design of Steel Structures (EU)", 'cyan', 'cyan')
    elif "Alumin" in mat_name or "Aluminum" in mat_name:
        ui_bullet("Aluminum Design Manual / ADM (US)", 'cyan', 'cyan')
        ui_bullet("EN 1999 (Eurocode 9) \u2014 Aluminium Structures (EU)", 'cyan', 'cyan')
    elif "Concrete" in mat_name:
        ui_bullet("ACI 318 \u2014 Building Code Requirements for Structural Concrete (US)", 'cyan', 'cyan')
        ui_bullet("EN 1992 (Eurocode 2) \u2014 Concrete Structures (EU)", 'cyan', 'cyan')
    elif "Timber" in mat_name or "Wood" in mat_name:
        ui_bullet("NDS \u2014 National Design Specification for Wood Construction (US)", 'cyan', 'cyan')
        ui_bullet("EN 1995 (Eurocode 5) \u2014 Timber Structures (EU)", 'cyan', 'cyan')
    else:
        ui_bullet("Select the governing material standard for your jurisdiction.", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_head("Loads & combinations", 'cyan', 'cyan')
    ui_bullet("ASCE/SEI 7 (US)  or  EN 1990/1991 (Eurocode basis & actions).", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_head("Serviceability deflection limits", 'cyan', 'cyan')
    ui_bullet("L/240 \u2014 roof members, no ceiling", 'cyan', 'cyan')
    ui_bullet("L/360 \u2014 floors / general structural members", 'cyan', 'cyan')
    ui_bullet("L/480 \u2014 members supporting brittle finishes", 'cyan', 'cyan')
    ui_blank('cyan')
    ui_close('cyan')

    # ================================================================== #
    #  Disclaimer
    # ================================================================== #
    print("\n")
    ui_open("NOTICE", 'yellow')
    ui_blank('yellow')
    ui_text("Preliminary 1D linear-elastic results for guidance only. Final design", 'white', 'yellow')
    ui_text("must be verified by a licensed engineer against the governing code and", 'white', 'yellow')
    ui_text("project-specific load combinations, connections and detailing.", 'white', 'yellow')
    ui_blank('yellow')
    ui_close('yellow')

    ui_footer("Press Enter to return to the main menu...")
