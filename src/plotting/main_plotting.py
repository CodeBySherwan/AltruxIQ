import numpy as np
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm

# --- TYPOGRAPHY HELPERS ---
def format_plotly_sci(val):
    """Converts extreme numbers to clean HTML exponents for Plotly."""
    if abs(val) >= 1e5 or (abs(val) < 1e-3 and val != 0):
        base, exp = f"{val:.2e}".split('e')
        return f"{base} &times; 10<sup>{int(exp)}</sup>"
    return f"{val:,.2f}"

def format_matplot_sci(val):
    """Converts extreme numbers to math formatting for Matplotlib."""
    if abs(val) >= 1e5 or (abs(val) < 1e-3 and val != 0):
        base, exp = f"{val:.2e}".split('e')
        return f"${base} \\times 10^{{{int(exp)}}}$"
    return f"{val:,.2f}"
# --------------------------
# --- DATA ANALYSIS HELPERS ---
def find_critical_points(X, BM):
    """
    Finds maximum bending moment location and points of contraflexure (zero-crossings).
    """
    # 1. Find absolute maximum bending moment
    idx_max = np.argmax(np.abs(BM))
    max_x = X[idx_max]
    max_y = BM[idx_max]
    
    # 2. Find points of contraflexure (where BM crosses zero)
    # Ignore the first and last few points to avoid false triggers at supports
    contraflexure_x = []
    signs = np.sign(BM)
    sign_changes = np.where(np.diff(signs))[0]
    
    for idx in sign_changes:
        # Ignore crossings exactly at the boundaries (x=0 or x=L)
        if idx > 5 and idx < len(X) - 5:
            # Simple linear interpolation for the exact zero-crossing x-coordinate
            dx = X[idx+1] - X[idx]
            dy = BM[idx+1] - BM[idx]
            if dy != 0:
                x_exact = X[idx] - BM[idx] * (dx / dy)
                contraflexure_x.append(x_exact)
                
    return max_x, max_y, contraflexure_x
# -----------------------------
# =====================================
# Plotly Plotting Functions
# =====================================

def Plotly_shear_force(X_Field, Total_ShearForce, beam_length):
    """
    Create professional Plotly visualization of shear force diagram.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
    beam_length : float
        Total length of the beam
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Shear Force Diagram Data ---
    x_shear = X_Field
    y_shear = Total_ShearForce

    # Find max/min values and their positions for annotations
    max_shear = round(np.max(y_shear), 3)
    min_shear = round(np.min(y_shear), 3)
    idx_max_shear = np.argmax(y_shear)
    idx_min_shear = np.argmin(y_shear)

    # --- Shear Force Trace ---
    trace_shear = go.Scatter(
        x=x_shear,
        y=y_shear,
        mode="lines",
        line=dict(color='#1f77b4', width=3),  # More professional blue
        name="Shear Force",
        hovertemplate="<b>%{y:.2f} N</b><extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(31,119,180,0.2)"  # Matching blue with transparency
    )
    
    # --- Horizontal Axis Line (Reference) ---
    trace_line = go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="black", width=1.5, dash='dot'),
        showlegend=False
    )


    # --- Layout for Shear Force Diagram ---
    layout_shear = go.Layout(
        title={
            'text': f"<b>Shear Force Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_shear)} N | Minimum: {format_plotly_sci(min_shear)} N</span>",
            'font': {'family': 'Arial, sans-serif'},
            'x': 0.5,
            'y': 0.95
        },
        xaxis=dict(
            title={
                'text': "Position along Beam (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        yaxis=dict(
            title={
                'text': "Shear Force (N)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        width=800,
        height=500,
        margin=dict(l=80, r=50, t=80, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest'
    )

    # --- Build Figures ---
    fig_shear = go.Figure(data=[trace_shear, trace_line], layout=layout_shear)
    fig_shear.show()


def Plotly_Deflection(X_Field, Deflection, beam_length):
    """
    Create professional Plotly visualization of beam deflection.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Deflection : numpy.ndarray
        Deflection values at each point
    beam_length : float
        Total length of the beam
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Deflection Diagram Data ---
    x_deflection = X_Field
    y_deflection = Deflection

    # Find max/min values and their positions for annotations
    max_deflection = round(np.max(y_deflection), 6)
    min_deflection = round(np.min(y_deflection), 6)
    idx_max_deflection = np.argmax(y_deflection)
    idx_min_deflection = np.argmin(y_deflection)

    # --- Deflection Trace ---
    trace_deflection = go.Scatter(
        x=x_deflection,
        y=y_deflection,
        mode="lines",
        line=dict(color='#2ca02c', width=3),  # Professional green
        name="Deflection",
        hovertemplate="<b>%{y:.2f} mm</b><extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(44,160,44,0.2)"  # Matching green with transparency
    )
    
    # --- Horizontal Axis Line (Reference) ---
    trace_line = go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="black", width=1.5, dash='dot'),
        showlegend=False
    )


    # --- Layout for Deflection Diagram ---
    layout_deflection = go.Layout(
        title={
            'text': f"<b>Deflection Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_deflection)} m | Minimum: {format_plotly_sci(min_deflection)} m</span>",
            'font': {'family': 'Arial, sans-serif'},
            'x': 0.5, 'y': 0.95
        },
        xaxis=dict(
            title={
                'text': "Position along Beam (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        yaxis=dict(
            title={
                'text': "Deflection (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),

        width=800,
        height=500,
        margin=dict(l=80, r=50, t=80, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest'
    )
    
    # --- Build Figures ---
    fig_deflection = go.Figure(data=[trace_deflection, trace_line], layout=layout_deflection)
    fig_deflection.show()

def Plotly_ShearStress(X_Field, ShearStress, beam_length):
    """
    Create Plotly visualization of shear stress along the beam.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    ShearStress : numpy.ndarray
        Shear stress values at each point (can be 2D)
    beam_length : float
        Total length of the beam
    """
    # Handle 2D ShearStress matrix if present
    if len(ShearStress.shape) > 1:
        # Option 1: Take maximum stress at each position (conservative approach)
        ShearStress = np.max(np.abs(ShearStress), axis=1)
        
        # Option 2: Take stress at neutral axis or any specific y-position
        # middle_index = len(ShearStress[0]) // 2
        # stress_to_plot = ShearStress[:, middle_index]
    else:
        ShearStress = ShearStress
    """
    Create professional Plotly visualization of shear stress along the beam.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    ShearStress : numpy.ndarray
        Shear stress values at each point
    beam_length : float
        Total length of the beam
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Shear Stress Diagram Data ---
    x_stress = X_Field
    y_stress = ShearStress

    # Find max/min values and their positions for annotations
    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)
    idx_max_stress = np.argmax(y_stress)
    idx_min_stress = np.argmin(y_stress)

    # --- Shear Stress Trace ---
    trace_stress = go.Scatter(
        x=x_stress,
        y=y_stress,
        mode="lines",
        line=dict(color='#d62728', width=3),  # Professional red
        name="Shear Stress",
        hovertemplate="<b>%{y:.2f} Pa</b><extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(214,39,40,0.2)"  # Matching red with transparency
    )
    
    # --- Horizontal Axis Line (Reference) ---
    trace_line = go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="black", width=1.5, dash='dot'),
        showlegend=False
    )


    # --- Layout for Shear Stress Diagram ---
    layout_stress = go.Layout(
        title={
            'text': f"<b>Shear Stress Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_stress)} Pa | Minimum: {format_plotly_sci(min_stress)} Pa</span>",
            'font': {'family': 'Arial, sans-serif'},
            'x': 0.5, 'y': 0.95
        },
        xaxis=dict(
            title={
                'text': "Position along Beam (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        yaxis=dict(
            title={
                'text': "Shear Stress (Pa)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1,
            exponentformat='e'
        ),

        width=800,
        height=500,
        margin=dict(l=80, r=50, t=80, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest'
    )
    
    # --- Build Figures --- 
    fig_stress = go.Figure(data=[trace_stress, trace_line], layout=layout_stress)
    fig_stress.show()


def Plotly_bending_moment(X_Field, Total_BendingMoment, beam_length):
    """
    Create professional Plotly visualization of bending moment diagram.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
    beam_length : float
        Total length of the beam
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Bending Moment Diagram Data ---
    x_bend = X_Field
    y_bend = Total_BendingMoment

    # Find max/min values and their positions for annotations
    max_bend = round(np.max(y_bend), 3)
    min_bend = round(np.min(y_bend), 3)
    idx_max_bend = np.argmax(y_bend)
    idx_min_bend = np.argmin(y_bend)

    # --- Bending Moment Trace ---
    trace_bend = go.Scatter(
        x=x_bend,
        y=y_bend,
        mode="lines",
        line=dict(color='#9467bd', width=3),  # Professional purple
        name="Bending Moment",
        hovertemplate="<b>%{y:.2f} N.m</b><extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(148,103,189,0.2)"  # Matching purple with transparency
    )
    
    # --- Horizontal Axis Line (Reference) ---
    trace_line = go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="black", width=1.5, dash='dot'),
        showlegend=False
    )

 
    # --- Layout for Bending Moment Diagram ---
    layout_bend = go.Layout(
        title={
            'text': f"<b>Bending Moment Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_bend)} N·m | Minimum: {format_plotly_sci(min_bend)} N·m</span>",
            'font': {'family': 'Arial, sans-serif'},
            'x': 0.5, 'y': 0.95
        },
        xaxis=dict(
            title={
                'text': "Position along Beam (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        yaxis=dict(
            title={
                'text': f"<b>Bending Moment Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_bend)} N·m | Minimum: {format_plotly_sci(min_bend)} N·m</span>",
                'font': {'family': 'Arial, sans-serif'},
                'x': 0.5, 'y': 0.95
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),

        width=800,
        height=500,
        margin=dict(l=80, r=50, t=80, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest'
    )
    
    # --- Build Figures ---
    fig_bend = go.Figure(data=[trace_bend, trace_line], layout=layout_bend)
    fig_bend.show()


def Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, Deflection=None, ShearStress=None):
    """
    Create combined professional Plotly visualization of multiple beam diagrams.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
    beam_length : float
        Total length of the beam
    Deflection : numpy.ndarray, optional
        Deflection values at each point
    ShearStress : numpy.ndarray, optional
        Shear stress values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # Slice arrays to every 5th point to optimize browser DOM performance (2000 pts instead of 10k)
    step = 5
    X_Field = X_Field[::step]
    Total_ShearForce = Total_ShearForce[::step]
    Total_BendingMoment = Total_BendingMoment[::step]
    if Deflection is not None:
        Deflection = Deflection[::step]
    if ShearStress is not None:
        ShearStress = ShearStress[::step]
    # Determine number of rows based on provided data
    num_rows = 2  # SFD and BMD are always included
    if Deflection is not None:
        num_rows += 1
    if ShearStress is not None:
        num_rows += 1
        
    # Create subplots
    fig = make_subplots(
        rows=num_rows, 
        cols=1,
        subplot_titles=["Shear Force Diagram", "Bending Moment Diagram"] + 
                        (["Deflection Diagram"] if Deflection is not None else []) +
                        (["Shear Stress Diagram"] if ShearStress is not None else []),
        vertical_spacing=0.12
    )
    
    # Add reference line (beam centerline)
    for i in range(1, num_rows + 1):
        fig.add_trace(
            go.Scatter(
                x=[0, beam_length],
                y=[0, 0],
                mode="lines",
                line=dict(color="black", width=1.5, dash='dot'),
                showlegend=False
            ),
            row=i, col=1
        )
    
    # --- Shear Force ---
    max_shear = round(np.max(Total_ShearForce), 3)
    min_shear = round(np.min(Total_ShearForce), 3)
    
    fig.add_trace(
        go.Scatter(
            x=X_Field,
            y=Total_ShearForce,
            mode="lines",
            line=dict(color='#1f77b4', width=2.5),
            fill="tozeroy",
            fillcolor="rgba(31,119,180,0.2)",
            name="Shear Force",
            hovertemplate="<b>%{y:.2f} N</b><extra></extra>",
        ),
        row=1, col=1
    )
    
    # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(X_Field, Total_ShearForce)
    
    # Add Point of Maximum Total_ShearForce
    fig.add_trace(go.Scatter(
        x=[max_x], y=[max_y],
        mode='markers',
        marker=dict(symbol='diamond', size=10, color='blue', line=dict(width=2, color='darkblue')),
        name='Max Shear Force',
        hovertemplate="<b>Max SF</b><br>X: %{x:.2f} m<br>value: %{y:.2f} N<extra></extra>"
    ), row=1, col=1)
    
    # Add Points of Contraflexure (if any exist)
    if contra_x:
        fig.add_trace(go.Scatter(
            x=contra_x, y=[0]*len(contra_x),
            mode='markers',
            marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
            name='Point of Contraflexure',
            hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} m<br>value: 0 N<extra></extra>"
        ), row=1, col=1)
    
    # --- Bending Moment ---
    max_bend = round(np.max(Total_BendingMoment), 3)
    min_bend = round(np.min(Total_BendingMoment), 3)
    
    fig.add_trace(
        go.Scatter(
            x=X_Field,
            y=Total_BendingMoment,
            mode="lines",
            line=dict(color='#9467bd', width=2.5),
            fill="tozeroy",
            fillcolor="rgba(148,103,189,0.2)",
            name="Bending Moment",
            hovertemplate="<b>%{y:.2f} N.m</b><extra></extra>"
        ),
        row=2, col=1
    )
    
     # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(X_Field, Total_BendingMoment)
    
    # Add Point of Maximum Bending Moment
    fig.add_trace(go.Scatter(
        x=[max_x], y=[max_y],
        mode='markers',
        marker=dict(symbol='diamond', size=10, color='purple', line=dict(width=2, color='darkviolet')),
        name='Max Shear Force',
        hovertemplate="<b>Max SF</b><br>X: %{x:.2f} m<br>value: %{y:.2f} N.m<extra></extra>"
    ), row=2, col=1)
    
    # Add Points of Contraflexure (if any exist)
    if contra_x:
        fig.add_trace(go.Scatter(
            x=contra_x, y=[0]*len(contra_x),
            mode='markers',
            marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
            name='Point of Contraflexure',
            hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} m<br>value: 0 N.m<extra></extra>"
        ), row=2, col=1) 
    
    # --- Deflection (if provided) ---
    current_row = 3
    if Deflection is not None:
        max_defl = round(np.max(Deflection), 6)
        min_defl = round(np.min(Deflection), 6)
        
        fig.add_trace(
            go.Scatter(
                x=X_Field,
                y=Deflection,
                mode="lines",
                line=dict(color='#2ca02c', width=2.5),
                fill="tozeroy",
                fillcolor="rgba(44,160,44,0.2)",
                name="Deflection",
                hovertemplate="<b>%{y:.2f} mm</b><extra></extra>"
            ),
            row=current_row, col=1
            )
        # Calculate critical structural points
        max_x, max_y, contra_x = find_critical_points(X_Field, Deflection)
        
        # Add Point of Maximum Deflection
        fig.add_trace(go.Scatter(
            x=[max_x], y=[max_y],
            mode='markers',
            marker=dict(symbol='diamond', size=10, color='green', line=dict(width=2, color='lime')),
            name='Deflection',
            hovertemplate="<b>Max DF</b><br>X: %{x:.2f} mm<br>value: %{y:.2f} N<extra></extra>"
        ), row=3, col=1)
        
        # Add Points of Contraflexure (if any exist)
        if contra_x:
            fig.add_trace(go.Scatter(
                x=contra_x, y=[0]*len(contra_x),
                mode='markers',
                marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
                name='Point of Contraflexure',
                hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} mm<br>value: 0 N·m<extra></extra>"
            ), row=3, col=1)       

            current_row = 4
    
    # --- Shear Stress (if provided) ---
    if ShearStress is not None:
        # Handle 2D ShearStress matrix if present
        if len(ShearStress.shape) > 1:
            # Take maximum stress at each position (conservative approach)
            ShearStress = np.max(np.abs(ShearStress), axis=1)
        else:
            ShearStress = ShearStress
            
        max_stress = round(np.max(ShearStress), 2)
        min_stress = round(np.min(ShearStress), 2)
        
        fig.add_trace(
            go.Scatter(
                x=X_Field,
                y=ShearStress,  # Use processed data
                mode="lines",
                line=dict(color='#d62728', width=2.5),
                fill="tozeroy",
                fillcolor="rgba(214,39,40,0.2)",
                name="Shear Stress",
                hovertemplate="<b>%{y:.2f} Pa</b><extra></extra>"
            ),
            row=4, col=1
        )
            
        # Calculate critical structural points
        max_x, max_y, contra_x = find_critical_points(X_Field, ShearStress)
        
        # Add Point of Maximum ShearStress
        fig.add_trace(go.Scatter(
            x=[max_x], y=[max_y],
            mode='markers',
            marker=dict(symbol='diamond', size=10, color='red', line=dict(width=2, color='darkred')),
            name='Max ShearStress',
            hovertemplate="<b>Max SS</b><br>X: %{x:.2f} Pa<br>Value: %{y:.2f} N<extra></extra>"
        ), row=4, col=1)
        
        # Add Points of Contraflexure (if any exist)
        if contra_x:
            fig.add_trace(go.Scatter(
                x=contra_x, y=[0]*len(contra_x),
                mode='markers',
                marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
                name='Point of Contraflexure',
                hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} Pa<br>M: 0 N·m<extra></extra>"
            ), row=4, col=1)       

    # Update layout and axis labels
    fig.update_layout(
        title={
            'text': " ",
            'font': {'size': 24, 'family': 'Arial, sans-serif'},
            'y': 0.98
        },
        height=250 * num_rows + 350,
        width=900,
        margin=dict(l=80, r=50, t=100, b=50),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.04,
            xanchor="center",
            x=0.5
        )
    )
    
    # Update x-axis titles only for the bottom subplot
    for i in range(1, num_rows):
        fig.update_xaxes(
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1,
            title="",
            row=i, col=1
        )
    
    # Set x-axis title for the bottom subplot
    fig.update_xaxes(
        title={
            'text': "Position along Beam (m)",
            'font': {'size': 14, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=num_rows, col=1
    )
    
    # Update y-axis titles
    fig.update_yaxes(
        title={
            'text': "Shear Force (N)",
            'font': {'size': 12, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title={
            'text': "Bending Moment (N·m)",
            'font': {'size': 12, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=2, col=1
    )
    
    if Deflection is not None:
        fig.update_yaxes(
            title={
                'text': "Deflection (m)",
                'font': {'size': 12, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1,
            row=3, col=1
        )
    
    if ShearStress is not None:
        fig.update_yaxes(
            title={
                'text': "Shear Stress (Pa)",
                'font': {'size': 12, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1,
            exponentformat='e',
            row=4,col=1
        )
    
    fig.show()
#=====================================
def Plotly_BendingStress(X_Field, BendingStress, beam_length):
    """
    Create Plotly visualization of bending stress along the beam.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    BendingStress : numpy.ndarray
        Bending stress values at each point
    beam_length : float
        Total length of the beam
    """
    # Handle 2D BendingStress matrix if present
    if len(BendingStress.shape) > 1:
        # Option 1: Take maximum stress at each position (conservative approach)
        BendingStress = np.max(np.abs(BendingStress), axis=1)
        
        # Option 2: Take stress at extreme fiber (normally the maximum)
        # For example, if the stress at the extreme fiber (top or bottom) is of interest:
        # stress_to_plot = BendingStress[:, 0]  # or BendingStress[:, -1] for bottom fiber
    else:
        BendingStress = BendingStress
    
    # --- Bending Stress Diagram Data ---
    x_stress = X_Field
    y_stress = BendingStress

    # Find max/min values and their positions for annotations
    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)
    idx_max_stress = np.argmax(y_stress)
    idx_min_stress = np.argmin(y_stress)

    # --- Bending Stress Trace ---
    trace_stress = go.Scatter(
        x=x_stress,
        y=y_stress,
        mode="lines",
        line=dict(color='#8c564b', width=3),  # Professional brown
        name="Bending Stress",
        hovertemplate="<b>%{y:.2f} Pa</b><extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(140,86,75,0.2)"  # Matching brown with transparency
    )
    
    # --- Horizontal Axis Line (Reference) ---
    trace_line = go.Scatter(
        x=[0, beam_length],
        y=[0, 0],
        mode="lines",
        line=dict(color="black", width=1.5, dash='dot'),
        showlegend=False
    )

    # --- Annotations for Bending Stress ---
    annotations_stress = [
        dict(
            x=x_stress[idx_max_stress],
            y=max_stress,
            text=f"Max: {max_stress:.2e} Pa",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            ax=0,
            ay=-30,
            font=dict(color="#8c564b", size=12)
        ),
        dict(
            x=x_stress[idx_min_stress],
            y=min_stress,
            text=f"Min: {min_stress:.2e} Pa",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.5,
            ax=0,
            ay=30,
            font=dict(color="#8c564b", size=12)
        )
    ]

    # --- Layout for Bending Stress Diagram ---
    layout_stress = go.Layout(
        title={
            'text': "Bending Stress Diagram",
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        xaxis=dict(
            title={
                'text': "Position along Beam (m)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1
        ),
        yaxis=dict(
            title={
                'text': "Bending Stress (Pa)",
                'font': {'size': 14, 'family': 'Arial, sans-serif'}
            },
            showgrid=True,
            gridcolor='rgba(211,211,211,0.5)',
            mirror=True,
            linecolor='black',
            linewidth=1,
            exponentformat='e'
        ),
        annotations=annotations_stress,
        width=800,
        height=500,
        margin=dict(l=80, r=50, t=80, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest'
    )
    
    # --- Build Figures ---
    fig_stress = go.Figure(data=[trace_stress, trace_line], layout=layout_stress)
    fig_stress.show()

#=====================================

def Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length):
    """
    Create professional Plotly visualization of shear force and bending moment diagrams.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
    beam_length : float
        Total length of the beam
        
    Returns:
    --------
    None, displays the plots
    """
    # Create subplots layout
    fig = make_subplots(
        rows=2, 
        cols=1,
        subplot_titles=("Shear Force Diagram", "Bending Moment Diagram"),
        vertical_spacing=0.15
    )
    
    # --- Shear Force ---
    # Find max/min values and their positions for annotations
    max_shear = round(np.max(Total_ShearForce), 3)
    min_shear = round(np.min(Total_ShearForce), 3)
    idx_max_shear = np.argmax(Total_ShearForce)
    idx_min_shear = np.argmin(Total_ShearForce)
    
    # Add trace for shear force
    fig.add_trace(
        go.Scatter(
            x=X_Field,
            y=Total_ShearForce,
            mode="lines",
            line=dict(color='#1f77b4', width=3),
            name="Shear Force",
            hovertemplate="<b>%{y:.2f} N</b><extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(31,119,180,0.2)"
        ),
        row=1, col=1
    )
    # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(X_Field, Total_ShearForce)
    
    # Add Point of Maximum Total_ShearForce
    fig.add_trace(go.Scatter(
        x=[max_x], y=[max_y],
        mode='markers',
        marker=dict(symbol='diamond', size=10, color='blue', line=dict(width=2, color='darkblue ')),
        name='Max Shear Force',
        hovertemplate="<b>Max SF</b><br>X: %{x:.2f} m<br>M: %{y:.2f} N<extra></extra>"
    ), row=1, col=1)
    
    # Add Points of Contraflexure (if any exist)
    if contra_x:
        fig.add_trace(go.Scatter(
            x=contra_x, y=[0]*len(contra_x),
            mode='markers',
            marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
            name='Point of Contraflexure',
            hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} m<br>M: 0 N·m<extra></extra>"
        ), row=1, col=1)



    # Add zero line for SFD
    fig.add_trace(
        go.Scatter(
            x=[0, beam_length],
            y=[0, 0],
            mode="lines",
            line=dict(color="black", width=1.5, dash='dot'),
            showlegend=False
        ),
        row=1, col=1
    )
    
    # --- Bending Moment ---
    # Find max/min values and their positions for annotations
    max_bend = round(np.max(Total_BendingMoment), 3)
    min_bend = round(np.min(Total_BendingMoment), 3)
    idx_max_bend = np.argmax(Total_BendingMoment)
    idx_min_bend = np.argmin(Total_BendingMoment)
    
    # Add trace for bending moment
    fig.add_trace(
        go.Scatter(
            x=X_Field,
            y=Total_BendingMoment,
            mode="lines",
            line=dict(color='#9467bd', width=3),
            name="Bending Moment",
            hovertemplate="<b>%{y:.2f} N.M</b><extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(148,103,189,0.2)"
        ),
        row=2, col=1
    )
    
    # Add zero line for BMD
    fig.add_trace(
        go.Scatter(
            x=[0, beam_length],
            y=[0, 0],
            mode="lines",
            line=dict(color="black", width=1.5, dash='dot'),
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(X_Field, Total_BendingMoment)
    
    # Add Point of Maximum Bending Moment
    fig.add_trace(go.Scatter(
        x=[max_x], y=[max_y],
        mode='markers',
        marker=dict(symbol='diamond', size=10, color='purple', line=dict(width=2, color='darkviolet')),
        name='Max Bending Moment',
        hovertemplate="<b>Max BM</b><br>X: %{x:.2f} m<br>M: %{y:.2f} N.m<extra></extra>"
    ), row=2, col=1)
    
    # Add Points of Contraflexure (if any exist)
    if contra_x:
        fig.add_trace(go.Scatter(
            x=contra_x, y=[0]*len(contra_x),
            mode='markers',
            marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)),
            name='Point of Contraflexure',
            hovertemplate="<b>Contraflexure</b><br>X: %{x:.2f} m<br>M: 0 N·m<extra></extra>"
        ), row=2, col=1)
    
    # Update layout
    fig.update_layout(
        title={
            'text': "Beam Analysis Results",
            'font': {'size': 24, 'family': 'Arial, sans-serif'}
        },
        height=900,
        width=800,
        margin=dict(l=80, r=50, t=120, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='closest',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Update axes properties
    fig.update_xaxes(
        title={
            'text': "Position along Beam (m)",
            'font': {'size': 14, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=2, col=1
    )
    
    fig.update_xaxes(
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        title="",
        row=1, col=1
    )
    
    fig.update_yaxes(
        title={
            'text': "Shear Force (N)",
            'font': {'size': 14, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=1, col=1
    )
    
    fig.update_yaxes(
        title={
            'text': "Bending Moment (N·m)",
            'font': {'size': 14, 'family': 'Arial, sans-serif'}
        },
        showgrid=True,
        gridcolor='rgba(211,211,211,0.5)',
        mirror=True,
        linecolor='black',
        linewidth=1,
        row=2, col=1
    )
    
    fig.show()


# =====================================
# Matplotlib Plotting Functions
# =====================================

def Matplot_shear_force(X_Field, Total_ShearForce):
    """
    Create professional Matplotlib visualization of shear force diagram.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Shear Force Diagram Data ---
    x_shear = X_Field
    y_shear = Total_ShearForce

    # Find max/min values and their positions for annotations
    max_shear = round(np.max(y_shear), 3)
    min_shear = round(np.min(y_shear), 3)
    idx_max_shear = np.argmax(y_shear)
    idx_min_shear = np.argmin(y_shear)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with proper sizing
    fig_shear, ax_shear = plt.subplots(figsize=(10, 6), dpi=100)

    # Plot with professional styling
    ax_shear.plot(x_shear, y_shear, color='#1f77b4', linewidth=2.5, label='Shear Force')
    
    # Fill areas with appropriate colors
    ax_shear.fill_between(x_shear, y_shear, 0, where=(y_shear >= 0), interpolate=True, 
                          alpha=0.3, color='#1f77b4', label='_nolegend_')
    ax_shear.fill_between(x_shear, y_shear, 0, where=(y_shear < 0), interpolate=True, 
                          alpha=0.3, color='#ff7f0e', label='_nolegend_')

    # Add reference line
    ax_shear.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    
    # Set title and labels with professional styling
    ax_shear.set_title('Shear Force Diagram', fontsize=22, pad=20)
    ax_shear.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_shear.set_ylabel('Shear Force (N)', fontsize=14, labelpad=10)

    # Annotate Maximum and Minimum values
    ax_shear.annotate(f"Max: {max_shear:.2f} N", 
                      xy=(x_shear[idx_max_shear], max_shear), 
                      xytext=(10, 30), textcoords='offset points',
                      arrowprops=dict(arrowstyle="->", color='#1f77b4', lw=1.5),
                      fontsize=12, color='#1f77b4', fontweight='bold')

    ax_shear.annotate(f"Min: {min_shear:.2f} N", 
                      xy=(x_shear[idx_min_shear], min_shear), 
                      xytext=(10, -40), textcoords='offset points',
                      arrowprops=dict(arrowstyle="->", color='#ff7f0e', lw=1.5),
                      fontsize=12, color='#ff7f0e', fontweight='bold')

    # Add legend, grid, and customize ticks
    ax_shear.legend(loc='best', fontsize=12)
    ax_shear.grid(True, linestyle='--', alpha=0.7)
    ax_shear.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    
    # Remove top and right spines for cleaner look
    ax_shear.spines['top'].set_visible(False)
    ax_shear.spines['right'].set_visible(False)
    
    # Improve x-axis tick locating
    ax_shear.xaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # Add subtle grid to improve readability
    ax_shear.grid(True, linestyle='--', alpha=0.5, color='gray')

    # Show plot with tight layout
    fig_shear.tight_layout()
    plt.show()


def Matplot_bending_moment(X_Field, Total_BendingMoment):
    """
    Create professional Matplotlib visualization of bending moment diagram.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Bending Moment Diagram Data ---
    x_bend = X_Field
    y_bend = Total_BendingMoment

    # Find max/min values and their positions for annotations
    max_bend = round(np.max(y_bend), 3)
    min_bend = round(np.min(y_bend), 3)
    idx_max_bend = np.argmax(y_bend)
    idx_min_bend = np.argmin(y_bend)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with proper sizing
    fig_bend, ax_bend = plt.subplots(figsize=(10, 6), dpi=100)

    # Plot with professional styling
    ax_bend.plot(x_bend, y_bend, color='#9467bd', linewidth=2.5, label='Bending Moment')
    
    # Fill areas with appropriate colors
    ax_bend.fill_between(x_bend, y_bend, 0, where=(y_bend >= 0), interpolate=True, 
                         alpha=0.3, color='#9467bd', label='_nolegend_')
    ax_bend.fill_between(x_bend, y_bend, 0, where=(y_bend < 0), interpolate=True, 
                         alpha=0.3, color='#2ca02c', label='_nolegend_')

    # Add reference line
    ax_bend.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    
    # Set title and labels with professional styling
    ax_bend.set_title('Bending Moment Diagram', fontsize=22, pad=20)
    ax_bend.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_bend.set_ylabel('Bending Moment (N·m)', fontsize=14, labelpad=10)

    # Annotate Maximum and Minimum values
    ax_bend.annotate(f"Max: {max_bend:.2f} N·m", 
                     xy=(x_bend[idx_max_bend], max_bend), 
                     xytext=(10, 30), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color='#9467bd', lw=1.5),
                     fontsize=12, color='#9467bd', fontweight='bold')

    ax_bend.annotate(f"Min: {min_bend:.2f} N·m", 
                     xy=(x_bend[idx_min_bend], min_bend), 
                     xytext=(10, -40), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color='#2ca02c', lw=1.5),
                     fontsize=12, color='#2ca02c', fontweight='bold')

    # Add legend, grid, and customize ticks
    ax_bend.legend(loc='best', fontsize=12)
    ax_bend.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    
    # Remove top and right spines for cleaner look
    ax_bend.spines['top'].set_visible(False)
    ax_bend.spines['right'].set_visible(False)
    
    # Improve x-axis tick locating
    ax_bend.xaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # Add subtle grid to improve readability
    ax_bend.grid(True, linestyle='--', alpha=0.5, color='gray')

    # Show plot with tight layout
    fig_bend.tight_layout()
    plt.show()


def Matplot_Deflection(X_Field, Deflection):
    """
    Create professional Matplotlib visualization of beam deflection.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Deflection : numpy.ndarray
        Deflection values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Deflection Diagram Data ---
    x_defl = X_Field
    y_defl = Deflection

    # Find max/min values and their positions for annotations
    max_defl = round(np.max(y_defl), 6)
    min_defl = round(np.min(y_defl), 6)
    idx_max_defl = np.argmax(y_defl)
    idx_min_defl = np.argmin(y_defl)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with proper sizing
    fig_defl, ax_defl = plt.subplots(figsize=(10, 6), dpi=100)

    # Plot with professional styling
    ax_defl.plot(x_defl, y_defl, color='#2ca02c', linewidth=2.5, label='Deflection')
    
    # Fill areas with appropriate colors
    ax_defl.fill_between(x_defl, y_defl, 0, where=(y_defl >= 0), interpolate=True, 
                         alpha=0.3, color='#2ca02c', label='_nolegend_')
    ax_defl.fill_between(x_defl, y_defl, 0, where=(y_defl < 0), interpolate=True, 
                         alpha=0.3, color='#d62728', label='_nolegend_')

    # Add reference line
    ax_defl.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    
    # Set title and labels with professional styling
    ax_defl.set_title('Deflection Diagram', fontsize=22, pad=20)
    ax_defl.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_defl.set_ylabel('Deflection (m)', fontsize=14, labelpad=10)

    # Annotate Maximum and Minimum values with correct units
    ax_defl.annotate(f"Max: {max_defl:.6f} m", 
                     xy=(x_defl[idx_max_defl], max_defl), 
                     xytext=(10, 30), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color='#2ca02c', lw=1.5),
                     fontsize=12, color='#2ca02c', fontweight='bold')

    ax_defl.annotate(f"Min: {min_defl:.6f} m", 
                     xy=(x_defl[idx_min_defl], min_defl), 
                     xytext=(10, -40), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.5),
                     fontsize=12, color='#d62728', fontweight='bold')

    # Add legend, grid, and customize ticks
    ax_defl.legend(loc='best', fontsize=12)
    ax_defl.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    
    # Remove top and right spines for cleaner look
    ax_defl.spines['top'].set_visible(False)
    ax_defl.spines['right'].set_visible(False)
    
    # Improve x-axis tick locating
    ax_defl.xaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # Set y-axis to use scientific notation for very small values
    ax_defl.ticklabel_format(axis='y', style='sci', scilimits=(-4,4))
    
    # Add subtle grid to improve readability
    ax_defl.grid(True, linestyle='--', alpha=0.5, color='gray')

    # Show plot with tight layout
    fig_defl.tight_layout()
    plt.show()


def Matplot_ShearStress(X_Field, Shear_stress):
    """
    Create professional Matplotlib visualization of shear stress.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Shearstress : numpy.ndarray
        Shear stress values at each point
        
    Returns:
    --------
    None, displays the plot
    """

    if len(Shear_stress.shape) > 1:
        y_stress = np.max(np.abs(Shear_stress), axis=1)
    else:
        y_stress = Shear_stress
        
    x_stress = X_Field


    # Find max/min values and their positions for annotations
    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)
    idx_max_stress = np.argmax(y_stress)
    idx_min_stress = np.argmin(y_stress)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with proper sizing
    fig_stress, ax_stress = plt.subplots(figsize=(10, 6), dpi=100)

    # Plot with professional styling
    ax_stress.plot(x_stress, y_stress, color='#d62728', linewidth=2.5, label='Shear Stress')
    
    # Fill areas with appropriate colors
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress >= 0), interpolate=True, 
                           alpha=0.3, color='#d62728', label='_nolegend_')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress < 0), interpolate=True, 
                           alpha=0.3, color='#ff7f0e', label='_nolegend_')

    # Add reference line
    ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    
    # Set title and labels with professional styling
    ax_stress.set_title('Shear Stress Diagram', fontsize=22, pad=20)
    ax_stress.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_stress.set_ylabel('Shear Stress (Pa)', fontsize=14, labelpad=10)

    # Annotate Maximum and Minimum values with correct units
    ax_stress.annotate(f"Max: {max_stress:.2e} Pa", 
                       xy=(x_stress[idx_max_stress], max_stress), 
                       xytext=(10, 30), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.5),
                       fontsize=12, color='#d62728', fontweight='bold')

    ax_stress.annotate(f"Min: {min_stress:.2e} Pa", 
                       xy=(x_stress[idx_min_stress], min_stress), 
                       xytext=(10, -40), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color='#ff7f0e', lw=1.5),
                       fontsize=12, color='#ff7f0e', fontweight='bold')

    # Add legend, grid, and customize ticks
    ax_stress.legend(loc='best', fontsize=12)
    ax_stress.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    
    # Remove top and right spines for cleaner look
    ax_stress.spines['top'].set_visible(False)
    ax_stress.spines['right'].set_visible(False)
    
    # Improve x-axis tick locating
    ax_stress.xaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # Set y-axis to use scientific notation
    ax_stress.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    
    # Add subtle grid to improve readability
    ax_stress.grid(True, linestyle='--', alpha=0.5, color='gray')

    # Show plot with tight layout
    fig_stress.tight_layout()
    plt.show()


def Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment):
    """
    Create professional combined Matplotlib visualization for shear force and bending moment diagrams.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # --- Shear Force and Bending Moment Data ---
    x_values = X_Field
    sf_values = Total_ShearForce
    bm_values = Total_BendingMoment

    # Find max/min values and positions
    max_sf = round(np.max(sf_values), 3)
    min_sf = round(np.min(sf_values), 3)
    max_bm = round(np.max(bm_values), 3)
    min_bm = round(np.min(bm_values), 3)
    
    idx_max_sf = np.argmax(sf_values)
    idx_min_sf = np.argmin(sf_values)
    idx_max_bm = np.argmax(bm_values)
    idx_min_bm = np.argmin(bm_values)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with GridSpec for better control
# Increase the figure height significantly and use GridSpec to control spacing
    fig = plt.figure(figsize=(12, 10), dpi=100)
    gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1], hspace=0.4)
    
    # Shear Force plot
    ax_sf = fig.add_subplot(gs[0])
    ax_sf.plot(x_values, sf_values, color='#1f77b4', linewidth=2.5, label='Shear Force')
    
    # Fill areas
    ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values >= 0), interpolate=True, 
                       alpha=0.3, color='#1f77b4')
    ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values < 0), interpolate=True, 
                       alpha=0.3, color='#ff7f0e')
    
    # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(x_values, sf_values)
    
    # Mark Maximum Total_ShearForce
    ax_sf.plot(max_x, max_y, marker='D', color='darkred', markersize=6, zorder=5, label='Max SF')
    
    # Mark Points of Contraflexure (if any exist)
    if contra_x:
        ax_sf.plot(contra_x, [0]*len(contra_x), marker='o', markerfacecolor='white', markeredgecolor='black', 
                 markersize=6, zorder=5, label='Contraflexure')
    
    # Optional: Add a small legend just for these markers on the BMD
    ax_sf.legend(loc='upper right', frameon=True, fontsize=8)


    # Reference line and styling for SF
    ax_sf.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    ax_sf.set_title('Shear Force Diagram', fontsize=20, pad=15)
    ax_sf.set_ylabel('Shear Force (N)', fontsize=14, labelpad=10)
    ax_sf.grid(True, linestyle='--', alpha=0.5, color='gray')
    ax_sf.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    ax_sf.spines['top'].set_visible(False)
    ax_sf.spines['right'].set_visible(False)
    
    # Annotations for SF
    ax_sf.annotate(f"Max: {max_sf:.2f} N", 
                   xy=(x_values[idx_max_sf], max_sf), 
                   xytext=(10, 20), textcoords='offset points',
                   arrowprops=dict(arrowstyle="->", color='#1f77b4', lw=1.5),
                   fontsize=12, color='#1f77b4', fontweight='bold')
    
    ax_sf.annotate(f"Min: {min_sf:.2f} N", 
                   xy=(x_values[idx_min_sf], min_sf), 
                   xytext=(10, -30), textcoords='offset points',
                   arrowprops=dict(arrowstyle="->", color='#ff7f0e', lw=1.5),
                   fontsize=12, color='#ff7f0e', fontweight='bold')
    ax_bm = fig.add_subplot(gs[1], sharex=ax_sf)
    ax_bm.plot(x_values, bm_values, color='#9467bd', linewidth=2.5, label='Bending Moment')
    
    # Fill areas
    ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values >= 0), interpolate=True, 
                       alpha=0.3, color='#9467bd')
    ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values < 0), interpolate=True, 
                       alpha=0.3, color='#2ca02c')
    # Calculate critical structural points
    max_x, max_y, contra_x = find_critical_points(x_values, sf_values)
    
    # Mark Maximum Bending Moment
    ax_bm.plot(max_x, max_y, marker='D', color='darkred', markersize=6, zorder=5, label='Max BM')
    
    # Mark Points of Contraflexure (if any exist)
    if contra_x:
        ax_bm.plot(contra_x, [0]*len(contra_x), marker='o', markerfacecolor='white', markeredgecolor='black', 
                 markersize=6, zorder=5, label='Contraflexure')
    
    # Optional: Add a small legend just for these markers on the BMD
    ax_bm.legend(loc='upper right', frameon=True, fontsize=8)
    # Reference line and styling for BM
    ax_bm.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    ax_bm.set_title('Bending Moment Diagram', fontsize=20, pad=15)
    ax_bm.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_bm.set_ylabel('Bending Moment (N·m)', fontsize=14, labelpad=10)
    ax_bm.grid(True, linestyle='--', alpha=0.5, color='gray')
    ax_bm.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    ax_bm.spines['top'].set_visible(False)
    ax_bm.spines['right'].set_visible(False)
    
    # Annotations for BM
    ax_bm.annotate(f"Max: {max_bm:.2f} N·m", 
                   xy=(x_values[idx_max_bm], max_bm), 
                   xytext=(10, 20), textcoords='offset points',
                   arrowprops=dict(arrowstyle="->", color='#9467bd', lw=1.5),
                   fontsize=12, color='#9467bd', fontweight='bold')
    
    ax_bm
    # Bending Moment plot
    ax_bm.annotate(f"Min: {min_bm:.2f} N·m", 
                   xy=(x_values[idx_min_bm], min_bm), 
                   xytext=(10, -30), textcoords='offset points',
                   arrowprops=dict(arrowstyle="->", color='#2ca02c', lw=1.5),
                   fontsize=12, color='#2ca02c', fontweight='bold')

    # Final touches
    ax_sf.legend(loc='best', fontsize=12)
    ax_bm.legend(loc='best', fontsize=12)
    plt.tight_layout(h_pad=3.0, pad=2.0)
    plt.show()


def Matplot_combined(X_Field, Total_ShearForce, Total_BendingMoment, Deflection=None, ShearStress=None):
    """
    Create professional combined Matplotlib visualization for multiple beam diagrams.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    Total_ShearForce : numpy.ndarray
        Shear force values at each point
    Total_BendingMoment : numpy.ndarray
        Bending moment values at each point
    Deflection : numpy.ndarray, optional
        Deflection values at each point
    ShearStress : numpy.ndarray, optional
        Shear stress values at each point
        
    Returns:
    --------
    None, displays the plot
    """
    # Determine number of plots based on provided data
    num_plots = 2  # Always include SF and BM
    if Deflection is not None:
        num_plots += 1
    if ShearStress is not None:
        num_plots += 1
    
    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with GridSpec for better control
# Increase the figure height significantly and use GridSpec to control spacing
    fig = plt.figure(figsize=(12, 5 * num_plots), dpi=100) # Increased height per plot
    gs = gridspec.GridSpec(num_plots, 1, height_ratios=[1] * num_plots, hspace=0.6) # Increased hspace
    
    # Add super title
    fig.suptitle('Beam Analysis Results', fontsize=24, y=0.98)
    
    # Colors for consistent styling
    colors = {
        'sf': {'line': '#1f77b4', 'fill_pos': '#1f77b4', 'fill_neg': '#ff7f0e'},
        'bm': {'line': '#9467bd', 'fill_pos': '#9467bd', 'fill_neg': '#2ca02c'},
        'defl': {'line': '#2ca02c', 'fill_pos': '#2ca02c', 'fill_neg': '#d62728'},
        'stress': {'line': '#d62728', 'fill_pos': '#d62728', 'fill_neg': '#ff7f0e'}
    }
    
    # 1. Shear Force plot
    ax_sf = fig.add_subplot(gs[0])
    ax_sf.plot(X_Field, Total_ShearForce, color=colors['sf']['line'], linewidth=2.5, label='Shear Force')
    if 0 < num_plots - 1:
        ax_sf.tick_params(labelbottom=False)
    # Fill areas
    ax_sf.fill_between(X_Field, Total_ShearForce, 0, where=(Total_ShearForce >= 0), 
                     interpolate=True, alpha=0.3, color=colors['sf']['fill_pos'])
    ax_sf.fill_between(X_Field, Total_ShearForce, 0, where=(Total_ShearForce < 0), 
                     interpolate=True, alpha=0.3, color=colors['sf']['fill_neg'])
    
    # Reference line and styling for SF
    ax_sf.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    max_V = np.max(Total_ShearForce)
    min_V = np.min(Total_ShearForce)
    ax_sf.set_title(
        f"Shear Force Diagram\nMax: {format_matplot_sci(max_V)} N  |  Min: {format_matplot_sci(min_V)} N", 
        fontsize=11, 
        fontweight='bold', 
        pad=10
    )
    ax_sf.set_ylabel('Shear Force (N)', fontsize=14, labelpad=10)
    ax_sf.grid(True, linestyle='--', alpha=0.5, color='gray')
    ax_sf.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    ax_sf.spines['top'].set_visible(False)
    ax_sf.spines['right'].set_visible(False)
    
    # Annotations for SF
    max_sf = round(np.max(Total_ShearForce), 3)
    min_sf = round(np.min(Total_ShearForce), 3)
    idx_max_sf = np.argmax(Total_ShearForce)
    idx_min_sf = np.argmin(Total_ShearForce)
    
    ax_sf.annotate(f"Max: {max_sf:.2f} N", 
                 xy=(X_Field[idx_max_sf], max_sf), 
                 xytext=(10, 20), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=colors['sf']['line'], lw=1.5),
                 fontsize=12, color=colors['sf']['line'], fontweight='bold')
    
    ax_sf.annotate(f"Min: {min_sf:.2f} N", 
                 xy=(X_Field[idx_min_sf], min_sf), 
                 xytext=(10, -30), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=colors['sf']['fill_neg'], lw=1.5),
                 fontsize=12, color=colors['sf']['fill_neg'], fontweight='bold')
    
    # 2. Bending Moment plot
    ax_bm = fig.add_subplot(gs[1], sharex=ax_sf)
    ax_bm.plot(X_Field, Total_BendingMoment, color=colors['bm']['line'], linewidth=2.5, label='Bending Moment')
    if 1 < num_plots - 1:
        ax_bm.tick_params(labelbottom=False)
    # Fill areas
    ax_bm.fill_between(X_Field, Total_BendingMoment, 0, where=(Total_BendingMoment >= 0), 
                     interpolate=True, alpha=0.3, color=colors['bm']['fill_pos'])
    ax_bm.fill_between(X_Field, Total_BendingMoment, 0, where=(Total_BendingMoment < 0), 
                     interpolate=True, alpha=0.3, color=colors['bm']['fill_neg'])
    
    # Reference line and styling for BM
    ax_bm.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    max_V = np.max(Total_ShearForce)
    min_V = np.min(Total_ShearForce)
    ax_bm.set_title(
        f"Bending Moment Diagram\nMax: {format_matplot_sci(max_V)} N  |  Min: {format_matplot_sci(min_V)} N", 
        fontsize=11, 
        fontweight='bold', 
        pad=10
    )
    ax_bm.set_ylabel('Bending Moment (N·m)', fontsize=14, labelpad=10)
    ax_bm.grid(True, linestyle='--', alpha=0.5, color='gray')
    ax_bm.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    ax_bm.spines['top'].set_visible(False)
    ax_bm.spines['right'].set_visible(False)
    
    # Annotations for BM
    max_bm = round(np.max(Total_BendingMoment), 3)
    min_bm = round(np.min(Total_BendingMoment), 3)
    idx_max_bm = np.argmax(Total_BendingMoment)
    idx_min_bm = np.argmin(Total_BendingMoment)
    
    ax_bm.annotate(f"Max: {max_bm:.2f} N·m", 
                 xy=(X_Field[idx_max_bm], max_bm), 
                 xytext=(10, 20), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=colors['bm']['line'], lw=1.5),
                 fontsize=12, color=colors['bm']['line'], fontweight='bold')
    
    ax_bm.annotate(f"Min: {min_bm:.2f} N·m", 
                 xy=(X_Field[idx_min_bm], min_bm), 
                 xytext=(10, -30), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=colors['bm']['fill_neg'], lw=1.5),
                 fontsize=12, color=colors['bm']['fill_neg'], fontweight='bold')
    
    current_row = 2
    
    # 3. Deflection plot (if provided)
    if Deflection is not None:
        ax_defl = fig.add_subplot(gs[current_row], sharex=ax_sf)
        ax_defl.plot(X_Field, Deflection, color=colors['defl']['line'], linewidth=2.5, label='Deflection')
        if current_row < num_plots - 1:
         ax_defl.tick_params(labelbottom=False)
        # Fill areas
        ax_defl.fill_between(X_Field, Deflection, 0, where=(Deflection >= 0), 
                           interpolate=True, alpha=0.3, color=colors['defl']['fill_pos'])
        ax_defl.fill_between(X_Field, Deflection, 0, where=(Deflection < 0), 
                           interpolate=True, alpha=0.3, color=colors['defl']['fill_neg'])
        
        # Reference line and styling for Deflection
        ax_defl.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        ax_defl.set_title(
        f"Deflection Diagram\nMax: {format_matplot_sci(max_V)} N  |  Min: {format_matplot_sci(min_V)} N", 
        fontsize=11, 
        fontweight='bold', 
        pad=10
    )
        ax_defl.set_ylabel('Deflection (m)', fontsize=14, labelpad=10)
        ax_defl.grid(True, linestyle='--', alpha=0.5, color='gray')
        ax_defl.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
        ax_defl.spines['top'].set_visible(False)
        ax_defl.spines['right'].set_visible(False)
        # Set y-axis to use scientific notation for very small values
        ax_defl.ticklabel_format(axis='y', style='sci', scilimits=(-4,4))
        
        # Annotations for Deflection
        max_defl = round(np.max(Deflection), 6)
        min_defl = round(np.min(Deflection), 6)
        idx_max_defl = np.argmax(Deflection)
        idx_min_defl = np.argmin(Deflection)
        
        ax_defl.annotate(f"Max: {max_defl:.6f} m", 
                       xy=(X_Field[idx_max_defl], max_defl), 
                       xytext=(10, 20), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color=colors['defl']['line'], lw=1.5),
                       fontsize=12, color=colors['defl']['line'], fontweight='bold')
        
        ax_defl.annotate(f"Min: {min_defl:.6f} m", 
                       xy=(X_Field[idx_min_defl], min_defl), 
                       xytext=(10, -30), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color=colors['defl']['fill_neg'], lw=1.5),
                       fontsize=12, color=colors['defl']['fill_neg'], fontweight='bold')
        
        current_row += 1
    
    # 4. Shear Stress plot (if provided)
    if ShearStress is not None:
        # Handle 2D ShearStress matrix if present
        if len(ShearStress.shape) > 1:
            # Take maximum stress at each position (conservative approach)
            ShearStress = np.max(np.abs(ShearStress), axis=1)
        else:
            ShearStress = ShearStress
            
        ax_stress = fig.add_subplot(gs[current_row], sharex=ax_sf)
        ax_stress.plot(X_Field, ShearStress, color=colors['stress']['line'], linewidth=2.5, label='Shear Stress')
        if current_row < num_plots - 1:
            ax_stress.tick_params(labelbottom=False)
        # Fill areas
        ax_stress.fill_between(X_Field, ShearStress, 0, where=(ShearStress >= 0), 
                             interpolate=True, alpha=0.3, color=colors['stress']['fill_pos'])
        ax_stress.fill_between(X_Field, ShearStress, 0, where=(ShearStress < 0), 
                             interpolate=True, alpha=0.3, color=colors['stress']['fill_neg'])
        
        # Reference line and styling for Shear Stress
        ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        ax_stress.set_title(
        f"Shear Stress Diagram\nMax: {format_matplot_sci(max_V)} N  |  Min: {format_matplot_sci(min_V)} N", 
        fontsize=11, 
        fontweight='bold', 
        pad=10
    )
        ax_stress.set_ylabel('Shear Stress (Pa)', fontsize=14, labelpad=10)
        ax_stress.grid(True, linestyle='--', alpha=0.5, color='gray')
        ax_stress.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
        ax_stress.spines['top'].set_visible(False)
        ax_stress.spines['right'].set_visible(False)
        # Set y-axis to use scientific notation
        ax_stress.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
        
        # Annotations for Shear Stress
        max_stress = round(np.max(ShearStress), 3)
        min_stress = round(np.min(ShearStress), 3)
        idx_max_stress = np.argmax(ShearStress)
        idx_min_stress = np.argmin(ShearStress)
        
        ax_stress.annotate(f"Max: {max_stress:.2e} Pa", 
                         xy=(X_Field[idx_max_stress], max_stress), 
                         xytext=(10, 20), textcoords='offset points',
                         arrowprops=dict(arrowstyle="->", color=colors['stress']['line'], lw=1.5),
                         fontsize=12, color=colors['stress']['line'], fontweight='bold')
        
        ax_stress.annotate(f"Min: {min_stress:.2e} Pa", 
                         xy=(X_Field[idx_min_stress], min_stress), 
                         xytext=(10, -30), textcoords='offset points',
                         arrowprops=dict(arrowstyle="->", color=colors['stress']['fill_neg'], lw=1.5),
                         fontsize=12, color=colors['stress']['fill_neg'], fontweight='bold')
    
    ax_stress.tick_params(labelbottom=False)
    ax_defl.tick_params(labelbottom=False)
    ax_bm.tick_params(labelbottom=False)
    # Add legends
    ax_sf.legend(loc='best', fontsize=12)
    ax_bm.legend(loc='best', fontsize=12)
    if Deflection is not None:
        ax_defl.legend(loc='best', fontsize=12)
    if ShearStress is not None:
        ax_stress.legend(loc='best', fontsize=12)
        
    plt.tight_layout(h_pad=3.0, pad=2.0)
    #plt.tight_layout(rect=[0, 0, 1, 0.97])  # Adjust for the suptitle
    plt.show()

#====================================================================

def Matplot_BendingStress(X_Field, BendingStress):
    """
    Create professional Matplotlib visualization of bending stress.
    
    Parameters:
    -----------
    X_Field : numpy.ndarray
        X-coordinates along the beam
    BendingStress : numpy.ndarray
        Bending stress values at each point
    """
    # Handle 2D BendingStress matrix if present
    if len(BendingStress.shape) > 1:
        BendingStress = np.max(np.abs(BendingStress), axis=1)
    else:
        BendingStress = BendingStress
    
    # --- Bending Stress Diagram Data ---
    x_stress = X_Field
    y_stress = BendingStress

    # Find max/min values and their positions for annotations
    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)
    idx_max_stress = np.argmax(y_stress)
    idx_min_stress = np.argmin(y_stress)

    # Set up professional styling
    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    # Create figure with proper sizing
    fig_stress, ax_stress = plt.subplots(figsize=(10, 6), dpi=100)

    # Plot with professional styling
    ax_stress.plot(x_stress, y_stress, color='#8c564b', linewidth=2.5, label='Bending Stress')
    
    # Fill areas with appropriate colors
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress >= 0), interpolate=True, 
                           alpha=0.3, color='#8c564b')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress < 0), interpolate=True, 
                           alpha=0.3, color='#ff9896')

    # Add reference line
    ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    
    # Set title and labels with professional styling
    ax_stress.set_title('Bending Stress Diagram', fontsize=22, pad=20)
    ax_stress.set_xlabel('Position along Beam (m)', fontsize=14, labelpad=10)
    ax_stress.set_ylabel('Bending Stress (Pa)', fontsize=14, labelpad=10)

    # Annotate Maximum and Minimum values with scientific notation
    ax_stress.annotate(f"Max: {max_stress:.2e} Pa", 
                       xy=(x_stress[idx_max_stress], max_stress), 
                       xytext=(10, 20), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color='#8c564b', lw=1.5),
                       fontsize=12, color='#8c564b', fontweight='bold')

    ax_stress.annotate(f"Min: {min_stress:.2e} Pa", 
                       xy=(x_stress[idx_min_stress], min_stress), 
                       xytext=(10, -30), textcoords='offset points',
                       arrowprops=dict(arrowstyle="->", color='#ff9896', lw=1.5),
                       fontsize=12, color='#ff9896', fontweight='bold')

    # Add legend, grid, and customize ticks
    ax_stress.legend(loc='best', fontsize=12)
    ax_stress.tick_params(axis='both', which='major', labelsize=12, width=1.5, length=5)
    
    # Remove top and right spines for cleaner look
    ax_stress.spines['top'].set_visible(False)
    ax_stress.spines['right'].set_visible(False)
    
    # Improve x-axis tick locating
    ax_stress.xaxis.set_major_locator(MaxNLocator(nbins=10))
    
    # Set y-axis to use scientific notation
    ax_stress.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
    
    # Add subtle grid to improve readability
    ax_stress.grid(True, linestyle='--', alpha=0.5, color='gray')

    # Show plot with tight layout
    fig_stress.tight_layout()
    plt.show()







# =====================================
# Helper Functions for Plotting
# =====================================

def format_loads_for_plotting(loads_dict):
    """
    Transform the dynamic load inputs into a list of tuples 
    in the format required by plotting routines.
    
    Parameters:
    -----------
    loads_dict: Dictionary containing keys "pointloads", "distributedloads",
                "momentloads", and "triangleloads".
                  
    Returns:
    --------
    formatted_loads: A list of loads formatted as:
         ("point_load", pos, magnitude)
         ("udl", start, end, intensity)
         ("moment", pos, moment)
         ("trl", start, end, intensity_start, intensity_end)
    """
    formatted_loads = []
    
    # Process point loads:
    for load in loads_dict.get("pointloads", []):
        pos, Fx, Fy = load
        # Choose which component to plot.
        # Here, we choose vertical if its magnitude is greater (or equal) than horizontal.
        if abs(Fy) >= abs(Fx):
            mag = Fy
        else:
            # For a horizontal load, we take the horizontal force.
            mag = Fx
        formatted_loads.append(("point_load", pos, mag))
        
    # Process distributed loads (UDL):
    for udl in loads_dict.get("distributedloads", []):
        start, end, intensity = udl
        formatted_loads.append(("udl", start, end, intensity))
        
    # Process moment loads:
    for mom in loads_dict.get("momentloads", []):
        pos, moment = mom
        formatted_loads.append(("moment", pos, moment))
    
    # Process triangular loads:
    for trl in loads_dict.get("triangleloads", []):
        # Triangular load defined as [start, end, intensity_start, intensity_end]
        start, end, intensity_start, intensity_end = trl
        formatted_loads.append(("trl", start, end, intensity_start, intensity_end))
    
    return formatted_loads