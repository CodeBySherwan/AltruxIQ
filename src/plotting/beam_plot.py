import os
import sys
# pyrefly: igno
# 1. Get the directory of cli.py (ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent directory (src folder)
src_dir = os.path.dirname(current_dir)
# 3. Add the src folder to Python's search path if it's not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import plotly.graph_objs as go
import numpy as np
from ui.Menus import get_divisor  # Grab our trusted unit divisor engine
from plotting.plotting_helper import (
    draw_beam, draw_support, draw_big_support, draw_point_load,
    draw_distributed_load, draw_moment_load, draw_triangle_load,
    draw_reaction, draw_horizontal_reaction
)

def plot_beam_schematic(beam_type, beam_length, A, B, continuous_supports, loads, units=None):
    """
    Plots the structural schematic dynamically based on the beam classification.
    Handles Simple, Cantilever, Fixed-Fixed, Propped, and Continuous beams.
    """
    if units is None:
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
    
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')
    dist_unit = f"{units['force']}/{units['length']}"

    scaled_length = beam_length / len_div

    # Base structural elements
    traces = [draw_beam(scaled_length)]
    
    # Helper to draw Fixed walls
    def draw_fixed_support(x_pos, name="Fixed Support"):
        return go.Scatter(
            x=[x_pos], y=[0], mode="markers",
            marker=dict(symbol="line-ns", color="black", size=30, line=dict(width=5)),
            name=name, showlegend=True
        )

    # --- Draw Supports based on Classification ---
    if beam_type == "Simple":
        traces.append(draw_support(A / len_div, "pin"))
        traces.append(draw_support(B / len_div, "roller"))
    if beam_type == "Overhanging Beam":
        traces.append(draw_support(A / len_div, "pin"))
        traces.append(draw_support(B / len_div, "roller"))
    elif beam_type == "Cantilever":
        traces.append(draw_fixed_support(0.0))
    elif beam_type == "Fixed-Fixed":
        traces.append(draw_fixed_support(0.0, "Left Fixed Support"))
        traces.append(draw_fixed_support(scaled_length, "Right Fixed Support"))
    elif beam_type == "Propped":
        traces.append(draw_fixed_support(0.0, "Fixed Support"))
        traces.append(draw_support(scaled_length, "roller"))
    elif beam_type == "Continuous":
        for s in continuous_supports:
            dof = s.get("dof", (0, 1, 0))
            # Tuple matching: (1,1,0) is pin, (0,1,0) is roller
            s_type = "pin" if tuple(dof) == (1, 1, 0) else "roller"
            traces.append(draw_support(s["pos"] / len_div, s_type))
            
    # --- Process and scale every load asset ---
    for load in loads:
        l_type = load[0]
        if l_type == "point_load":
            pos, mag = load[1], load[2]
            traces.append(draw_point_load(pos / len_div, mag / force_div, unit=units['force']))
        elif l_type == "udl":
            start, end, intensity = load[1], load[2], load[3]
            max_intensity = max(abs(intensity), 1e-9)
            traces.extend(draw_distributed_load(
                start / len_div, end / len_div, intensity / force_div, intensity / force_div, 
                max_intensity / force_div, unit=dist_unit
            ))
        elif l_type == "moment":
            pos, moment = load[1], load[2]
            traces.extend(draw_moment_load(pos / len_div, moment / moment_div, unit=units['moment']))
        elif l_type == "trl":
            start, end, i_start, i_end = load[1], load[2], load[3], load[4]
            max_i = max(abs(i_start), abs(i_end), 1e-9)
            traces.extend(draw_distributed_load(
                start / len_div, end / len_div, i_start / force_div, i_end / force_div, 
                max_i / force_div, unit=dist_unit
            ))
            
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"{beam_type} Beam Schematic ({units['length'].upper()} system)",
        xaxis=dict(title=f"Beam Span ({units['length']})", range=[-0.5, scaled_length + 0.5]),
        yaxis=dict(title="Load Scaling Indicator", range=[-1.5, 1.5], showgrid=False, zeroline=True),
        plot_bgcolor="white"
    )
    fig.show()

def plot_reaction_diagram(reactions, units=None):
    """
    Plots the boundary condition reactions extracted from structural equilibrium.
    Compatible with any indeterminate or determinate support configuration.
    """
    if units is None:
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
        
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')

    # Determine beam span from reaction coordinates for the reference line
    max_pos = max([r["pos"] for r in reactions]) if reactions else 1.0
    scaled_length = (max_pos / len_div) * 1.1 if max_pos > 0 else 1.0

    # Initialize layout with the base beam
    traces = [draw_beam(scaled_length)]
    
    # Iterate through the unified list-of-dicts Reaction structure
    for r in reactions:
        pos = r["pos"] / len_div
        Fy = r["Fy"] / force_div
        Fx = r["Fx"] / force_div
        M = r["M"] / moment_div
        
        # Plot markers depending on active constraints at this position
        if abs(Fy) > 1e-6:
            traces.append(draw_reaction(pos, Fy, unit=units['force']))
        if abs(Fx) > 1e-6:
            traces.append(draw_horizontal_reaction(pos, Fx, unit=units['force']))
        if abs(M) > 1e-6:
            traces.extend(draw_moment_load(pos, M, unit=units['moment']))
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"Reaction Forces Diagram ({units['length'].upper()})",
        xaxis=dict(title=f"Beam Coordinates ({units['length']})"),
        yaxis=dict(title="Reaction Indicator Scales", range=[-2, 2], showgrid=False, zeroline=True),
        plot_bgcolor="white"
    )
    fig.show()