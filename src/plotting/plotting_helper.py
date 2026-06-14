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



def draw_point_load(x, magnitude, level=0):
    """
    Draws a point load arrow. 
    Positive loads (upward) are drawn above the beam.
    Negative loads (downward) are drawn under the beam in red.
    They stack vertically end-to-end if multiple exist at the same x.
    """
    arrow_length = 1.0  # Defines how long the arrow body is
    
    if magnitude < 0: 
        # Negative load: Under the beam, pointing DOWN, colored Red
        y_start = -level * arrow_length           # Tail of the arrow
        y_end = -(level + 1) * arrow_length       # Head of the arrow
        sym = "triangle-down"
        text_pos = "bottom center"
        color = "red"
    else: 
        # Positive load: Above the beam, pointing UP, colored Green
        y_start = level * arrow_length            # Tail of the arrow
        y_end = (level + 1) * arrow_length        # Head of the arrow
        sym = "triangle-up"
        text_pos = "top center"
        color = "green"
        
    return go.Scatter(
        x=[x, x],
        y=[y_start, y_end],
        mode="lines+text+markers",
        line=dict(color=color, width=3),
        # size=[0, 15] hides the marker at y_start (tail) and shows it at y_end (head)
        marker=dict(symbol=sym, color=color, size=[0, 15]),
        # Text is placed only at the head of the arrow
        text=[None, f"<b>{abs(magnitude):.2f} N</b>"], 
        textposition=text_pos,
        showlegend=False,
        name="Point Load",
        hovertemplate=f"<b>Point Load</b><br>Location: {x} m<br>Magnitude: {magnitude:.2f} N<extra></extra>"
    )

def draw_moment(x, magnitude, level=0):
    """Draws a moment arc, expanding the radius outward for overlapping moments."""
    traces = []
    # Expand the radius outward for each additional moment at this location
    radius = 0.4 + (level * 0.3)
    
    # Draw arc (semi-circle above the beam)
    theta = np.linspace(0, np.pi, 30)
    x_arc = x + radius * np.cos(theta)
    y_arc = radius * np.sin(theta)
    
    # Arc line
    traces.append(go.Scatter(
        x=x_arc, y=y_arc, mode="lines",
        line=dict(color="blue", width=2),
        showlegend=False,
        hoverinfo="skip"
    ))
    
    # Arrowhead placement (left side for positive, right side for negative)
    arrow_x = (x - radius) if magnitude > 0 else (x + radius)
    traces.append(go.Scatter(
        x=[arrow_x], y=[0], mode="markers",
        marker=dict(symbol="triangle-down", color="blue", size=10),
        showlegend=False, hoverinfo="skip"
    ))
        
    # Add magnitude label, pushed up according to the new radius
    traces.append(go.Scatter(
        x=[x], y=[radius + 0.15], mode="text",
        text=[f"<b>{abs(magnitude):.2f} N·m</b>"],
        textfont=dict(size=14, color="blue", family="Arial, sans-serif"),
        showlegend=False,
        hoverinfo="skip"
    ))
    
    return traces

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


