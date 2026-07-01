"""
pyvista_plotting.py
===================
Commercial-grade 3D FEA visualisations for AltruxIQ.
"""

import os
import sys
import datetime
import logging
import numpy as np

_log = logging.getLogger("altruxiq.pyvista")

try:
    import vtk
except ImportError:
    vtk = None

try:
    import pyvista as pv
except ImportError:
    raise ImportError("PyVista is not installed. Run: pip install pyvista")

from ui.Menus import  print_success, print_error

from common.units import default_units,get_divisor  # canonical default units dict
from common.paths import SCREENSHOTS_DIR, EXPORTS_DIR
from ui.inputs import ask_choice, ask_yes_no
from termcolor import colored

# ---------------------------------------------------------------------------
# VISUAL CONFIGURATION — centralised magic numbers
# ---------------------------------------------------------------------------
_FEA_CMAP          = "RdBu_r"   # Diverging blue-white-red, reversed (red=max)
_N_COLORS          = 10         # Discrete colour bands (ANSYS style)
_BG_COLOR          = "white"
_EDGE_COLOR        = "#444444"   # Darker edge for better definition
_BEAM_COLOR        = "#9E9E9E"   # Neutral grey for undeformed ghost
_GHOST_OPACITY     = 0.35        # Undeformed reference mesh opacity
_GHOST_STYLE       = "wireframe" # Undeformed reference display style
_CIRCLE_SEGMENTS   = 48          # Polygon vertices for circular sections

# Mesh material / lighting response (lower ambient => lighting variation visible)
_AMBIENT           = 0.25
_DIFFUSE           = 0.65
_SPECULAR          = 0.15
_SPECULAR_POWER    = 25

# Interaction / animation defaults
_SLIDER_EVENT_TYPE = "always"    # Real-time slider updates (DEF-09 fix)
_DEFAULT_FPS       = 24          # Animation playback speed
_DEFAULT_N_FRAMES  = 60          # Animation frame count

# Centralized via common.paths (single source of truth for on-disk locations).
_SCREENSHOT_DIR    = str(SCREENSHOTS_DIR)
_EXPORT_DIR        = str(EXPORTS_DIR)

COLOR_MAX        = "red"
COLOR_MIN        = "blue"
COLOR_PROBE      = "yellow"
COLOR_PIN        = "lime"

# ---------------------------------------------------------------------------
# OVERLAY (HUD) STYLE  —  neat framed "cards" with a consistent palette
# ---------------------------------------------------------------------------
_INK            = "#1B2631"               # primary slate text
_INK_SOFT       = "#5D6D7E"               # secondary / muted text
_HEADER_INK     = "#10202B"               # centred title banner
_PANEL_BG       = (0.985, 0.988, 0.992)   # near-white card fill
_PANEL_FRAME    = (0.74, 0.78, 0.82)      # subtle cool-grey border
_PROBE_BG       = (1.00, 0.98, 0.86)      # warm parchment for the probe read-out
_PROBE_FRAME    = (0.62, 0.58, 0.32)
_PANEL_OPACITY  = 0.92
_HRULE          = "\u2500" * 22           # divider rule for HUD cards

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

def _ensure_export_dir() -> str:
    path = os.path.normpath(_EXPORT_DIR)
    os.makedirs(path, exist_ok=True)
    return path

def _downsample_for_visuals(X_Field: np.ndarray, scalar_field: np.ndarray, target_fraction: float = 0.5):
    n_original = len(X_Field)
    if n_original < 10: return X_Field, scalar_field
    step = max(2, int(1.0 / target_fraction))
    X_vis = X_Field[::step]
    scalar_vis = scalar_field[::step]
    if X_vis[-1] != X_Field[-1]:
        X_vis = np.append(X_vis, X_Field[-1])
        if scalar_field.ndim > 1:
            scalar_vis = np.vstack([scalar_vis, scalar_field[-1]])
        else:
            scalar_vis = np.append(scalar_vis, scalar_field[-1])
    return X_vis, scalar_vis

def _rect_polygon(h: float, w: float):
    hh, hw = h / 2.0, w / 2.0
    return np.array([[-hh, -hw], [-hh, hw], [hh, hw], [hh, -hw]])

def _circle_polygon(r: float, n: int = _CIRCLE_SEGMENTS):
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

def _build_cross_section_loops(shape: str, section_dims: dict, c: float, b: float):
    """Return {"outer": Nx2 loop, "inner": Mx2 loop or None}.

    For HOLLOW profiles the inner loop has the SAME number of vertices as the
    outer loop, in matching index order, so the bore wall and the annular end
    caps can be built as simple quad strips between corresponding vertices.
    """
    sd = section_dims or {}
    H  = sd.get("H", sd.get("h", 2 * c if c > 0 else 0.2))
    W  = sd.get("W", sd.get("w", b if b > 0 else 0.1))
    bf = sd.get("bf", sd.get("B_f", W))
    tf = sd.get("tf", sd.get("T_f", H * 0.15))
    tw = sd.get("tw", sd.get("T_w", W * 0.20))
    R  = sd.get("R", sd.get("r", H / 2))
    t  = sd.get("t", sd.get("thickness", sd.get("wall", None)))   # wall thickness

    s = (shape or "").lower()
    is_hollow = "hollow" in s or "tube" in s

    if "i-beam" in s or "i beam" in s or s == "i":
        return {"outer": _ibeam_polygon(H, bf, max(tf, H * 0.10), max(tw, W * 0.10)), "inner": None}
    if "t-beam" in s or "t beam" in s or s == "t":
        return {"outer": _tbeam_polygon(H, bf, max(tf, H * 0.12), max(tw, W * 0.15)), "inner": None}

    if "circle" in s:
        outer = _circle_polygon(R)
        if is_hollow:
            ri = sd.get("ri", sd.get("Ri", sd.get("r_inner", None)))
            if ri is None:
                wall = t if (t and t > 0) else R * 0.15
                ri = max(R - wall, R * 0.05)
            return {"outer": outer, "inner": _circle_polygon(ri)}   # same n & angles -> aligned
        return {"outer": outer, "inner": None}

    # Square / Rectangle (solid or hollow). "Square" forces equal sides.
    if "square" in s:
        side = W if W > 0 else H
        H = W = side
    outer = _rect_polygon(H, W)
    if is_hollow:
        wall = t if (t and t > 0) else min(H, W) * 0.12
        Hi = sd.get("Hi", sd.get("hi", max(H - 2 * wall, H * 0.05)))
        Wi = sd.get("Wi", sd.get("wi", max(W - 2 * wall, W * 0.05)))
        return {"outer": outer, "inner": _rect_polygon(Hi, Wi)}     # 4 corners, aligned
    return {"outer": outer, "inner": None}

def _build_cross_section_polygon(shape: str, section_dims: dict, c: float, b: float):
    """Backward-compatible helper: returns only the outer perimeter loop."""
    return _build_cross_section_loops(shape, section_dims, c, b)["outer"]

def _apply_visual_scaling(plotter: pv.Plotter, beam_length: float, section_dim_max: float):
    if section_dim_max <= 0:
        plotter._altruxiq_scale = (1.0, 1.0, 1.0)
        return
    aspect_ratio = beam_length / section_dim_max
    if aspect_ratio > 10.0:
        scale_factor = min(aspect_ratio / 5.0, 8.0)
        plotter.set_scale(xscale=1.0, yscale=scale_factor, zscale=scale_factor)
        plotter._altruxiq_scale = (1.0, scale_factor, scale_factor)
    else:
        plotter._altruxiq_scale = (1.0, 1.0, 1.0)

def _frame_camera(plotter: pv.Plotter, mesh: pv.PolyData):
    plotter.view_xy()      # Sets Y up, X right, Z towards viewer
    plotter.reset_camera()
    plotter.camera.zoom(1.2) # Zoom in just a little bit (1.0 is default, >1 zooms in)

def _ring_block_vectorised(poly, X_Field, scalar_field, y_offsets):
    """Vectorised construction of one extruded ring of points (DEF-06).

    Replaces the per-station Python loop with pure NumPy ``repeat``/``tile``
    operations (~40-100x faster for large ``n_x``).  Returns
    ``(points (n_x*m, 3), scalars (n_x*m,), m)``.
    """
    m = len(poly)
    n_x = len(X_Field)
    x = np.repeat(X_Field, m)                           # x0,x0,..,x1,x1,..
    y = np.tile(poly[:, 0], n_x) + np.repeat(y_offsets, m)
    z = np.tile(poly[:, 1], n_x)
    pts = np.column_stack([x, y, z])
    sv = np.repeat(scalar_field, m)
    return pts, sv, m

def _wall_quads(n_x: int, m: int, base_offset: int = 0, reverse: bool = False) -> np.ndarray:
    """Vectorised lateral-wall quad strip in flat VTK face format (ENH-06).

    Connects adjacent cross-section rings with ``(n_x-1) * m`` quads.
    ``reverse=True`` flips winding so the inner bore normals face the hole.
    """
    if n_x < 2:
        return np.empty(0, dtype=np.int64)
    i = np.arange(n_x - 1)
    j = np.arange(m)
    jn = (j + 1) % m
    bc   = (i[:, None] * m + j[None, :]) + base_offset          # current ring, vertex j
    bn   = ((i + 1)[:, None] * m + j[None, :]) + base_offset    # next ring,    vertex j
    bc_n = (i[:, None] * m + jn[None, :]) + base_offset         # current ring, vertex j+1
    bn_n = ((i + 1)[:, None] * m + jn[None, :]) + base_offset   # next ring,    vertex j+1
    head = np.full_like(bc, 4)
    if not reverse:
        quads = np.stack([head, bc, bn, bn_n, bc_n], axis=-1)
    else:
        quads = np.stack([head, bc_n, bn_n, bn, bc], axis=-1)
    return quads.reshape(-1)

def _build_beam_mesh(
    X_Field: np.ndarray, scalar_field: np.ndarray, shape: str,
    section_dims: dict, c: float, b: float, scalar_name: str,
    y_offsets: np.ndarray = None,
) -> pv.PolyData:
    """Extrude the cross-section along X into a closed surface.

    Handles solid AND hollow profiles:
      * solid  -> outer wall + single-polygon end caps (concave-safe, so
                  I-beam / T-beam tessellate correctly instead of the old
                  centroid-fan that overlapped itself on non-convex outlines).
      * hollow -> outer wall + inner bore wall + annular ring end caps, so the
                  hole is genuinely open instead of looking solid.

    Point generation and the lateral walls are fully vectorised (DEF-06 /
    ENH-06); the end-cap rings are short (<= _CIRCLE_SEGMENTS iterations) and
    left as explicit loops for clarity.

    y_offsets : optional per-station lateral (Y) offset for drawing the
                deflected shape. Length must match X_Field.
    """
    loops = _build_cross_section_loops(shape, section_dims, c, b)
    outer, inner = loops["outer"], loops["inner"]
    n_x = len(X_Field)
    if y_offsets is None:
        y_offsets = np.zeros(n_x)

    o_pts, o_sc, n_o = _ring_block_vectorised(outer, X_Field, scalar_field, y_offsets)
    all_pts, all_sc, face_blocks = [o_pts], [o_sc], []

    # outer lateral wall (vectorised)
    face_blocks.append(_wall_quads(n_x, n_o, base_offset=0, reverse=False))

    if inner is not None:
        i_pts, i_sc, n_i = _ring_block_vectorised(inner, X_Field, scalar_field, y_offsets)
        off = n_x * n_o                       # index offset for inner points
        all_pts.append(i_pts); all_sc.append(i_sc)

        # inner bore wall (reverse winding -> normals face the bore)
        face_blocks.append(_wall_quads(n_x, n_i, base_offset=off, reverse=True))

        # annular end caps (ring of quads between outer and inner loops)
        caps = []
        for j in range(n_o):                  # start cap
            jn = (j + 1) % n_o
            caps.extend([4, j, jn, off + jn, off + j])
        bo, bi = (n_x - 1) * n_o, off + (n_x - 1) * n_i
        for j in range(n_o):                  # end cap
            jn = (j + 1) % n_o
            caps.extend([4, bo + jn, bo + j, bi + j, bi + jn])
        face_blocks.append(np.asarray(caps, dtype=np.int64))
    else:
        # solid end caps as single polygon faces (VTK ear-clips concave shapes)
        caps = [n_o] + list(range(n_o - 1, -1, -1))                 # start cap (-X)
        bo = (n_x - 1) * n_o
        caps += [n_o] + list(range(bo, bo + n_o))                   # end cap   (+X)
        face_blocks.append(np.asarray(caps, dtype=np.int64))

    pts = np.vstack(all_pts)
    scalar_vals = np.concatenate(all_sc)
    faces = np.concatenate(face_blocks).astype(np.int64)
    mesh = pv.PolyData(pts, faces)
    mesh.point_data[scalar_name] = scalar_vals
    mesh = mesh.triangulate()                 # tessellate polygon caps
    return mesh

def _make_plotter() -> pv.Plotter:
    pl = pv.Plotter(window_size=(1600, 900))
    try: pl.enable_anti_aliasing('ssaa')
    except AttributeError: pass
    pl.set_background(color=_BG_COLOR)
    pl.add_axes(line_width=2, color="black", labels_off=False)
    try: pl.add_light(vtk.vtkLight())
    except Exception: pass
    pl._altruxiq_scale = (1.0, 1.0, 1.0)
    return pl

def _add_fea_annotations(plotter, title: str, subtitle: str, max_val: float, min_val: float, units: str):
    text_block = (
        f"  AltruxIQ   ·   Structural Analysis  \n"
        f"  {_HRULE}  \n"
        f"  Result    {title}  \n"
        f"  Subcase   Static Loads, Step 1  \n"
        f"  Range     {min_val:.3f}  to  {max_val:.3f} {units}  "
    )
    actor = plotter.add_text(text_block, position=(0.012, 0.985), font_size=11,
                             color=_INK, font="arial", viewport=True)
    _PlotterBase._style_overlay(actor, _PANEL_BG, _PANEL_OPACITY, _PANEL_FRAME, 1,
                                justification="left", vjustification="top")

def _add_support_glyphs(plotter, reactions, l_div, f_div, m_div, visual_beam_length):
    max_f = 1e-9
    for r in reactions:
        max_f = max(max_f, abs(r.get("Fy", 0.0) / f_div), abs(r.get("Fx", 0.0) / f_div))
    base_length = visual_beam_length if visual_beam_length > 0 else 1.0
    max_arrow_size = base_length * 0.15
    scale_factor = max_arrow_size / max_f
    for r in reactions:
        x = r["pos"] / l_div
        Fy, Fx = r.get("Fy", 0.0) / f_div, r.get("Fx", 0.0) / f_div
        if abs(Fy) > 1e-9:
            visual_mag = abs(Fy) * scale_factor
            direction_sign = np.sign(Fy)
            start_y = -direction_sign * visual_mag
            origin = np.array([[x, start_y, 0.0]])
            direction = np.array([[0.0, direction_sign, 0.0]])
            plotter.add_arrows(origin, direction, mag=visual_mag, color="red")
            label_pos = np.array([[x, start_y - (direction_sign * base_length * 0.03), 0.0]])
            plotter.add_point_labels(label_pos, [f"Fy = {Fy:.2f}"], font_size=10, text_color="black", show_points=False)
        if abs(Fx) > 1e-9:
            visual_mag = abs(Fx) * scale_factor
            direction_sign = np.sign(Fx)
            start_x = x - (direction_sign * visual_mag)
            origin = np.array([[start_x, 0.0, 0.0]])
            direction = np.array([[direction_sign, 0.0, 0.0]])
            plotter.add_arrows(origin, direction, mag=visual_mag, color="blue")
            label_pos = np.array([[start_x - (direction_sign * base_length * 0.03), 0.0, 0.0]])
            plotter.add_point_labels(label_pos, [f"Fx = {Fx:.2f}"], font_size=10, text_color="black", show_points=False)

# ===========================================================================
# _PlotterBase  (shared infrastructure for all AltruxIQ plotters)
# ===========================================================================

class _PlotterBase:
    """Shared infrastructure mixin for ProbingPlotter and AnimationPlotter.

    Centralises three-point lighting, framed-text overlays and adaptive
    scalar-bar formatting so the two plotters stay visually consistent.
    """

    def _setup_lighting(self):
        """Three-point studio lighting for a professional 3D appearance (DEF-04)."""
        if vtk is None or self.plotter is None:
            return
        try:
            self.plotter.remove_all_lights()
            # Key light: strong, front-left, slightly warm
            key = vtk.vtkLight()
            key.SetPosition(10, 10, 10); key.SetFocalPoint(0, 0, 0)
            key.SetIntensity(1.0); key.SetColor(1.0, 0.98, 0.95)
            self.plotter.add_light(key)
            # Fill light: soft, front-right, slightly cool
            fill = vtk.vtkLight()
            fill.SetPosition(-8, 5, 8); fill.SetFocalPoint(0, 0, 0)
            fill.SetIntensity(0.35); fill.SetColor(0.9, 0.92, 1.0)
            self.plotter.add_light(fill)
            # Rim/back light: separates beam from background
            rim = vtk.vtkLight()
            rim.SetPosition(0, -15, -5); rim.SetFocalPoint(0, 0, 0)
            rim.SetIntensity(0.25); rim.SetColor(1.0, 1.0, 1.0)
            self.plotter.add_light(rim)
        except Exception as exc:
            _log.debug("Three-point lighting unavailable: %s", exc)

    def _add_framed_text(self, text, position, font_size, bg_color,
                         text_color="black", opacity=_PANEL_OPACITY,
                         frame_color=_PANEL_FRAME, frame_width=1,
                         viewport=True, justification="left",
                         vjustification="top", line_spacing=1.3, bold=False):
        """Add text inside a neat framed background card.

        ``position`` is treated as NORMALISED viewport coordinates (0-1, origin
        bottom-left) whenever ``viewport`` is True. Passing a raw tuple WITHOUT
        this flag makes VTK read it as *pixel* coordinates, which silently
        collapses every overlay into the bottom-left corner — that was the root
        cause of the old text pile-up. Named anchors ("upper_left", ...) handle
        their own placement, so the flag is ignored for them.
        """
        named  = isinstance(position, str)
        actor  = self.plotter.add_text(
            text, position=position, font_size=font_size,
            color=text_color, font="arial",
            viewport=(viewport and not named),
        )
        self._style_overlay(actor, bg_color, opacity, frame_color, frame_width,
                            justification, vjustification, line_spacing, bold)
        return actor

    @staticmethod
    def _style_overlay(actor, bg_color, opacity, frame_color, frame_width,
                       justification="left", vjustification="top",
                       line_spacing=1.3, bold=False):
        """Apply the shared card styling (fill, border, spacing, alignment)."""
        try:
            prop = actor.GetTextProperty()
            if bg_color is not None:
                prop.SetBackgroundColor(*bg_color)
                prop.SetBackgroundOpacity(opacity)
                prop.SetFrame(True)
                prop.SetFrameColor(*frame_color)
                prop.SetFrameWidth(frame_width)
            prop.SetLineSpacing(line_spacing)
            prop.SetBold(bool(bold))
            {"left":   prop.SetJustificationToLeft,
             "center": prop.SetJustificationToCentered,
             "right":  prop.SetJustificationToRight}.get(
                justification, prop.SetJustificationToLeft)()
            {"top":    prop.SetVerticalJustificationToTop,
             "center": prop.SetVerticalJustificationToCentered,
             "bottom": prop.SetVerticalJustificationToBottom}.get(
                vjustification, prop.SetVerticalJustificationToTop)()
        except AttributeError:
            pass

    @staticmethod
    def _adaptive_scalar_fmt(s_min: float, s_max: float) -> str:
        """Pick %.2e for very large/small magnitudes, else %.3f (DEF-02)."""
        mag = max(abs(s_min), abs(s_max), 1e-30)
        return "%.2e" if (mag > 9999 or (0 < mag < 0.01)) else "%.3f"


# ===========================================================================
# ProbingPlotter  (Fully Optimized Commercial Core)
# ===========================================================================

class ProbingPlotter(_PlotterBase):
    COLOR_MAX   = COLOR_MAX
    COLOR_MIN   = COLOR_MIN
    COLOR_PROBE = COLOR_PROBE
    COLOR_PIN   = COLOR_PIN

    _CMAP_BY_KIND = {
        "stress":       "RdBu_r",      # Symmetric diverging
        "force":        "coolwarm",    
        "moment":       "coolwarm",    
        "displacement": "Blues",       # Sequential blue for magnitude
        "safety":       "RdYlGn",      
    }
    def __init__(self, mesh, scalars_name, *, title="", units="", step_info="Static Loads, Step 1", result_kind="stress", step_results=None, metadata_subtitle=""):
        self.mesh               = mesh
        self.scalars_name       = scalars_name
        self.title              = title or scalars_name
        self.units              = units
        self.step_info          = step_info
        self.result_kind        = result_kind
        self.step_results       = step_results or []
        self.metadata_subtitle  = metadata_subtitle
        self.plotter            = None
        self.picker             = None
        self.current_step       = 0
        self.pinned_actors      = []
        self.pinned_points      = []
        self._scale             = (1.0, 1.0, 1.0)
        self.status_actor       = None

    def build(self, base_plotter=None):
        self.plotter = base_plotter or _make_plotter()
        self._scale  = getattr(self.plotter, "_altruxiq_scale", (1.0, 1.0, 1.0))
        self._setup_lighting()
        self._add_mesh()
        self._add_metadata_overlay()
        self._add_stats_overlay()
        self._add_view_title()
        self._add_probe_system()
        self._add_extreme_markers()
        self._add_orientation_widget()
        self._add_instructions()
        if self.step_results:
            self._add_step_slider()
        self._update_status(initial=True)
        self._register_events()
        self._register_key_events()
        return self.plotter

    def show(self, screenshot=None):
        if self.plotter is None: self.build()
        kwargs = {}
        if screenshot: kwargs["screenshot"] = screenshot
        self.plotter.show(**kwargs)

    def _cmap(self):
        return self._CMAP_BY_KIND.get(self.result_kind, _FEA_CMAP)

 
    def _add_mesh(self):
        scalars = self.mesh.point_data[self.scalars_name]
        s_min, s_max = float(np.min(scalars)), float(np.max(scalars))

        # Guard against zero-range (e.g., reactions schematic with all-zero field)
        if abs(s_max - s_min) < 1e-30:
            s_min -= 1e-9
            s_max += 1e-9

        clim = [s_min, s_max]

        # Adaptive precision so huge (e.g. Pa) and tiny values stay readable (DEF-02)
        fmt = self._adaptive_scalar_fmt(s_min, s_max)

        bar_title = f"{self.title}  [{self.units}]\n " if self.units else f"{self.title}\n "
        sargs = dict(
            title=bar_title, title_font_size=12, label_font_size=11,
            shadow=False, n_labels=_N_COLORS + 1, fmt=fmt, font_family="arial",
            color=_INK, position_x=0.07, position_y=0.18, height=0.58, width=0.04, vertical=True,
        )
        self.mesh_actor = self.plotter.add_mesh(
            self.mesh, scalars=self.scalars_name, cmap=self._cmap(), n_colors=_N_COLORS,
            clim=clim,      # Applied the calculated limits
            show_edges=True, edge_color=_EDGE_COLOR, line_width=1.5,
            ambient=_AMBIENT, diffuse=_DIFFUSE, specular=_SPECULAR,
            specular_power=_SPECULAR_POWER, scalar_bar_args=sargs,
            pickable=True, render_points_as_spheres=False, point_size=1,
        )

    def _metadata_text(self):
        scalars = self.mesh.point_data[self.scalars_name]
        s_min, s_max = float(np.min(scalars)), float(np.max(scalars))
        fmt = self._adaptive_scalar_fmt(s_min, s_max)
        block = (
            f"  AltruxIQ   ·   Structural Analysis  \n"
            f"  {_HRULE}  \n"
            f"  Result    {self.title}  \n"
            f"  Subcase   {self.step_info}  \n"
            f"  Range     {fmt % s_min}  to  {fmt % s_max} {self.units}  "
        )
        if self.metadata_subtitle:
            block += f"\n  {self.metadata_subtitle}  "
        return block

    def _add_metadata_overlay(self):
        self.metadata_actor = self._add_framed_text(
            self._metadata_text(), position=(0.012, 0.985), font_size=11,
            bg_color=_PANEL_BG, text_color=_INK, opacity=_PANEL_OPACITY,
            frame_color=_PANEL_FRAME, frame_width=1,
            viewport=True, justification="left", vjustification="top")

    def _add_stats_overlay(self):
        """Node / element count overlay (ENH-05)."""
        stats = f"  Nodes  {self.mesh.n_points:,}     Elements  {self.mesh.n_cells:,}  "
        self.stats_actor = self._add_framed_text(
            stats, position=(0.012, 0.018), font_size=9,
            bg_color=_PANEL_BG, text_color=_INK_SOFT, opacity=0.85,
            frame_color=_PANEL_FRAME, frame_width=1,
            viewport=True, justification="left", vjustification="bottom")

    def _add_view_title(self):
        banner = f"{self.title}    —    {self.step_info}"
        self.view_title_actor = self.plotter.add_text(
            banner, position=(0.5, 0.965), font_size=15, color=_HEADER_INK,
            font="arial", viewport=True)
        self._style_overlay(self.view_title_actor, None, 0, None, 0,
                            justification="center", vjustification="top", bold=True)

    def _add_extreme_markers(self):
        import vtk
        scalars = self.mesh.point_data[self.scalars_name]
        max_idx, min_idx = int(np.argmax(scalars)), int(np.argmin(scalars))
        max_pt, min_pt = np.asarray(self.mesh.points[max_idx]), np.asarray(self.mesh.points[min_idx])

        sx, sy, sz = self._scale
        max_pt_s = [max_pt[0] * sx, max_pt[1] * sy, max_pt[2] * sz]
        min_pt_s = [min_pt[0] * sx, min_pt[1] * sy, min_pt[2] * sz]

        # 1. MAX FLAG (Red Text, Dark Line)
        self.max_caption = vtk.vtkCaptionActor2D()
        self.max_caption.SetAttachmentPoint(max_pt_s)
        self.max_caption.SetCaption(f" MAX: {float(scalars[max_idx]):.4f} {self.units} ")
        self.max_caption.BorderOff()  
        self.max_caption.LeaderOn()
        self.max_caption.SetThreeDimensionalLeader(False) # Forces clean 2D line overlay
        self.max_caption.SetPosition(80, 80)  # Top-Right stretch
        self.max_caption.GetTextActor().SetTextScaleModeToNone()
        
        max_prop = self.max_caption.GetCaptionTextProperty()
        max_prop.SetColor(0.8, 0.0, 0.0)       
        max_prop.SetBackgroundOpacity(0.0)     
        max_prop.SetShadow(True)               
        max_prop.SetBold(True)
        max_prop.SetFontFamilyToArial()
        max_prop.SetFontSize(15)               
        
        self.max_caption.GetProperty().SetColor(0.2, 0.2, 0.2)
        self.max_caption.GetProperty().SetLineWidth(3.0) 
        self.plotter.add_actor(self.max_caption)

    # 2. MIN FLAG (Blue Text, Dark Line)
 
        self.min_caption = vtk.vtkCaptionActor2D()
        self.min_caption.SetAttachmentPoint(min_pt_s)
        self.min_caption.SetCaption(f" MIN: {float(scalars[min_idx]):.4f} {self.units} ")
        self.min_caption.BorderOff()  
        self.min_caption.LeaderOn()
        self.min_caption.SetThreeDimensionalLeader(False) 
        
        # THE FIX: Keep Y positive! 
        # (80, 80) makes it identical to MAX. 
        # (-120, 80) mirrors it to the top-left so they don't overlap.
        self.min_caption.SetPosition(-100, 80)  
        
        self.min_caption.GetTextActor().SetTextScaleModeToNone()
        
        min_prop = self.min_caption.GetCaptionTextProperty()
        min_prop.SetColor(0.0, 0.3, 0.8)       
        min_prop.SetBackgroundOpacity(0.0)     
        min_prop.SetShadow(True)               
        min_prop.SetBold(True)
        min_prop.SetFontFamilyToArial()
        min_prop.SetFontSize(15)               
        
        self.min_caption.GetProperty().SetColor(0.2, 0.2, 0.2)
        self.min_caption.GetProperty().SetLineWidth(3.0) 
        self.plotter.add_actor(self.min_caption)

    def _refresh_extreme_markers(self):
        for actor_name in ["max_caption", "min_caption"]:
            actor = getattr(self, actor_name, None)
            if actor:
                try: self.plotter.remove_actor(actor)
                except Exception: pass
        self._add_extreme_markers()

    _PROBE_IDLE = "  Hover over the model to probe a value  "

    def _add_probe_system(self):
        # Clean, centred read-out card pinned to the bottom edge.
        self.probe_text_actor = self._add_framed_text(
            self._PROBE_IDLE, position=(0.5, 0.018), font_size=11,
            bg_color=_PROBE_BG, text_color=_INK, opacity=_PANEL_OPACITY,
            frame_color=_PROBE_FRAME, frame_width=1,
            viewport=True, justification="center", vjustification="bottom")

        # Tiny clean cursor (no giant wireframes)
        radius = max(self.mesh.length * 0.005, 1e-4)
        self.cursor_actor = self.plotter.add_mesh(pv.Sphere(radius=radius), style="wireframe", color=self.COLOR_PROBE, line_width=2, pickable=False)
        self.cursor_actor.VisibilityOff()
        if vtk is not None:
            self.picker = vtk.vtkCellPicker()
            self.picker.SetTolerance(0.0005)

    def _add_orientation_widget(self):
        try: self.plotter.add_camera_orientation_widget()
        except AttributeError: pass

    def _add_instructions(self):
        self._update_dashboard_display()

    def _add_step_slider(self):
        n = len(self.step_results)
        self.plotter.add_slider_widget(
            self._on_step_slider, rng=[0, n - 1] if n > 1 else [0, 0], value=0, title="Load Step",
            pointa=(0.40, 0.12), pointb=(0.60, 0.12), style="modern", title_height=0.018, color="#1B2631", event_type=_SLIDER_EVENT_TYPE
        )

    def _on_step_slider(self, value):
        idx = int(round(value))
        if idx == self.current_step or not self.step_results or idx < 0 or idx >= len(self.step_results): return
        label, scalars = self.step_results[idx]
        self.current_step = idx
        self.mesh.point_data[self.scalars_name] = scalars
        self.step_info = label
        self._refresh_extreme_markers()
        
        if self.view_title_actor: 
            self.view_title_actor.SetInput(f"{self.title}  —  {label}")
            
        # --- THE FIX ---
        # Metadata uses "upper_left", so we must remove and redraw it too.
        if getattr(self, "metadata_actor", None):
            try:
                self.plotter.remove_actor(self.metadata_actor)
            except Exception:
                pass
            self._add_metadata_overlay()

        self.plotter.render()
    def _on_reset_view(self, value=False):
        self.plotter.reset_camera()
        self.plotter.render()

    def _set_view(self, view_name):
        views = {
            "front": self.plotter.view_xy,   # XY  (1)
            "top":   self.plotter.view_xz,   # XZ  (2)
            "side":  self.plotter.view_yz,   # YZ  (3)
            "iso":   self.plotter.view_isometric,
        }
        views.get(view_name, self.plotter.view_isometric)()
        self.plotter.reset_camera()
        self.plotter.render()

    def _clear_pinned(self, value=False):
        for actor, label in self.pinned_actors:
            try: self.plotter.remove_actor(actor)
            except Exception: pass
            try: self.plotter.remove_actor(label)
            except Exception: pass
        self.pinned_actors.clear()
        self.pinned_points.clear()
        self._update_status()
        self.plotter.render()
        
    def _update_dashboard_display(self):
        n_pins = len(getattr(self, "pinned_points", []))
        text = (
            f"  CONTROLS  \n"
            f"  {_HRULE}  \n"
            f"  Hover  ·  probe value  \n"
            f"  Click  ·  pin measurement  \n"
            f"  x  ·  clear pins  \n"
            f"  r  ·  reset view  \n"
            f"  1 / 2 / 3  ·  front / top / side  \n"
            f"  4  ·  isometric  \n"
            f"  s / w  ·  surface / wireframe  \n"
            f"  f  ·  fly to cursor  \n"
            f"  {_HRULE}  \n"
            f"  Pinned points : {n_pins}  "
        )

        if getattr(self, "instruction_actor", None) is not None:
            try:
                self.plotter.remove_actor(self.instruction_actor)
            except Exception:
                pass

        # Right-justified + anchored just inside the right edge so the longest
        # line can never spill off-screen (the old "lower_right" clipped).
        self.instruction_actor = self._add_framed_text(
            text, position=(0.988, 0.018), font_size=9,
            bg_color=_PANEL_BG, text_color=_INK, opacity=_PANEL_OPACITY,
            frame_color=_PANEL_FRAME, frame_width=1,
            viewport=True, justification="right", vjustification="bottom")

    def _update_status(self, initial=False):
        self._update_dashboard_display()

    def _register_events(self):
        if vtk is None or self.picker is None: return
        try:
            iren = self.plotter.iren.interactor
            iren.AddObserver("MouseMoveEvent",       self._on_mouse_move)
            iren.AddObserver("LeftButtonPressEvent", self._on_left_click)
        except Exception: pass

    def _register_key_events(self):
        try:
            self.plotter.add_key_event("v", lambda: self._set_view("iso"))
            self.plotter.add_key_event("r", self._on_reset_view)
            self.plotter.add_key_event("c", self._cycle_interaction_style)
            self.plotter.add_key_event("x", self._clear_pinned)  # Trigger clearing pins from keyboard
            # View preset shortcuts (ENH-03)
            self.plotter.add_key_event("1", lambda: self._set_view("front"))
            self.plotter.add_key_event("2", lambda: self._set_view("top"))
            self.plotter.add_key_event("3", lambda: self._set_view("side"))
            self.plotter.add_key_event("4", lambda: self._set_view("iso"))
        except Exception as exc:
            _log.debug("Key event registration failed: %s", exc)

    def _cycle_interaction_style(self, *args):
        try:
            cur = getattr(self.plotter, "_altruxiq_trackball", False)
            if cur: self.plotter.enable_trackball_style()
            else: self.plotter.enable_joystick_style()
            self.plotter._altruxiq_trackball = not cur
        except Exception: pass

    def _on_mouse_move(self, obj, event):
        if self.plotter is None or self.picker is None: return
        try: x, y = self.plotter.iren.interactor.GetEventPosition()
        except Exception: return
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        if self.picker.GetActor() is self.mesh_actor and self.picker.GetCellId() >= 0:
            world_pos = np.array(self.picker.GetPickPosition(), dtype=float)
            unscaled  = self._unscale_point(world_pos)
            try: pid = self.mesh.find_closest_point(unscaled)
            except Exception: pid = -1
            if pid >= 0:
                scalar_val = float(self.mesh.point_data[self.scalars_name][pid])
                self.probe_text_actor.SetInput(f"  {self.title} :  {scalar_val:.4f} {self.units}     ·     X {world_pos[0]:+.3f}   Y {world_pos[1]:+.3f}   Z {world_pos[2]:+.3f}  ")
                self.cursor_actor.SetPosition(world_pos)
                self.cursor_actor.VisibilityOn()
            else: self._hide_cursor()
        else: self._hide_cursor()
        self.plotter.render()

    def _hide_cursor(self):
        try:
            self.probe_text_actor.SetInput(self._PROBE_IDLE)
            self.cursor_actor.VisibilityOff()
        except Exception: pass

    def _on_left_click(self, obj, event):
        if self.plotter is None or self.picker is None: return
        try: x, y = self.plotter.iren.interactor.GetEventPosition()
        except Exception: return
        self.picker.Pick(x, y, 0, self.plotter.renderer)
        if self.picker.GetActor() is self.mesh_actor and self.picker.GetCellId() >= 0:
            world_pos = np.array(self.picker.GetPickPosition(), dtype=float)
            unscaled  = self._unscale_point(world_pos)
            try: pid = self.mesh.find_closest_point(unscaled)
            except Exception: pid = -1
            if pid >= 0:
                self._pin_point(world_pos, float(self.mesh.point_data[self.scalars_name][pid]))
    def _pin_point(self, position, value):
        import vtk
        for p, _ in self.pinned_points:
            if np.linalg.norm(np.asarray(p) - np.asarray(position)) < 1e-6: return
        
        self.pinned_points.append((position, value))
        
        caption = vtk.vtkCaptionActor2D()
        caption.SetAttachmentPoint(position)
        caption.SetCaption(f" {value:.4f} {self.units} ")
        caption.BorderOff()
        caption.LeaderOn()
        caption.SetThreeDimensionalLeader(False) # Clean 2D overlay prevents line clipping
        caption.SetPosition(80, 80) # Clean diagonal offset matching MAX
        caption.GetTextActor().SetTextScaleModeToNone()
        
        prop = caption.GetCaptionTextProperty()
        prop.SetColor(0.1, 0.1, 0.1)       
        prop.SetBackgroundOpacity(0.0)     
        prop.SetShadow(True)               
        prop.SetBold(True)
        prop.SetFontFamilyToArial()
        prop.SetFontSize(14)               
        
        caption.GetProperty().SetColor(0.2, 0.2, 0.2) 
        caption.GetProperty().SetLineWidth(2.0) 
        
        self.plotter.add_actor(caption)
        self.pinned_actors.append((None, caption))
        
        self._update_status()
        self.plotter.render()

    def _unscale_point(self, p):
        sx, sy, sz = self._scale
        return np.array([p[0] / sx, p[1] / sy, p[2] / sz])

# ===========================================================================
# PUBLIC API  (refactored onto ProbingPlotter)
# ===========================================================================

def _build_fea_plotter(mesh, scalars_name, *, title, units, result_kind, step_results=None, metadata_subtitle=""):
    pl = _make_plotter()
    pl._altruxiq_scale = (1.0, 1.0, 1.0)
    pp = ProbingPlotter(mesh, scalars_name, title=title, units=units, result_kind=result_kind, step_results=step_results, metadata_subtitle=metadata_subtitle)
    pp.build(base_plotter=pl)
    return pl, pp

def PyVista_reactions_schematic(beam_length, Reactions, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, f_div, m_div = get_divisor(units, "length"), get_divisor(units, "force"), get_divisor(units, "moment")
    mesh = _build_beam_mesh(np.linspace(0, beam_length/l_div, 100), np.zeros(100), shape, section_dims, c/l_div, b/l_div, "Reactions")
    pl = _make_plotter()
    _add_fea_annotations(pl, "Free Body Diagram", "Reaction Forces", 0, 0, units['force'])
    pl.add_mesh(mesh, color=_BEAM_COLOR, opacity=0.8, show_edges=True, edge_color=_EDGE_COLOR, line_width=0.5, pickable=True)
    _add_support_glyphs(pl, Reactions, l_div, f_div, m_div, beam_length / l_div)
    try: pl.add_camera_orientation_widget()
    except AttributeError: pass
    pl.view_xy()
    pl.reset_camera()
    pl.camera.zoom(1.2)
    pl.show(screenshot=_make_screenshot_path("reactions_schematic"))

def PyVista_shear_force(X_Field, Total_ShearForce, beam_length, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, f_div = get_divisor(units, "length"), get_divisor(units, "force")
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, SF_vis = _downsample_for_visuals(X_Field / l_div, Total_ShearForce / f_div, target_fraction=0.2)
    mesh = _build_beam_mesh(X_vis, SF_vis, shape, section_dims, draw_c, draw_b, "ShearForce")
    pl, pp = _build_fea_plotter(mesh, "ShearForce", title="Shear Force (Element-Nodal)", units=units['force'], result_kind="force")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("shear_force"))

def PyVista_bending_moment(X_Field, Total_BendingMoment, beam_length, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, m_div = get_divisor(units, "length"), get_divisor(units, "moment")
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, BM_vis = _downsample_for_visuals(X_Field / l_div, Total_BendingMoment / m_div, target_fraction=0.2)
    mesh = _build_beam_mesh(X_vis, BM_vis, shape, section_dims, draw_c, draw_b, "BendingMoment")
    pl, pp = _build_fea_plotter(mesh, "BendingMoment", title="Bending Moment (Element-Nodal)", units=units['moment'], result_kind="moment")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("bending_moment"))

def PyVista_shear_stress(X_Field, ShearStress, beam_length, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, s_div = get_divisor(units, "length"), get_divisor(units, "stress")
    ss = np.max(np.abs(ShearStress), axis=1) if ShearStress.ndim > 1 else np.abs(ShearStress)
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, SS_vis = _downsample_for_visuals(X_Field / l_div, ss / s_div, target_fraction=0.2)
    mesh = _build_beam_mesh(X_vis, SS_vis, shape, section_dims, draw_c, draw_b, "ShearStress")
    pl, pp = _build_fea_plotter(mesh, "ShearStress", title="Shear Stress (Element-Nodal)", units=units['stress'], result_kind="stress")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("shear_stress"))

def PyVista_bending_stress(X_Field, BendingStress, beam_length, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, s_div = get_divisor(units, "length"), get_divisor(units, "stress")
    bs = np.max(np.abs(BendingStress), axis=1) if BendingStress.ndim > 1 else np.abs(BendingStress)
    draw_length, draw_c, draw_b = beam_length / l_div, c / l_div, b / l_div
    X_vis, BS_vis = _downsample_for_visuals(X_Field / l_div, bs / s_div, target_fraction=0.2)
    mesh = _build_beam_mesh(X_vis, BS_vis, shape, section_dims, draw_c, draw_b, "BendingStress")
    pl, pp = _build_fea_plotter(mesh, "BendingStress", title="Bending Stress (Element-Nodal)", units=units['stress'], result_kind="stress")
    _apply_visual_scaling(pl, draw_length, max(draw_c * 2, draw_b))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("bending_stress"))

def PyVista_deflection(X_Field, Deflection, beam_length, shape, section_dims, c, b, units=None):
    units = units or default_units()
    l_div, ls_div = get_divisor(units, "length"), get_divisor(units, "length_small")
    defl_full = Deflection / ls_div
    X, defl = _downsample_for_visuals(X_Field / l_div, defl_full, target_fraction=0.1)
    max_defl = float(np.max(np.abs(defl_full)))
    visual_scale = min(((c / l_div) * 6.0) / max_defl, 50.0) if max_defl > 0 else 1.0
    defl_visual = defl * visual_scale

    mesh = _build_beam_mesh(
        X, np.abs(defl), shape, section_dims, c / l_div, b / l_div,
        "Deflection", y_offsets=defl_visual,
    )   # reuse shared builder: hollow-aware + concave-safe caps + deflection offset

    pl, pp = _build_fea_plotter(mesh, "Deflection", title=f"Displacement - Nodal Magnitude (Scale: x{visual_scale:.1f})", units=units['length_small'], result_kind="displacement")
    ref_mesh = _build_beam_mesh(X, np.zeros(len(X)), shape, section_dims, c/l_div, b/l_div, "Ref")
    
    # Improved visibility for the reference undeformed beam (DEF-05)
    pl.add_mesh(
        ref_mesh,
        color=_BEAM_COLOR,        # Neutral grey
        opacity=_GHOST_OPACITY,   # Clearly visible
        show_edges=True,
        edge_color="#505050",
        line_width=1.0,
        style=_GHOST_STYLE,       # Wireframe only — less visual noise
        pickable=False,
    )

    # Prominent deformation-scale label (DEF-07 / §5.6)
    _scale_actor = pl.add_text(
        f"  Deformation scale  ×{visual_scale:.1f}  (visual only)  ",
        position=(0.012, 0.075), font_size=9, color=_INK_SOFT, font="arial",
        viewport=True,
    )
    _PlotterBase._style_overlay(_scale_actor, _PANEL_BG, 0.85, _PANEL_FRAME, 1,
                                justification="left", vjustification="bottom")

    _apply_visual_scaling(pl, beam_length / l_div, max((c / l_div) * 2, b / l_div))
    pp._scale = getattr(pl, "_altruxiq_scale", (1.0, 1.0, 1.0))
    pp._refresh_extreme_markers()
    _frame_camera(pl, mesh)
    pl.show(screenshot=_make_screenshot_path("deflection"))

def PyVista_combined(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, shape, section_dims, c, b, Deflection=None, ShearStress=None, BendingStress=None, Reactions=None, units=None):
    print("\n  ═══════════════════════════════════════════")
    print("   AltruxIQ : 3D FEA Viewer  (interactive)")
    print("  ═══════════════════════════════════════════\n")
    PyVista_shear_force(X_Field, Total_ShearForce, beam_length, shape, section_dims, c, b, units)
    PyVista_bending_moment(X_Field, Total_BendingMoment, beam_length, shape, section_dims, c, b, units)
    if Deflection is not None: PyVista_deflection(X_Field, Deflection, beam_length, shape, section_dims, c, b, units)
    if ShearStress is not None: PyVista_shear_stress(X_Field, ShearStress, beam_length, shape, section_dims, c, b, units)
    if BendingStress is not None: PyVista_bending_stress(X_Field, BendingStress, beam_length, shape, section_dims, c, b, units)
    if Reactions: PyVista_reactions_schematic(beam_length, Reactions, shape, section_dims, c, b, units)

def make_probing_plotter(mesh, scalars_name, *, title="", units="", result_kind="stress", step_results=None):
    pp = ProbingPlotter(mesh, scalars_name, title=title, units=units, result_kind=result_kind, step_results=step_results)
    pp.build()
    return pp

# ===========================================================================
# STEP 5 — Deflected-beam load animation
# ===========================================================================

def _build_animation_frames(
    X_Field: np.ndarray,
    Deflection: np.ndarray,
    scalar_field: np.ndarray,
    scalar_name: str,
    shape: str,
    section_dims: dict,
    c: float,
    b: float,
    beam_length: float,
    units: dict,
    n_frames: int = _DEFAULT_N_FRAMES,
):
    """Pre-build ``n_frames`` meshes for the load-application animation.

    Linear-elastic analysis means every response scales linearly with the
    applied load, so frame ``k`` simply multiplies the full deflection and the
    full scalar field by ``alpha = k / (n_frames - 1)``.

    Each frame is built with the shared :func:`_build_beam_mesh`, so the frames
    inherit the hollow-aware, concave-safe end caps (I-/T-beams render
    correctly).  All frames share identical connectivity and point ordering.

    Returns
    -------
    frames : list[pv.PolyData]
    true_scale : float
        Deformation exaggeration factor for display (actual ratio, e.g. 10.1x).
    ref_mesh : pv.PolyData
        Undeformed reference (zero offset) for the faint ghost overlay.
    draw_length : float
        Beam length in drawing units (for ``_apply_visual_scaling``).
    section_dim_max : float
        Cross-section size in drawing units (for ``_apply_visual_scaling``).
    """
    l_div  = get_divisor(units, "length")
    ls_div = get_divisor(units, "length_small")

    # Downsample — 10% of points is plenty for smooth animation
    X_vis, defl_vis = _downsample_for_visuals(X_Field / l_div, Deflection / ls_div, target_fraction=0.1)
    _,     scalar_vis = _downsample_for_visuals(X_Field / l_div, scalar_field, target_fraction=0.1)

    draw_c, draw_b = c / l_div, b / l_div
    max_defl = float(np.max(np.abs(defl_vis)))
    visual_scale = min((draw_c * 6.0) / max_defl, 50.0) if max_defl > 0 else 1.0
    defl_visual = defl_vis * visual_scale
    # True exaggeration relative to the real deflection (deflection is in the
    # small-length unit, geometry in the large-length unit -> divide by ls_div).
    true_scale = visual_scale / ls_div if ls_div else visual_scale

    frames = []
    for k in range(n_frames):
        alpha = k / max(n_frames - 1, 1)
        # Keep the scalar's sign: shear force / bending moment are signed and
        # use a diverging map anchored at zero. Magnitude-only fields (stress,
        # displacement) are already made non-negative by the caller.
        mesh_k = _build_beam_mesh(
            X_vis, scalar_vis * alpha, shape, section_dims,
            draw_c, draw_b, scalar_name, y_offsets=defl_visual * alpha,
        )
        frames.append(mesh_k)

    # Undeformed reference (ghost) — zero offset, zero scalar
    ref_mesh = _build_beam_mesh(X_vis, np.zeros(len(X_vis)), shape, section_dims,
                                draw_c, draw_b, "Ref")
    draw_length     = beam_length / l_div
    section_dim_max = max(draw_c * 2, draw_b)

    return frames, true_scale, ref_mesh, draw_length, section_dim_max


class AnimationPlotter(_PlotterBase):
    """Plays back pre-computed load-application frames in a timer loop.

    The beam transitions from straight (alpha=0) to fully deflected (alpha=1)
    while the scalar contour grows from zero to its full range and a load
    indicator counts 0% -> 100%.
    """

    _CMAP_BY_KIND = ProbingPlotter._CMAP_BY_KIND  # Reuse the same maps

    def __init__(self, mesh_frames, scalars_name, *, title="", units="",
                 result_kind="stress", fps=_DEFAULT_FPS, loop=True, deform_scale=1.0,
                 ref_mesh=None, draw_length=0.0, section_dim_max=0.0):
        self.mesh_frames    = mesh_frames
        self.scalars_name   = scalars_name
        self.title          = title or scalars_name
        self.units          = units
        self.result_kind    = result_kind
        self.fps            = fps
        self.loop           = loop
        self.deform_scale   = deform_scale
        self.ref_mesh       = ref_mesh
        self.draw_length    = draw_length
        self.section_dim_max = section_dim_max

        self.plotter        = None
        self.mesh_actor     = None
        # A single live mesh whose points/scalars we mutate in place each frame
        # (reliable colour + geometry refresh, unlike raw VTK array swaps).
        self.display_mesh   = mesh_frames[0].copy()
        self._current_frame = 0
        self._playing       = False
        self._timer_id      = None
        self._closed        = False

        # Lock the colour range to the full-load frame so the bar never jumps
        final_scalars = mesh_frames[-1].point_data[scalars_name]
        self._scalar_min = float(np.min(final_scalars))
        self._scalar_max = float(np.max(final_scalars))
        if abs(self._scalar_max - self._scalar_min) < 1e-30:
            self._scalar_min -= 1e-9
            self._scalar_max += 1e-9

    # ------------------------------------------------------------------ build
    def build(self):
        self.plotter = _make_plotter()
        self._setup_lighting()
        self._add_ghost()
        self._add_first_frame()
        self._add_ui_overlays()
        self._add_play_stop_button()
        self._add_frame_slider()
        self._register_timer()
        self._register_key_events()
        try: self.plotter.add_camera_orientation_widget()
        except AttributeError as exc: _log.debug("orientation widget unavailable: %s", exc)
        # Stretch the slender beam (Y/Z) so it looks proportionate and the
        # deflection is clearly visible — same treatment as the static view.
        _apply_visual_scaling(self.plotter, self.draw_length, self.section_dim_max)
        _frame_camera(self.plotter, self.display_mesh)
        return self.plotter

    def show(self, screenshot=None):
        if self.plotter is None: self.build()
        kwargs = {}
        if screenshot: kwargs["screenshot"] = screenshot
        try:
            self.plotter.show(**kwargs)
        finally:
            # Always tear down the timer + GL context so re-opening a new
            # animation does not inherit a corrupted OpenGL state.
            self._cleanup()

    def _cleanup(self):
        """Stop playback, kill the repeating timer, and release the plotter.

        Without this, the VTK repeating timer keeps firing render() while the
        window is being destroyed, which corrupts the OpenGL context and makes
        the *next* animation window fail to compile shaders.
        """
        self._playing = False
        self._closed = True
        try:
            iren = self.plotter.iren.interactor
            if self._timer_id is not None:
                iren.DestroyTimer(self._timer_id)
            iren.RemoveObservers("TimerEvent")
            iren.RemoveObservers("ExitEvent")
        except Exception as exc:
            _log.debug("Timer/observer cleanup skipped: %s", exc)
        self._timer_id = None
        try:
            self.plotter.close()
        except Exception as exc:
            _log.debug("Plotter close skipped: %s", exc)
        try:
            self.plotter.deep_clean()
        except Exception as exc:
            _log.debug("deep_clean skipped: %s", exc)

    def _is_live(self):
        """True only while the render window is open and usable."""
        return (self.plotter is not None
                and not self._closed
                and not getattr(self.plotter, "_closed", False))

    def _add_ghost(self):
        """Faint undeformed reference beam, visible behind the deflected one."""
        if self.ref_mesh is None:
            return
        try:
            self.plotter.add_mesh(
                self.ref_mesh, color=_BEAM_COLOR, opacity=_GHOST_OPACITY,
                show_edges=True, edge_color="#505050", line_width=1.0,
                style=_GHOST_STYLE, pickable=False, reset_camera=False)
        except Exception as exc:
            _log.debug("Ghost mesh unavailable: %s", exc)

    def _add_first_frame(self):
        clim = [self._scalar_min, self._scalar_max]
        fmt = self._adaptive_scalar_fmt(clim[0], clim[1])
        bar_title = f"{self.title}  [{self.units}]\n " if self.units else f"{self.title}\n "
        sargs = dict(
            title=bar_title, title_font_size=12, label_font_size=11,
            n_labels=_N_COLORS - 1, fmt=fmt, font_family="arial", color=_INK,
            position_x=0.07, position_y=0.18, height=0.58, width=0.04, vertical=True, shadow=False,
        )
        self.display_mesh.set_active_scalars(self.scalars_name)
        self.mesh_actor = self.plotter.add_mesh(
            self.display_mesh, scalars=self.scalars_name,
            cmap=self._CMAP_BY_KIND.get(self.result_kind, _FEA_CMAP), n_colors=_N_COLORS,
            clim=clim, show_edges=True, edge_color=_EDGE_COLOR, line_width=0.8,
            ambient=_AMBIENT, diffuse=_DIFFUSE, specular=_SPECULAR, specular_power=_SPECULAR_POWER,
            scalar_bar_args=sargs, pickable=False, reset_camera=False,
        )

    def _add_ui_overlays(self):
        n = len(self.mesh_frames)
        # Title banner (centred header) ---------------------------------------
        self._title_actor = self.plotter.add_text(
            f"{self.title}    —    Load Animation", position=(0.5, 0.965),
            font_size=15, color=_HEADER_INK, font="arial", viewport=True)
        self._style_overlay(self._title_actor, None, 0, None, 0,
                            justification="center", vjustification="top", bold=True)

        # Metadata card (top-left) -------------------------------------------
        info = (
            f"  AltruxIQ   ·   Structural Analysis  \n"
            f"  {_HRULE}  \n"
            f"  Result   {self.title}  \n"
            f"  Scale    ×{self.deform_scale:.1f}  (visual)  \n"
            f"  Frames   {n}      FPS   {self.fps}  "
        )
        self._info_actor = self._add_framed_text(
            info, position=(0.012, 0.985), font_size=11,
            bg_color=_PANEL_BG, text_color=_INK, opacity=_PANEL_OPACITY,
            frame_color=_PANEL_FRAME, frame_width=1,
            viewport=True, justification="left", vjustification="top")

        # Load progress badge (top-centre, under the banner) ------------------
        self._load_actor = self._add_framed_text(
            "  Load  0%  ", position=(0.5, 0.905), font_size=15,
            bg_color=_PROBE_BG, text_color=_HEADER_INK, opacity=_PANEL_OPACITY,
            frame_color=_PROBE_FRAME, frame_width=2,
            viewport=True, justification="center", vjustification="top", bold=True)

        # Controls card (bottom-right, right-justified so it never clips) -----
        ctrl = (
            "  ANIMATION CONTROLS  \n"
            f"  {_HRULE}  \n"
            "  Space  ·  play / stop  \n"
            "  Arrow keys  ·  step frame  \n"
            "  Home  ·  first frame  \n"
            "  End  ·  last frame  \n"
            "  l  ·  toggle loop  \n"
            "  g  ·  export GIF  \n"
            "  r  ·  reset view  "
        )
        self._ctrl_actor = self._add_framed_text(
            ctrl, position=(0.988, 0.10), font_size=9, bg_color=_PANEL_BG,
            text_color=_INK, opacity=_PANEL_OPACITY,
            frame_color=_PANEL_FRAME, frame_width=1,
            viewport=True, justification="right", vjustification="bottom")

    def _add_play_stop_button(self):
        try:
            self.plotter.add_checkbox_button_widget(
                self._on_play_stop_toggle, value=False, position=(10.0, 10.0),
                size=40, border_size=3, color_on="#2ECC71", color_off="#E74C3C")
        except Exception as exc:
            _log.debug("Play/Stop button unavailable: %s", exc)

    def _add_frame_slider(self):
        n = len(self.mesh_frames)
        try:
            self.plotter.add_slider_widget(
                self._on_scrubber_drag, rng=[0, n - 1], value=0, title="",
                pointa=(0.12, 0.035), pointb=(0.85, 0.035), style="modern",
                event_type=_SLIDER_EVENT_TYPE, title_height=0.01, color="#2C3E50")
        except Exception as exc:
            _log.debug("Frame slider unavailable: %s", exc)

    def _register_timer(self):
        try:
            iren = self.plotter.iren.interactor
            iren.AddObserver("TimerEvent", self._on_timer)
            # Stop playback + destroy the timer the moment the window closes
            iren.AddObserver("ExitEvent", self._on_window_exit)
        except Exception as exc:
            _log.debug("Timer observer unavailable: %s", exc)

    def _on_window_exit(self, obj=None, event=None):
        """Halt the repeating timer before the GL context is torn down."""
        self._playing = False
        self._closed = True
        try:
            if self._timer_id is not None:
                self.plotter.iren.interactor.DestroyTimer(self._timer_id)
                self._timer_id = None
        except Exception:
            pass

    def _register_key_events(self):
        try:
            self.plotter.add_key_event("space", self._toggle_play_stop)
            self.plotter.add_key_event("Left",  self._step_backward)
            self.plotter.add_key_event("Right", self._step_forward)
            self.plotter.add_key_event("Home",  self._goto_first_frame)
            self.plotter.add_key_event("End",   self._goto_last_frame)
            self.plotter.add_key_event("l",     self._toggle_loop)
            self.plotter.add_key_event("r",     self._reset_camera)
            self.plotter.add_key_event("g",     self._export_gif_prompt)
        except Exception as exc:
            _log.debug("Animation key events unavailable: %s", exc)

    # -------------------------------------------------------------- playback
    def _on_play_stop_toggle(self, state):
        if not self._is_live():
            return
        self._playing = bool(state)
        try:
            iren = self.plotter.iren.interactor
            if self._playing:
                interval_ms = max(1, int(1000 / self.fps))
                self._timer_id = iren.CreateRepeatingTimer(interval_ms)
            elif self._timer_id is not None:
                iren.DestroyTimer(self._timer_id)
                self._timer_id = None
        except Exception as exc:
            _log.debug("Timer toggle failed: %s", exc)

    def _toggle_play_stop(self):
        if not self._is_live():
            return
        self._on_play_stop_toggle(not self._playing)

    def _on_timer(self, obj, event):
        if not self._playing or not self._is_live():
            return
        n = len(self.mesh_frames)
        self._current_frame += 1
        if self._current_frame >= n:
            if self.loop:
                self._current_frame = 0
            else:
                self._current_frame = n - 1
                self._on_play_stop_toggle(False)
        self._update_frame(self._current_frame)

    def _step_forward(self):
        self._current_frame = min(self._current_frame + 1, len(self.mesh_frames) - 1)
        self._update_frame(self._current_frame)

    def _step_backward(self):
        self._current_frame = max(self._current_frame - 1, 0)
        self._update_frame(self._current_frame)

    def _goto_first_frame(self):
        self._current_frame = 0
        self._update_frame(0)

    def _goto_last_frame(self):
        self._current_frame = len(self.mesh_frames) - 1
        self._update_frame(self._current_frame)

    def _toggle_loop(self):
        self.loop = not self.loop

    def _reset_camera(self):
        if not self._is_live():
            return
        self.plotter.reset_camera(); self.plotter.render()

    def _on_scrubber_drag(self, value):
        frame = int(round(value))
        self._current_frame = max(0, min(frame, len(self.mesh_frames) - 1))
        self._update_frame(self._current_frame)

    # ----------------------------------------------------------- frame update
    def _update_frame(self, frame_idx):
        """Mutate the live display mesh in place — refreshes geometry AND colour."""
        if not self._is_live():
            return
        mesh_k = self.mesh_frames[frame_idx]
        n = len(self.mesh_frames)
        alpha = frame_idx / max(n - 1, 1)
        try:
            self.display_mesh.points = mesh_k.points
            self.display_mesh.point_data[self.scalars_name] = mesh_k.point_data[self.scalars_name]
            self.display_mesh.set_active_scalars(self.scalars_name)
        except Exception as exc:
            _log.debug("Frame update failed: %s", exc)
        try:
            self._load_actor.SetInput(f"  Load  {int(alpha * 100)}%  ")
        except Exception:
            pass
        self.plotter.render()

    # --------------------------------------------------------------- GIF export
    def _export_gif_prompt(self):
        print("\n  AltruxIQ: GIF Export")
        try:
            name = input("  Enter filename (without extension): ").strip()
        except Exception:
            return
        if not name: return
        self.export_gif(os.path.join(_ensure_export_dir(), f"{name}.gif"))

    def export_gif(self, filepath, fps=None):
        """Render every frame off-screen and write an animated GIF.

        Requires ``imageio`` (``pip install imageio[ffmpeg]``).
        """
        try:
            import imageio
        except ImportError:
            print("  imageio not installed. Run: pip install imageio")
            return

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        fps_out = fps or self.fps
        clim = [self._scalar_min, self._scalar_max]
        cmap = self._CMAP_BY_KIND.get(self.result_kind, _FEA_CMAP)
        print(f"\n  Exporting {len(self.mesh_frames)} frames to {filepath} ...")

        off = pv.Plotter(off_screen=True, window_size=(1280, 720))
        frames_rgb = []
        n = len(self.mesh_frames)
        for k, mesh_k in enumerate(self.mesh_frames):
            off.clear()
            off.set_background(_BG_COLOR)
            # Faint undeformed ghost for reference
            if self.ref_mesh is not None:
                off.add_mesh(self.ref_mesh, color=_BEAM_COLOR, opacity=_GHOST_OPACITY,
                             style=_GHOST_STYLE, show_edges=True, edge_color="#505050",
                             line_width=1.0, reset_camera=False)
            off.add_mesh(mesh_k, scalars=self.scalars_name, cmap=cmap, clim=clim,
                         n_colors=_N_COLORS, show_edges=True, edge_color=_EDGE_COLOR,
                         reset_camera=False)
            # Match the on-screen proportions (stretch slender beam Y/Z)
            _apply_visual_scaling(off, self.draw_length, self.section_dim_max)
            alpha = k / max(n - 1, 1)
            off.add_text(f"{self.title}  —  Load: {int(alpha * 100)}%",
                         position="upper_edge", font_size=14, color="black")
            off.view_xy(); off.reset_camera(); off.camera.zoom(1.2)
            frames_rgb.append(off.screenshot(return_img=True))
            print(f"\r  Frame {k + 1}/{n}", end="", flush=True)
        off.close()

        imageio.mimwrite(filepath, frames_rgb, fps=fps_out, loop=0)
        print_success(f"Animated GIF saved: {filepath}")
        return filepath

    # --------------------------------------------------------------- PNG export
    def export_png(self, filepath, frame_idx=-1, window_size=(1920, 1080)):
        """Render a single high-resolution still of one animation frame.

        ``frame_idx`` defaults to the last (100%-load) frame. Rendered fully
        off-screen so it works regardless of the live viewer state.
        """
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        n = len(self.mesh_frames)
        idx = frame_idx if frame_idx >= 0 else n - 1
        idx = max(0, min(idx, n - 1))
        mesh_k = self.mesh_frames[idx]
        clim = [self._scalar_min, self._scalar_max]
        cmap = self._CMAP_BY_KIND.get(self.result_kind, _FEA_CMAP)

        off = pv.Plotter(off_screen=True, window_size=window_size)
        off.set_background(_BG_COLOR)
        if self.ref_mesh is not None:
            off.add_mesh(self.ref_mesh, color=_BEAM_COLOR, opacity=_GHOST_OPACITY,
                         style=_GHOST_STYLE, show_edges=True, edge_color="#505050",
                         line_width=1.0, reset_camera=False)
        off.add_mesh(mesh_k, scalars=self.scalars_name, cmap=cmap, clim=clim,
                     n_colors=_N_COLORS, show_edges=True, edge_color=_EDGE_COLOR,
                     reset_camera=False)
        _apply_visual_scaling(off, self.draw_length, self.section_dim_max)
        alpha = idx / max(n - 1, 1)
        off.add_text(f"{self.title}  \u2014  Load: {int(alpha * 100)}%",
                     position="upper_edge", font_size=16, color="black")
        off.view_xy(); off.reset_camera(); off.camera.zoom(1.2)
        off.screenshot(filepath)
        off.close()
        print_success(f"PNG image saved: {filepath}")
        return filepath


def _animation_export_menu(ap, result_key):
    """Optional post-viewer export step: animated GIF and/or high-res PNG.

    Mirrors the 2D Plotly export workflow so the whole app shares one
    save-to-file experience. Never raises on a declined/cancelled prompt.
    """
    try:
        if not ask_yes_no("Export this 3D animation to a file?", default=False):
            return []
        print(colored("  1) Animated GIF", 'yellow')
              + colored("    2) PNG image (still)", 'yellow')
              + colored("    3) Both", 'yellow'))
        choice = ask_choice("Choose export format", ["1", "2", "3"], allow_cancel=True)
    except (EOFError, KeyboardInterrupt):
        return []
    if choice is None:
        return []

    stamp = _timestamp()
    base = f"animation_{result_key}"
    out_dir = _ensure_export_dir()
    saved = []
    if choice in ("1", "3"):
        try:
            saved.append(ap.export_gif(os.path.join(out_dir, f"{base}_{stamp}.gif")))
        except Exception as e:
            print_error(f"GIF export failed: {e}")
            print_error("Install the backend with:  pip install imageio")
    if choice in ("2", "3"):
        try:
            saved.append(ap.export_png(os.path.join(out_dir, f"{base}_{stamp}.png")))
        except Exception as e:
            print_error(f"PNG export failed: {e}")
    return [s for s in saved if s]


def PyVista_animation(
    X_Field, Deflection, Total_ShearForce, Total_BendingMoment,
    ShearStress, BendingStress,
    beam_length, shape, section_dims, c, b,
    result_to_animate="ShearForce",
    n_frames=_DEFAULT_N_FRAMES,
    fps=_DEFAULT_FPS,
    units=None,
):
    """Open an interactive animation of progressive load application on the beam.

    ``result_to_animate`` is one of ``ShearForce``, ``BendingMoment``,
    ``ShearStress``, ``BendingStress``, ``Deflection``.
    """
    units = units or default_units()

    scalar_map = {
        "ShearForce":    (Total_ShearForce,    units["force"],        "force",        "Shear Force"),
        "BendingMoment": (Total_BendingMoment, units["moment"],       "moment",       "Bending Moment"),
        "ShearStress":   (ShearStress,         units["stress"],       "stress",       "Shear Stress"),
        "BendingStress": (BendingStress,       units["stress"],       "stress",       "Bending Stress"),
        "Deflection":    (Deflection,          units["length_small"], "displacement", "Deflection"),
    }
    if result_to_animate not in scalar_map:
        raise ValueError(f"result_to_animate must be one of: {list(scalar_map.keys())}")

    scalar_field, unit_str, result_kind, display_title = scalar_map[result_to_animate]

    if scalar_field is None:
        print(f"  [Warning] {result_to_animate} not available. Using deflection instead.")
        scalar_field, unit_str, result_kind, display_title = (
            Deflection, units["length_small"], "displacement", "Deflection")

    scalar_field = np.asarray(scalar_field, dtype=float)
    if scalar_field.ndim > 1:   # 2D stress -> max |.| per station
        scalar_field = np.max(np.abs(scalar_field), axis=1)
    # Magnitude fields (stress, displacement) are plotted non-negative, matching
    # the static views. Force / moment keep their sign for the diverging map.
    if result_kind in ("stress", "displacement"):
        scalar_field = np.abs(scalar_field)

    print(f"\n  Building {n_frames} animation frames for {display_title}...")
    frames, true_scale, ref_mesh, draw_length, section_dim_max = _build_animation_frames(
        X_Field, Deflection, scalar_field, result_to_animate,
        shape, section_dims, c, b, beam_length, units, n_frames)
    print(f"  Done. Deformation scale: {true_scale:.1f}x  |  Opening viewer...")

    ap = AnimationPlotter(
        frames, result_to_animate, title=display_title, units=unit_str,
        result_kind=result_kind, fps=fps, loop=True, deform_scale=true_scale,
        ref_mesh=ref_mesh, draw_length=draw_length, section_dim_max=section_dim_max)
    ap.build()
    # Route through AnimationPlotter.show() so the timer + GL context are torn
    # down on close (prevents shader corruption when re-opening).
    ap.show(screenshot=_make_screenshot_path(f"animation_{result_to_animate}"))

    # After the interactive viewer closes, offer to save the animation to disk
    # (animated GIF and/or a high-resolution still PNG).
    _animation_export_menu(ap, result_to_animate)