"""
plot_theme.py
=============
Single source of visual truth for every 2D structural diagram in the
analysis/design checker.  Import this module once and all Plotly and
Matplotlib figures inherit one consistent, commercial-grade look
(think SAP2000 / RFEM / STAAD report graphics).

Why this exists
---------------
Previously every plotting function hard-coded its own colours, fonts,
margins and grid styling.  That reads as "ad-hoc" and is the #1 thing
that separates a hobby plot from a commercial product.  Centralising the
identity here means:

  * one palette, one font, one grid -> instant visual consistency
  * white-labelling / rebranding is a one-line change
  * future diagrams automatically match

Public API
----------
    register_plotly_theme()                  -> registers + activates the template
    plotly_layout(title, subtitle, ...)      -> a ready-to-use go.Layout
    finalize_plotly(fig, ...)                -> watermark + returns show() config
    PLOTLY_CONFIG                            -> high-res export / clean modebar config

    apply_matplotlib_theme()                 -> sets global rcParams
    style_mpl_axes(ax, accent=...)           -> spines / grid / ticks for one Axes
    add_mpl_watermark(fig)                   -> subtle brand mark
    stat_subtitle(label, vmax, vmin, unit)   -> formatted "Max .. | Min .." string

    SERIES, palette constants, fmt_value()
"""

from __future__ import annotations
import plotly.graph_objs as go
import plotly.io as pio

# --------------------------------------------------------------------------
#  BRAND / WHITE-LABEL  (override these two lines to rebrand the whole suite)
# --------------------------------------------------------------------------
BRAND_NAME      = "STRUCT·FEA"
BRAND_WATERMARK = "STRUCT·FEA  |  Structural Analysis & Design"

# --------------------------------------------------------------------------
#  TYPOGRAPHY
# --------------------------------------------------------------------------
FONT_FAMILY    = "Inter, 'Segoe UI', Arial, Helvetica, sans-serif"
MPL_FONT_STACK = ["Inter", "Segoe UI", "Arial", "Helvetica", "DejaVu Sans"]

TITLE_SIZE     = 19
SUBTITLE_SIZE  = 13
AXIS_TITLE_SIZE = 13
TICK_SIZE      = 12
LEGEND_SIZE    = 12

# --------------------------------------------------------------------------
#  CORE PALETTE  (muted, engineering, professional — no neon primaries)
# --------------------------------------------------------------------------
INK         = "#1F2933"   # primary text / titles
SUBTLE_INK  = "#6B7682"   # secondary text / subtitles / watermark
STRUCTURE   = "#334155"   # the beam / structural member
SUPPORT     = "#334155"   # supports drawn in the same structural ink
AXIS        = "#AAB3BD"   # axis lines + ticks
GRID        = "#ECEFF3"   # gridlines (very light)
ZERO_LINE   = "#5B6670"   # datum / zero axis
PAPER_BG    = "#FFFFFF"
PLOT_BG     = "#FFFFFF"
PANEL_BG    = "#F4F7FA"   # subtle header / stat band
BORDER      = "#DCE3EA"
CRITICAL    = "#F0A500"   # max / critical marker (amber)
NODE_MARKER = "#11161C"   # contraflexure / zero-crossing nodes

# --------------------------------------------------------------------------
#  PER-QUANTITY ACCENTS  (line colour + soft translucent fill)
# --------------------------------------------------------------------------
SERIES = {
    "shear":       {"line": "#1E66F5", "fill": "rgba(30,102,245,0.12)",  "label": "Shear Force"},
    "moment":      {"line": "#D64550", "fill": "rgba(214,69,80,0.12)",   "label": "Bending Moment"},
    "deflect":     {"line": "#0E9F6E", "fill": "rgba(14,159,110,0.12)",  "label": "Deflection"},
    "shearstress": {"line": "#0E7C86", "fill": "rgba(14,124,134,0.12)",  "label": "Shear Stress"},
    "bendstress":  {"line": "#7C4DCB", "fill": "rgba(124,77,203,0.12)",  "label": "Bending Stress"},
}

# Load / action accents for the schematic
LOAD_POINT   = "#D64550"   # downward point loads (red)
LOAD_POINT_UP = "#0E9F6E"  # upward point loads (green)
LOAD_DIST    = "#1E66F5"   # distributed loads (blue)
LOAD_MOMENT  = "#7C4DCB"   # moments (violet)
REACTION_V   = "#0E9F6E"   # vertical reactions (green)
REACTION_H   = "#E08600"   # horizontal reactions (amber)


# ==========================================================================
#  NUMBER FORMATTING
# ==========================================================================
def fmt_value(val, sig=2):
    """Human-readable value with scientific notation for extremes (Plotly HTML)."""
    if val is None:
        return "—"
    a = abs(val)
    if a != 0 and (a >= 1e5 or a < 1e-3):
        base, exp = f"{val:.{sig}e}".split("e")
        return f"{base} &times; 10<sup>{int(exp)}</sup>"
    return f"{val:,.{sig}f}"


def fmt_value_mpl(val, sig=2):
    """Same as fmt_value but with Matplotlib math-text exponents."""
    if val is None:
        return "—"
    a = abs(val)
    if a != 0 and (a >= 1e5 or a < 1e-3):
        base, exp = f"{val:.{sig}e}".split("e")
        return rf"${base}\times10^{{{int(exp)}}}$"
    return f"{val:,.{sig}f}"


def fmt_load(val):
    """Clean label for load magnitudes: thousands separators, sci only for extremes."""
    if val is None:
        return "—"
    a = abs(val)
    if a != 0 and (a >= 1e6 or a < 1e-2):
        base, exp = f"{val:.2e}".split("e")
        return f"{base} &times; 10<sup>{int(exp)}</sup>"
    if a >= 1000:
        return f"{val:,.0f}"
    return f"{val:,.2f}"


def stat_subtitle(vmax, vmin, unit, html=True, sig=2):
    """Build a consistent 'Max … | Min …' stat string."""
    f = fmt_value if html else fmt_value_mpl
    sep = "&nbsp;&nbsp;|&nbsp;&nbsp;" if html else "   |   "
    return f"Max {f(vmax, sig)} {unit}{sep}Min {f(vmin, sig)} {unit}"


# ==========================================================================
#  PLOTLY THEME
# ==========================================================================
def register_plotly_theme(activate=True):
    """Register the 'struct_fea' Plotly template and (optionally) activate it."""
    axis_common = dict(
        showgrid=True, gridcolor=GRID, gridwidth=1,
        zeroline=False,
        showline=True, linecolor=AXIS, linewidth=1.2, mirror=True,
        ticks="outside", tickcolor=AXIS, ticklen=5, tickwidth=1,
        tickfont=dict(size=TICK_SIZE, color=INK),
        title=dict(font=dict(size=AXIS_TITLE_SIZE, color=SUBTLE_INK)),
        automargin=True,
    )
    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(family=FONT_FAMILY, size=TICK_SIZE, color=INK),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        colorway=[s["line"] for s in SERIES.values()],
        xaxis=axis_common,
        yaxis=axis_common,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white", bordercolor=BORDER,
            font=dict(family=FONT_FAMILY, size=12, color=INK),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0,
            font=dict(size=LEGEND_SIZE, color=INK),
            bgcolor="rgba(255,255,255,0)", borderwidth=0,
        ),
        margin=dict(l=80, r=40, t=96, b=70),
    )
    pio.templates["struct_fea"] = template
    if activate:
        pio.templates.default = "struct_fea"
    return template


def plotly_layout(title, subtitle=None, xtitle="", ytitle="",
                  width=860, height=520, schematic=False, **kw):
    """
    Build a consistent go.Layout.

    title     : main diagram title (bold)
    subtitle  : grey stat line under the title (e.g. Max/Min) — HTML allowed
    schematic : True hides the y grid/zeroline for structural schematics
    """
    register_plotly_theme(activate=False)
    title_html = f"<b>{title}</b>"
    if subtitle:
        title_html += (f"<br><span style='font-size:{SUBTITLE_SIZE}px;"
                       f"color:{SUBTLE_INK};font-weight:400'>{subtitle}</span>")

    layout = go.Layout(
        template="struct_fea",
        title=dict(text=title_html, x=0.5, xanchor="center", y=0.94,
                   yanchor="top", font=dict(size=TITLE_SIZE, color=INK)),
        width=width, height=height,
        xaxis=dict(title=dict(text=xtitle)),
        yaxis=dict(title=dict(text=ytitle)),
    )
    if schematic:
        layout.xaxis.update(showgrid=False, zeroline=False)
        layout.yaxis.update(showgrid=False, zeroline=True, zerolinecolor=BORDER,
                            zerolinewidth=1, showticklabels=False, title=dict(text=""))
    layout.update(kw)
    return layout


def add_plotly_watermark(fig, text=BRAND_WATERMARK):
    """Add a subtle product watermark in the lower-right of the paper area."""
    fig.add_annotation(
        text=text, xref="paper", yref="paper", x=1.0, y=-0.16,
        xanchor="right", yanchor="bottom", showarrow=False,
        font=dict(size=10, color="#C2CBD3", family=FONT_FAMILY),
    )
    return fig


def zero_datum(x0, x1):
    """A clean dashed datum line trace from x0 to x1 at y=0."""
    return go.Scatter(
        x=[x0, x1], y=[0, 0], mode="lines",
        line=dict(color=ZERO_LINE, width=1.3, dash="dot"),
        hoverinfo="skip", showlegend=False,
    )


def max_marker(x, y, accent, name, unit, length_unit):
    """Consistent critical-value diamond marker."""
    return go.Scatter(
        x=[x], y=[y], mode="markers",
        marker=dict(symbol="diamond", size=11, color=CRITICAL,
                    line=dict(width=1.6, color=accent)),
        name=name, showlegend=False,
        hovertemplate=(f"<b>{name}</b><br>x = %{{x:.3f}} {length_unit}"
                       f"<br>%{{y:.3f}} {unit}<extra></extra>"),
    )


def node_markers(xs, name, length_unit):
    """Consistent zero-crossing / contraflexure open-circle markers."""
    if not len(xs):
        return None
    return go.Scatter(
        x=list(xs), y=[0] * len(xs), mode="markers",
        marker=dict(symbol="circle-open", size=9, color=NODE_MARKER,
                    line=dict(width=1.8)),
        name=name, showlegend=False,
        hovertemplate=f"<b>{name}</b><br>x = %{{x:.3f}} {length_unit}<extra></extra>",
    )


# High-resolution export + decluttered modebar (passed to fig.show(config=...))
PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
    "toImageButtonOptions": {
        "format": "png", "filename": "structural_diagram",
        "scale": 3, "height": 600, "width": 1000,
    },
    "responsive": True,
}


# ==========================================================================
#  MATPLOTLIB THEME
# ==========================================================================
def apply_matplotlib_theme():
    """Set global Matplotlib rcParams for the commercial look."""
    import matplotlib as mpl
    import matplotlib.font_manager as fm

    available = {f.name for f in fm.fontManager.ttflist}
    family = next((f for f in MPL_FONT_STACK if f in available), "DejaVu Sans")

    mpl.rcParams.update({
        "font.family": family,
        "font.size": 12,
        "text.color": INK,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 1.1,
        "axes.labelcolor": SUBTLE_INK,
        "axes.labelsize": AXIS_TITLE_SIZE,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 1.0,
        "grid.linestyle": "-",
        "xtick.color": SUBTLE_INK,
        "ytick.color": SUBTLE_INK,
        "xtick.labelsize": TICK_SIZE,
        "ytick.labelsize": TICK_SIZE,
        "figure.facecolor": PAPER_BG,
        "axes.facecolor": PLOT_BG,
        "legend.frameon": False,
        "legend.fontsize": LEGEND_SIZE,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
    })
    return family


def si_tick_formatter():
    """Matplotlib FuncFormatter giving k / M / G suffixes (matches Plotly ticks)."""
    from matplotlib.ticker import FuncFormatter

    def _fmt(v, _pos):
        a = abs(v)
        if a == 0:
            return "0"
        for div, suf in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
            if a >= div:
                val = v / div
                return (f"{val:.0f}{suf}" if abs(val) >= 10 or val == int(val)
                        else f"{val:.1f}{suf}")
        if a < 1:
            return f"{v:.3g}"
        return f"{v:.0f}"
    return FuncFormatter(_fmt)


def style_mpl_axes(ax, accent=None):
    """Apply consistent spine / grid / datum styling to a single Axes."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    ax.grid(True, color=GRID, linewidth=1.0)
    ax.axhline(0, color=ZERO_LINE, linewidth=1.2, linestyle=(0, (2, 2)), zorder=2)
    return ax


def add_mpl_watermark(fig, text=BRAND_WATERMARK):
    fig.text(0.99, 0.005, text, ha="right", va="bottom",
             fontsize=8, color="#C2CBD3")
    return fig
