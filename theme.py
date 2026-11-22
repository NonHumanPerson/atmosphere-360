"""
Atmosphere360: Mumbai — Design System & Theme Engine
Theme configuration, color palettes, typography, and Plotly templates.
"""
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

COLORS = {
    "bg": "#0B1220",
    "background": "#0B1220",
    "surface": "#162235",
    "surface_raised": "#1C2B42",
    "surface_hover": "#223552",
    "border": "#24364F",
    "border_focus": "#2DD4BF",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "accent": "#2DD4BF",          
    "accent_subtle": "rgba(45, 212, 191, 0.12)",
    "accent_secondary": "#38BDF8", 
    "warning": "#F59E0B",           
    "info": "#38BDF8",              
    "critical": "#EF4444",       
    "success": "#10B981",           
}

AQI_PALETTE = {
    "Good": "#10B981",
    "Satisfactory": "#84CC16",
    "Moderate": "#F59E0B",
    "Poor": "#F97316",
    "Very Poor": "#EF4444",
    "Severe": "#A855F7",
    "Missing": "#64748B",
}

AQI_BREAKPOINTS = [
    (0, 50, "Good", "#10B981"),
    (50, 100, "Satisfactory", "#84CC16"),
    (100, 200, "Moderate", "#F59E0B"),
    (200, 300, "Poor", "#F97316"),
    (300, 400, "Very Poor", "#EF4444"),
    (400, 700, "Severe", "#A855F7"),
]

PRIORITY_PALETTE = {
    "Highest": "#EF4444",      
    "Elevated": "#F59E0B",     
    "Moderate": "#38BDF8",   
    "Routine": "#64748B",     
}

def get_priority_tier(rank: int, capacity_n: int = 5) -> tuple[str, str]:
    """Returns (tier_label, hex_color) for an inspection priority rank."""
    if rank <= capacity_n:
        return ("Highest Priority", PRIORITY_PALETTE["Highest"])
    elif rank <= capacity_n * 2:
        return ("Elevated Priority", PRIORITY_PALETTE["Elevated"])
    elif rank <= capacity_n * 3:
        return ("Moderate Priority", PRIORITY_PALETTE["Moderate"])
    return ("Routine Monitoring", PRIORITY_PALETTE["Routine"])

def get_aqi_category_color(aqi_val: float) -> tuple[str, str]:
    """Returns (category_name, hex_color) for any numeric AQI value."""
    if aqi_val is None or (isinstance(aqi_val, float) and (aqi_val != aqi_val)):
        return ("Missing", AQI_PALETTE["Missing"])
    for low, high, cat, col in AQI_BREAKPOINTS:
        if low <= aqi_val <= high:
            return (cat, col)
    if aqi_val > 400:
        return ("Severe", AQI_PALETTE["Severe"])
    return ("Good", AQI_PALETTE["Good"])

def register_plotly_theme():
    """Configures and registers the Atmosphere360 command center dark theme in Plotly."""
    template = go.layout.Template()
    template.layout = go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            color=COLORS["text"],
            size=12,
        ),
        title=dict(
            font=dict(size=15, color=COLORS["text"], weight=600),
            x=0.0,
            xanchor="left",
            pad=dict(b=10),
        ),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            title=dict(font=dict(color=COLORS["text_muted"], size=12)),
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.08)",
            linecolor=COLORS["border"],
            zerolinecolor="rgba(148, 163, 184, 0.12)",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            title=dict(font=dict(color=COLORS["text_muted"], size=12)),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["surface_raised"],
            bordercolor=COLORS["accent"],
            font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        ),
        legend=dict(
            font=dict(color=COLORS["text"], size=11),
            bgcolor="rgba(22, 34, 53, 0.8)",
            bordercolor=COLORS["border"],
            borderwidth=1,
        ),
        colorway=[
            COLORS["accent"],
            COLORS["accent_secondary"],
            COLORS["warning"],
            COLORS["success"],
            COLORS["critical"],
            "#84CC16",
            "#A855F7",
        ],
        margin=dict(l=45, r=20, t=45, b=40),
    )
    pio.templates["atmosphere360_dark"] = template
    pio.templates.default = "atmosphere360_dark"

register_plotly_theme()

def inject_custom_css():
    """Injects the token-based Atmosphere360 design system into Streamlit.

    All values come from the semantic COLORS map above. The CSS layer consumes
    CSS custom properties so components never hard-code colour, spacing, or type.
    """
    tokens = f"""
    <style>
    :root {{
        /* Colour tokens */
        --cp-bg: {COLORS["bg"]};
        --cp-surface: {COLORS["surface"]};
        --cp-surface-2: {COLORS["surface_raised"]};
        --cp-surface-3: {COLORS["surface_hover"]};
        --cp-border: {COLORS["border"]};
        --cp-focus: {COLORS["border_focus"]};
        --cp-text: {COLORS["text"]};
        --cp-text-muted: #A9B8CC;
        --cp-accent: {COLORS["accent"]};
        --cp-accent-soft: {COLORS["accent_subtle"]};
        --cp-blue: {COLORS["accent_secondary"]};
        --cp-warning: {COLORS["warning"]};
        --cp-critical: {COLORS["critical"]};
        --cp-success: {COLORS["success"]};

        /* 4px-based spacing scale */
        --cp-space-1: 4px;
        --cp-space-2: 8px;
        --cp-space-3: 12px;
        --cp-space-4: 16px;
        --cp-space-5: 20px;
        --cp-space-6: 24px;
        --cp-space-8: 32px;
        --cp-space-10: 40px;

        /* Shape, elevation, type, motion */
        --cp-radius-sm: 8px;
        --cp-radius-md: 12px;
        --cp-radius-lg: 16px;
        --cp-shadow-1: 0 4px 16px rgba(2, 6, 23, 0.35);
        --cp-shadow-2: 0 8px 28px rgba(2, 6, 23, 0.45);
        --cp-font: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
        --cp-motion: 180ms;
        --cp-ease: cubic-bezier(0.2, 0.7, 0.3, 1);
    }}
    """

    css = """
    /* ---------- Browser surfaces: they carry the design too ---------- */
    html, body, [class*="css"], [data-testid="stAppViewContainer"] {
        font-family: var(--cp-font);
        color: var(--cp-text);
        background-color: var(--cp-bg);
        font-size: 16px;
        line-height: 1.5;
        -webkit-font-smoothing: antialiased;
    }
    #MainMenu, footer, [data-testid="stToolbarActions"],
    [data-testid="stAppDeployButton"] { display: none; }
    [data-testid="stHeader"] {
        background: transparent;
        min-height: 40px;
    }
    ::selection { background: rgba(45, 212, 191, 0.28); color: #ffffff; }
    input, textarea { caret-color: var(--cp-accent); }
    a { color: var(--cp-accent); text-underline-offset: 3px; }
    a:hover { color: #5EEAD4; }
    :focus-visible {
        outline: 2px solid var(--cp-focus) !important;
        outline-offset: 2px !important;
    }
    * { scrollbar-width: thin; scrollbar-color: #344A6A var(--cp-bg); }
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: var(--cp-bg); }
    ::-webkit-scrollbar-thumb {
        background: #344A6A; border-radius: 999px; border: 2px solid var(--cp-bg);
    }
    ::-webkit-scrollbar-thumb:hover { background: #46618A; }

    .block-container {
        padding-top: var(--cp-space-6) !important;
        padding-bottom: var(--cp-space-10) !important;
        max-width: 1400px !important;
    }

    /* ---------- Type scale ---------- */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        font-weight: 700;
        line-height: 1.25;
        letter-spacing: -0.01em;
        margin: var(--cp-space-6) 0 var(--cp-space-2);
    }
    .stMarkdown h1 { font-size: 1.5rem; }
    .stMarkdown h2 { font-size: 1.25rem; }
    .stMarkdown h3 { font-size: 1.125rem; }
    .stMarkdown h4 { font-size: 1rem; }
    .stMarkdown p { max-width: 75ch; }
    [data-testid="stCaptionContainer"] {
        font-size: 0.8125rem;
        color: var(--cp-text-muted);
        line-height: 1.5;
    }
    hr {
        border: 0;
        border-top: 1px solid var(--cp-border);
        margin: var(--cp-space-6) 0;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background-color: #0E1726;
        border-right: 1px solid var(--cp-border);
    }
    [data-testid="stSidebar"] hr {
        margin: var(--cp-space-4) 0;
        border-color: var(--cp-border);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        background: transparent;
        gap: var(--cp-space-1);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background-color: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm);
        padding: 10px 12px;
        transition: background-color var(--cp-motion) var(--cp-ease),
                    border-color var(--cp-motion) var(--cp-ease);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background-color: var(--cp-surface-3);
        border-color: var(--cp-accent);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background-color: rgba(45, 212, 191, 0.10);
        border-color: var(--cp-accent);
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        font-size: 0.875rem;
        font-weight: 500;
    }
    .cp-sidebar-brand {
        display: flex; align-items: center; gap: var(--cp-space-3);
        margin-bottom: var(--cp-space-3);
    }
    .cp-sidebar-mark {
        width: 36px; height: 36px; flex-shrink: 0;
        background: var(--cp-accent-soft);
        border: 1px solid var(--cp-accent);
        border-radius: var(--cp-radius-sm);
        display: flex; align-items: center; justify-content: center;
        color: var(--cp-accent);
    }
    .cp-sidebar-name { font-size: 1rem; font-weight: 700; color: #ffffff; line-height: 1.2; }
    .cp-sidebar-tag {
        font-size: 0.75rem; font-weight: 600; color: var(--cp-accent);
        letter-spacing: 0.04em; text-transform: uppercase;
    }
    .cp-replay-card {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm);
        padding: var(--cp-space-3) var(--cp-space-4);
        font-size: 0.875rem;
        color: var(--cp-text-muted);
        line-height: 1.5;
    }
    .cp-replay-title { font-weight: 700; color: #ffffff; margin-bottom: var(--cp-space-1); }
    .cp-replay-card strong { color: #ffffff; font-variant-numeric: tabular-nums; }

    /* ---------- Header ---------- */
    .cp-cmd-header {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-lg);
        padding: var(--cp-space-5) var(--cp-space-6);
        margin-bottom: var(--cp-space-4);
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: var(--cp-space-5);
        box-shadow: var(--cp-shadow-1);
    }
    .cp-cmd-branding { display: flex; align-items: center; gap: var(--cp-space-4); }
    .cp-cmd-icon {
        width: 44px; height: 44px; flex-shrink: 0;
        background: var(--cp-accent-soft);
        border: 1px solid var(--cp-accent);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; color: var(--cp-accent);
    }
    .cp-cmd-titles { display: flex; flex-direction: column; }
    .cp-cmd-name {
        font-size: 1.5rem; font-weight: 700; color: #ffffff;
        letter-spacing: -0.02em; margin: 0; line-height: 1.2;
    }
    .cp-cmd-tagline {
        font-size: 0.875rem; color: var(--cp-text-muted); margin: var(--cp-space-1) 0 0 0;
    }
    .cp-cmd-badges { display: flex; align-items: center; gap: var(--cp-space-2); flex-wrap: wrap; }

    /* ---------- Status bar ---------- */
    .cp-status-bar {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-md);
        padding: var(--cp-space-3) var(--cp-space-5);
        margin-bottom: var(--cp-space-5);
        display: flex; align-items: center; justify-content: space-between;
        flex-wrap: wrap; gap: var(--cp-space-4);
    }
    .cp-status-items { display: flex; align-items: center; flex-wrap: wrap; gap: var(--cp-space-3) 0; }
    .cp-status-item { position: relative; display: flex; flex-direction: column; gap: 2px; padding: 0 var(--cp-space-4); }
    .cp-status-item:first-child { padding-left: 0; }
    .cp-status-item + .cp-status-item::before {
        content: ""; position: absolute; left: 0; top: 2px; bottom: 2px;
        width: 1px; background: var(--cp-border);
    }
    .cp-status-label {
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: var(--cp-text-muted);
    }
    .cp-status-value {
        font-size: 0.875rem; font-weight: 600; color: #ffffff;
        display: flex; align-items: center; gap: var(--cp-space-1);
        font-variant-numeric: tabular-nums;
    }
    .cp-status-note { font-size: 0.875rem; color: var(--cp-text-muted); }

    /* ---------- Pills ---------- */
    .cp-pill {
        background: var(--cp-surface-2);
        border: 1px solid var(--cp-border);
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex; align-items: center; gap: var(--cp-space-1);
        line-height: 1.4;
    }
    .cp-pill-amber { background: rgba(245, 158, 11, 0.12); border-color: rgba(245, 158, 11, 0.4); color: #FBBF24; }
    .cp-pill-teal { background: var(--cp-accent-soft); border-color: var(--cp-accent); color: var(--cp-accent); }
    .cp-pill-red { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.4); color: #F87171; }
    .cp-pill-green { background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.4); color: #34D399; }

    /* ---------- Disclaimer ---------- */
    .cp-disclaimer {
        background: rgba(245, 158, 11, 0.10);
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: var(--cp-radius-sm);
        padding: var(--cp-space-2) var(--cp-space-4);
        margin-bottom: var(--cp-space-3);
        display: flex; align-items: center; flex-wrap: wrap;
        gap: var(--cp-space-2) var(--cp-space-3);
        font-size: 0.875rem; color: var(--cp-text);
    }
    .cp-disclaimer strong { color: #FBBF24; font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; }

    /* ---------- Cards ---------- */
    .cp-kpi-card, .cp-queue-card, .cp-hero-card, .cp-detail-card {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        box-shadow: var(--cp-shadow-1);
    }
    .cp-kpi-card, .cp-hero-card, .cp-queue-card { position: relative; overflow: hidden; }
    .cp-kpi-card::before, .cp-hero-card::before, .cp-queue-card::before, .cp-action-dossier::before {
        content: ""; position: absolute; inset: 0 0 auto 0; height: 2px;
        background: var(--cp-card-accent, var(--cp-accent));
    }
    .cp-kpi-card {
        border-radius: var(--cp-radius-md);
        padding: var(--cp-space-4) var(--cp-space-5);
        height: 100%;
    }
    .cp-kpi-label {
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: var(--cp-text-muted);
        margin-bottom: var(--cp-space-2);
        display: flex; align-items: center; justify-content: space-between; gap: var(--cp-space-2);
    }
    .cp-kpi-val {
        font-size: 1.75rem; font-weight: 700; letter-spacing: -0.02em;
        line-height: 1.1; font-variant-numeric: tabular-nums;
    }
    .cp-kpi-sub {
        font-size: 0.875rem; color: var(--cp-text-muted);
        margin-top: var(--cp-space-2); line-height: 1.4;
    }
    .cp-queue-card {
        border-radius: var(--cp-radius-md);
        padding: var(--cp-space-4);
        margin-bottom: var(--cp-space-3);
    }
    .cp-queue-top { display: flex; align-items: center; justify-content: space-between; gap: var(--cp-space-2); margin-bottom: var(--cp-space-2); }
    .cp-queue-rank {
        color: var(--cp-card-accent, var(--cp-accent));
        font-size: 0.75rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
    }
    .cp-queue-station { color: #ffffff; font-size: 1.0625rem; font-weight: 700; line-height: 1.3; }
    .cp-queue-meta { color: var(--cp-text-muted); font-size: 0.875rem; margin: var(--cp-space-1) 0 var(--cp-space-3); }
    .cp-queue-action {
        color: var(--cp-text); font-size: 0.875rem; line-height: 1.5;
        background: var(--cp-surface-2); border-radius: var(--cp-radius-sm);
        padding: var(--cp-space-3); border: 1px solid var(--cp-border);
    }
    .cp-rank-row {
        background: var(--cp-surface); border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm); padding: var(--cp-space-3) var(--cp-space-4);
        margin-bottom: var(--cp-space-2);
        display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: var(--cp-space-3);
    }
    .cp-rank-chip {
        display: inline-flex; align-items: center; justify-content: center;
        min-width: 40px; padding: 4px 8px;
        border-radius: var(--cp-radius-sm);
        background: var(--cp-card-accent, var(--cp-accent));
        color: #07131F; font-size: 0.8125rem; font-weight: 700;
        font-variant-numeric: tabular-nums;
    }
    .cp-reason-badges { display: flex; flex-wrap: wrap; gap: var(--cp-space-1); margin-top: var(--cp-space-2); }
    .cp-rank-stats { display: flex; align-items: center; gap: var(--cp-space-5); }
    .cp-stat-label { font-size: 0.75rem; color: var(--cp-text-muted); text-transform: uppercase; }
    .cp-stat-value { font-size: 1.125rem; font-weight: 700; font-variant-numeric: tabular-nums; }

    .cp-action-dossier {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-lg);
        padding: var(--cp-space-5) var(--cp-space-6);
        margin-top: var(--cp-space-4);
        box-shadow: var(--cp-shadow-1);
        position: relative;
    }
    .cp-action-title { font-size: 1.0625rem; font-weight: 700; color: #ffffff; margin: 0 0 var(--cp-space-3) 0; }
    .cp-action-text { font-size: 0.9375rem; color: var(--cp-text); line-height: 1.5; margin-bottom: var(--cp-space-3); }
    .cp-action-lead { font-weight: 700; color: #ffffff; }
    .cp-action-body {
        margin-top: var(--cp-space-2); font-size: 0.9375rem; line-height: 1.5;
        background: var(--cp-surface-2); border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm); padding: var(--cp-space-3) var(--cp-space-4);
    }
    .cp-evidence-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: var(--cp-space-3);
        background: var(--cp-surface-2); border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm); padding: var(--cp-space-3) var(--cp-space-4);
        font-size: 0.875rem; color: var(--cp-text-muted); line-height: 1.5;
    }
    .cp-evidence-grid strong { color: #ffffff; display: block; margin-bottom: var(--cp-space-1); }

    .cp-source-card {
        background: var(--cp-surface); border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-md); padding: var(--cp-space-4) var(--cp-space-5);
        margin-bottom: var(--cp-space-3);
    }
    .cp-source-title { margin: 0; color: #ffffff; font-size: 0.9375rem; font-weight: 700; }
    .cp-source-meta { font-size: 0.875rem; color: var(--cp-text-muted); margin-bottom: var(--cp-space-2); }
    .cp-source-body { font-size: 0.875rem; color: var(--cp-text); line-height: 1.5; }

    /* ---------- Personal AQI hero + detail cards ---------- */
    .cp-hero-card {
        border-radius: var(--cp-radius-lg);
        padding: var(--cp-space-5);
        height: 100%; text-align: center;
    }
    .cp-hero-label {
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; color: var(--cp-text-muted);
    }
    .cp-hero-value {
        font-size: 2.75rem; font-weight: 700; line-height: 1.05;
        letter-spacing: -0.03em; font-variant-numeric: tabular-nums;
        color: var(--cp-card-accent, var(--cp-text)); margin-top: var(--cp-space-2);
    }
    .cp-hero-sub { font-size: 0.9375rem; font-weight: 600; color: var(--cp-card-accent, var(--cp-text)); margin-top: var(--cp-space-2); }
    .cp-hero-meta { font-size: 0.875rem; color: var(--cp-text-muted); margin-top: var(--cp-space-3); }
    .cp-guidance-card {
        background: var(--cp-surface); border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-lg); padding: var(--cp-space-5);
        box-shadow: var(--cp-shadow-1); height: 100%;
    }
    .cp-guidance-icon {
        display: block; font-family: "Material Symbols Rounded";
        font-size: 2rem; line-height: 1; color: var(--cp-card-accent, var(--cp-accent));
        margin-bottom: var(--cp-space-2);
    }
    .cp-guidance-title { font-weight: 700; color: #ffffff; margin-bottom: var(--cp-space-2); }
    .cp-guidance-body { font-size: 0.875rem; color: var(--cp-text); line-height: 1.5; }
    .cp-guidance-body strong { color: #ffffff; }
    .cp-detail-card { border-radius: var(--cp-radius-md); padding: var(--cp-space-4); }
    .cp-detail-row {
        display: flex; justify-content: space-between; align-items: baseline;
        gap: var(--cp-space-3); margin-bottom: var(--cp-space-3);
        font-size: 0.9375rem;
    }
    .cp-detail-row dt { color: var(--cp-text-muted); }
    .cp-detail-row dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
    .cp-delta { font-size: 0.75rem; font-variant-numeric: tabular-nums; }
    .cp-detail-note { font-size: 0.875rem; color: var(--cp-text-muted); line-height: 1.5; }

    /* ---------- Native controls ---------- */
    .stButton button, .stDownloadButton button {
        min-height: 40px; border-radius: var(--cp-radius-sm);
        border: 1px solid var(--cp-border);
        background: var(--cp-surface-2); color: var(--cp-text);
        font-family: var(--cp-font); font-size: 0.875rem; font-weight: 600;
        transition: background-color var(--cp-motion) var(--cp-ease),
                    border-color var(--cp-motion) var(--cp-ease);
    }
    .stButton button:hover { background: var(--cp-surface-3); border-color: var(--cp-accent); }
    .stButton button[kind="primary"] { background: var(--cp-accent); border-color: var(--cp-accent); color: #07231F; }
    .stButton button[kind="primary"]:hover { background: #5EEAD4; }
    .stButton button:disabled { opacity: 0.45; cursor: not-allowed; }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: var(--cp-surface-2) !important;
        color: var(--cp-text) !important;
        border: 1px solid var(--cp-border) !important;
        border-radius: var(--cp-radius-sm) !important;
        font-size: 0.875rem !important;
    }
    [data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stSelectbox"] [data-baseweb="select"]:focus-within > div {
        border-color: var(--cp-accent) !important;
        box-shadow: 0 0 0 2px rgba(45, 212, 191, 0.18) !important;
    }
    [data-testid="stExpander"] details {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm);
    }
    [data-testid="stExpander"] summary { font-size: 0.875rem; }
    [data-testid="stMetric"] {
        background: var(--cp-surface);
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-sm);
        padding: var(--cp-space-3) var(--cp-space-4);
    }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; color: var(--cp-text-muted) !important; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; font-weight: 700 !important; font-variant-numeric: tabular-nums; }
    [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

    /* ---------- Tabs and data ---------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: var(--cp-space-1);
        background-color: var(--cp-surface);
        border-radius: var(--cp-radius-md);
        padding: var(--cp-space-1);
        border: 1px solid var(--cp-border);
        margin-bottom: var(--cp-space-5);
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: var(--cp-radius-sm) !important;
        padding: 8px 14px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: var(--cp-text-muted) !important;
        border: none !important;
        background-color: transparent !important;
        transition: background-color var(--cp-motion) var(--cp-ease),
                    color var(--cp-motion) var(--cp-ease);
        white-space: nowrap;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background-color: var(--cp-surface-3) !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--cp-accent) !important;
        color: #07131F !important;
        font-weight: 700 !important;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid var(--cp-border);
        border-radius: var(--cp-radius-md);
        overflow: hidden;
        background-color: var(--cp-surface);
    }

    /* ---------- Footer ---------- */
    .cp-footer {
        margin-top: var(--cp-space-10);
        padding-top: var(--cp-space-5);
        padding-bottom: var(--cp-space-6);
        border-top: 1px solid var(--cp-border);
        text-align: center;
    }
    .cp-footer-primary { font-size: 0.9375rem; font-weight: 500; color: var(--cp-text); margin-bottom: var(--cp-space-2); }
    .cp-footer-primary strong { color: #ffffff; font-weight: 700; }
    .cp-footer-secondary {
        font-size: 0.8125rem; color: var(--cp-text-muted);
        line-height: 1.5; max-width: 820px; margin: 0 auto;
    }

    /* ---------- Structural adaptation ---------- */
    @media (max-width: 1100px) {
        .cp-status-item { padding: 0 var(--cp-space-3); }
        .cp-status-note { display: none; }
    }
    @media (max-width: 860px) {
        .cp-cmd-header, .cp-status-bar { align-items: flex-start; }
        .cp-evidence-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
        .block-container { padding: var(--cp-space-3) var(--cp-space-3) var(--cp-space-8) !important; }
        .cp-cmd-header { padding: var(--cp-space-4); }
        .cp-cmd-name { font-size: 1.25rem; }
        .cp-status-item { padding-left: 0; }
        .cp-status-item + .cp-status-item::before { display: none; }
        .cp-action-dossier { padding: var(--cp-space-4); }
        .stTabs [data-baseweb="tab"] { padding: 8px 10px !important; font-size: 0.8125rem !important; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { transition: none !important; animation: none !important; }
    }
    </style>
    """
    st.markdown(tokens + css, unsafe_allow_html=True)
