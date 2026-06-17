import numpy as np
import os
import sys
import plotly.graph_objs as go
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import matplotlib.gridspec as gridspec
from matplotlib.ticker import MaxNLocator
import matplotlib.font_manager as fm
# --- PATH INJECTION (The Fix) ---

# 1. Get the directory of cli.py (ui folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Get the parent directory (src folder)
src_dir = os.path.dirname(current_dir)
# 3. Add the src folder to Python's search path if it's not already there
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
from ui.Menus import get_divisor  # Added import for dynamic units

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

# --- UNIT SCALING HELPER ---
def _get_scale(units):
    """Extracts unit labels and divisors dynamically."""
    if units is None:
        # Safe fallback if run outside the CLI environment
        units = {'length': 'm', 'length_small': 'mm', 'force': 'N', 'moment': 'N·m', 'stress': 'Pa'}
        return units, 1.0, 1.0, 1.0, 1.0, 1.0
    
    l_div = get_divisor(units, 'length')
    ls_div = get_divisor(units, 'length_small')
    f_div = get_divisor(units, 'force')
    m_div = get_divisor(units, 'moment')
    s_div = get_divisor(units, 'length_small')
    
    return units, l_div, ls_div, f_div, m_div, s_div

# --- DATA ANALYSIS HELPERS ---
def find_critical_points(X, Y):
    """
    Finds absolute maximum location and points of zero-crossings.
    """
    idx_max = np.argmax(np.abs(Y))
    max_x = X[idx_max]
    max_y = Y[idx_max]
    
    contraflexure_x = []
    signs = np.sign(Y)
    sign_changes = np.where(np.diff(signs))[0]
    
    for idx in sign_changes:
        if idx > 5 and idx < len(X) - 5:
            dx = X[idx+1] - X[idx]
            dy = Y[idx+1] - Y[idx]
            if dy != 0:
                x_exact = X[idx] - Y[idx] * (dx / dy)
                contraflexure_x.append(x_exact)
                
    return max_x, max_y, contraflexure_x

# =====================================
# Plotly Plotting Functions
# =====================================

def Plotly_shear_force(X_Field, Total_ShearForce, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_shear = X_Field / l_div
    y_shear = Total_ShearForce / f_div
    L_scaled = beam_length / l_div

    max_shear = round(np.max(y_shear), 3)
    min_shear = round(np.min(y_shear), 3)

    trace_shear = go.Scatter(
        x=x_shear, y=y_shear, mode="lines", line=dict(color='#1f77b4', width=3),
        name="Shear Force", hovertemplate=f"<b>%{{y:.2f}} {u['force']}</b><extra></extra>",
        fill="tozeroy", fillcolor="rgba(31,119,180,0.2)"
    )
    
    trace_line = go.Scatter(
        x=[0, L_scaled], y=[0, 0], mode="lines",
        line=dict(color="black", width=1.5, dash='dot'), showlegend=False
    )

    layout_shear = go.Layout(
        title={
            'text': f"<b>Shear Force Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_shear)} {u['force']} | Minimum: {format_plotly_sci(min_shear)} {u['force']}</span>",
            'font': {'family': 'Arial, sans-serif'}, 'x': 0.5, 'y': 0.95
        },
        xaxis=dict(title=f"Position along Beam ({u['length']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        yaxis=dict(title=f"Shear Force ({u['force']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        width=800, height=500, margin=dict(l=80, r=50, t=80, b=80), plot_bgcolor='white', paper_bgcolor='white', hovermode='closest'
    )
    go.Figure(data=[trace_shear, trace_line], layout=layout_shear).show()


def Plotly_Deflection(X_Field, Deflection, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_deflection = X_Field / l_div
    y_deflection = Deflection / ls_div
    L_scaled = beam_length / l_div

    max_deflection = round(np.max(y_deflection), 6)
    min_deflection = round(np.min(y_deflection), 6)

    trace_deflection = go.Scatter(
        x=x_deflection, y=y_deflection, mode="lines", line=dict(color='#2ca02c', width=3),
        name="Deflection", hovertemplate=f"<b>%{{y:.2f}} {u['length_small']}</b><extra></extra>",
        fill="tozeroy", fillcolor="rgba(44,160,44,0.2)"
    )
    
    trace_line = go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False)

    layout_deflection = go.Layout(
        title={
            'text': f"<b>Deflection Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_deflection)} {u['length_small']} | Minimum: {format_plotly_sci(min_deflection)} {u['length_small']}</span>",
            'font': {'family': 'Arial, sans-serif'}, 'x': 0.5, 'y': 0.95
        },
        xaxis=dict(title=f"Position along Beam ({u['length']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        yaxis=dict(title=f"Deflection ({u['length_small']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        width=800, height=500, margin=dict(l=80, r=50, t=80, b=80), plot_bgcolor='white', paper_bgcolor='white', hovermode='closest'
    )
    go.Figure(data=[trace_deflection, trace_line], layout=layout_deflection).show()


def Plotly_ShearStress(X_Field, ShearStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    if len(ShearStress.shape) > 1:
        ShearStress = np.max(np.abs(ShearStress), axis=1)
        
    x_stress = X_Field / l_div
    y_stress = ShearStress / s_div
    L_scaled = beam_length / l_div

    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)

    trace_stress = go.Scatter(
        x=x_stress, y=y_stress, mode="lines", line=dict(color='#d62728', width=3),
        name="Shear Stress", hovertemplate=f"<b>%{{y:.2f}} {u['stress']}</b><extra></extra>",
        fill="tozeroy", fillcolor="rgba(214,39,40,0.2)"
    )
    
    trace_line = go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False)

    layout_stress = go.Layout(
        title={
            'text': f"<b>Shear Stress Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_stress)} {u['stress']} | Minimum: {format_plotly_sci(min_stress)} {u['stress']}</span>",
            'font': {'family': 'Arial, sans-serif'}, 'x': 0.5, 'y': 0.95
        },
        xaxis=dict(title=f"Position along Beam ({u['length']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        yaxis=dict(title=f"Shear Stress ({u['stress']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1, exponentformat='e'),
        width=800, height=500, margin=dict(l=80, r=50, t=80, b=80), plot_bgcolor='white', paper_bgcolor='white', hovermode='closest'
    )
    go.Figure(data=[trace_stress, trace_line], layout=layout_stress).show()


def Plotly_bending_moment(X_Field, Total_BendingMoment, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_bend = X_Field / l_div
    y_bend = Total_BendingMoment / m_div
    L_scaled = beam_length / l_div

    max_bend = round(np.max(y_bend), 3)
    min_bend = round(np.min(y_bend), 3)

    trace_bend = go.Scatter(
        x=x_bend, y=y_bend, mode="lines", line=dict(color='#9467bd', width=3),
        name="Bending Moment", hovertemplate=f"<b>%{{y:.2f}} {u['moment']}</b><extra></extra>",
        fill="tozeroy", fillcolor="rgba(148,103,189,0.2)"
    )
    
    trace_line = go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False)

    layout_bend = go.Layout(
        title={
            'text': f"<b>Bending Moment Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_bend)} {u['moment']} | Minimum: {format_plotly_sci(min_bend)} {u['moment']}</span>",
            'font': {'family': 'Arial, sans-serif'}, 'x': 0.5, 'y': 0.95
        },
        xaxis=dict(title=f"Position along Beam ({u['length']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        yaxis=dict(title=f"Bending Moment ({u['moment']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        width=800, height=500, margin=dict(l=80, r=50, t=80, b=80), plot_bgcolor='white', paper_bgcolor='white', hovermode='closest'
    )
    go.Figure(data=[trace_bend, trace_line], layout=layout_bend).show()


def Plotly_BendingStress(X_Field, BendingStress, beam_length, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    if len(BendingStress.shape) > 1:
        BendingStress = np.max(np.abs(BendingStress), axis=1)
        
    x_stress = X_Field / l_div
    y_stress = BendingStress / s_div
    L_scaled = beam_length / l_div

    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)

    trace_stress = go.Scatter(
        x=x_stress, y=y_stress, mode="lines", line=dict(color='#8c564b', width=3),
        name="Bending Stress", hovertemplate=f"<b>%{{y:.2f}} {u['stress']}</b><extra></extra>",
        fill="tozeroy", fillcolor="rgba(140,86,75,0.2)"
    )
    
    trace_line = go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False)

    annotations_stress = [
        dict(x=x_stress[np.argmax(y_stress)], y=max_stress, text=f"Max: {max_stress:.2e} {u['stress']}", showarrow=True, arrowhead=2, arrowsize=1, ax=0, ay=-30, font=dict(color="#8c564b", size=12)),
        dict(x=x_stress[np.argmin(y_stress)], y=min_stress, text=f"Min: {min_stress:.2e} {u['stress']}", showarrow=True, arrowhead=2, arrowsize=1, ax=0, ay=30, font=dict(color="#8c564b", size=12))
    ]

    layout_stress = go.Layout(
        title={
            'text': f"<b>Bending Stress Diagram</b><br><span style='font-size:14px; color:gray;'>Maximum: {format_plotly_sci(max_stress)} {u['stress']} | Minimum: {format_plotly_sci(min_stress)} {u['stress']}</span>",
            'font': {'family': 'Arial, sans-serif'}, 'x': 0.5, 'y': 0.95
        },
        xaxis=dict(title=f"Position along Beam ({u['length']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1),
        yaxis=dict(title=f"Bending Stress ({u['stress']})", showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1, exponentformat='e'),
        annotations=annotations_stress, width=800, height=500, margin=dict(l=80, r=50, t=80, b=80), plot_bgcolor='white', paper_bgcolor='white', hovermode='closest'
    )
    go.Figure(data=[trace_stress, trace_line], layout=layout_stress).show()


def Plotly_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, plot_type='Both', units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_vals = X_Field / l_div
    sf_vals = Total_ShearForce / f_div
    bm_vals = Total_BendingMoment / m_div
    L_scaled = beam_length / l_div

    num_plots = 2 if plot_type == 'Both' else 1
    subplot_titles = ["Shear Force Diagram", "Bending Moment Diagram"] if plot_type == 'Both' else None
    main_title = " " if plot_type == 'Both' else ("Shear Force Diagram" if plot_type == 'SFD' else "Bending Moment Diagram")

    fig = make_subplots(rows=num_plots, cols=1, subplot_titles=subplot_titles, vertical_spacing=0.18 if num_plots > 1 else 0.0)
    
    if subplot_titles:
        for annotation in fig['layout']['annotations']:
            annotation['font'] = dict(size=16, family='Arial, sans-serif', color='#2c3e50')
            annotation['y'] += 0.02
            
    current_row = 1
    
    if plot_type in ['SFD', 'Both']:
        fig.add_trace(go.Scatter(x=x_vals, y=sf_vals, mode="lines", line=dict(color='#1f77b4', width=3), name="Shear Force", hovertemplate=f"<b>%{{y:.2f}} {u['force']}</b><extra></extra>", fill="tozeroy", fillcolor="rgba(31,119,180,0.15)"), row=current_row, col=1)
        max_x, max_y, contra_x = find_critical_points(x_vals, sf_vals)
        fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='blue', line=dict(width=2, color='darkblue')), name='Max SF', hovertemplate=f"<b>Max SF</b><br>X: %{{x:.2f}} {u['length']}<br>SF: %{{y:.2f}} {u['force']}<extra></extra>"), row=current_row, col=1)
        if contra_x:
            fig.add_trace(go.Scatter(x=contra_x, y=[0]*len(contra_x), mode='markers', marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)), name='Zero SF', hovertemplate=f"<b>Zero SF</b><br>X: %{{x:.2f}} {u['length']}<extra></extra>"), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False), row=current_row, col=1)
        
        fig.update_yaxes(title={'text': f"Shear Force ({u['force']})", 'font': {'size': 13}}, row=current_row, col=1)
        fig.update_xaxes(title={'text': f"Position ({u['length']})" if plot_type != 'Both' else ""}, row=current_row, col=1)
        current_row += 1

    if plot_type in ['BMD', 'Both']:
        fig.add_trace(go.Scatter(x=x_vals, y=bm_vals, mode="lines", line=dict(color='#9467bd', width=3), name="Bending Moment", hovertemplate=f"<b>%{{y:.2f}} {u['moment']}</b><extra></extra>", fill="tozeroy", fillcolor="rgba(148,103,189,0.15)"), row=current_row, col=1)
        fig.add_trace(go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False), row=current_row, col=1)
        max_x, max_y, contra_x = find_critical_points(x_vals, bm_vals)
        fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='purple', line=dict(width=2, color='darkviolet')), name='Max BM', hovertemplate=f"<b>Max BM</b><br>X: %{{x:.2f}} {u['length']}<br>BM: %{{y:.2f}} {u['moment']}<extra></extra>"), row=current_row, col=1)
        if contra_x:
            fig.add_trace(go.Scatter(x=contra_x, y=[0]*len(contra_x), mode='markers', marker=dict(symbol='circle-open', size=10, color='black', line=dict(width=2)), name='Contraflexure', hovertemplate=f"<b>Contraflexure</b><br>X: %{{x:.2f}} {u['length']}<extra></extra>"), row=current_row, col=1)

        fig.update_yaxes(title={'text': f"Bending Moment ({u['moment']})", 'font': {'size': 13}}, row=current_row, col=1)
        fig.update_xaxes(title={'text': f"Position along Beam ({u['length']})", 'font': {'size': 13}}, row=current_row, col=1)

    fig.update_layout(title={'text': main_title, 'x': 0.5, 'y': 0.96, 'xanchor': 'center', 'font': {'size': 22, 'family': 'Arial'}}, height=450 * num_plots, width=850, margin=dict(l=80, r=50, t=130 if num_plots == 2 else 100, b=80), plot_bgcolor='white', paper_bgcolor='white')
    fig.show()


def Plotly_combined_diagrams(X_Field, Total_ShearForce, Total_BendingMoment, beam_length, Deflection=None, ShearStress=None, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    step = 5
    x_vals = X_Field[::step] / l_div
    sf_vals = Total_ShearForce[::step] / f_div
    bm_vals = Total_BendingMoment[::step] / m_div
    L_scaled = beam_length / l_div
    
    num_rows = 2
    subplot_titles = ["Shear Force Diagram", "Bending Moment Diagram"]
    
    if Deflection is not None:
        defl_vals = Deflection[::step] / ls_div
        num_rows += 1
        subplot_titles.append("Deflection Diagram")
    if ShearStress is not None:
        if len(ShearStress.shape) > 1:
            ShearStress = np.max(np.abs(ShearStress), axis=1)
        stress_vals = ShearStress[::step] / s_div
        num_rows += 1
        subplot_titles.append("Shear Stress Diagram")
        
    fig = make_subplots(rows=num_rows, cols=1, subplot_titles=subplot_titles, vertical_spacing=0.12)
    
    for i in range(1, num_rows + 1):
        fig.add_trace(go.Scatter(x=[0, L_scaled], y=[0, 0], mode="lines", line=dict(color="black", width=1.5, dash='dot'), showlegend=False), row=i, col=1)
    
    # 1. Shear Force
    fig.add_trace(go.Scatter(x=x_vals, y=sf_vals, mode="lines", line=dict(color='#1f77b4', width=2.5), fill="tozeroy", fillcolor="rgba(31,119,180,0.2)", name="Shear Force", hovertemplate=f"<b>%{{y:.2f}} {u['force']}</b><extra></extra>"), row=1, col=1)
    max_x, max_y, contra_x = find_critical_points(x_vals, sf_vals)
    fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='blue', line=dict(width=2, color='darkblue')), name='Max SF', hovertemplate=f"<b>Max SF</b><br>X: %{{x:.2f}} {u['length']}<br>Y: %{{y:.2f}} {u['force']}<extra></extra>"), row=1, col=1)
    
    # 2. Bending Moment
    fig.add_trace(go.Scatter(x=x_vals, y=bm_vals, mode="lines", line=dict(color='#9467bd', width=2.5), fill="tozeroy", fillcolor="rgba(148,103,189,0.2)", name="Bending Moment", hovertemplate=f"<b>%{{y:.2f}} {u['moment']}</b><extra></extra>"), row=2, col=1)
    max_x, max_y, contra_x = find_critical_points(x_vals, bm_vals)
    fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='purple', line=dict(width=2, color='darkviolet')), name='Max BM', hovertemplate=f"<b>Max BM</b><br>X: %{{x:.2f}} {u['length']}<br>Y: %{{y:.2f}} {u['moment']}<extra></extra>"), row=2, col=1)
    
    current_row = 3
    # 3. Deflection
    if Deflection is not None:
        fig.add_trace(go.Scatter(x=x_vals, y=defl_vals, mode="lines", line=dict(color='#2ca02c', width=2.5), fill="tozeroy", fillcolor="rgba(44,160,44,0.2)", name="Deflection", hovertemplate=f"<b>%{{y:.2f}} {u['length_small']}</b><extra></extra>"), row=current_row, col=1)
        max_x, max_y, contra_x = find_critical_points(x_vals, defl_vals)
        fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='green', line=dict(width=2, color='lime')), name='Max Defl', hovertemplate=f"<b>Max DF</b><br>X: %{{x:.2f}} {u['length']}<br>Y: %{{y:.2f}} {u['length_small']}<extra></extra>"), row=current_row, col=1)
        current_row += 1
        
    # 4. Shear Stress
    if ShearStress is not None:
        fig.add_trace(go.Scatter(x=x_vals, y=stress_vals, mode="lines", line=dict(color='#d62728', width=2.5), fill="tozeroy", fillcolor="rgba(214,39,40,0.2)", name="Shear Stress", hovertemplate=f"<b>%{{y:.2f}} {u['stress']}</b><extra></extra>"), row=current_row, col=1)
        max_x, max_y, contra_x = find_critical_points(x_vals, stress_vals)
        fig.add_trace(go.Scatter(x=[max_x], y=[max_y], mode='markers', marker=dict(symbol='diamond', size=10, color='red', line=dict(width=2, color='darkred')), name='Max Stress', hovertemplate=f"<b>Max SS</b><br>X: %{{x:.2f}} {u['length']}<br>Y: %{{y:.2f}} {u['stress']}<extra></extra>"), row=current_row, col=1)

    fig.update_layout(height=250 * num_rows + 350, width=900, margin=dict(l=80, r=50, t=100, b=50), plot_bgcolor='white', paper_bgcolor='white')
    
    for i in range(1, num_rows):
        fig.update_xaxes(showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1, title="", row=i, col=1)
    
    fig.update_xaxes(title={'text': f"Position along Beam ({u['length']})"}, showgrid=True, gridcolor='rgba(211,211,211,0.5)', mirror=True, linecolor='black', linewidth=1, row=num_rows, col=1)
    fig.update_yaxes(
        title=dict(
            text=f"Shear Force ({units['force']})",
            exponentformat="power"   # <-- REMOVE FROM HERE
        ),
        row=1, col=1
    )
    fig.update_yaxes(
    title=dict(text=f"Bending Moment ({units['moment']}·{units['length']})"),
    exponentformat="power",  # <--- Moved outside the title dict
    row=2, col=1
)
    
    current_row = 3
    if Deflection is not None:
        fig.update_yaxes(
    title=dict(text=f"Deflection ({units['length_small']})"),
    exponentformat="power",  # <--- Moved outside the title dict
    row=3, col=1
)
        current_row += 1
    if ShearStress is not None:
        fig.update_yaxes(
    title=dict(text=f"Shear Stress ({units['stress']})"),
    exponentformat="power",  # <--- Moved outside the title dict
    row=current_row, col=1
)

    
    fig.show()

# =====================================
# Matplotlib Plotting Functions
# =====================================

def Matplot_sfd_bmd(X_Field, Total_ShearForce, Total_BendingMoment, plot_type='Both', units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_values = X_Field / l_div
    sf_values = Total_ShearForce / f_div
    bm_values = Total_BendingMoment / m_div

    plt.rcParams['font.family'] = 'Arial'
    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.edgecolor'] = 'black'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.alpha'] = 0.7
    
    num_plots = 2 if plot_type == 'Both' else 1
    fig = plt.figure(figsize=(12, 5 * num_plots), dpi=100)
    gs = gridspec.GridSpec(num_plots, 1, height_ratios=[1] * num_plots, hspace=0.4)
    
    current_row = 0
    ax_sf = None
    
    if plot_type in ['SFD', 'Both']:
        ax_sf = fig.add_subplot(gs[current_row])
        max_sf = round(np.max(sf_values), 3)
        min_sf = round(np.min(sf_values), 3)
        
        ax_sf.plot(x_values, sf_values, color='#1f77b4', linewidth=2.5, label='Shear Force')
        ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values >= 0), alpha=0.3, color='#1f77b4')
        ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values < 0), alpha=0.3, color='#ff7f0e')
        
        max_x, max_y, contra_x = find_critical_points(x_values, sf_values)
        ax_sf.plot(max_x, max_y, marker='D', color='darkred', markersize=6, zorder=5, label='Max SF')
        if contra_x:
            ax_sf.plot(contra_x, [0]*len(contra_x), marker='o', markerfacecolor='white', markeredgecolor='black', markersize=6, zorder=5)
        
        ax_sf.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        ax_sf.set_title('Shear Force Diagram', fontsize=20, pad=15)
        if plot_type == 'SFD':
            ax_sf.set_xlabel(f'Position along Beam ({u["length"]})', fontsize=14, labelpad=10)
        ax_sf.set_ylabel(f'Shear Force ({u["force"]})', fontsize=14, labelpad=10)
        ax_sf.grid(True)
        ax_sf.spines['top'].set_visible(False)
        ax_sf.spines['right'].set_visible(False)
        
        ax_sf.annotate(f"Max: {max_sf:.2f} {u['force']}", xy=(x_values[np.argmax(sf_values)], max_sf), xytext=(10, 20), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#1f77b4', lw=1.5), color='#1f77b4', fontweight='bold')
        ax_sf.annotate(f"Min: {min_sf:.2f} {u['force']}", xy=(x_values[np.argmin(sf_values)], min_sf), xytext=(10, -30), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#ff7f0e', lw=1.5), color='#ff7f0e', fontweight='bold')
        current_row += 1

    if plot_type in ['BMD', 'Both']:
        ax_bm = fig.add_subplot(gs[current_row], sharex=ax_sf) if plot_type == 'Both' else fig.add_subplot(gs[current_row])
        max_bm = round(np.max(bm_values), 3)
        min_bm = round(np.min(bm_values), 3)

        ax_bm.plot(x_values, bm_values, color='#9467bd', linewidth=2.5, label='Bending Moment')
        ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values >= 0), alpha=0.3, color='#9467bd')
        ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values < 0), alpha=0.3, color='#2ca02c')
                           
        max_x, max_y, contra_x = find_critical_points(x_values, bm_values)
        ax_bm.plot(max_x, max_y, marker='D', color='darkred', markersize=6, zorder=5, label='Max BM')
        if contra_x:
            ax_bm.plot(contra_x, [0]*len(contra_x), marker='o', markerfacecolor='white', markeredgecolor='black', markersize=6, zorder=5)
        
        ax_bm.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        ax_bm.set_title('Bending Moment Diagram', fontsize=20, pad=15)
        ax_bm.set_xlabel(f'Position along Beam ({u["length"]})', fontsize=14, labelpad=10)
        ax_bm.set_ylabel(f'Bending Moment ({u["moment"]})', fontsize=14, labelpad=10)
        ax_bm.grid(True)
        ax_bm.spines['top'].set_visible(False)
        ax_bm.spines['right'].set_visible(False)
        
        ax_bm.annotate(f"Max: {max_bm:.2f} {u['moment']}", xy=(x_values[np.argmax(bm_values)], max_bm), xytext=(10, 20), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#9467bd', lw=1.5), color='#9467bd', fontweight='bold')
        ax_bm.annotate(f"Min: {min_bm:.2f} {u['moment']}", xy=(x_values[np.argmin(bm_values)], min_bm), xytext=(10, -30), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#2ca02c', lw=1.5), color='#2ca02c', fontweight='bold')

    plt.tight_layout(h_pad=3.0, pad=2.0)
    plt.show()

def Matplot_ShearStress(X_Field, Shear_stress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    if len(Shear_stress.shape) > 1:
        y_stress = np.max(np.abs(Shear_stress), axis=1) / s_div
    else:
        y_stress = Shear_stress / s_div
        
    x_stress = X_Field / l_div

    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)

    plt.rcParams['font.family'] = 'Arial'
    fig_stress, ax_stress = plt.subplots(figsize=(10, 6), dpi=100)

    ax_stress.plot(x_stress, y_stress, color='#d62728', linewidth=2.5, label='Shear Stress')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress >= 0), alpha=0.3, color='#d62728')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress < 0), alpha=0.3, color='#ff7f0e')

    ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    ax_stress.set_title('Shear Stress Diagram', fontsize=22, pad=20)
    ax_stress.set_xlabel(f'Position along Beam ({u["length"]})', fontsize=14, labelpad=10)
    ax_stress.set_ylabel(f'Shear Stress ({u["stress"]})', fontsize=14, labelpad=10)

    ax_stress.annotate(f"Max: {max_stress:.2e} {u['stress']}", xy=(x_stress[np.argmax(y_stress)], max_stress), xytext=(10, 30), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.5), color='#d62728', fontweight='bold')
    ax_stress.annotate(f"Min: {min_stress:.2e} {u['stress']}", xy=(x_stress[np.argmin(y_stress)], min_stress), xytext=(10, -40), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#ff7f0e', lw=1.5), color='#ff7f0e', fontweight='bold')

    ax_stress.spines['top'].set_visible(False)
    ax_stress.spines['right'].set_visible(False)
    ax_stress.grid(True, linestyle='--', alpha=0.5, color='gray')
    fig_stress.tight_layout()
    plt.show()

def Matplot_BendingStress(X_Field, BendingStress, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    if len(BendingStress.shape) > 1:
        y_stress = np.max(np.abs(BendingStress), axis=1) / s_div
    else:
        y_stress = BendingStress / s_div
        
    x_stress = X_Field / l_div

    max_stress = round(np.max(y_stress), 3)
    min_stress = round(np.min(y_stress), 3)

    plt.rcParams['font.family'] = 'Arial'
    fig_stress, ax_stress = plt.subplots(figsize=(10, 6), dpi=100)

    ax_stress.plot(x_stress, y_stress, color='#8c564b', linewidth=2.5, label='Bending Stress')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress >= 0), alpha=0.3, color='#8c564b')
    ax_stress.fill_between(x_stress, y_stress, 0, where=(y_stress < 0), alpha=0.3, color='#ff9896')

    ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    ax_stress.set_title('Bending Stress Diagram', fontsize=22, pad=20)
    ax_stress.set_xlabel(f'Position along Beam ({u["length"]})', fontsize=14, labelpad=10)
    ax_stress.set_ylabel(f'Bending Stress ({u["stress"]})', fontsize=14, labelpad=10)

    ax_stress.annotate(f"Max: {max_stress:.2e} {u['stress']}", xy=(x_stress[np.argmax(y_stress)], max_stress), xytext=(10, 20), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#8c564b', lw=1.5), color='#8c564b', fontweight='bold')
    ax_stress.annotate(f"Min: {min_stress:.2e} {u['stress']}", xy=(x_stress[np.argmin(y_stress)], min_stress), xytext=(10, -30), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#ff9896', lw=1.5), color='#ff9896', fontweight='bold')

    ax_stress.spines['top'].set_visible(False)
    ax_stress.spines['right'].set_visible(False)
    ax_stress.grid(True, linestyle='--', alpha=0.5, color='gray')
    fig_stress.tight_layout()
    plt.show()

def Matplot_Deflection(X_Field, Deflection, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_defl = X_Field / l_div
    y_defl = Deflection / ls_div

    max_defl = round(np.max(y_defl), 6)
    min_defl = round(np.min(y_defl), 6)

    plt.rcParams['font.family'] = 'Arial'
    fig_defl, ax_defl = plt.subplots(figsize=(10, 6), dpi=100)

    ax_defl.plot(x_defl, y_defl, color='#2ca02c', linewidth=2.5, label='Deflection')
    ax_defl.fill_between(x_defl, y_defl, 0, where=(y_defl >= 0), alpha=0.3, color='#2ca02c')
    ax_defl.fill_between(x_defl, y_defl, 0, where=(y_defl < 0), alpha=0.3, color='#d62728')

    ax_defl.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    ax_defl.set_title('Deflection Diagram', fontsize=22, pad=20)
    ax_defl.set_xlabel(f'Position along Beam ({u["length"]})', fontsize=14, labelpad=10)
    ax_defl.set_ylabel(f'Deflection ({u["length_small"]})', fontsize=14, labelpad=10)

    ax_defl.annotate(f"Max: {max_defl:.6f} {u['length_small']}", xy=(x_defl[np.argmax(y_defl)], max_defl), xytext=(10, 30), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#2ca02c', lw=1.5), color='#2ca02c', fontweight='bold')
    ax_defl.annotate(f"Min: {min_defl:.6f} {u['length_small']}", xy=(x_defl[np.argmin(y_defl)], min_defl), xytext=(10, -40), textcoords='offset points', arrowprops=dict(arrowstyle="->", color='#d62728', lw=1.5), color='#d62728', fontweight='bold')

    ax_defl.spines['top'].set_visible(False)
    ax_defl.spines['right'].set_visible(False)
    ax_defl.grid(True, linestyle='--', alpha=0.5, color='gray')
    fig_defl.tight_layout()
    plt.show()

def Matplot_combined(X_Field, Total_ShearForce, Total_BendingMoment, Deflection=None, ShearStress=None, units=None):
    u, l_div, ls_div, f_div, m_div, s_div = _get_scale(units)
    
    x_values = X_Field / l_div
    sf_values = Total_ShearForce / f_div
    bm_values = Total_BendingMoment / m_div
    
    num_plots = 2
    if Deflection is not None:
        Deflection = Deflection / ls_div
        num_plots += 1
    if ShearStress is not None:
        if len(ShearStress.shape) > 1:
            ShearStress = np.max(np.abs(ShearStress), axis=1)
        ShearStress = ShearStress / s_div
        num_plots += 1
        
    plt.rcParams['font.family'] = 'Arial'
    fig = plt.figure(figsize=(12, 5 * num_plots), dpi=100)
    gs = gridspec.GridSpec(num_plots, 1, height_ratios=[1] * num_plots, hspace=0.6)
    fig.suptitle('Beam Analysis Results', fontsize=24, y=0.98)
    
    # 1. Shear Force
    ax_sf = fig.add_subplot(gs[0])
    ax_sf.plot(x_values, sf_values, color='#1f77b4', linewidth=2.5)
    if num_plots > 1: ax_sf.tick_params(labelbottom=False)
    ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values >= 0), alpha=0.3, color='#1f77b4')
    ax_sf.fill_between(x_values, sf_values, 0, where=(sf_values < 0), alpha=0.3, color='#ff7f0e')
    ax_sf.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    max_sf = np.max(sf_values)
    min_sf = np.min(sf_values)
    ax_sf.set_title(f"Shear Force Diagram\nMax: {format_matplot_sci(max_sf)} {u['force']}  |  Min: {format_matplot_sci(min_sf)} {u['force']}", fontsize=11, fontweight='bold', pad=10)
    ax_sf.set_ylabel(f"Shear Force ({u['force']})", fontsize=14, labelpad=10)
    ax_sf.grid(True)
    ax_sf.spines['top'].set_visible(False)
    ax_sf.spines['right'].set_visible(False)
    
    # 2. Bending Moment
    ax_bm = fig.add_subplot(gs[1], sharex=ax_sf)
    ax_bm.plot(x_values, bm_values, color='#9467bd', linewidth=2.5)
    if num_plots > 2: ax_bm.tick_params(labelbottom=False)
    ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values >= 0), alpha=0.3, color='#9467bd')
    ax_bm.fill_between(x_values, bm_values, 0, where=(bm_values < 0), alpha=0.3, color='#2ca02c')
    ax_bm.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
    max_bm = np.max(bm_values)
    min_bm = np.min(bm_values)
    ax_bm.set_title(f"Bending Moment Diagram\nMax: {format_matplot_sci(max_bm)} {u['moment']}  |  Min: {format_matplot_sci(min_bm)} {u['moment']}", fontsize=11, fontweight='bold', pad=10)
    ax_bm.set_ylabel(f"Bending Moment ({u['moment']})", fontsize=14, labelpad=10)
    ax_bm.grid(True)
    ax_bm.spines['top'].set_visible(False)
    ax_bm.spines['right'].set_visible(False)
    
    current_row = 2
    
    # 3. Deflection
    if Deflection is not None:
        ax_defl = fig.add_subplot(gs[current_row], sharex=ax_sf)
        ax_defl.plot(x_values, Deflection, color='#2ca02c', linewidth=2.5)
        if current_row < num_plots - 1: ax_defl.tick_params(labelbottom=False)
        ax_defl.fill_between(x_values, Deflection, 0, where=(Deflection >= 0), alpha=0.3, color='#2ca02c')
        ax_defl.fill_between(x_values, Deflection, 0, where=(Deflection < 0), alpha=0.3, color='#d62728')
        ax_defl.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        max_defl = np.max(Deflection)
        min_defl = np.min(Deflection)
        ax_defl.set_title(f"Deflection Diagram\nMax: {format_matplot_sci(max_defl)} {u['length_small']}  |  Min: {format_matplot_sci(min_defl)} {u['length_small']}", fontsize=11, fontweight='bold', pad=10)
        ax_defl.set_ylabel(f"Deflection ({u['length_small']})", fontsize=14, labelpad=10)
        ax_defl.grid(True)
        ax_defl.spines['top'].set_visible(False)
        ax_defl.spines['right'].set_visible(False)
        current_row += 1
        
    # 4. Shear Stress
    if ShearStress is not None:
        ax_stress = fig.add_subplot(gs[current_row], sharex=ax_sf)
        ax_stress.plot(x_values, ShearStress, color='#d62728', linewidth=2.5)
        ax_stress.fill_between(x_values, ShearStress, 0, where=(ShearStress >= 0), alpha=0.3, color='#d62728')
        ax_stress.fill_between(x_values, ShearStress, 0, where=(ShearStress < 0), alpha=0.3, color='#ff7f0e')
        ax_stress.axhline(y=0, color='black', linewidth=1.5, linestyle='--')
        max_stress = np.max(ShearStress)
        min_stress = np.min(ShearStress)
        ax_stress.set_title(f"Shear Stress Diagram\nMax: {format_matplot_sci(max_stress)} {u['stress']}  |  Min: {format_matplot_sci(min_stress)} {u['stress']}", fontsize=11, fontweight='bold', pad=10)
        ax_stress.set_ylabel(f"Shear Stress ({u['stress']})", fontsize=14, labelpad=10)
        ax_stress.grid(True)
        ax_stress.spines['top'].set_visible(False)
        ax_stress.spines['right'].set_visible(False)
        
    plt.xlabel(f"Position along Beam ({u['length']})", fontsize=14, labelpad=10)
    plt.tight_layout(h_pad=3.0, pad=2.0)
    plt.show()

# =====================================
# Helper Functions for Plotting
# =====================================

def format_loads_for_plotting(loads_dict):
    """
    Transform the dynamic load inputs into a list of tuples.
    (Note: Scaling happens down the line in beam_plot.py, so we leave as base SI here).
    """
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