import sys
import os
# --- PATH INJECTION (The Fix) ---
# 1. Get the directory of cli.py (ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent directory (src folder)
src_dir = os.path.dirname(current_dir)
# 3. Add the src folder to Python's search path if it's not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from plotly.subplots import make_subplots
import plotly.graph_objs as go
import plotting.plotting_helper as ph

def plot_beam_schematic(beam_length, A, B, support_types, loads):
    fig = make_subplots(rows=1, cols=1)

    # Beam line
    fig.add_trace(ph.draw_beam(beam_length))

    # Loads
    for load in loads:
        if load[0] == "point_load":
            fig.add_trace(ph.draw_point_load(*load[1:]))
        elif load[0] == "udl":
            for trace in ph.draw_udl(*load[1:]):
                fig.add_trace(trace)
        elif load[0] == "moment":
            for trace in ph.draw_moment(*load[1:]):
                fig.add_trace(trace)
    # Supports
    fig.add_trace(ph.draw_big_support(A, support_types[0]))
    fig.add_trace(ph.draw_big_support(B, support_types[1]))

    fig.update_layout(
        width=1000,
        height=600,
        title=dict(text="Beam Schematic", x=0.4),
        xaxis=dict(title="Beam Length (m)", range=[-0.5, beam_length + 0.5]),
        yaxis=dict(title="", range=[-2, 2], showgrid=False, zeroline=False),
        hovermode="closest",
        plot_bgcolor="rgba(173,216,230,0.3)"  # Light blue background
    )
    fig.show()


def plot_reaction_diagram(A, B, reactions,support_types):
    Va, Vb, Ha = reactions
    fig = make_subplots(rows=1, cols=1)


    fig.add_trace(ph.draw_beam(B + 0.5))  # baseline
    fig.add_trace(ph.draw_reaction(A, Va))
    fig.add_trace(ph.draw_reaction(B, Vb))
    


    if abs(Ha) > 0:
        fig.add_trace(ph.draw_horizontal_reaction(A, Ha))

    # Supports
    fig.add_trace(ph.draw_support(A, support_types[0]))
    fig.add_trace(ph.draw_support(B, support_types[1]))

    fig.update_layout(
        width=1000,
        height=600,
        title=dict(text="Support Reaction Diagram", x=0.4),
        xaxis=dict(title="Beam Length (m)", range=[-0.5, B + 0.5]),
        yaxis=dict(title="", range=[-2, 2], showgrid=False, zeroline=False, showticklabels=False),  # Removed Y-axis numbers
        hovermode="closest",
        plot_bgcolor="rgba(173,216,230,0.3)"  # Light blue background
    )
    fig.show()


def plot_cantilever_beam_schematic(beam_length, loads, title="Cantilever Beam Analysis"):
    """
    Create professional visualization of a cantilever beam with all types of loads.
    
    Parameters:
    -----------
    beam_length : float
        Total length of the beam in meters
    loads : list
        List of loads in the format [(load_type, *params), ...] where:
            - Point load: ("point_load", position, magnitude)
            - UDL: ("udl", start_position, end_position, magnitude)
            - Moment: ("moment", position, magnitude)
            - Triangular load: ("trl", start_position, end_position, start_magnitude, end_magnitude)
    title : str, optional
        Title for the plot
    
    Returns:
    --------
    fig : plotly.graph_objects.Figure
        The plotly figure object with the beam schematic
    """
    fig = go.Figure()
    
    # Draw beam line with improved appearance
    fig.add_trace(go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="purple", width=5),
        showlegend=False
    ))
    
    # Draw professional fixed support at x=0
    # Main support rectangle
    fig.add_trace(go.Scatter(
        x=[-0.05, -0.05, -0.25, -0.25, -0.05],
        y=[-0.2, 0.2, 0.2, -0.2, -0.2],
        mode="lines",
        line=dict(color="black", width=2),
        fill="toself",
        fillcolor="rgba(169,169,169,0.7)",
        name="Fixed Support",
        showlegend=True
    ))
    
    # Add hatching effect to fixed support (to make it look more professional)
    for i in range(-3, 4):
        y_pos = i/20
        fig.add_trace(go.Scatter(
            x=[-0.25, -0.05],
            y=[y_pos, y_pos],
            mode="lines",
            line=dict(color="black", width=1),
            showlegend=False
        ))
    
    # Add vertical line connecting support to beam
    fig.add_trace(go.Scatter(
        x=[0, 0],
        y=[-0.2, 0.2],
        mode="lines",
        line=dict(color="black", width=2),
        showlegend=False
    ))
    
    # Draw loads
    for load in loads:
        if load[0] == "point_load":
            fig.add_trace(ph.draw_point_load(*load[1:]))
        elif load[0] == "udl":
            for trace in ph.draw_udl(*load[1:]):
                fig.add_trace(trace)
        elif load[0] == "moment":
            for trace in ph.draw_moment(*load[1:]):
                fig.add_trace(trace)
        elif load[0] == "trl":
            # Implement triangular load visualization
            start, end, intensity_start, intensity_end = load[1:]
            
            # Calculate heights based on intensities and directions
            max_intensity = max(abs(intensity_start), abs(intensity_end))
            if max_intensity > 0:
                y_start = 0.5 * (1 if intensity_start > 0 else -1) * (abs(intensity_start)/max_intensity)
                y_end = 0.5 * (1 if intensity_end > 0 else -1) * (abs(intensity_end)/max_intensity)
                
                # Draw triangular load outline
                fig.add_trace(go.Scatter(
                    x=[start, start, end, end, start],
                    y=[0, y_start, y_end, 0, 0],
                    mode="lines",
                    line=dict(color="purple", width=2),
                    fill="toself",
                    fillcolor="rgba(128,0,128,0.3)",
                    showlegend=False
                ))
                
                # Add vertical lines at start and end
                fig.add_trace(go.Scatter(
                    x=[start, start],
                    y=[0, y_start],
                    mode="lines",
                    line=dict(color="purple", width=3),
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=[end, end],
                    y=[0, y_end],
                    mode="lines",
                    line=dict(color="purple", width=3),
                    showlegend=False
                ))
                
                # Add load intensity labels
                if intensity_start != 0:
                    fig.add_trace(go.Scatter(
                        x=[start],
                        y=[y_start * 1.2],
                        mode="text",
                        text=[f"<b>{abs(intensity_start):.3f} N/m</b>"],
                        textposition="top center" if intensity_start > 0 else "bottom center",
                        showlegend=False
                    ))
                
                if intensity_end != 0:
                    fig.add_trace(go.Scatter(
                        x=[end],
                        y=[y_end * 1.2],
                        mode="text",
                        text=[f"<b>{abs(intensity_end):.3f} N/m</b>"],
                        textposition="top center" if intensity_end > 0 else "bottom center",
                        showlegend=False
                    ))
    
    # Update layout for professional appearance
    fig.update_layout(
        width=1000,
        height=600,
        title=dict(
            text=title,
            font=dict(size=24, color="black", family="Arial, sans-serif"),
            x=0.5
        ),
        xaxis=dict(
            title=dict(
                text="Beam Length (m)",
                font=dict(size=16, family="Arial, sans-serif")
            ),
            range=[-0.5, beam_length + 0.5],
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor="black",
            showgrid=True,
            gridcolor="rgba(211,211,211,0.5)",
            gridwidth=1
        ),
        yaxis=dict(
            title="",
            range=[-1, 1],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        hovermode="closest",
        plot_bgcolor="rgba(240,248,255,0.8)",  # Light blue background
        paper_bgcolor="white",
        legend=dict(
            x=0.01,
            y=0.99,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1,
            font=dict(size=12, family="Arial, sans-serif")
        ),
        margin=dict(l=80, r=50, t=100, b=80)
    )
    
    # Add annotations for beam length
    fig.add_annotation(
        x=beam_length/2,
        y=-0.6,
        text=f"Length = {beam_length} m",
        showarrow=False,
        font=dict(size=14, family="Arial, sans-serif")
    )
    
    return fig
def draw_triangular_load(start, end, intensity_start, intensity_end):
    """
    Create traces to display a triangular load.
    
    Parameters:
    -----------
    start : float
        Starting position of the load
    end : float
        Ending position of the load
    intensity_start : float
        Load intensity at the start position
    intensity_end : float
        Load intensity at the end position
    
    Returns:
    --------
    list of go.Scatter
        List of plotly traces that represent the triangular load
    """
    traces = []
    
    # Determine maximum intensity for scaling
    max_intensity = max(abs(intensity_start), abs(intensity_end))
    
    # Calculate scaled heights for visualization
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
            text=[f"<b>{abs(intensity_start):.3f} N/m</b>"],
            textposition="top center" if intensity_start > 0 else "bottom center",
            showlegend=False
        ))
    
    if intensity_end != 0:
        traces.append(go.Scatter(
            x=[end],
            y=[y_end * 1.2],
            mode="text",
            text=[f"<b>{abs(intensity_end):.3f} N/m</b>"],
            textposition="top center" if intensity_end > 0 else "bottom center",
            showlegend=False
        ))
    
    return traces