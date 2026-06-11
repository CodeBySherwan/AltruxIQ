import plotly.graph_objs as go
import numpy as np

def draw_beam(length):
    return go.Scatter(
        x=[0, length],
        y=[0, 0],
        mode="lines",
        line=dict(color="purple", width=5),
        showlegend=False
    )

def draw_support(x, support_type):
    if support_type == "pin":
        return go.Scatter(
            x=[x],
            y=[0],
            mode="markers",
            marker=dict(symbol="circle", color="blue", size=15),
            name="Pin Support",  # Legend entry for pin support
            showlegend=True
        )
    elif support_type == "roller":
        return go.Scatter(
            x=[x],
            y=[0],
            mode="markers",
            marker=dict(symbol="circle", color="red", size=15),
            name="Roller Support",  # Legend entry for roller support
            showlegend=True
        )

def draw_big_support(x, support_type):
    if support_type == "pin":
        return go.Scatter(
            x=[x],
            y=[0],
            mode="markers",
            marker=dict(symbol="circle", color="blue", size=25),
            name="Pin Support",  # Legend entry for pin support
            showlegend=True
        )
    elif support_type == "roller":
        return go.Scatter(
            x=[x],
            y=[0],
            mode="markers",
            marker=dict(symbol="circle", color="red", size=25),
            name="Roller Support",  # Legend entry for roller support
            showlegend=True
        )



def draw_point_load(x, magnitude):
    return go.Scatter(
        x=[x, x],
        y=[0, 0.4 * (1 if magnitude > 0 else -1)],
        mode="lines+text+markers",
        marker= dict(size=10,symbol= "arrow-bar-up", angleref="previous"),
        line=dict(color="red", width=4),
        text=[None, f"<b>{abs(magnitude):.3f} N</b>"],
        textposition="top center" if magnitude > 0 else "bottom center",
        showlegend=False,  
        # Legend entry for point load
        name="Point Load"
    )

def draw_udl(x_start, x_end, magnitude):
    traces = []

    y_val = 0.5 * (1 if magnitude > 0 else -1)
    fill_y = 0.5 * (1 if magnitude > 0 else -1)

    traces.append(go.Scatter(
        x=[x_start, x_start],
        y=[0, y_val],
        mode="lines",
        line=dict(color="purple", width=4),
        showlegend=False
    ))
    traces.append(go.Scatter(
        x=[x_end, x_end],
        y=[0, y_val],
        mode="lines",
        line=dict(color="purple", width=4),
        showlegend=False
    ))

    traces.append(go.Scatter(
        x=[x_start, x_end, x_end, x_start, x_start],
        y=[0, 0, fill_y, fill_y, 0],
        fill="toself",
        fillcolor="rgba(128,0,128,0.3)",  # Purple with transparency
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False
    ))

    mid_x = (x_start + x_end) / 2
    traces.append(go.Scatter(
        x=[mid_x],
        y=[0.8 * (1 if magnitude > 0 else -1)],
        mode="text",
        text=[f"<b>{abs(magnitude):.3f} N/m</b>"],
        textposition="top center",
        showlegend=False
    ))

    return traces

import numpy as np
import plotly.graph_objs as go

def draw_moment(x, magnitude):
    """
    Create a simple text-based representation of moment using direction emojis,
    positioned close to the beam.
    
    Parameters:
    -----------
    x : float
        Position of the moment along the beam
    magnitude : float
        Magnitude of the moment where:
        - Negative = CLOCKWISE rotation (⭮)
        - Positive = COUNTERCLOCKWISE rotation (⭯)
    
    Returns:
    --------
    list
        List of plotly traces representing the moment
    """
    traces = []
    
    # Determine direction symbol based on sign
    if magnitude < 0:  # Clockwise
        direction_symbol = "⭮"  # Clockwise arrow emoji
    else:  # Counterclockwise
        direction_symbol = "⭯"  # Counterclockwise arrow emoji
    
    # Add moment symbol trace - positioned closer to the beam
    traces.append(go.Scatter(
        x=[x],
        y=[0],  # Positioned much closer to the beam (y=0)
        mode="text",
        text=direction_symbol,
        textfont=dict(
            size=50,  # Slightly smaller to not overwhelm the diagram
            color="blue",
            family="Arial, sans-serif"
        ),
        showlegend=False
    ))
    
    # Add magnitude label - positioned right next to the symbol
    traces.append(go.Scatter(
        x=[x],
        y=[0.3],  # Positioned just above the symbol
        mode="text",
        text=f"{abs(magnitude):.3f} Nm",
        textfont=dict(
            size=18,
            color="blue",
            family="Arial, sans-serif"
        ),
        showlegend=False
    ))
    
    return traces
def draw_reaction(x, magnitude):
    arrow_tip = 1.2 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, x],
        y=[0, arrow_tip],
        mode="lines+text+markers",
        line=dict(color="red", width=4),
        marker=dict(symbol="triangle-up" if magnitude > 0 else "triangle-down", color="red", size=10),
        text=[None, f"<b>{abs(magnitude):.2f} N</b>"],
        textposition="top center" if magnitude > 0 else "bottom center",
        showlegend=False,
        name="Vertical_R", # Legend entry for vertical reaction
    )

def draw_horizontal_reaction(x, magnitude):
    arrow_tip = x + 1.2 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, arrow_tip],
        y=[0, 0],
        mode="lines+text+markers",
        line=dict(color="orange", width=4),
        marker=dict(symbol="triangle-right" if magnitude > 0 else "triangle-left", color="orange", size=10),
        text=[None, f"<b>{abs(magnitude):.2f} N</b>"],
        textposition="top right" if magnitude > 0 else "top left",  # Adjusted to avoid overlap
        showlegend=False,
        name="Horizontal_R", # Legend entry for horizontal reaction
    )


