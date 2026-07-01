import os
import sys

import plotly.graph_objs as go
import numpy as np
from common.units import get_divisor # trusted unit divisor engine
from common.units import default_units  # canonical default units dict
from plotting.plotting_helper import (
    draw_beam, draw_support, draw_big_support, draw_fixed_support,
    draw_point_load, draw_distributed_load, draw_moment_load,
    draw_triangle_load, draw_reaction, draw_horizontal_reaction,
)
from plotting import plot_theme as T
try:
    from plotting.export_helper import present_plotly
except Exception:                       # pragma: no cover
    from export_helper import present_plotly


def _add(traces, item):
    """Append a single trace or extend with a list of traces — keeps the
    schematic builder agnostic to whether a helper returns one or many."""
    if isinstance(item, (list, tuple)):
        traces.extend(item)
    else:
        traces.append(item)


def plot_beam_schematic(beam_type, beam_length, A, B, continuous_supports, loads, units=None):
    """
    Structural schematic, drawn dynamically from the beam classification.
    Handles Simple, Overhanging, Cantilever, Fixed-Fixed, Propped, Continuous/Custom.
    """
    if units is None:
        units = default_units()

    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')
    dist_unit = f"{units['force']}/{units['length']}"

    scaled_length = beam_length / len_div
    traces = [draw_beam(scaled_length)]

    # --- Supports by classification ---
    if beam_type in ("Simple", "Overhanging Beam"):
        _add(traces, draw_support(A / len_div, "pin"))
        _add(traces, draw_support(B / len_div, "roller"))
    elif beam_type == "Cantilever":
        _add(traces, draw_fixed_support(0.0))
    elif beam_type == "Fixed-Fixed":
        _add(traces, draw_fixed_support(0.0, "Left Fixed Support"))
        _add(traces, draw_fixed_support(scaled_length, "Right Fixed Support"))
    elif beam_type == "Propped":
        _add(traces, draw_fixed_support(0.0, "Fixed Support"))
        _add(traces, draw_support(scaled_length, "roller"))
    elif beam_type in ("Continuous", "Custom"):
        for s in continuous_supports:
            dof = s.get("dof", (0, 1, 0))
            if s.get("ky") is not None or s.get("kx") is not None:
                is_vert = s.get("ky") is not None
                label = "V-Spring" if is_vert else "H-Spring"
                _add(traces, go.Scatter(
                    x=[s["pos"] / len_div], y=[0], mode="markers+text",
                    marker=dict(symbol="bowtie", size=18, color=T.REACTION_H,
                                line=dict(width=1.5, color=T.SUPPORT)),
                    text=[label], textfont=dict(color=T.SUBTLE_INK, size=11),
                    textposition="bottom center" if is_vert else "top center",
                    name=label, showlegend=False, hoverinfo="text",
                ))
            elif tuple(dof) == (1, 1, 1):
                _add(traces, draw_fixed_support(s["pos"] / len_div, "Custom Fixed"))
            else:
                s_type = "pin" if tuple(dof) == (1, 1, 0) else "roller"
                _add(traces, draw_support(s["pos"] / len_div, s_type))

    # --- Loads ---
    for load in loads:
        l_type = load[0]
        if l_type == "point_load":
            pos, mag = load[1], load[2]
            _add(traces, draw_point_load(pos / len_div, mag / force_div, unit=units['force']))
        elif l_type == "udl":
            start, end, intensity = load[1], load[2], load[3]
            max_intensity = max(abs(intensity), 1e-9)
            _add(traces, draw_distributed_load(
                start / len_div, end / len_div, intensity / force_div,
                intensity / force_div, max_intensity / force_div, unit=dist_unit))
        elif l_type == "moment":
            pos, moment = load[1], load[2]
            _add(traces, draw_moment_load(pos / len_div, moment / moment_div, unit=units['moment']))
        elif l_type == "trl":
            start, end, i_start, i_end = load[1], load[2], load[3], load[4]
            max_i = max(abs(i_start), abs(i_end), 1e-9)
            _add(traces, draw_distributed_load(
                start / len_div, end / len_div, i_start / force_div,
                i_end / force_div, max_i / force_div, unit=dist_unit))

    fig = go.Figure(data=traces)
    fig.update_layout(T.plotly_layout(
        title=f"{beam_type} Beam — Structural Schematic",
        subtitle=f"Span {scaled_length:,.3g} {units['length']}  ·  {units['length'].upper()} unit system",
        xtitle=f"Span ({units['length']})",
        width=920, height=460, schematic=True,
    ))
    fig.update_xaxes(range=[-0.6, scaled_length + 0.6])
    fig.update_yaxes(range=[-1.7, 1.7])
    T.add_plotly_watermark(fig)
    present_plotly(fig, "Beam_Schematic")


def plot_reaction_diagram(reactions, units=None):
    """
    Boundary reactions from structural equilibrium — works for any
    determinate or indeterminate support configuration.
    """
    if units is None:
        units = default_units()

    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')

    max_pos = max([r["pos"] for r in reactions]) if reactions else 1.0
    scaled_length = (max_pos / len_div) if max_pos > 0 else 1.0

    traces = [draw_beam(scaled_length)]

    # Mark support nodes for context
    for r in reactions:
        _add(traces, go.Scatter(
            x=[r["pos"] / len_div], y=[0], mode="markers",
            marker=dict(symbol="triangle-down", size=20, color="white",
                        line=dict(width=2.2, color=T.SUPPORT)),
            hoverinfo="skip", showlegend=False, cliponaxis=False))

    for r in reactions:
        pos = r["pos"] / len_div
        Fy = r["Fy"] / force_div
        Fx = r["Fx"] / force_div
        M = r["M"] / moment_div
        if abs(Fy) > 1e-6:
            _add(traces, draw_reaction(pos, Fy, unit=units['force']))
        if abs(Fx) > 1e-6:
            _add(traces, draw_horizontal_reaction(pos, Fx, unit=units['force']))
        if abs(M) > 1e-6:
            _add(traces, draw_moment_load(pos, M, unit=units['moment']))

    fig = go.Figure(data=traces)
    fig.update_layout(T.plotly_layout(
        title="Support Reactions",
        subtitle="Equilibrium reactions at each boundary condition",
        xtitle=f"Beam Coordinate ({units['length']})",
        width=920, height=460, schematic=True,
    ))
    fig.update_xaxes(range=[-0.8, scaled_length + 0.8])
    fig.update_yaxes(range=[-1.9, 1.9])
    T.add_plotly_watermark(fig)
    present_plotly(fig, "Reaction_Diagram")
