"""
Command Center — Officer Intelligence (Module 5)
City-level AQI hotspot map, priority zones, AI daily briefing, complaint integration.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import DEFAULT_WEIGHTS, AQI_CATEGORIES
from src.models.prioritization import compute_station_priority_scores
from src.decision.routing import compute_inspection_route
from src.decision.viz import plot_inspection_route_map
from charts import plot_priority_map
from src.llm import get_gemini_client
from src.data.sqlite_store import (
    get_complaints, 
    get_complaint_stats,
    get_active_alerts,
    create_deployment,
    get_deployments,
    get_inspection_teams,
    update_deployment_status,
    seed_default_teams,
    DEPLOYMENT_STATUSES,
    ACTION_TYPES,
    generate_expected_alerts_from_data,
    acknowledge_alert,
)
from src.data.sqlite_store import get_db as get_sqlite_db
from src.ingest.live_feed import fetch_openmeteo_forecast, fetch_openmeteo_air_quality
from serpapi_client import get_client as get_serpapi_client


def get_aqi_category(aqi: float) -> tuple:
    """Get AQI category name and color."""
    for cat, (low, high, color) in AQI_CATEGORIES.items():
        if low <= aqi <= high:
            return cat, color
    return "Unknown", "#6B7280"


def render_command_center_tab(
    daily_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    priority_df: pd.DataFrame,
    decision_date: str,
    target_date: str,
    capacity_n: int = 5
):
    """Render Command Center - Officer Intelligence tab."""
    st.markdown("### :material/account_balance: Command Center — Officer Intelligence")
    st.caption(f"Mumbai Metropolitan Region • Decision: {decision_date} • Target: {target_date}")
    
    # Compute dynamic priority scores
    weights = st.session_state.get("weights", DEFAULT_WEIGHTS)
    dyn_priority = compute_station_priority_scores(
        preds_df,
        w_exposure=weights.get("w_exp", 0.30),
        w_persistence=weights.get("w_pers", 0.25),
        w_trend=weights.get("w_trend", 0.15),
        w_forecast=weights.get("w_fore", 0.20),
        w_gap=weights.get("w_gap", 0.10),
    )
    
    # Get complaints
    complaints = get_complaints(limit=100)
    complaint_stats = get_complaint_stats()
    
    # ==================== TOP ROW: KPIs ====================
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        st.metric("Active Stations", daily_df["canonical_station"].nunique())
    with kpi2:
        high_priority = len(dyn_priority[dyn_priority["rank"] <= capacity_n])
        st.metric("Priority Zones", high_priority, help=f"Top {capacity_n} by composite score")
    with kpi3:
        avg_aqi = dyn_priority["latest_aqi"].mean()
        st.metric("City Avg AQI", f"{avg_aqi:.0f}")
    with kpi4:
        open_complaints = complaint_stats.get("by_status", {}).get("Submitted", 0) + \
                         complaint_stats.get("by_status", {}).get("Under Review", 0) + \
                         complaint_stats.get("by_status", {}).get("Assigned", 0) + \
                         complaint_stats.get("by_status", {}).get("In Progress", 0)
        st.metric("Open Complaints", open_complaints, delta_color="inverse")
    with kpi5:
        severe_zones = len(dyn_priority[dyn_priority["latest_aqi"] > 200])
        st.metric("Severe AQI Zones", severe_zones, delta_color="inverse")
    
    st.markdown("---")
    
    # ==================== MAIN LAYOUT ====================
    left_col, right_col = st.columns([2, 1])
    
    # LEFT: Hotspot Map + Priority Table
    with left_col:
        st.markdown("#### :material/map: AQI Hotspot Map")
        
        # Map with priority zones
        fig_map = plot_priority_map(
            dyn_priority,
            selected_station=None,
            priority_filter="All",
            capacity_n=capacity_n,
        )
        
        # Add complaint markers
        if complaints:
            complaint_lats = []
            complaint_lons = []
            complaint_texts = []
            for c in complaints:
                if c.latitude and c.longitude:
                    complaint_lats.append(c.latitude)
                    complaint_lons.append(c.longitude)
                    complaint_texts.append(f"{c.reference_id}: {c.category} at {c.location}")
            
            if complaint_lats:
                fig_map.add_trace(go.Scattermapbox(
                    lat=complaint_lats,
                    lon=complaint_lons,
                    mode="markers",
                    marker=dict(size=12, color="#EF4444", symbol="circle"),
                    text=complaint_texts,
                    hoverinfo="text",
                    name="Citizen Complaints",
                    showlegend=True,
                ))
        
        st.plotly_chart(fig_map, width='stretch', config={"displayModeBar": False})
        
        st.markdown("#### :material/checklist: Top Priority Zones")
        top_zones = dyn_priority.head(capacity_n).copy()
        top_zones["AQI Category"] = top_zones["latest_aqi"].apply(lambda x: get_aqi_category(x)[0])
        
        display_cols = ["rank", "station", "priority_score", "latest_aqi", "AQI Category", "zone"]
        display_df = top_zones[display_cols].rename(columns={
            "rank": "Rank",
            "station": "Station / Zone",
            "priority_score": "Score",
            "latest_aqi": "AQI",
            "zone": "Region",
        })
        
        st.dataframe(
            display_df,
            column_config={
                "Rank": st.column_config.NumberColumn("Rank", width="small", format="#%d"),
                "Score": st.column_config.ProgressColumn("Priority Score", format="%.1f", min_value=0, max_value=100, width="medium"),
                "AQI": st.column_config.NumberColumn("AQI", format="%.0f", width="small"),
                "AQI Category": st.column_config.TextColumn("Category", width="small"),
                "Station / Zone": st.column_config.TextColumn("Station", width="medium"),
                "Region": st.column_config.TextColumn("Region", width="medium"),
            },
            hide_index=True,
            width='stretch',
        )
    
    # RIGHT: AI Daily Briefing + Complaints + Actions
    with right_col:
        st.markdown("#### :material/smart_toy: AI Daily Briefing")
        
        # Generate or show cached briefing
        if "command_briefing" not in st.session_state:
            st.session_state.command_briefing = ""
        
        if st.button(":material/restart_alt: Generate Fresh Briefing", width='stretch'):
            client = get_gemini_client()
            if client.api_key:
                with st.spinner("Generating AI briefing..."):
                    # Prepare data for briefing
                    top_5 = dyn_priority.head(5).to_dict("records")
                    recent_complaints = complaints[:5] if complaints else []
                    complaint_data = [
                        {"category": c.category, "location": c.location, "status": c.status}
                        for c in recent_complaints
                    ]
                    
                    # Forecast summary
                    forecast_aqi = dyn_priority.head(10)["latest_aqi"].mean()
                    forecast_summary = f"City-wide AQI trending {'up' if forecast_aqi > avg_aqi else 'down'}. Avg predicted: {forecast_aqi:.0f}"
                    
                    response = client.generate_officer_briefing(top_5, complaint_data, forecast_summary)
                    
                    if response.success:
                        st.session_state.command_briefing = response.content
                    else:
                        st.session_state.command_briefing = f"AI Error: {response.error}"
            else:
                st.session_state.command_briefing = "Configure Groq API key for AI briefings"
        
        if st.session_state.command_briefing:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #2DD4BF15, #2DD4BF08); 
                        border: 1px solid #2DD4BF; border-radius: 12px; padding: 16px;">
                {st.session_state.command_briefing.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Click 'Generate Fresh Briefing' for AI-powered daily summary")
        
        st.markdown("---")
        
        # Complaint Summary
        st.markdown("#### :material/location_on: Citizen Complaints")
        if complaints:
            for c in complaints[:5]:
                priority_icon = "🔴" if c.priority == 1 else "🟡" if c.priority == 2 else "🟢"
                st.markdown(f"""
                <div style="background: rgba(22,34,53,0.5); border-radius: 8px; padding: 10px; margin-bottom: 8px; border-left: 3px solid #EF4444;">
                    {priority_icon} <strong>{c.reference_id}</strong> • {c.category}<br>
                    <small>{c.location}</small><br>
                    <span style="color: #9CA3AF;">Status: {c.status}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No citizen complaints yet")
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("#### :material/bolt: Quick Actions")
        
        if st.button(":material/map: Compute Inspection Route", width='stretch'):
            st.session_state.show_route = True
        
        if st.button(":material/bar_chart: Export Briefing PDF", width='stretch'):
            st.session_state.export_briefing = True
        
        if st.button(":material/campaign: Send Alert to Field Teams", width='stretch'):
            st.success("Alert sent to field team channel (simulated)")
        
        # SerpApi pollution source identification
        st.markdown("---")
        st.markdown("#### :material/search: Pollution Source Intelligence (SerpApi)")
        
        selected_station = st.selectbox(
            "Analyze sources near:",
            options=dyn_priority["station"].tolist()[:10],
            index=0
        )
        
        if st.button(":material/factory: Find Nearby Sources", width='stretch'):
            serpapi = get_serpapi_client()
            if serpapi.api_key:
                with st.spinner("Searching for pollution sources..."):
                    response = serpapi.find_pollution_sources(selected_station)
                    if response.success and response.data:
                        local_results = response.data.get("local_results", [])
                        if local_results:
                            st.markdown(f"Found {len(local_results)} potential sources near {selected_station}:")
                            for place in local_results[:5]:
                                st.write(f"- **{place.get('title', 'Unknown')}**: {place.get('address', 'No address')} ({place.get('type', 'Unknown')})")
                        else:
                            st.info("No specific sources found in Maps")
                    else:
                        st.error(f"Search failed: {response.error}")
            else:
                st.warning("SerpApi key not configured")


# ==================== EXPECTED ALERTS & TEAM DEPLOYMENT ====================
    st.markdown("---")
    st.markdown("#### :material/crisis_alert: Expected Alerts & Team Deployment")
    
    # Generate/refresh expected alerts
    if "expected_alerts_generated" not in st.session_state:
        st.session_state.expected_alerts_generated = False
    
    if st.button(":material/restart_alt: Refresh Expected Alerts", width='stretch'):
        with st.spinner("Analyzing forecast, wind, persistence & complaints..."):
            # Fetch live forecast data
            weather_fc = fetch_openmeteo_forecast(19.0760, 72.8777)
            aqi_fc = fetch_openmeteo_air_quality(19.0760, 72.8777)
            
            # Generate alerts
            new_alerts = generate_expected_alerts_from_data(
                dyn_priority, daily_df, complaints, weather_fc, aqi_fc
            )
            st.session_state.expected_alerts_generated = True
            if new_alerts:
                st.success(f"Generated {len(new_alerts)} new expected alerts!")
            else:
                st.info("No new alerts - all zones within normal parameters or already acknowledged.")
    
    # Display active alerts
    active_alerts = get_active_alerts()
    if active_alerts:
        st.markdown(f"**{len(active_alerts)} Active Expected Alert(s):**")
        
        for alert in active_alerts:
            alert_colors = {
                "High Alert": "#EF4444",
                "Watch": "#F59E0B", 
                "Advisory": "#38BDF8"
            }
            color = alert_colors.get(alert.alert_level, "#2DD4BF")
            
            with st.expander(f"🚨 {alert.alert_level}: {alert.station} ({alert.region})", expanded=True):
                col_a1, col_a2 = st.columns([3, 1])
                
                with col_a1:
                    st.markdown(f"""
                    **Station:** {alert.station} ({alert.region})
                    **Alert Level:** <span style="color: {color}; font-weight: 700;">{alert.alert_level}</span>
                    **Current AQI:** {alert.current_aqi:.0f if alert.current_aqi else 'N/A'} | **Forecast AQI:** {alert.forecast_aqi:.0f if alert.forecast_aqi else 'N/A'}
                    **Wind Stagnation:** {'Yes' if alert.wind_stagnation else 'No'} | **Persistence:** {alert.persistence_days} days | **Complaints:** {alert.complaint_count}
                    **Valid Until:** {alert.valid_until[:16].replace('T', ' ')}
                    """, unsafe_allow_html=True)
                    
                    reasons = eval(alert.trigger_reasons) if alert.trigger_reasons else []
                    if reasons:
                        st.markdown("**Trigger Reasons:**")
                        for r in reasons:
                            st.markdown(f"- {r}")
                
                with col_a2:
                    if st.button(f":material/check_circle: Acknowledge", key=f"ack_{alert.id}", width='stretch'):
                        acknowledge_alert(alert.id, "Officer")
                        st.success("Alert acknowledged!")
                        st.rerun()
                    
                    if st.button(f":material/rocket_launch: Deploy Team", key=f"deploy_{alert.id}", width='stretch', type="primary"):
                        st.session_state.deploy_from_alert = alert.id
                        st.rerun()
    else:
        st.info("No active expected alerts. Click 'Refresh Expected Alerts' to analyze current conditions.")
    
    # Team Deployment UI
    st.markdown("---")
    st.markdown("#### :material/rocket_launch: Deploy Inspection Team")
    
    # Check if deploying from alert
    if "deploy_from_alert" in st.session_state:
        alert = None
        for a in active_alerts:
            if a.id == st.session_state.deploy_from_alert:
                alert = a
                break
        if alert:
            st.info(f"Deploying for: **{alert.alert_level}** at **{alert.station}**")
            default_zone = alert.station
            default_region = alert.region
            default_priority = 1 if alert.alert_level == "High Alert" else 2
            default_action = "General Inspection"
            if "Construction" in str(eval(alert.trigger_reasons) if alert.trigger_reasons else []):
                default_action = "Construction Dust Audit"
            elif "Industrial" in str(eval(alert.trigger_reasons) if alert.trigger_reasons else []):
                default_action = "Industrial Stack Check"
            elif "complaint" in str(eval(alert.trigger_reasons) if alert.trigger_reasons else []).lower():
                default_action = "Complaint Investigation"
        else:
            default_zone = default_region = default_action = ""
            default_priority = 2
    else:
        default_zone = default_region = default_action = ""
        default_priority = 2
    
    with st.form("deploy_team_form"):
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            teams = get_inspection_teams()
            team_options = {f"{t.name} ({t.team_type})": t.id for t in teams}
            selected_team = st.selectbox("Inspection Team *", list(team_options.keys()))
            
            zone_station = st.selectbox("Target Zone/Station *", dyn_priority["station"].tolist(), index=0 if not default_zone else dyn_priority["station"].tolist().index(default_zone) if default_zone in dyn_priority["station"].tolist() else 0)
            zone_region = st.text_input("Region/Ward", value=default_region)
        with dcol2:
            action_type = st.selectbox("Action Type *", ACTION_TYPES, index=ACTION_TYPES.index(default_action) if default_action in ACTION_TYPES else 0)
            priority = st.select_slider("Priority", options=[1, 2, 3], value=default_priority, format_func=lambda x: {1: "🔴 High", 2: "🟡 Medium", 3: "🟢 Low"}[x])
            linked_complaints = st.multiselect("Link Complaints", 
                options=[f"{c.reference_id} - {c.category} at {c.location[:30]}" for c in complaints],
                default=[c for c in complaints if default_zone and default_zone.lower() in c.location.lower()] if default_zone else [])
        
        action_notes = st.text_area("Action Notes / Instructions", placeholder="Specific instructions for the team...")
        
        if st.form_submit_button("🚀 Dispatch Team", type="primary", width='stretch'):
            team_id = team_options[selected_team]
            
            # Extract complaint IDs from linked_complaints
            linked_ids = []
            for lc in linked_complaints:
                ref_id = lc.split(" - ")[0]
                with get_sqlite_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM complaints WHERE reference_id = ?", (ref_id,))
                    row = cursor.fetchone()
                    if row:
                        linked_ids.append(row[0])
            
            # Build expected AQI data
            expected_aqi_data = {}
            if alert:
                expected_aqi_data = {
                    "alert_level": alert.alert_level,
                    "current_aqi": alert.current_aqi,
                    "forecast_aqi": alert.forecast_aqi,
                    "trigger_reasons": eval(alert.trigger_reasons) if alert.trigger_reasons else []
                }
            
            deployment = create_deployment(
                team_id=team_id,
                zone_station=zone_station,
                zone_region=zone_region,
                action_type=action_type,
                priority=priority,
                linked_complaint_ids=linked_ids if linked_ids else None,
                expected_aqi=expected_aqi_data if expected_aqi_data else None,
                action_notes=action_notes
            )
            
            st.success(f":material/check_circle: Team dispatched! Deployment ID: {deployment.id[:8]}...")
            if "deploy_from_alert" in st.session_state:
                del st.session_state.deploy_from_alert
            st.rerun()
    
    # Active Deployments
    st.markdown("---")
    st.markdown("#### :material/checklist: Active Deployments")
    
    active_deployments = get_deployments(status=None)
    active_deployments = [d for d in active_deployments if d.status in ["Dispatched", "On-Site", "Action Taken"]]
    
    if active_deployments:
        for dep in active_deployments:
            team = get_inspection_team(dep.team_id)
            team_name = team.name if team else "Unknown"
            status_colors = {
                "Dispatched": "#38BDF8",
                "On-Site": "#2DD4BF",
                "Action Taken": "#A78BFA",
                "Verified": "#10B981",
                "Closed": "#6B7280"
            }
            dep_color = status_colors.get(dep.status, "#2DD4BF")
            
            with st.expander(f"🚚 {team_name} → {dep.zone_station} ({dep.action_type}) • {dep.status}", expanded=False):
                dep_c1, dep_c2 = st.columns([2, 1])
                with dep_c1:
                    st.markdown(f"""
                    **Team:** {team_name} ({dep.team_id[:8]}...)
                    **Zone:** {dep.zone_station} ({dep.zone_region or 'N/A'})
                    **Action:** {dep.action_type}
                    **Priority:** {'🔴 High' if dep.priority == 1 else '🟡 Medium' if dep.priority == 2 else '🟢 Low'}
                    **Dispatched:** {dep.dispatched_at[:16].replace('T', ' ')}
                    **Notes:** {dep.action_notes or '—'}
                    """)
                with dep_c2:
                    # Status progression
                    current_idx = DEPLOYMENT_STATUSES.index(dep.status) if dep.status in DEPLOYMENT_STATUSES else 0
                    for i, s in enumerate(DEPLOYMENT_STATUSES):
                        if i <= current_idx:
                            st.markdown(f":material/check_circle: {s}")
                        else:
                            st.markdown(f"⏳ {s}")
                    
                    if current_idx < len(DEPLOYMENT_STATUSES) - 1:
                        next_status = DEPLOYMENT_STATUSES[current_idx + 1]
                        if st.button(f":material/arrow_forward: {next_status}", key=f"dep_next_{dep.id}", width='stretch'):
                            update_deployment_status(dep.id, next_status)
                            st.success(f"Updated to {next_status}")
                            st.rerun()
                    
                    if st.button(f":material/edit_note: Add Notes", key=f"dep_notes_{dep.id}", width='stretch'):
                        notes = st.text_area("Notes", key=f"dep_notes_input_{dep.id}", value=dep.action_notes or "")
                        if st.button("Save", key=f"dep_notes_save_{dep.id}"):
                            update_deployment_status(dep.id, dep.status, action_notes=notes)
                            st.success("Notes saved!")
    else:
        st.info("No active deployments. Dispatch a team above.")


def render_inspection_route_planner(
    dyn_priority: pd.DataFrame,
    capacity_n: int = 5
):
    """Render inspection route planner for field teams."""
    st.markdown("### :material/map: Inspection Route Planner")
    st.caption(f"Optimized route for top {capacity_n} priority zones")
    
    top_stations = dyn_priority.head(capacity_n)
    route_lat = pd.to_numeric(top_stations["latitude"], errors="coerce")
    route_lon = pd.to_numeric(top_stations["longitude"], errors="coerce")
    route_mask = route_lat.between(-90, 90) & route_lon.between(-180, 180)
    route_locations = top_stations.loc[route_mask].copy()
    
    if len(route_locations) < 2:
        st.warning("Need at least 2 valid locations for routing")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        start_options = ["Auto (Nearest to depot)"] + route_locations["station"].tolist()
        start_station = st.selectbox("Starting Point", start_options)
        
        if st.button(":material/rocket_launch: Compute Optimal Route", type="primary", width='stretch'):
            start = None if start_station == "Auto (Nearest to depot)" else start_station
            with st.spinner("Computing route..."):
                route_df, total_dist = compute_inspection_route(route_locations, len(route_locations), start)
                st.session_state.route_df = route_df
                st.session_state.route_dist = total_dist
    
    with col2:
        if "route_df" in st.session_state:
            route_df = st.session_state.route_df
            total_dist = st.session_state.route_dist
            
            st.metric("Total Distance", f"{total_dist:.1f} km")
            st.metric("Avg Leg", f"{route_df['distance_from_prev_km'].mean():.1f} km")
            st.metric("Stops", len(route_df))
            
            st.warning(":material/warning: Straight-line (haversine) distances. Actual road travel will vary.")
    
    # Display route
    if "route_df" in st.session_state:
        route_df = st.session_state.route_df
        
        # Route map
        fig = plot_inspection_route_map(route_df, None)
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        
        # Itinerary table
        st.markdown("#### :material/checklist: Inspection Itinerary")
        display = route_df[[
            "stop_number", "station", "zone", "latest_aqi",
            "priority_score", "distance_from_prev_km", "cumulative_distance_km"
        ]].rename(columns={
            "stop_number": "Stop #",
            "station": "Station",
            "zone": "Zone",
            "latest_aqi": "AQI",
            "priority_score": "Score",
            "distance_from_prev_km": "Leg (km)",
            "cumulative_distance_km": "Total (km)",
        })
        
        st.dataframe(display, width='stretch', hide_index=True)
        
        # Export
        csv = display.to_csv(index=False)
        st.download_button(
            "📥 Download Route CSV",
            csv,
            f"inspection_route_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            width='stretch'
        )


if __name__ == "__main__":
    print("Command Center module loaded")