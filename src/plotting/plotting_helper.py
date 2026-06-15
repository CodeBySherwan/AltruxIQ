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
def draw_point_load(x, magnitude, level=0,unit="N"):
    """
    Draws a point load arrow. 
    Positive loads (upward) are drawn above the beam.
    Negative loads (downward) are drawn under the beam in red.
    They stack vertically end-to-end if multiple exist at the same x.
    """
    arrow_length = 0.4 # Defines how long the arrow body is
    
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
        text_pos ="top center" 
        color = "green"
        
    return go.Scatter(
        x=[x, x],
        y=[y_start, y_end],
        mode="lines+text+markers",
        line=dict(color=color, width=3),
        # size=[0, 15] hides the marker at y_start (tail) and shows it at y_end (head)
        marker=dict(symbol=sym, color=color, size=[0, 15]),
        # Text is placed only at the head of the arrow (y_end)
        text=[None, f"<b>{abs(magnitude):.2f} {unit}</b>"],
        textposition=text_pos,
        showlegend=False,
        name="Point Load",
        hovertemplate=f"<b>Point Load</b><br>Location: {x} m<br>Magnitude: {magnitude:.2f} N<extra></extra>"
    )


def draw_moment_load(x, magnitude, unit="N·m"):
    theta = np.linspace(0, np.pi, 50)
    radius = 0.3
    
    x_arc = x + radius * np.cos(theta)
    y_arc = radius * np.sin(theta)
    
    if magnitude < 0:
        x_arc = x_arc[::-1]
    
    traces = []
    
    # Arc
    traces.append(go.Scatter(
        x=x_arc,
        y=y_arc,
        mode="lines",
        line=dict(color="green", width=3),
        showlegend=False
    ))
    
    # Arrowhead
    traces.append(go.Scatter(
        x=[x_arc[-1]],
        y=[y_arc[-1]],
        mode="markers+text",
        marker=dict(symbol="triangle-right" if magnitude > 0 else "triangle-left", color="green", size=10),
        text=[f"<b>{abs(magnitude):.2f} {unit}</b>"],
        textposition="top center",
        showlegend=False
    ))
    
    return traces

def draw_distributed_load(start, end, intensity_start, intensity_end, max_intensity, unit="N/m"):
    traces = []
    
    if max_intensity == 0:
        max_intensity = 1 
        
    y_start = 0.5 * (1 if intensity_start > 0 else -1) * (abs(intensity_start)/max_intensity)
    y_end = 0.5 * (1 if intensity_end > 0 else -1) * (abs(intensity_end)/max_intensity)
    
    # Draw main area fill
    traces.append(go.Scatter(
        x=[start, start, end, end, start],
        y=[0, y_start, y_end, 0, 0],
        mode="lines",
        line=dict(color="purple", width=2),
        fill="toself",
        fillcolor="rgba(128,0,128,0.3)",
        showlegend=False
    ))
    
    # Add vertical lines at start and end
    traces.append(go.Scatter(
        x=[start, start],
        y=[0, y_start],
        mode="lines",
        line=dict(color="purple", width=3),
        showlegend=False
    ))
    
    traces.append(go.Scatter(
        x=[end, end],
        y=[0, y_end],
        mode="lines",
        line=dict(color="purple", width=3),
        showlegend=False
    ))
    
    # Add load intensity labels
    if intensity_start != 0:
        traces.append(go.Scatter(
            x=[start],
            y=[y_start * 1.2],
            mode="text",
            text=[f"<b>{abs(intensity_start):.3f} {unit}</b>"],
            textposition="top center" if intensity_start > 0 else "bottom center",
            showlegend=False
        ))
        
    if intensity_end != 0 and abs(start - end) > 0.01: 
        traces.append(go.Scatter(
            x=[end],
            y=[y_end * 1.2],
            mode="text",
            text=[f"<b>{abs(intensity_end):.3f} {unit}</b>"],
            textposition="top center" if intensity_end > 0 else "bottom center",
            showlegend=False
        ))
        
    return traces

def draw_triangle_load(x_start, x_end, magnitude, unit="N/m"):
    traces = []
    
    # Draw the triangular fill
    traces.append(go.Scatter(
        x=[x_start, x_end, x_start],
        y=[0, 0, 0.5 * (1 if magnitude > 0 else -1)],
        mode="lines",
        fill="toself",
        fillcolor="rgba(0, 0, 255, 0.2)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False
    ))

    mid_x = (x_start + x_end) / 2
    traces.append(go.Scatter(
        x=[mid_x],
        y=[0.8 * (1 if magnitude > 0 else -1)],
        mode="text",
        text=[f"<b>{abs(magnitude):.3f} {unit}</b>"],
        textposition="top center",
        showlegend=False
    ))

    return traces

def draw_reaction(x, magnitude, unit="N"):
    arrow_tip = 1.2 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, x],
        y=[0, arrow_tip],
        mode="lines+text+markers",
        line=dict(color="red", width=4),
        marker=dict(symbol="triangle-up" if magnitude > 0 else "triangle-down", color="red", size=10),
        text=[None, f"<b>{abs(magnitude):.2f} {unit}</b>"],
        textposition="top center" if magnitude > 0 else "bottom center",
        showlegend=False,
        name="Vertical_R", 
    )

def draw_horizontal_reaction(x, magnitude, unit="N"):
    arrow_tip = x + 1.2 * (1 if magnitude > 0 else -1)
    return go.Scatter(
        x=[x, arrow_tip],
        y=[0, 0],
        mode="lines+text+markers",
        line=dict(color="orange", width=4),
        marker=dict(symbol="triangle-right" if magnitude > 0 else "triangle-left", color="orange", size=10),
        text=[None, f"<b>{abs(magnitude):.2f} {unit}</b>"],
        textposition="middle right" if magnitude > 0 else "middle left",
        showlegend=False,
        name="Horizontal_R", 
    )