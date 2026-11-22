"""
Atmosphere360: Mumbai — Air Quality & Health Action Platform
Predict • Explain • Act • Protect

Three Modes: Citizen | Officer | Enterprise
"""
import json
import importlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import components as ui_components
ui_components = importlib.reload(ui_components)
from components import (
    render_action_dossier,
    render_action_strip,
    render_compact_banner,
    render_data_status_bar,
    render_footer,
    render_header,
    render_kpi_card,
    render_ranked_summary,
    render_source_card,
    render_takeaway,
)
from icons import ICONS
from config import (
    EVENT_NAME, TEAM_MEMBERS, DATA_ATTRIBUTION,
    USER_MODES, DEFAULT_MODE, DEFAULT_WEIGHTS,
)
import theme
theme = importlib.reload(theme)
from theme import AQI_PALETTE, COLORS, get_aqi_category_color, get_priority_tier
import charts
charts = importlib.reload(charts)

from src.decision.whatif import compute_rank_stability, compute_rank_delta
from src.decision.routing import compute_inspection_route
from src.decision.briefing import render_briefing_export_ui
from src.decision.validation import render_validation_panel
from src.decision.reliability import station_reliability
from src.decision import viz as decision_viz
decision_viz = importlib.reload(decision_viz)

from src.citizen.citizen_view import render_citizen_mode, render_aqi_card_export
from src.demo.guided_demo import render_guided_demo
from src.demo.replay_dates import shift_date_columns

# New module imports
from src.citizen.my_air import render_my_air_tab, render_aircare_tab
from src.citizen.purifier_match import render_purifier_match_tab
from src.officer.civic_pulse import render_civic_pulse_tab, render_officer_complaint_queue
from src.officer.command_center import render_command_center_tab, render_inspection_route_planner
from src.enterprise.airsense import render_airsense_tab, render_building_portfolio
from src.ingest.live_feed import build_live_context, render_live_city_pulse_strip
from src.admin.admin_panel import render_admin_panel

# Page Configuration
st.set_page_config(
    page_title="Atmosphere360: Mumbai — Air Quality & Health Action Platform",
    page_icon=ICONS["page_icon"],
    layout="wide",
    initial_sidebar_state="auto",
)

theme.inject_custom_css()

# Data Paths
DATA_PATH = Path("data/processed/mumbai_aqi_daily_clean.parquet")
PREDICTIONS_PATH = Path("data/processed/holdout_predictions.parquet")
PRIORITY_PATH = Path("data/processed/mumbai_priority_rankings.parquet")
METRICS_PATH = Path("reports/evaluation_metrics.json")

@st.cache_data
def load_all_datasets():
    daily = pd.read_parquet(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()
    preds = pd.read_parquet(PREDICTIONS_PATH) if PREDICTIONS_PATH.exists() else pd.DataFrame()
    priority = pd.read_parquet(PRIORITY_PATH) if PRIORITY_PATH.exists() else pd.DataFrame()

    if not daily.empty:
        delta = pd.Timestamp.now().normalize() - pd.to_datetime(daily["date"], errors="raise").max()
        shift_date_columns(daily, ("date",), delta)
        if not preds.empty:
            shift_date_columns(preds, ("date",), delta)
        if not priority.empty:
            shift_date_columns(priority, ("date", "target_date"), delta)

    return daily, preds, priority

def _get_data_freshness():
    """Returns data freshness metadata from actual file timestamps and data ranges."""
    info = {}
    if DATA_PATH.exists():
        mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime)
        info["file_updated"] = mtime.strftime("%d %b %Y, %H:%M IST")
    if PREDICTIONS_PATH.exists():
        mtime = datetime.fromtimestamp(PREDICTIONS_PATH.stat().st_mtime)
        info["model_updated"] = mtime.strftime("%d %b %Y, %H:%M IST")
    return info

daily_df, preds_df, priority_df = load_all_datasets()
data_freshness = _get_data_freshness()

if daily_df.empty or preds_df.empty:
    st.error("Processed datasets missing. Run `python -m src.clean.clean_pipeline` first.", icon=":material/error:")
    st.stop()

if "weights" not in st.session_state:
    st.session_state.weights = DEFAULT_WEIGHTS.copy()

# Station Discovery
target_day = preds_df["date"].max()
recent_predictions = preds_df[(preds_df["date"] < target_day) & (preds_df["date"] >= target_day - pd.Timedelta(days=7))]
all_stations = sorted(
    set(daily_df["canonical_station"].dropna())
    & set(preds_df.loc[preds_df["date"] == target_day, "canonical_station"].dropna())
    & set(recent_predictions["canonical_station"].dropna())
)

default_station = "Bandra Kurla Complex" if "Bandra Kurla Complex" in all_stations else all_stations[0]
if "selected_station" not in st.session_state or st.session_state.selected_station not in all_stations:
    st.session_state.selected_station = default_station

# Dynamic Priority Scoring
@st.cache_data
def get_cached_priority_scores(w_dict):
    from src.models.prioritization import compute_station_priority_scores
    return compute_station_priority_scores(
        preds_df,
        w_exposure=w_dict["w_exp"],
        w_persistence=w_dict["w_pers"],
        w_trend=w_dict["w_trend"],
        w_forecast=w_dict["w_fore"],
        w_gap=w_dict["w_gap"],
    )

dyn_priority = get_cached_priority_scores(st.session_state.weights)
decision_date = pd.to_datetime(dyn_priority["date"].iloc[0]).strftime("%d %b %Y")
target_date = pd.to_datetime(dyn_priority["target_date"].iloc[0]).strftime("%d %b %Y")
data_start = daily_df["date"].min().strftime("%d %b %Y")
data_end = daily_df["date"].max().strftime("%d %b %Y")

reliability_df = station_reliability(daily_df, dyn_priority["date"].iloc[0])

# ==========================================
# LIVE CONTEXT (built once, shared across all modes)
# ==========================================
@st.cache_data(ttl=1800)
def get_live_context(station_name: str, hist_df: pd.DataFrame):
    return build_live_context(station_name, hist_df)

# Build live context for default station (will be updated per mode)
live_context = get_live_context(default_station, daily_df)

# ==========================================
# SIDEBAR: MODE SELECTOR (NEW - at top)
# ==========================================
st.sidebar.markdown(
    '<div class="cp-sidebar-brand">'
    '  <div class="cp-sidebar-mark">'
    '    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2DD4BF" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 21h18M5 21V7l8-4v18M13 21V11l6 3v7M8 10h1M8 14h1M8 18h1M16 16h1M16 19h1"/></svg>'
    '  </div>'
    '  <div>'
    '    <div class="cp-sidebar-name">Atmosphere360</div>'
    '    <div class="cp-sidebar-tag">Air quality &amp; health action platform</div>'
    '  </div>'
    '</div>',
    unsafe_allow_html=True,
)

# MODE SELECTOR
st.sidebar.markdown("##### :material/tune: Select mode")
mode_options = list(USER_MODES.keys())
mode_labels = [USER_MODES[k] for k in mode_options]

if "user_mode" not in st.session_state:
    st.session_state.user_mode = DEFAULT_MODE

def on_mode_change():
    chosen = st.session_state.mode_radio
    idx = mode_labels.index(chosen)
    st.session_state.user_mode = mode_options[idx]

selected_mode_label = st.sidebar.radio(
    "User Mode",
    mode_labels,
    index=mode_options.index(st.session_state.user_mode),
    key="mode_radio",
    on_change=on_mode_change,
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# Live City Pulse Strip (shared across all modes)
with st.sidebar:
    # Update live context if station changed
    if "live_context_station" not in st.session_state:
        st.session_state.live_context_station = default_station
    
    if st.session_state.live_context_station != st.session_state.selected_station:
        st.session_state.live_context_station = st.session_state.selected_station
        st.session_state.live_context = get_live_context(st.session_state.selected_station, daily_df)
    
    live_context = st.session_state.get("live_context", live_context)
    render_live_city_pulse_strip(live_context)

st.sidebar.markdown("---")

current_mode = st.session_state.user_mode

# ==========================================
# MODE-SPECIFIC SIDEBAR & CONTENT
# ==========================================

if current_mode == "citizen":
    # ---- CITIZEN MODE ----
    st.sidebar.caption(":material/home: Personal air quality and health")
    
    # Location selector
    st.sidebar.markdown(f"##### {ICONS['sidebar_location']} Your Location")
    focus_idx = all_stations.index(st.session_state.selected_station) if st.session_state.selected_station in all_stations else 0
    chosen_station = st.sidebar.selectbox(
        "Nearest Monitoring Station",
        all_stations,
        index=focus_idx,
        help="Select the station closest to your location",
        label_visibility="collapsed",
    )
    if chosen_station != st.session_state.selected_station:
        st.session_state.selected_station = chosen_station
    
    selected_station = st.session_state.selected_station
    
    # Prepare station data
    st_daily = daily_df[
        (daily_df["canonical_station"] == selected_station)
        & (daily_df["date"] <= pd.to_datetime(dyn_priority["date"].iloc[0]))
    ].sort_values("date").copy()
    st_preds = preds_df[preds_df["canonical_station"] == selected_station].sort_values("date").copy()
    st_prio_row = dyn_priority[dyn_priority["station"] == selected_station]
    st_prio = st_prio_row.iloc[0] if not st_prio_row.empty else None
    
    # Cross-tab navigation sync (handle quick-action buttons from other tabs)
    if st.session_state.get("show_aircare"):
        st.session_state.citizen_tab_idx = 1
        st.session_state.show_aircare = False
    elif st.session_state.get("show_purifier"):
        st.session_state.citizen_tab_idx = 2
        st.session_state.show_purifier = False
    elif st.session_state.get("show_civic"):
        st.session_state.citizen_tab_idx = 3
        st.session_state.show_civic = False
    
    # Citizen Navigation
    CITIZEN_TABS = [
        ":material/home: My Air",
        ":material/medical_services: AirCare",
        ":material/search: PurifierMatch",
        ":material/location_on: CivicPulse",
    ]
    
    if "citizen_tab_idx" not in st.session_state:
        st.session_state.citizen_tab_idx = 0
    
    citizen_tab = st.sidebar.radio(
        "Citizen Dashboard",
        CITIZEN_TABS,
        index=st.session_state.citizen_tab_idx,
        key="citizen_tab_radio",
        label_visibility="collapsed",
    )
    
    # Main header
    render_header(selected_station, decision_date, total_stations=daily_df["canonical_station"].nunique())
    render_data_status_bar(
        decision_date=decision_date,
        target_date=target_date,
        reliability_label="Medium",
        total_stations=daily_df["canonical_station"].nunique(),
        observation_range=f"{data_start} – {data_end}",
        data_source="CPCB / MPCB & Open-Meteo ERA5 + Live Feed",
    )
    render_compact_banner()
    
    # Render selected tab (pass live_context)
    if citizen_tab == ":material/home: My Air":
        render_my_air_tab(st_daily, st_preds, selected_station, decision_date, live_context)
    elif citizen_tab == ":material/medical_services: AirCare":
        render_aircare_tab(st_daily, st_preds, selected_station, decision_date, live_context)
    elif citizen_tab == ":material/search: PurifierMatch":
        render_purifier_match_tab()
    elif citizen_tab == ":material/location_on: CivicPulse":
        render_civic_pulse_tab()

elif current_mode == "officer":
    # ---- OFFICER MODE ----
    st.sidebar.caption(":material/account_balance: Municipal command console (BMC / MPCB)")
    
    # Capacity slider
    st.sidebar.markdown(f"##### {ICONS['sidebar_budget']} Inspection Fleet Capacity")
    capacity_n = st.sidebar.slider(
        "Top Zones to Inspect",
        1, 15, 5,
        help="Number of priority zones the municipal enforcement fleet can physically inspect this week.",
        label_visibility="collapsed",
    )
    
    # Policy weights (same as before)
    with st.sidebar.expander(f"{ICONS['sidebar_weights']} Prioritisation Policy Weights", expanded=False):
        st.caption("Adjust weight of multi-criteria evidence:")
        
        if st.button("Reset Weights", icon=ICONS["sidebar_reset"], width='stretch'):
            st.session_state.weights = DEFAULT_WEIGHTS.copy()
            st.rerun()
        
        w_exp = st.slider("Recent Exposure (7-day)", 0.0, 1.0, float(st.session_state.weights["w_exp"]), 0.05)
        w_pers = st.slider("Persistence Shock (>150)", 0.0, 1.0, float(st.session_state.weights["w_pers"]), 0.05)
        w_trend = st.slider("Trend Acceleration", 0.0, 1.0, float(st.session_state.weights["w_trend"]), 0.05)
        w_fore = st.slider("Forecast Risk (24h)", 0.0, 1.0, float(st.session_state.weights["w_fore"]), 0.05)
        w_gap = st.slider("Vulnerability Corridor", 0.0, 1.0, float(st.session_state.weights["w_gap"]), 0.05)
        
        st.session_state.weights = {
            "w_exp": w_exp,
            "w_pers": w_pers,
            "w_trend": w_trend,
            "w_fore": w_fore,
            "w_gap": w_gap,
        }
        total_w = sum(st.session_state.weights.values())
        if abs(total_w - 1.0) < 0.01:
            st.success(f"Weights Balanced ({total_w:.2f})", icon=":material/check_circle:")
        else:
            st.caption(f"Normalized Total: {total_w:.2f} (auto-scaled to 100%)")
    
    st.sidebar.markdown("---")
    
    # Officer Navigation
    OFFICER_TABS = [
        ":material/account_balance: Command Center",
        ":material/place: Complaint Queue",
        ":material/route: Route Planner",
        ":material/leaderboard: Priority Rankings",
    ]
    
    if "officer_tab_idx" not in st.session_state:
        st.session_state.officer_tab_idx = 0
    
    # Cross-tab navigation sync for officer mode
    if st.session_state.get("show_route"):
        st.session_state.officer_tab_idx = 2
        st.session_state.show_route = False
    elif st.session_state.get("export_briefing"):
        st.session_state.officer_tab_idx = 0  # Command Center has briefing export
        st.session_state.export_briefing = False
    
    officer_tab = st.sidebar.radio(
        "Officer Dashboard",
        OFFICER_TABS,
        index=st.session_state.officer_tab_idx,
        key="officer_tab_radio",
        label_visibility="collapsed",
    )
    
    # Header
    render_header("Mumbai Metro", decision_date, total_stations=daily_df["canonical_station"].nunique())
    render_data_status_bar(
        decision_date=decision_date,
        target_date=target_date,
        reliability_label="Medium",
        total_stations=daily_df["canonical_station"].nunique(),
        observation_range=f"{data_start} – {data_end}",
        data_source="CPCB / MPCB & Open-Meteo ERA5",
    )
    render_compact_banner()
    
    # Render selected tab
    if officer_tab == ":material/account_balance: Command Center":
        render_command_center_tab(
            daily_df, preds_df, dyn_priority,
            decision_date, target_date, capacity_n
        )
    elif officer_tab == ":material/place: Complaint Queue":
        render_officer_complaint_queue()
    elif officer_tab == ":material/route: Route Planner":
        render_inspection_route_planner(dyn_priority, capacity_n)
    elif officer_tab == ":material/leaderboard: Priority Rankings":
        # Reuse existing priority ranking view from original app
        render_takeaway(
            "Complete multi-criteria priority rankings for municipal inspection triage."
        )
        
        render_action_strip(dyn_priority, top_n=min(5, capacity_n))
        
        st.markdown("---")
        
        table_df = dyn_priority.copy()
        table_df["Action"] = np.where(table_df["rank"] <= capacity_n, "INSPECT", "ROUTINE")
        table_df["Category"] = table_df["latest_aqi"].apply(lambda v: get_aqi_category_color(v)[0])
        
        table_df = table_df.merge(
            reliability_df[["station", "coverage_pct", "missing_hours_pct", "confidence"]],
            on="station", how="left"
        )
        table_df["coverage_pct"] = table_df["coverage_pct"].fillna(0)
        table_df["missing_hours_pct"] = table_df["missing_hours_pct"].fillna(100)
        table_df["confidence"] = table_df["confidence"].fillna("Low")
        
        display_df = table_df[[
            "rank", "station", "priority_score", "latest_aqi", "Category", "coverage_pct", "missing_hours_pct", "confidence", "Action", "zone"
        ]].rename(columns={
            "rank": "Rank",
            "station": "Zone / Station",
            "priority_score": "Score",
            "latest_aqi": "AQI",
            "coverage_pct": "Coverage %",
            "missing_hours_pct": "Unavailable %",
            "confidence": "Confidence",
            "Action": "Action Status",
            "zone": "Zone",
        })
        
        st.dataframe(
            display_df,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small", format="#%d"),
                "Score": st.column_config.ProgressColumn(
                    "Priority Score",
                    help="Composite score combining recent exposure, persistence, trend, and forecast.",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    width="medium",
                ),
                "AQI": st.column_config.NumberColumn("Latest AQI", format="%.0f", width="small"),
                "Category": st.column_config.TextColumn("CPCB Category", width="small"),
                "Coverage %": st.column_config.ProgressColumn("Usable Hours", format="%.0f%%", min_value=0, max_value=100, width="small"),
                "Unavailable %": st.column_config.NumberColumn("Unavailable %", format="%.1f%%", width="small"),
                "Confidence": st.column_config.TextColumn("Data Confidence", width="small"),
                "Action Status": st.column_config.TextColumn("Action Status", width="small"),
                "Zone": st.column_config.TextColumn("Region", width="medium"),
            },
            hide_index=True,
            width='stretch',
            height=400,
        )

elif current_mode == "enterprise":
    # ---- ENTERPRISE MODE ----
    st.sidebar.caption(":material/business: Indoor air quality intelligence")
    
    # Location selector for outdoor reference
    st.sidebar.markdown(f"##### {ICONS['sidebar_location']} Outdoor Reference Station")
    focus_idx = all_stations.index(st.session_state.selected_station) if st.session_state.selected_station in all_stations else 0
    chosen_station = st.sidebar.selectbox(
        "Reference Station",
        all_stations,
        index=focus_idx,
        help="Outdoor monitoring station for indoor/outdoor comparison",
        label_visibility="collapsed",
    )
    if chosen_station != st.session_state.selected_station:
        st.session_state.selected_station = chosen_station
    
    selected_station = st.session_state.selected_station
    
    # Enterprise Navigation
    ENTERPRISE_TABS = [
        ":material/business: AirSense Monitor",
        ":material/analytics: Building Portfolio",
    ]
    
    if "enterprise_tab_idx" not in st.session_state:
        st.session_state.enterprise_tab_idx = 0
    
    enterprise_tab = st.sidebar.radio(
        "Enterprise Dashboard",
        ENTERPRISE_TABS,
        index=st.session_state.enterprise_tab_idx,
        key="enterprise_tab_radio",
        label_visibility="collapsed",
    )
    
    # Header
    render_header("Enterprise Dashboard", decision_date, total_stations=daily_df["canonical_station"].nunique())
    render_data_status_bar(
        decision_date=decision_date,
        target_date=target_date,
        reliability_label="Medium",
        total_stations=daily_df["canonical_station"].nunique(),
        observation_range=f"{data_start} – {data_end}",
        data_source="CPCB / MPCB & Open-Meteo ERA5 (Outdoor Reference)",
    )
    render_compact_banner()
    
    # Render selected tab
    if enterprise_tab == ":material/business: AirSense Monitor":
        render_airsense_tab(daily_df, preds_df, selected_station, decision_date)
    elif enterprise_tab == ":material/analytics: Building Portfolio":
        render_building_portfolio()

elif current_mode == "admin":
    # ---- ADMIN MODE (Owner Only) ----
    render_admin_panel()

# ==========================================
# FOOTER
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown(
    '<div class="cp-replay-card">'
    '  <div class="cp-replay-title">Historical decision replay</div>'
    f'  <div>Replay date: <strong>{decision_date}</strong><br>'
    f'    Screening target: <strong>{target_date}</strong><br>'
    '    Source: <strong>CPCB CAAQMS &amp; ERA5</strong></div>'
    '</div>',
    unsafe_allow_html=True,
)

with st.sidebar.expander(f"{ICONS['info']} About Atmosphere360", expanded=False):
    st.markdown(f"**Built for {EVENT_NAME}**  \nby **{TEAM_MEMBERS}**")
    st.caption(
        "Atmosphere360 is an air quality & health action platform for citizens, municipal officers, and enterprises. "
        "Not an official warning system. All AI recommendations require human-in-the-loop verification. "
        "Synthetic data is clearly labeled.\n\n"
        f"**Data Sources:** {DATA_ATTRIBUTION}."
    )

render_footer()