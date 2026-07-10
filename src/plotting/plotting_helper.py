"""
plotting_helper.py
==================
Drawing primitives for the structural *schematic* (beam, supports, loads,
reactions).  Every element now pulls its colours, weights and fonts from
``plot_theme`` so the schematic matches the analysis diagrams.

Engineering-convention upgrades over the previous version:
  * the beam is a solid structural-ink member (was bright purple)
  * supports use proper symbols — pin triangle, roller triangle on rollers,
    fixed/encastre hatched wall — instead of plain coloured dots
  * loads share one muted palette and consistent arrow weights / labels

All public function names and signatures are unchanged, so this is a
drop-in replacement.
"""

import plotly.graph_objs as go
import numpy as np

try:
    from plotting import plot_theme as T          # package import (real app)
except ImportError:                                  # pragma: no cover
    import plot_theme as T                         # flat import (tests/preview)


# --------------------------------------------------------------------------
#  BEAM MEMBER
# --------------------------------------------------------------------------
def draw_beam(length):
    """The structural member itself — a solid steel-ink line."""
    return go.Scatter(
        x=[0, length], y=[0, 0], mode="lines",
        line=dict(color=T.STRUCTURE, width=6),
        hoverinfo="skip", showlegend=False, name="Beam",
    )


# --------------------------------------------------------------------------
#  SUPPORT SYMBOLS  (drawn with screen-space markers so they stay crisp
#  regardless of the schematic's stretched x/y aspect ratio)
# --------------------------------------------------------------------------
def _ground_hatch(x, half_w=0.16, n=5, y=-0.34):
    """Short diagonal hatch ticks under a support to denote 'ground'."""
    xs, ys = [], []
    for i in range(n):
        x0 = x - half_w + (2 * half_w) * i / (n - 1)
        xs += [x0, x0 - 0.07, None]
        ys += [y, y - 0.13, None]
    return go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color=T.SUPPORT, width=1.4),
        hoverinfo="skip", showlegend=False,
    )


def _support_traces(x, support_type, size, show_legend, legend_name):
    """Build the marker + ground line + (roller wheels) for a support."""
    traces = []
    # Triangle body, apex at the node (y=0)
    traces.append(go.Scatter(
        x=[x], y=[0], mode="markers",
        marker=dict(symbol="triangle-down", size=size, color="white",
                    line=dict(width=2.2, color=T.SUPPORT)),
        cliponaxis=False,
        name=legend_name, showlegend=show_legend, legendgroup=legend_name,
        hovertemplate=f"<b>{legend_name}</b><extra></extra>",
    ))
    # Triangle is drawn just below the node so its apex meets the beam:
    traces[-1].update(y=[-0.02])

    if support_type == "roller":
        # rollers: a row of small circles + ground line
        traces.append(go.Scatter(
            x=[x], y=[-0.30], mode="markers",
            marker=dict(symbol="line-ew", size=size * 0.9,
                        line=dict(width=2, color=T.SUPPORT)),
            hoverinfo="skip", showlegend=False, legendgroup=legend_name,
        ))
        traces.append(go.Scatter(
            x=[x - 0.07, x + 0.07], y=[-0.40, -0.40], mode="markers",
            marker=dict(symbol="circle", size=size * 0.28,
                        color="white", line=dict(width=1.6, color=T.SUPPORT)),
            hoverinfo="skip", showlegend=False, legendgroup=legend_name,
        ))
    else:  # pin / hinge -> ground hatch
        traces.append(_ground_hatch(x))
    return traces


def draw_support(x, support_type):
    """Standard pin or roller support symbol."""
    legend = "Pin Support" if support_type == "pin" else "Roller Support"
    return _multi(_support_traces(x, support_type, 22, True, legend))


def draw_big_support(x, support_type):
    """Larger pin/roller symbol (used where extra emphasis is wanted)."""
    legend = "Pin Support" if support_type == "pin" else "Roller Support"
    return _multi(_support_traces(x, support_type, 30, True, legend))


def draw_fixed_support(x, name="Fixed Support", height=0.55):
    """Encastre / fixed wall: vertical face with diagonal hatching."""
    traces = []
    # Vertical wall face
    traces.append(go.Scatter(
        x=[x, x], y=[-height, height], mode="lines",
        line=dict(color=T.SUPPORT, width=3),
        name=name, showlegend=True, legendgroup=name,
        hovertemplate=f"<b>{name}</b><extra></extra>",
    ))
    # Diagonal hatch marks on the support side
    side = -1 if x <= 0 else 1   # hatch points away from the span
    n = 6
    xs, ys = [], []
    for i in range(n):
        yy = -height + (2 * height) * i / (n - 1)
        xs += [x, x + side * 0.14, None]
        ys += [yy, yy + 0.16, None]
    traces.append(go.Scatter(
        x=xs, y=ys, mode="lines",
        line=dict(color=T.SUPPORT, width=1.3),
        hoverinfo="skip", showlegend=False, legendgroup=name,
    ))
    return _multi(traces)


# Helper: bundle several traces into something the caller can `.append()`.
# A go.Scatter is returned for single traces; a list for multiples. beam_plot
# appends/extends, so we expose a tiny wrapper that behaves for both paths.
class _MultiTrace(list):
    """A list of traces that also tolerates being passed to fig.add_trace style code."""
    pass


def _multi(traces):
    return _MultiTrace(traces)


# --------------------------------------------------------------------------
#  POINT LOAD
# --------------------------------------------------------------------------
def draw_point_load(x, magnitude, level=0, unit="N"):
    """
    Vertical point-load arrow.  Downward (negative) below the beam in red,
    upward (positive) above the beam in green; stacks by ``level``.
    """
    arrow_length = 0.42
    if magnitude < 0:
        y_start = -level * arrow_length
        y_end = -(level + 1) * arrow_length
        sym, text_pos, color = "triangle-down", "bottom center", T.LOAD_POINT
    else:
        y_start = level * arrow_length
        y_end = (level + 1) * arrow_length
        sym, text_pos, color = "triangle-up", "top center", T.LOAD_POINT_UP

    return go.Scatter(
        x=[x, x], y=[y_start, y_end], mode="lines+text+markers",
        line=dict(color=color, width=3),
        marker=dict(symbol=sym, color=color, size=[0, 13]),
        text=[None, f"<b>{abs(magnitude):,.2f} {unit}</b>"],
        textposition=text_pos, textfont=dict(color=T.INK, size=12),
        showlegend=False, name="Point Load",
        hovertemplate=(f"<b>Point Load</b><br>Location: {x:.3f}"
                       f"<br>Magnitude: {magnitude:,.2f} {unit}<extra></extra>"),
    )


# --------------------------------------------------------------------------
#  MOMENT LOAD
# --------------------------------------------------------------------------
def draw_moment_load(x, magnitude, unit="N\u00b7m"):
    theta = np.linspace(0, np.pi, 60)
    radius = 0.32
    x_arc = x + radius * np.cos(theta)
    y_arc = radius * np.sin(theta)
    if magnitude < 0:
        x_arc = x_arc[::-1]

    color = T.LOAD_MOMENT
    return [
        go.Scatter(x=x_arc, y=y_arc, mode="lines",
                   line=dict(color=color, width=3), hoverinfo="skip",
                   showlegend=False),
        go.Scatter(
            x=[x_arc[-1]], y=[y_arc[-1]], mode="markers+text",
            marker=dict(symbol="triangle-right" if magnitude > 0 else "triangle-left",
                        color=color, size=12),
            text=[f"<b>{abs(magnitude):,.2f} {unit}</b>"],
            textposition="top center", textfont=dict(color=T.INK, size=12),
            showlegend=False,
            hovertemplate=(f"<b>Moment</b><br>Location: {x:.3f}"
                           f"<br>Magnitude: {magnitude:,.2f} {unit}<extra></extra>"),
        ),
    ]


# --------------------------------------------------------------------------
#  DISTRIBUTED (UNIFORM / TRAPEZOIDAL) LOAD
# --------------------------------------------------------------------------
def draw_distributed_load(start, end, intensity_start, intensity_end,
                          max_intensity, unit="N/m"):
    if max_intensity == 0:
        max_intensity = 1
    color = T.LOAD_DIST
    y_start = 0.55 * (1 if intensity_start > 0 else -1) * (abs(intensity_start) / max_intensity)
    y_end   = 0.55 * (1 if intensity_end   > 0 else -1) * (abs(intensity_end)   / max_intensity)

    traces = [
        # filled load block
        go.Scatter(
            x=[start, start, end, end, start],
            y=[0, y_start, y_end, 0, 0],
            mode="lines", line=dict(color=color, width=2),
            fill="toself", fillcolor=T.SERIES["shear"]["fill"],
            hoverinfo="skip", showlegend=False,
        ),
    ]
    # evenly-spaced direction arrows across the span (commercial look)
    n_arrows = max(2, int(round((end - start) / 0.6)) + 1)
    xs = np.linspace(start, end, n_arrows)
    for i, xa in enumerate(xs):
        frac = 0 if (end - start) == 0 else (xa - start) / (end - start)
        ytip = y_start + (y_end - y_start) * frac
        up = ytip >= 0
        traces.append(go.Scatter(
            x=[xa, xa], y=[ytip, 0], mode="lines+markers",
            line=dict(color=color, width=1.6),
            marker=dict(symbol="triangle-down" if up else "triangle-up",
                        color=color, size=[0, 9]),
            hoverinfo="skip", showlegend=False,
        ))
    # intensity labels at the ends
    if intensity_start != 0:
        traces.append(go.Scatter(
            x=[start], y=[y_start * 1.22], mode="text",
            text=[f"<b>{T.fmt_load(abs(intensity_start))} {unit}</b>"],
            textposition="top center" if intensity_start > 0 else "bottom center",
            textfont=dict(color=T.INK, size=12), hoverinfo="skip", showlegend=False,
        ))
    if intensity_end != 0 and abs(start - end) > 0.01:
        traces.append(go.Scatter(
            x=[end], y=[y_end * 1.22], mode="text",
            text=[f"<b>{T.fmt_load(abs(intensity_end))} {unit}</b>"],
            textposition="top center" if intensity_end > 0 else "bottom center",
            textfont=dict(color=T.INK, size=12), hoverinfo="skip", showlegend=False,
        ))
    return traces


# --------------------------------------------------------------------------
#  TRIANGULAR LOAD
# --------------------------------------------------------------------------
def draw_triangle_load(x_start, x_end, magnitude, unit="N/m"):
    color = T.LOAD_DIST
    peak = 0.55 * (1 if magnitude > 0 else -1)
    traces = [
        go.Scatter(
            x=[x_start, x_end, x_start], y=[0, 0, peak],
            mode="lines", fill="toself",
            fillcolor=T.SERIES["shear"]["fill"],
            line=dict(color=color, width=2), hoverinfo="skip", showlegend=False,
        ),
        go.Scatter(
            x=[(x_start + x_end) / 2], y=[peak * 1.35], mode="text",
            text=[f"<b>{T.fmt_load(abs(magnitude))} {unit}</b>"],
            textposition="top center", textfont=dict(color=T.INK, size=12),
            hoverinfo="skip", showlegend=False,
        ),
    ]
    return traces


# --------------------------------------------------------------------------
#  REACTIONS
# --------------------------------------------------------------------------
def draw_reaction(x, magnitude, unit="N"):
    """Vertical support reaction arrow."""
    color = T.REACTION_V
    tip = 1.15 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, x], y=[0, tip], mode="lines+text+markers",
        line=dict(color=color, width=3.5),
        marker=dict(symbol="triangle-up" if magnitude > 0 else "triangle-down",
                    color=color, size=[0, 12]),
        text=[None, f"<b>{abs(magnitude):,.2f} {unit}</b>"],
        textposition="top center" if magnitude > 0 else "bottom center",
        textfont=dict(color=T.INK, size=12),
        showlegend=False, name="Vertical Reaction",
        hovertemplate=(f"<b>Vertical Reaction</b><br>x = {x:.3f}"
                       f"<br>%{{customdata}}<extra></extra>"),
        customdata=[f"{magnitude:,.2f} {unit}", f"{magnitude:,.2f} {unit}"],
    )


def draw_horizontal_reaction(x, magnitude, unit="N"):
    """Horizontal support reaction arrow."""
    color = T.REACTION_H
    tip = x + 1.15 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, tip], y=[0, 0], mode="lines+text+markers",
        line=dict(color=color, width=3.5),
        marker=dict(symbol="triangle-right" if magnitude > 0 else "triangle-left",
                    color=color, size=[0, 12]),
        text=[None, f"<b>{abs(magnitude):,.2f} {unit}</b>"],
        textposition="middle right" if magnitude > 0 else "middle left",
        textfont=dict(color=T.INK, size=12),
        showlegend=False, name="Horizontal Reaction",
        hovertemplate=(f"<b>Horizontal Reaction</b><br>x = {x:.3f}"
                       f"<br>{magnitude:,.2f} {unit}<extra></extra>"),
    )
