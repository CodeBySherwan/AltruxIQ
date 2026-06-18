"""
pyvista_plotting.py
===================
Commercial-grade 3D FEA visualisations for AltruxIQ.

Features:
  - Triangulated and subdivided meshes for high-fidelity contour interpolation.
  - Discrete color banding (16 levels) with wireframe overlays.
  - Standardized top-left annotation blocks and left-aligned scalar bars.
  - Pure white background with matte model shading.
"""

import os
import sys
import datetime
import numpy as np

# ---------------------------------------------------------------------------
# PATH INJECTION
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir     = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ui.Menus import get_divisor

try:
    import pyvista as pv
except ImportError:
    raise ImportError("PyVista is not installed. Run: pip install pyvista")

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------------------------
_FEA_CMAP       = "turbo"             # 'turbo' or 'jet' (classic ANSYS)
_N_COLORS       = 15                  # 15 bands usually aligns text perfectly
_BG_COLOR       = "white"             
_EDGE_COLOR     = "black"             # Pure black for aggressive FEA wireframes
_BEAM_COLOR     = "#A0A0A0"           # Darker grey for the undeformed/schematic geometry
_SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "screenshots")

# ===========================================================================
# INTERNAL HELPERS
# ===========================================================================

def _ensure_screenshot_dir() -> str:
    path = os.path.normpath(_SCREENSHOT_DIR)
    os.makedirs(path, exist_ok=True)
    return path

def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _make_screenshot_path(name: str) -> str:
    return os.path.join(_ensure_screenshot_dir(), f"{name}_{_timestamp()}.png")

def _downsample_for_visuals(X_Field: np.ndarray, scalar_field: np.ndarray, target_fraction: float = 0.5):
    """
    Reduces the density of the mesh for visualization purposes only,
    giving that chunky, discrete commercial FEA appearance.
    """
    n_original = len(X_Field)
    if n_original < 10: 
        return X_Field, scalar_field # Leave it alone if it's already a tiny mesh
    
    # Calculate the step size (e.g., target_fraction 0.5 = step of 2)
    step = max(2, int(1.0 / target_fraction))
    
    # Slice the arrays to grab every Nth node
    X_vis = X_Field[::step]
    scalar_vis = scalar_field[::step]
    
    # Strictly ensure the very last node is included so the beam doesn't shrink
    if X_vis[-1] != X_Field[-1]:
        X_vis = np.append(X_vis, X_Field[-1])
        # If it's a 2D array (like stress tensors), handle it safely
        if scalar_field.ndim > 1:
            scalar_vis = np.vstack([scalar_vis, scalar_field[-1]])
        else:
            scalar_vis = np.append(scalar_vis, scalar_field[-1])
            
    return X_vis, scalar_vis
# ---------------------------------------------------------------------------
# Cross-section polygon builders
# ---------------------------------------------------------------------------

def _rect_polygon(h: float, w: float):
    hh, hw = h / 2.0, w / 2.0
    return np.array([[-hh, -hw], [-hh, hw], [hh, hw], [hh, -hw]])

def _hollow_rect_polygon(H: float, W: float, t: float):
    return _rect_polygon(H, W)

def _circle_polygon(r: float, n: int = 24):
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([r * np.sin(theta), r * np.cos(theta)])

def _ibeam_polygon(H: float, bf: float, tf: float, tw: float):
    hh, hw = H / 2.0, bf / 2.0
    return np.array([
        [ hh, -hw], [ hh, hw], [ hh - tf, hw], [ hh - tf, tw / 2],
        [-(hh - tf), tw / 2], [-(hh - tf), hw], [-hh, hw],
        [-hh, -hw], [-(hh - tf), -hw], [-(hh - tf), -tw / 2],
        [ hh - tf, -tw / 2], [ hh - tf, -hw],
    ])

def _tbeam_polygon(H: float, bf: float, tf: float, tw: float):
    hh, hw = H / 2.0, bf / 2.0
    return np.array([
        [ hh, -hw], [ hh, hw], [ hh - tf, hw], [ hh - tf, tw / 2],
        [-hh, tw / 2], [-hh, -tw / 2], [ hh - tf, -tw / 2], [ hh - tf, -hw],
    ])

def _build_cross_section_polygon(shape: str, section_dims: dict, c: float, b: float):
    sd = section_dims or {}
    H  = sd.get("H", sd.get("h", 2 * c if c > 0 else 0.2))
    W  = sd.get("W", sd.get("w", b if b > 0 else 0.1))
    bf = sd.get("bf", sd.get("B_f", W))
    tf = sd.get("tf", sd.get("T_f", H * 0.15))
    tw = sd.get("tw", sd.get("T_w", W * 0.20))
    R  = sd.get("R", sd.get("r", H / 2))
    t  = sd.get("t", H * 0.1)

    s = (shape or "").lower()
    if "i-beam" in s or "i beam" in s or s == "i":
        return _ibeam_polygon(H, bf, max(tf, H * 0.10), max(tw, W * 0.10))
    elif "t-beam" in s or "t beam" in s or s == "t":
        return _tbeam_polygon(H, bf, max(tf, H * 0.12), max(tw, W * 0.15))
    elif "circle" in s:
        return _circle_polygon(R)
    else:
        return _rect_polygon(H, W)


def _apply_visual_scaling(plotter: pv.Plotter, beam_length: float, section_dim_max: float):
    """Applies aggressive geometric scaling to thicken the cross-section."""
    if section_dim_max <= 0: return

    aspect_ratio = beam_length / section_dim_max
    
    # Increased scaling thresholds for a thicker beam
    if aspect_ratio > 10.0:
        scale_factor = min(aspect_ratio / 5.0, 8.0) # Doubled the thickness cap
        plotter.set_scale(xscale=1.0, yscale=scale_factor, zscale=scale_factor)

def _frame_camera(plotter: pv.Plotter, mesh: pv.PolyData):
    """Forces an ANSYS-style isometric view with Y strictly UP."""
    
    # 1. Find the exact mathematical center of your beam
    bounds = mesh.bounds
    cx = (bounds[0] + bounds[1]) / 2.0
    cy = (bounds[2] + bounds[3]) / 2.0
    cz = (bounds[4] + bounds[5]) / 2.0
    
    # 2. Use the beam's length to calculate how far back the camera should sit
    length = bounds[1] - bounds[0]
    if length == 0: 
        length = 1.0 # Fallback safety
        
    # 3. Explicitly define the camera: (Position, Focal Point, View Up)
    # - Position: Positive X, Y, and Z stations the camera in the correct quadrant
    # - Focal Point: Looking directly at the center of the beam
    # - View Up: (0.0, 1.0, 0.0) absolutely forces the Y-axis to be vertical
    plotter.camera_position = [
        (cx + length * 0.6, cy + length * 0.5, cz + length * 0.8), 
        (cx, cy, cz),                                  
        (0.0, 1.0, 0.0)                                
    ]
    
    plotter.camera.zoom(0.8)
    
# ---------------------------------------------------------------------------
# Core Meshing Engine
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Core Meshing Engine (Phase 1 Update)
# ---------------------------------------------------------------------------

def _build_beam_mesh(
    X_Field: np.ndarray, scalar_field: np.ndarray, shape: str,
    section_dims: dict, c: float, b: float, scalar_name: str
) -> pv.PolyData:
    """
    Builds a clean, quad-based 3D mesh. 
    Strictly avoids triangulation to maintain a commercial-grade wireframe.
    """
    polygon = _build_cross_section_polygon(shape, section_dims, c, b)
    n_pts = len(polygon)
    n_x = len(X_Field)

    # 1. Initialize 3D points and scalar arrays
    pts = np.zeros((n_x * n_pts, 3))
    scalar_vals = np.zeros(n_x * n_pts)

    # 2. Map the 2D cross-section along the X-axis nodes
    for i, x in enumerate(X_Field):
        start = i * n_pts
        end = start + n_pts
        pts[start:end, 0] = x                 # X coordinates
        pts[start:end, 1] = polygon[:, 0]     # Y coordinates
        pts[start:end, 2] = polygon[:, 1]     # Z coordinates
        
        # Apply the 1D solver value to the entire cross-section ring at this node
        scalar_vals[start:end] = scalar_field[i]

    # 3. Explicitly define Quad faces (No triangles!)
    faces = []
    
    # Generate the side walls (Longitudinal elements)
    for i in range(n_x - 1):
        base_current = i * n_pts
        base_next = (i + 1) * n_pts
        
        for j in range(n_pts):
            j_next = (j + 1) % n_pts
            
            # Format: [Number of points in face, pt1, pt2, pt3, pt4]
            # The '4' tells PyVista this is a strict Quad face.
            faces.extend([
                4, 
                base_current + j,        # Bottom-left
                base_next + j,           # Bottom-right
                base_next + j_next,      # Top-right
                base_current + j_next    # Top-left
            ])

    # 4. Generate clean N-gon end caps (avoids center-point triangle fans)
    # Start cap
    start_cap = [n_pts] + [j for j in range(n_pts)]
    faces.extend(start_cap)
    
    # End cap
    end_cap = [n_pts] + [(n_x - 1) * n_pts + j for j in range(n_pts)]
    faces.extend(end_cap)

    # 5. Assemble the mesh
    mesh = pv.PolyData(pts, np.array(faces, dtype=int))
    mesh.point_data[scalar_name] = scalar_vals
    
    # NOTE: We specifically DO NOT call .triangulate() or .subdivide() here.
    # The mesh is now purely structural.

    return mesh
# ---------------------------------------------------------------------------
# UI & Plotter Factory
# ---------------------------------------------------------------------------

def _make_plotter() -> pv.Plotter:
    """Setup a modern, clean window with a pure white background."""
    pl = pv.Plotter(window_size=(1600, 900))
    
    # Correct method to apply high-quality anti-aliasing for clean wireframes
    try:
        pl.enable_anti_aliasing('ssaa')  # Super-Sample Anti-Aliasing
    except AttributeError:
        pass # Fails gracefully if you are on an older PyVista version
        
    pl.set_background(color=_BG_COLOR)
    pl.add_axes(line_width=2, color="black", labels_off=False)
    return pl

def _add_fea_annotations(plotter, title: str, subtitle: str, max_val: float, min_val: float, units: str):
    """Replicates the top-left block text seen in commercial software."""
    text_block = (
        f"AltruxIQ : Structural Analysis Result\n"
        f"Result: {title}\n"
        f"Subcase - Static Loads, Step 1\n"
        f"Min: {min_val:.3f}, Max: {max_val:.3f}, Units = {units}"
    )
    # Removed line_spacing argument to ensure compatibility across PyVista versions
    plotter.add_text(text_block, position="upper_left", font_size=10, 
                     color="black", font="arial")

def _add_colorbar_mesh(plotter, mesh, scalar_name, label):
    """Left-aligned, discrete colorband legend with flat, accurate lighting."""
    
    # NEW: Add a newline character to force physical spacing below the title
    padded_title = f"{label}\n "
    
    # Format the colorbar to mimic enterprise FEA legends
    sargs = dict(
        title=padded_title,      # <-- Use the padded title here
        title_font_size=14,
        label_font_size=12,
        shadow=False,
        n_labels=_N_COLORS + 1,  
        fmt="%.3f",              
        font_family="arial",
        color="black",
        position_x=0.03,         
        position_y=0.05,         
        height=0.80,             
        width=0.06,              
        vertical=True
    )
    
    plotter.add_mesh(
        mesh,
        scalars=scalar_name,
        cmap=_FEA_CMAP,
        n_colors=_N_COLORS,    
        show_edges=True,       
        edge_color=_EDGE_COLOR,
        line_width=1.5,        
        ambient=0.6,           
        diffuse=0.4,           
        specular=0.0,          
        scalar_bar_args=sargs,
    )

def _add_support_glyphs(plotter, reactions, l_div, f_div, m_div):
    """Cleaned up reaction arrows."""
    for r in reactions:
        x = r["pos"] / l_div
        Fy, Fx = r.get("Fy", 0.0) / f_div, r.get("Fx", 0.0) / f_div
        origin = np.array([[x, 0.0, 0.0]])

        if abs(Fy) > 1e-9:
            mag = abs(Fy)
            plotter.add_arrows(origin, np.array([[0.0, np.sign(Fy), 0.0]]), mag=mag*0.2, color="blue")
            plotter.add_point_labels(origin, [f"Fy={Fy:.2f}"], font_size=10, text_color="black", show_points=False)
        if abs(Fx) > 1e-9:
            plotter.add_arrows(origin, np.array([[np.sign(Fx), 0.0, 0.0]]), mag=abs(Fx)*0.2, color="red")

# ===========================================================================
# PUBLIC FUNCTIONS
# ===========================================================================

def PyVista_reactions_schematic(beam_length, Reactions, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "force": "N", "moment": "N·m"}
    l_div, f_div, m_div = get_divisor(units, "length"), get_divisor(units, "force"), get_divisor(units, "moment")

    mesh = _build_beam_mesh(np.linspace(0, beam_length/l_div, 100), np.zeros(100), 
                            shape, section_dims, c/l_div, b/l_div, "Reactions")

    pl = _make_plotter()
    _add_fea_annotations(pl, "Free Body Diagram", "Reaction Forces", 0, 0, units['force'])
    
    pl.add_mesh(mesh, color=_BEAM_COLOR, opacity=0.8, show_edges=True, edge_color=_EDGE_COLOR, line_width=0.5)
    _add_support_glyphs(pl, Reactions, l_div, f_div, m_div)
    
    pl.camera_position = "iso"
    pl.show(screenshot=_make_screenshot_path("reactions_schematic"))

# ---------------------------------------------------------------------------

def PyVista_shear_force(X_Field, Total_ShearForce, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "force": "N"}
    l_div, f_div = get_divisor(units, "length"), get_divisor(units, "force")
    X, SF = X_Field / l_div, Total_ShearForce / f_div

    mesh = _build_beam_mesh(X, SF, shape, section_dims, c/l_div, b/l_div, "ShearForce")
    
    pl = _make_plotter()
    _add_fea_annotations(pl, "Shear Force (Element-Nodal)", "", np.max(SF), np.min(SF), units['force'])
    _add_colorbar_mesh(pl, mesh, "ShearForce", f"Shear Force ({units['force']})")
    
    pl.camera_position = "iso"
    pl.show(screenshot=_make_screenshot_path("shear_force"))

# ---------------------------------------------------------------------------

def PyVista_bending_moment(X_Field, Total_BendingMoment, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "moment": "N·m"}
    l_div, m_div = get_divisor(units, "length"), get_divisor(units, "moment")
    X, BM = X_Field / l_div, Total_BendingMoment / m_div

    mesh = _build_beam_mesh(X, BM, shape, section_dims, c/l_div, b/l_div, "BendingMoment")
    
    pl = _make_plotter()
    _add_fea_annotations(pl, "Bending Moment (Element-Nodal)", "", np.max(BM), np.min(BM), units['moment'])
    _add_colorbar_mesh(pl, mesh, "BendingMoment", f"Bending Moment ({units['moment']})")
    
    pl.camera_position = "iso"
    pl.show(screenshot=_make_screenshot_path("bending_moment"))

# ---------------------------------------------------------------------------

def PyVista_shear_stress(X_Field, ShearStress, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "stress": "MPa"}
    l_div, s_div = get_divisor(units, "length"), get_divisor(units, "stress")
    ss = np.max(np.abs(ShearStress), axis=1) if ShearStress.ndim > 1 else np.abs(ShearStress)
    
    X = X_Field / l_div
    SS = ss / s_div
    draw_length = beam_length / l_div
    draw_c = c / l_div
    draw_b = b / l_div

    # --- NEW: Halve the elements for the visualizer ---
    X_vis, SS_vis = _downsample_for_visuals(X, SS, target_fraction=0.2)

    # Pass the downsampled arrays to the mesher``
    mesh = _build_beam_mesh(X_vis, SS_vis, shape, section_dims, draw_c, draw_b, "ShearStress")
    
    pl = _make_plotter()
    _add_fea_annotations(pl, "Shear Stress (Element-Nodal)", "", np.max(SS), np.min(SS), units['stress'])
    _add_colorbar_mesh(pl, mesh, "ShearStress", f"Shear Stress ({units['stress']})")
    
    # Apply new scaling and camera lock
    max_dim = max(draw_c * 2, draw_b)  
    _apply_visual_scaling(pl, draw_length, max_dim)
    _frame_camera(pl, mesh)
    
    # Remove any old 'pl.camera_position = "iso"' calls down here
    pl.show(screenshot=_make_screenshot_path("shear_stress"))

# ---------------------------------------------------------------------------

def PyVista_bending_stress(X_Field, BendingStress, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "stress": "MPa"}
    l_div, s_div = get_divisor(units, "length"), get_divisor(units, "stress")
    bs = np.max(np.abs(BendingStress), axis=1) if BendingStress.ndim > 1 else BendingStress
    X, BS = X_Field / l_div, bs / s_div

    mesh = _build_beam_mesh(X, BS, shape, section_dims, c/l_div, b/l_div, "BendingStress")
    
    pl = _make_plotter()
    _add_fea_annotations(pl, "Bending Stress (Element-Nodal)", "", np.max(BS), np.min(BS), units['stress'])
    _add_colorbar_mesh(pl, mesh, "BendingStress", f"Bending Stress ({units['stress']})")
    
    pl.camera_position = "iso"
    pl.show(screenshot=_make_screenshot_path("bending_stress"))

# ---------------------------------------------------------------------------

def PyVista_deflection(X_Field, Deflection, beam_length, shape, section_dims, c, b, units=None):
    units = units or {"length": "m", "length_small": "mm"}
    l_div, ls_div = get_divisor(units, "length"), get_divisor(units, "length_small")
    X, defl = X_Field / l_div, Deflection / ls_div

    max_defl = float(np.max(np.abs(defl)))
    visual_scale = min(((c / l_div) * 6.0) / max_defl, 50.0) if max_defl > 0 else 1.0
    defl_visual = defl * visual_scale

    polygon = _build_cross_section_polygon(shape, section_dims, c/l_div, b/l_div)
    n_pts, n = len(polygon), len(X)
    pts, disp_vals = np.zeros((n * n_pts, 3)), np.zeros(n * n_pts)

    for i in range(n):
        start = i * n_pts
        pts[start:start+n_pts, 0] = X[i]
        pts[start:start+n_pts, 1] = polygon[:, 0] + defl_visual[i]
        pts[start:start+n_pts, 2] = polygon[:, 1]
        disp_vals[start:start+n_pts] = abs(defl[i])

    faces = []
    for i in range(n - 1):
        for j in range(n_pts):
            faces += [4, i*n_pts + j, i*n_pts + (j+1)%n_pts, (i+1)*n_pts + (j+1)%n_pts, (i+1)*n_pts + j]

    for rs in [0, (n - 1) * n_pts]:
        c_idx = len(pts)
        pts = np.vstack([pts, pts[rs:rs+n_pts].mean(axis=0)])
        disp_vals = np.append(disp_vals, abs(defl[0 if rs == 0 else -1]))
        for j in range(n_pts): faces += [3, c_idx, rs + j, rs + (j+1)%n_pts]

    mesh = pv.PolyData(pts, np.array(faces, dtype=int))
    mesh.point_data["Deflection"] = disp_vals
    mesh = mesh.triangulate()

    pl = _make_plotter()
    _add_fea_annotations(pl, f"Displacement - Nodal Magnitude (Scale: x{visual_scale:.1f})", "", max_defl, 0.0, units['length_small'])
    _add_colorbar_mesh(pl, mesh, "Deflection", f"Deflection ({units['length_small']})")
    
    # Ghostly undeformed reference frame
    ref_mesh = _build_beam_mesh(X, np.zeros(len(X)), shape, section_dims, c/l_div, b/l_div, "Ref")
    pl.add_mesh(ref_mesh, color="white", opacity=0.1, show_edges=True, edge_color="#D3D3D3")
    
    pl.camera_position = "iso"
    pl.show(screenshot=_make_screenshot_path("deflection"))

# ---------------------------------------------------------------------------

def PyVista_combined(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, shape, section_dims, c, b, 
                     Deflection=None, ShearStress=None, BendingStress=None, Reactions=None, units=None):
    """Sequential viewer."""
    print("\n  ═══════════════════════════════════════════")
    print("   AltruxIQ : 3D FEA Viewer")
    print("  ═══════════════════════════════════════════\n")

    PyVista_shear_force(X_Field, Total_ShearForce, beam_length, shape, section_dims, c, b, units)
    PyVista_bending_moment(X_Field, Total_BendingMoment, beam_length, shape, section_dims, c, b, units)
    
    if Deflection is not None: PyVista_deflection(X_Field, Deflection, beam_length, shape, section_dims, c, b, units)
    if ShearStress is not None: PyVista_shear_stress(X_Field, ShearStress, beam_length, shape, section_dims, c, b, units)
    if BendingStress is not None: PyVista_bending_stress(X_Field, BendingStress, beam_length, shape, section_dims, c, b, units)
    if Reactions: PyVista_reactions_schematic(beam_length, Reactions, shape, section_dims, c, b, units)