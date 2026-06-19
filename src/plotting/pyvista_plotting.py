"""
pyvista_plotting.py
===================
Commercial-grade 3D FEA visualisations for AltruxIQ.
"""

import os
import sys
import datetime
import numpy as np

try:
    import vtk
except ImportError:
    vtk = None

try:
    import pyvista as pv
except ImportError:
    raise ImportError("PyVista is not installed. Run: pip install pyvista")

# ---------------------------------------------------------------------------
# PATH INJECTION
# ---------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir     = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from ui.Menus import get_divisor

# ---------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------------------------
_FEA_CMAP       = "turbo"             
_N_COLORS       = 15                  
_BG_COLOR       = "white"
_EDGE_COLOR     = "black"
_BEAM_COLOR     = "#A0A0A0"
_SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "screenshots")

COLOR_MAX        = "red"
COLOR_MIN        = "blue"
COLOR_PROBE      = "yellow"
COLOR_PIN        = "lime"

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

def _build_beam_mesh(
    X_Field: np.ndarray, scalar_field: np.ndarray, shape: str,
    section_dims: dict, c: float, b: float, scalar_name: str
) -> pv.PolyData:
    polygon = _build_cross_section_polygon(shape, section_dims, c, b)
    n_pts = len(polygon)
    n_x = len(X_Field)
    pts = np.zeros((n_x * n_pts, 3))
    scalar_vals = np.zeros(n_x * n_pts)
    for i, x in enumerate(X_Field):
        start = i * n_pts
        end = start + n_pts
        pts[start:end, 0] = x
        pts[start:end, 1] = polygon[:, 0]
        pts[start:end, 2] = polygon[:, 1]
        scalar_vals[start:end] = scalar_field[i]
    faces = []
    for i in range(n_x - 1):
        base_current = i * n_pts
        base_next = (i + 1) * n_pts
        for j in range(n_pts):
            j_next = (j + 1) % n_pts
            faces.extend([4, base_current + j, base_next + j,
                          base_next + j_next, base_current + j_next])
    faces.extend([n_pts] + [j for j in range(n_pts)])
    faces.extend([n_pts] + [(n_x - 1) * n_pts + j for j in range(n_pts)])
    mesh = pv.PolyData(pts, np.array(faces, dtype=int))
    mesh.point_data[scalar_name] = scalar_vals
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
        f"AltruxIQ : Structural Analysis Result\n"
        f"Result: {title}\n"
        f"Subcase - Static Loads, Step 1\n"
        f"Min: {min_val:.3f}, Max: {max_val:.3f}, Units = {units}"
    )
    plotter.add_text(text_block, position="upper_left", font_size=10, color="black", font="arial")

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
# ProbingPlotter  (Fully Optimized Commercial Core)
# ===========================================================================

class ProbingPlotter:
    COLOR_MAX   = COLOR_MAX
    COLOR_MIN   = COLOR_MIN
    COLOR_PROBE = COLOR_PROBE
    COLOR_PIN   = COLOR_PIN

    _CMAP_BY_KIND = {
        "stress":       _FEA_CMAP,
        "force":        "coolwarm",
        "moment":       "coolwarm",
        "displacement": "viridis",
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
        self._add_mesh()
        self._add_metadata_overlay()
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
        sargs = dict(
            title=f"{self.title}\n ", title_font_size=14, label_font_size=12,
            shadow=False, n_labels=_N_COLORS + 1, fmt="%.3f", font_family="arial",
            color="black", position_x=0.03, position_y=0.05, height=0.70, width=0.06, vertical=True,
        )
        self.mesh_actor = self.plotter.add_mesh(
            self.mesh, scalars=self.scalars_name, cmap=self._cmap(), n_colors=_N_COLORS,
            show_edges=True, edge_color=_EDGE_COLOR, line_width=1.5,
            ambient=0.6, diffuse=0.4, specular=0.0, scalar_bar_args=sargs,
            pickable=True, render_points_as_spheres=False, point_size=1,
        )

    def _add_metadata_overlay(self):
        scalars = self.mesh.point_data[self.scalars_name]
        text_block = (
            f"AltruxIQ : Structural Analysis Result\n"
            f"Result: {self.title}\n"
            f"Subcase - {self.step_info}\n"
            f"Min: {float(np.min(scalars)):.3f}, Max: {float(np.max(scalars)):.3f}, Units = {self.units}"
        )
        if self.metadata_subtitle: text_block += f"\n{self.metadata_subtitle}"
        self.metadata_actor = self.plotter.add_text(
            text_block, position="upper_left", font_size=10, color="black", font="arial"
        )

    def _add_view_title(self):
        banner = f"{self.title}  —  {self.step_info}"
        self.view_title_actor = self.plotter.add_text(
            banner, position=(0.30, 0.94), font_size=14, color="#1B2631", font="arial", shadow=True
        )

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

    def _add_probe_system(self):
        # OPTIMIZED: Moved to bottom center and added a VTK dynamic background panel
        self.probe_text_actor = self.plotter.add_text(
            " Hover to probe... ", position=(0.35, 0.02), font_size=12, color="black", font="arial"
        )
        
        # Tap into underlying VTK property to add a clean, solid UI box behind the text
        try:
            prop = self.probe_text_actor.GetTextProperty()
            prop.SetBackgroundColor(1.0, 1.0, 0.8) # Light yellow
            prop.SetBackgroundOpacity(0.9)
            prop.SetFrame(True)
            prop.SetFrameColor(0.2, 0.2, 0.2)
            prop.SetFrameWidth(2)
        except AttributeError:
            pass

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
            pointa=(0.40, 0.12), pointb=(0.60, 0.12), style="modern", title_height=0.018, color="#1B2631", event_type="end"
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
                
            text_block = (
                f"AltruxIQ : Structural Analysis Result\n"
                f"Result: {self.title}\n"
                f"Subcase - {self.step_info}\n"
                f"Min: {float(np.min(scalars)):.3f}, Max: {float(np.max(scalars)):.3f}, Units = {self.units}"
            )
            if self.metadata_subtitle: 
                text_block += f"\n{self.metadata_subtitle}"
                
            self.metadata_actor = self.plotter.add_text(
                text_block, position="upper_left", font_size=10, color="black", font="arial"
            )
            
        self.plotter.render()
    def _on_reset_view(self, value=False):
        self.plotter.reset_camera()
        self.plotter.render()

    def _set_view(self, view_name):
        self.plotter.view_isometric()
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
            f" CONTROLS\n ─────────────────\n"
            f" Hover : Probe value\n"
            f" Click : Pin measurement\n"
            f" r     : Reset view\n"
            f" s / w : Surface / Wireframe\n"
            f" f     : Fly to cursor\n"
            f" ─────────────────\n"
            f" 📌 Pinned Points: {n_pins} "
        )
        
        if getattr(self, "instruction_actor", None) is not None:
            try:
                self.plotter.remove_actor(self.instruction_actor)
            except Exception:
                pass

        self.instruction_actor = self.plotter.add_text(
            text, position="lower_right", font_size=9, color="black", font="arial"
        )
        
        try:
            prop = self.instruction_actor.GetTextProperty()
            prop.SetBackgroundColor(0.96, 0.96, 0.96)
            prop.SetBackgroundOpacity(0.95)
            prop.SetFrame(True)
            prop.SetFrameColor(0.6, 0.6, 0.6)
            prop.SetFrameWidth(1)
        except AttributeError:
            pass

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
        except Exception: pass

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
                self.probe_text_actor.SetInput(f" X: {world_pos[0]:+.4f}  Y: {world_pos[1]:+.4f}  Z: {world_pos[2]:+.4f} \n {self.title}: {scalar_val:.4f} {self.units} ")
                self.cursor_actor.SetPosition(world_pos)
                self.cursor_actor.VisibilityOn()
            else: self._hide_cursor()
        else: self._hide_cursor()
        self.plotter.render()

    def _hide_cursor(self):
        try:
            self.probe_text_actor.SetInput(" Hover to probe... ")
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
    units = units or {"length": "m", "force": "N", "moment": "N·m"}
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
    units = units or {"length": "m", "force": "N"}
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
    units = units or {"length": "m", "moment": "N·m"}
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
    units = units or {"length": "m", "stress": "MPa"}
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
    units = units or {"length": "m", "stress": "MPa"}
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
    units = units or {"length": "m", "length_small": "mm"}
    l_div, ls_div = get_divisor(units, "length"), get_divisor(units, "length_small")
    defl_full = Deflection / ls_div
    X, defl = _downsample_for_visuals(X_Field / l_div, defl_full, target_fraction=0.1)
    max_defl = float(np.max(np.abs(defl_full)))
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

    pl, pp = _build_fea_plotter(mesh, "Deflection", title=f"Displacement - Nodal Magnitude (Scale: x{visual_scale:.1f})", units=units['length_small'], result_kind="displacement")
    ref_mesh = _build_beam_mesh(X, np.zeros(len(X)), shape, section_dims, c/l_div, b/l_div, "Ref")
    pl.add_mesh(ref_mesh, color="white", opacity=0.1, show_edges=True, edge_color="#D3D3D3", pickable=False)

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