"""
main_plotting.py
================
The 2D analysis diagrams (Shear Force, Bending Moment, Deflection, Shear
Stress, Bending Stress) in both Plotly (interactive) and Matplotlib
(static / report) backends.

All visual styling now comes from ``plot_theme`` so every diagram shares one
commercial-grade identity: one palette, one font, consistent grids, datum
lines, critical-point markers, stat sub-headers and a subtle product
watermark.  Public function names and signatures are unchanged.
"""

import numpy as np
import os
import sys
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import matplotlib.gridspec as gridspec

from common.units import get_scale

try:
    from plotting import plot_theme as T
except ImportError:                     # pragma: no cover  (flat import for previews)
    import plot_theme as T

T.register_plotly_theme()
T.apply_matplotlib_theme()

try:
    from plotting.export_helper import present_plotly
except ImportError:                     # pragma: no cover (flat import for previews)
    from export_helper import present_plotly


# --------------------------------------------------------------------------
#  TYPOGRAPHY / NUMBER HELPERS  (kept for backward compatibility)
# --------------------------------------------------------------------------
def format_plotly_sci(val):
    return T.fmt_value(val)


def format_matplot_sci(val):
    return T.fmt_value_mpl(val)


# --------------------------------------------------------------------------
#  UNIT SCALING
# --------------------------------------------------------------------------
# Batch SI->display divisors come from `common.units.get_scale`.
# NOTE: this supersedes the former local `_get_scale`, which computed the
# stress divisor from 'length_small' (off by ~1e9). `get_scale(...).stress`
# now returns the real STRESS divisor (metric 1e6 -> MPa). The destructuring
# pattern `u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)` is
# positional-compatible (namedtuple), so call sites are unchanged.


def find_critical_points(X, Y):
    """Absolute-max location and zero-crossing (contraflexure) abscissae."""
    idx_max = np.argmax(np.abs(Y))
    max_x, max_y = X[idx_max], Y[idx_max]
    contraflexure_x = []
    signs = np.sign(Y)
    for idx in np.where(np.diff(signs))[0]:
        if 5 < idx < len(X) - 5:
            dx, dy = X[idx + 1] - X[idx], Y[idx + 1] - Y[idx]
            if dy != 0:
                contraflexure_x.append(X[idx] - Y[idx] * (dx / dy))
    return max_x, max_y, contraflexure_x


# ==========================================================================
#  SHARED PLOTLY SINGLE-DIAGRAM RENDERER
# ==========================================================================
def _render_single(x, y, key, title, value_unit, length_unit, ytitle, sig=2, name=None):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    accent = T.SERIES[key]["line"]
    fill = T.SERIES[key]["fill"]
    vmax, vmin = float(np.max(y)), float(np.min(y))
    imax, imin = int(np.argmax(y)), int(np.argmin(y))
    x0, x1 = float(x[0]), float(x[-1])

    traces = [
        T.zero_datum(x0, x1),
        go.Scatter(
            x=x, y=y, mode="lines",
            line=dict(color=accent, width=2.6, shape="spline", smoothing=0.4),
            fill="tozeroy", fillcolor=fill, name=T.SERIES[key]["label"],
            hovertemplate=(f"<b>%{{y:.3f}} {value_unit}</b>"
                           f"<br>x = %{{x:.3f}} {length_unit}<extra></extra>"),
        ),
        T.max_marker(x[imax], y[imax], accent, "Maximum", value_unit, length_unit),
        T.max_marker(x[imin], y[imin], accent, "Minimum", value_unit, length_unit),
    ]
    _, _, contra = find_critical_points(x, y)
    nm = T.node_markers(contra, "Zero crossing", length_unit)
    if nm is not None:
        traces.append(nm)

    fig = go.Figure(traces)
    fig.update_layout(T.plotly_layout(
        title=title,
        subtitle=T.stat_subtitle(vmax, vmin, value_unit, sig=sig),
        xtitle=f"Position along Beam ({length_unit})",
        ytitle=ytitle,
    ))
    span = (vmax - vmin) or (abs(vmax) or 1.0)
    fig.update_yaxes(range=[vmin - 0.14 * span, vmax + 0.14 * span])
    fig.update_xaxes(range=[x0 - 0.02 * (x1 - x0), x1 + 0.02 * (x1 - x0)])
    T.add_plotly_watermark(fig)
    present_plotly(fig, name or title)


# ==========================================================================
#  PLOTLY — SINGLE DIAGRAMS
# ==========================================================================
def Plotly_shear_force(X_Field, Total_ShearForce, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    _render_single(X_Field / l_div, Total_ShearForce / f_div, "shear",
                   "Shear Force Diagram", u['force'], u['length'],
                   f"Shear Force ({u['force']})")


def Plotly_Deflection(X_Field, Deflection, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    _render_single(X_Field / l_div, Deflection / ls_div, "deflect",
                   "Deflection Diagram", u['length_small'], u['length'],
                   f"Deflection ({u['length_small']})", sig=3)


def Plotly_ShearStress(X_Field, ShearStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    if len(np.shape(ShearStress)) > 1:
        ShearStress = np.max(np.abs(ShearStress), axis=1)
    _render_single(X_Field / l_div, ShearStress / s_div, "shearstress",
                   "Shear Stress Diagram", u['stress'], u['length'],
                   f"Shear Stress ({u['stress']})")


def Plotly_bending_moment(X_Field, Total_BendingMoment, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    _render_single(X_Field / l_div, Total_BendingMoment / m_div, "moment",
                   "Bending Moment Diagram", u['moment'], u['length'],
                   f"Bending Moment ({u['moment']})")


def Plotly_BendingStress(X_Field, BendingStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    if len(np.shape(BendingStress)) > 1:
        BendingStress = np.max(np.abs(BendingStress), axis=1)
    _render_single(X_Field / l_div, BendingStress / s_div, "bendstress",
                   "Bending Stress Diagram", u['stress'], u['length'],
                   f"Bending Stress ({u['stress']})")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  STEPPED BAR — AXIAL ANALYSIS (Plotly)
#  Same _render_single renderer as shear/moment/stress, just different
#  SERIES keys (defined in plot_theme.SERIES) so colours stay consistent.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def Plotly_AxialForce(X_Field, AxialForce, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    _render_single(X_Field / l_div, AxialForce / f_div, "axial",
                   "Axial Force Diagram", u['force'], u['length'],
                   f"Axial Force ({u['force']})")


def Plotly_AxialDisplacement(X_Field, AxialDisplacement, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    _render_single(X_Field / l_div, AxialDisplacement / ls_div, "axialdispl",
                   "Axial Displacement Diagram", u['length_small'], u['length'],
                   f"Axial Displacement ({u['length_small']})", sig=3)


def Plotly_CombinedStress(X_Field, CombinedStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    if len(np.shape(CombinedStress)) > 1:
        CombinedStress = np.max(np.abs(CombinedStress), axis=1)
    _render_single(X_Field / l_div, CombinedStress / s_div, "combinedstress",
                   "Combined Stress Diagram (Bending + Axial)", u['stress'], u['length'],
                   f"Combined Stress ({u['stress']})")


# ==========================================================================
#  PLOTLY — STACKED / COMBINED
# ==========================================================================
def _stack_axis_titles(fig, n_rows, titles):
    """Style subplot titles to match the theme."""
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=15, family=T.FONT_FAMILY, color=T.INK)
        ann['x'] = 0.0
        ann['xanchor'] = 'left'


def _add_series(fig, row, x, y, key, length_unit, value_unit):
    accent = T.SERIES[key]["line"]
    fill = T.SERIES[key]["fill"]
    fig.add_trace(T.zero_datum(float(x[0]), float(x[-1])), row=row, col=1)
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=accent, width=2.4, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor=fill, name=T.SERIES[key]["label"],
        hovertemplate=(f"<b>%{{y:.3f}} {value_unit}</b>"
                       f"<br>x = %{{x:.3f}} {length_unit}<extra></extra>"),
    ), row=row, col=1)
    imax, imin = int(np.argmax(y)), int(np.argmin(y))
    fig.add_trace(T.max_marker(x[imax], y[imax], accent, "Max", value_unit, length_unit), row=row, col=1)
    fig.add_trace(T.max_marker(x[imin], y[imin], accent, "Min", value_unit, length_unit), row=row, col=1)


def Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
                   plot_type='Both', units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    x = X_Field / l_div
    sf = Total_ShearForce / f_div
    bm = Total_BendingMoment / m_div

    panels = []
    if plot_type in ('SFD', 'Both'):
        panels.append(("shear", sf, f"Shear Force ({u['force']})", u['force'], "Shear Force Diagram"))
    if plot_type in ('BMD', 'Both'):
        panels.append(("moment", bm, f"Bending Moment ({u['moment']})", u['moment'], "Bending Moment Diagram"))

    n = len(panels)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True,
                        vertical_spacing=0.13 if n > 1 else 0.0,
                        subplot_titles=[p[4] for p in panels])
    _stack_axis_titles(fig, n, [p[4] for p in panels])

    for i, (key, y, ylab, vunit, _t) in enumerate(panels, start=1):
        _add_series(fig, i, x, y, key, u['length'], vunit)
        fig.update_yaxes(title=dict(text=ylab), row=i, col=1)
    fig.update_xaxes(title=dict(text=f"Position along Beam ({u['length']})"), row=n, col=1)

    fig.update_layout(
        template="struct_fea", showlegend=False,
        title=dict(text="<b>Internal Force Diagrams</b>", x=0.5, xanchor="center",
                   y=0.975, font=dict(size=T.TITLE_SIZE, color=T.INK)),
        width=880, height=360 * n + 80,
        margin=dict(l=85, r=45, t=110, b=70),
    )
    T.add_plotly_watermark(fig)
    present_plotly(fig, f"Internal_Force_Diagrams_{plot_type}")


def Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length,
                             Deflection=None, ShearStress=None, AxialForce=None,
                             CombinedStress=None, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    step = 5
    x = X_Field[::step] / l_div

    panels = [
        ("shear", Total_ShearForce[::step] / f_div, f"Shear Force ({u['force']})", u['force'], "Shear Force Diagram"),
        ("moment", Total_BendingMoment[::step] / m_div, f"Bending Moment ({u['moment']})", u['moment'], "Bending Moment Diagram"),
    ]
    if Deflection is not None:
        panels.append(("deflect", Deflection[::step] / ls_div,
                       f"Deflection ({u['length_small']})", u['length_small'], "Deflection Diagram"))
    if ShearStress is not None:
        ss = ShearStress
        if len(np.shape(ss)) > 1:
            ss = np.max(np.abs(ss), axis=1)
        panels.append(("shearstress", ss[::step] / s_div,
                       f"Shear Stress ({u['stress']})", u['stress'], "Shear Stress Diagram"))
    if AxialForce is not None:
        panels.append(("axial", AxialForce[::step] / f_div,
                       f"Axial Force ({u['force']})", u['force'], "Axial Force Diagram"))
    if CombinedStress is not None:
        cs = CombinedStress
        if len(np.shape(cs)) > 1:
            cs = np.max(np.abs(cs), axis=1)
        panels.append(("combinedstress", cs[::step] / s_div,
                       f"Combined Stress ({u['stress']})", u['stress'], "Combined Stress Diagram"))

    n = len(panels)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=[p[4] for p in panels])
    _stack_axis_titles(fig, n, [p[4] for p in panels])

    for i, (key, y, ylab, vunit, _t) in enumerate(panels, start=1):
        _add_series(fig, i, x, y, key, u['length'], vunit)
        fig.update_yaxes(title=dict(text=ylab), row=i, col=1)
    fig.update_xaxes(title=dict(text=f"Position along Beam ({u['length']})"), row=n, col=1)

    fig.update_layout(
        template="struct_fea", showlegend=False,
        title=dict(text="<b>Beam Analysis Results</b>", x=0.5, xanchor="center",
                   y=0.985, font=dict(size=T.TITLE_SIZE + 2, color=T.INK)),
        width=920, height=290 * n + 110,
        margin=dict(l=85, r=45, t=110, b=70),
    )
    T.add_plotly_watermark(fig)
    present_plotly(fig, "Beam_Analysis_Results")


# ==========================================================================
#  MATPLOTLIB — SHARED RENDERER
# ==========================================================================
def _render_single_mpl(ax, x, y, key, title, value_unit, length_unit, ylabel, sig=2):
    accent = T.SERIES[key]["line"]
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ax.plot(x, y, color=accent, linewidth=2.4, zorder=3)
    ax.fill_between(x, y, 0, where=(y >= 0), color=accent, alpha=0.14, zorder=1)
    ax.fill_between(x, y, 0, where=(y < 0), color=accent, alpha=0.07, zorder=1)
    T.style_mpl_axes(ax, accent)
    ax.yaxis.set_major_formatter(T.si_tick_formatter())

    vmax, vmin = float(np.max(y)), float(np.min(y))
    imax, imin = int(np.argmax(y)), int(np.argmin(y))
    for xi, yi in ((x[imax], y[imax]), (x[imin], y[imin])):
        ax.plot(xi, yi, marker="D", markersize=7, markerfacecolor=T.CRITICAL,
                markeredgecolor=accent, markeredgewidth=1.4, zorder=5)

    ax.set_title(title, loc="left", pad=20)
    ax.text(0.0, 1.015, T.stat_subtitle(vmax, vmin, value_unit, html=False, sig=sig),
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=T.SUBTITLE_SIZE, color=T.SUBTLE_INK)
    ax.set_xlabel(f"Position along Beam ({length_unit})", labelpad=8)
    ax.set_ylabel(ylabel, labelpad=8)
    span = (vmax - vmin) or (abs(vmax) or 1.0)
    ax.set_ylim(vmin - 0.16 * span, vmax + 0.16 * span)
    ax.margins(x=0.01)


def Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, plot_type='Both', units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    x = X_Field / l_div
    sf = Total_ShearForce / f_div
    bm = Total_BendingMoment / m_div

    panels = []
    if plot_type in ('SFD', 'Both'):
        panels.append(("shear", sf, "Shear Force Diagram", u['force'], f"Shear Force ({u['force']})"))
    if plot_type in ('BMD', 'Both'):
        panels.append(("moment", bm, "Bending Moment Diagram", u['moment'], f"Bending Moment ({u['moment']})"))

    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(11, 4.6 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for ax, (key, y, title, vunit, ylab) in zip(axes, panels):
        _render_single_mpl(ax, x, y, key, title, vunit, u['length'], ylab)
    fig.suptitle("Internal Force Diagrams", fontsize=18, fontweight="bold",
                 color=T.INK, x=0.07, ha="left", y=0.995)
    T.add_mpl_watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.97], h_pad=3.5)
    plt.show()


def Matplot_ShearStress(X_Field, Shear_stress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    y = np.max(np.abs(Shear_stress), axis=1) if len(np.shape(Shear_stress)) > 1 else Shear_stress
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, y / s_div, "shearstress",
                       "Shear Stress Diagram", u['stress'], u['length'],
                       f"Shear Stress ({u['stress']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


def Matplot_BendingStress(X_Field, BendingStress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    y = np.max(np.abs(BendingStress), axis=1) if len(np.shape(BendingStress)) > 1 else BendingStress
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, y / s_div, "bendstress",
                       "Bending Stress Diagram", u['stress'], u['length'],
                       f"Bending Stress ({u['stress']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  STEPPED BAR — AXIAL ANALYSIS (Matplotlib)
#  Same _render_single_mpl renderer as the stress diagrams above.
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def Matplot_AxialForce(X_Field, AxialForce, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, AxialForce / f_div, "axial",
                       "Axial Force Diagram", u['force'], u['length'],
                       f"Axial Force ({u['force']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


def Matplot_AxialDisplacement(X_Field, AxialDisplacement, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, AxialDisplacement / ls_div, "axialdispl",
                       "Axial Displacement Diagram", u['length_small'], u['length'],
                       f"Axial Displacement ({u['length_small']})", sig=3)
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


def Matplot_CombinedStress(X_Field, CombinedStress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    y = np.max(np.abs(CombinedStress), axis=1) if len(np.shape(CombinedStress)) > 1 else CombinedStress
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, y / s_div, "combinedstress",
                       "Combined Stress Diagram", u['stress'], u['length'],
                       f"Combined Stress ({u['stress']})")
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


def Matplot_Deflection(X_Field, Deflection, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _render_single_mpl(ax, X_Field / l_div, Deflection / ls_div, "deflect",
                       "Deflection Diagram", u['length_small'], u['length'],
                       f"Deflection ({u['length_small']})", sig=3)
    T.add_mpl_watermark(fig)
    fig.tight_layout()
    plt.show()


def Matplot_combined(X_Field, Total_ShearForce, Total_BendingMoment,
                     Deflection=None, ShearStress=None, AxialForce=None,
                     CombinedStress=None, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = get_scale(units)
    x = X_Field / l_div

    panels = [
        ("shear", Total_ShearForce / f_div, "Shear Force Diagram", u['force'], f"Shear Force ({u['force']})"),
        ("moment", Total_BendingMoment / m_div, "Bending Moment Diagram", u['moment'], f"Bending Moment ({u['moment']})"),
    ]
    if Deflection is not None:
        panels.append(("deflect", Deflection / ls_div, "Deflection Diagram",
                       u['length_small'], f"Deflection ({u['length_small']})"))
    if ShearStress is not None:
        ss = ShearStress
        if len(np.shape(ss)) > 1:
            ss = np.max(np.abs(ss), axis=1)
        panels.append(("shearstress", ss / s_div, "Shear Stress Diagram",
                       u['stress'], f"Shear Stress ({u['stress']})"))
    if AxialForce is not None:
        panels.append(("axial", AxialForce / f_div, "Axial Force Diagram",
                       u['force'], f"Axial Force ({u['force']})"))
    if CombinedStress is not None:
        cs = CombinedStress
        if len(np.shape(cs)) > 1:
            cs = np.max(np.abs(cs), axis=1)
        panels.append(("combinedstress", cs / s_div, "Combined Stress Diagram",
                       u['stress'], f"Combined Stress ({u['stress']})"))

    n = len(panels)
    fig, axes = plt.subplots(n, 1, figsize=(11.5, 4.3 * n), sharex=True)
    if n == 1:
        axes = [axes]
    for i, (ax, (key, y, title, vunit, ylab)) in enumerate(zip(axes, panels)):
        sig = 3 if key == "deflect" else 2
        _render_single_mpl(ax, x, y, key, title, vunit, u['length'], ylab, sig=sig)
        if i < n - 1:
            ax.set_xlabel("")
    fig.suptitle("Beam Analysis Results", fontsize=19, fontweight="bold",
                 color=T.INK, x=0.07, ha="left", y=0.997)
    T.add_mpl_watermark(fig)
    fig.tight_layout(rect=[0, 0, 1, 0.97], h_pad=4.0)
    plt.show()


# ==========================================================================
#  LOAD FORMATTING (unchanged)
# ==========================================================================
def format_loads_for_plotting(loads_dict):
    formatted_loads = []
    for load in loads_dict.get("pointloads", []):
        pos, Fx, Fy = load
        mag = Fy if abs(Fy) >= abs(Fx) else Fx
        formatted_loads.append(("point_load", pos, mag))
    for udl in loads_dict.get("distributedloads", []):
        start, end, intensity = udl
        formatted_loads.append(("udl", start, end, intensity))
    for mom in loads_dict.get("momentloads", []):
        pos, moment = mom
        formatted_loads.append(("moment", pos, moment))
    for trl in loads_dict.get("triangleloads", []):
        start, end, intensity_start, intensity_end = trl
        formatted_loads.append(("trl", start, end, intensity_start, intensity_end))
    return formatted_loads
