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

def plot_beam_schematic(beam_length, A, B, support_types, loads, units=None):
    """Plots the structural schematic of a simply supported beam with active units scaling."""
    # 1. Setup dynamic unit configurations
    if units is None:
        # Fallback to standard metric defaults if not provided
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
    
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')
    dist_unit = f"{units['force']}/{units['length']}"

    # Scale geometry to active unit system (e.g., meters -> feet)
    scaled_length = beam_length / len_div
    scaled_A = A / len_div
    scaled_B = B / len_div

    # Base structural elements
    traces = [draw_beam(scaled_length)]
    
    for s_type in support_types:
        if s_type == "pin":
            traces.append(draw_support(scaled_A, "pin"))
        elif s_type == "roller":
            traces.append(draw_support(scaled_B, "roller"))
            
    # Process and dynamically scale every load asset
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
        title=f"Beam Schematic ({units['length'].upper()} system)",
        xaxis=dict(title=f"Beam Span ({units['length']})", range=[-0.5, scaled_length + 0.5]),
        yaxis=dict(title="Load Scaling Indicator", range=[-1.5, 1.5], showgrid=False, zeroline=True),
        plot_bgcolor="white"
    )
    fig.show()

def plot_cantilever_beam_schematic(beam_length, loads, title="Cantilever Beam Analysis", units=None):
    """Plots the structural schematic of a cantilever beam with active units scaling."""
    if units is None:
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
        
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')
    moment_div = get_divisor(units, 'moment')
    dist_unit = f"{units['force']}/{units['length']}"

    scaled_length = beam_length / len_div

    # Build layout assets
    traces = [
        draw_beam(scaled_length),
        go.Scatter(
            x=[0], y=[0], mode="markers",
            marker=dict(symbol="line-ns", color="black", size=30, line=dict(width=5)),
            name="Fixed Support", showlegend=True
        )
    ]
    
    # Process and dynamically scale every load asset
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
        title=f"{title} ({units['length'].upper()} system)",
        xaxis=dict(title=f"Beam Span ({units['length']})", range=[-0.2, scaled_length + 0.5]),
        yaxis=dict(title="Load Scaling Indicator", range=[-1.5, 1.5], showgrid=False, zeroline=True),
        plot_bgcolor="white"
    )
    return fig

def plot_reaction_diagram(A, B, reactions, support_types, units=None):
    """Plots the boundary condition reactions extracted from structural equilibrium."""
    if units is None:
        units = {'length': 'm', 'force': 'N', 'moment': 'N·m'}
        
    len_div = get_divisor(units, 'length')
    force_div = get_divisor(units, 'force')

    scaled_A = A / len_div
    scaled_B = B / len_div

    # Simple Supported beam array context mapping
    Va, Vb, Ha = reactions[0], reactions[1], reactions[2]

    # Initialize layout using big supports for reference boundary visibility
    traces = [
        draw_beam(max(scaled_A, scaled_B) * 1.1),
        draw_big_support(scaled_A, "pin"),
        draw_big_support(scaled_B, "roller"),
        draw_reaction(scaled_A, Va / force_div, unit=units['force']),
        draw_reaction(scaled_B, Vb / force_div, unit=units['force']),
        draw_horizontal_reaction(scaled_A, Ha / force_div, unit=units['force'])
    ]
    
    fig = go.Figure(data=traces)
    fig.update_layout(
        title=f"Reaction Forces Diagram ({units['length'].upper()})",
        xaxis=dict(title=f"Beam Coordinates ({units['length']})"),
        yaxis=dict(title="Reaction Indicator Scales", range=[-2, 2], showgrid=False),
        plot_bgcolor="white"
    )
    fig.show()