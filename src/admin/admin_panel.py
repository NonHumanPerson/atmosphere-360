"""
Admin Panel for Atmosphere360
Owner-only panel for managing tier privileges, feature flags, and revenue metrics.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from src.data.sqlite_store import (
    get_all_tier_configs,
    get_tier_config,
    update_tier_config,
    get_revenue_metrics,
    get_revenue_summary,
    record_revenue_metric,
    DEFAULT_TIER_CONFIGS,
    TierConfig,
    RevenueMetric,
)


# Simple owner authentication (in production, use proper auth)
ADMIN_PASSWORD = "atmosphere3602026"  # Demo password - change in production!


def check_admin_auth() -> bool:
    """Check if user is authenticated as admin."""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    return st.session_state.admin_authenticated


def render_admin_login() -> bool:
    """Render admin login form."""
    if check_admin_auth():
        return True
    
    st.markdown("### :material/lock: Owner Admin Panel")
    st.caption("Enter admin password to access tier management and revenue analytics")
    
    with st.form("admin_login"):
        password = st.text_input("Admin Password", type="password")
        submitted = st.form_submit_button("🔓 Access Admin Panel", type="primary", width='stretch')
        
        if submitted:
            if password == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("Access granted!")
                st.rerun()
            else:
                st.error("Invalid password")
    
    return False


def render_admin_panel():
    """Render the full admin panel."""
    if not render_admin_login():
        return
    
    # Logout button in sidebar
    with st.sidebar:
        if st.button(":material/logout: Logout", width='stretch'):
            st.session_state.admin_authenticated = False
            st.rerun()
    
    st.markdown("### :material/build: Admin Panel — Tier Management & Revenue Analytics")
    st.caption("Configure feature flags, rate limits, pricing, and monitor revenue across all tiers")
    
    # Tabs for different admin sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Tier Configurations",
        "💰 Revenue Analytics", 
        "📊 System Metrics",
        "⚙️ System Settings"
    ])
    
    # ==================== TAB 1: TIER CONFIGURATIONS ====================
    with tab1:
        render_tier_config_tab()
    
    # ==================== TAB 2: REVENUE ANALYTICS ====================
    with tab2:
        render_revenue_analytics_tab()
    
    # ==================== TAB 3: SYSTEM METRICS ====================
    with tab3:
        render_system_metrics_tab()
    
    # ==================== TAB 4: SYSTEM SETTINGS ====================
    with tab4:
        render_system_settings_tab()


def render_tier_config_tab():
    """Render tier configuration management."""
    st.markdown("#### :material/my_location: Tier Feature Flags & Pricing")
    
    tier_configs = get_all_tier_configs()
    
    if not tier_configs:
        st.warning("No tier configs found. Click 'Initialize Defaults' below.")
        if st.button(":material/build: Initialize Default Tier Configs", type="primary"):
            from src.data.sqlite_store import seed_tier_configs
            seed_tier_configs()
            st.success("Default tier configurations initialized!")
            st.rerun()
        return
    
    # Display current tier summary
    st.markdown("##### Current Tier Overview")
    summary_cols = st.columns(len(tier_configs))
    
    for idx, (tier_name, config) in enumerate(tier_configs.items()):
        with summary_cols[idx]:
            tier_colors = {
                "free": "#10B981",
                "pro": "#38BDF8",
                "enterprise": "#F59E0B",
                "officer": "#A78BFA"
            }
            color = tier_colors.get(tier_name, "#2DD4BF")
            
            flags = json.loads(config.feature_flags) if config.feature_flags else {}
            enabled_count = sum(1 for v in flags.values() if v is True)
            total_count = len(flags)
            
            pricing = config.pricing_inr
            if isinstance(pricing, str):
                try:
                    pricing = json.loads(pricing)
                except:
                    pricing = 0
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, {color}15, {color}08); 
                        border: 2px solid {color}; border-radius: 12px; padding: 16px;">
                <div style="font-size: 1.2rem; font-weight: 700; color: {color};">{tier_name.upper()}</div>
                <div style="color: #9CA3AF; margin-top: 4px;">₹{pricing:,}/month</div>
                <div style="margin-top: 12px; font-size: 0.85rem;">
                    Features: {enabled_count}/{total_count} enabled
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed configuration for each tier
    for tier_name, config in tier_configs.items():
        tier_colors = {
            "free": "#10B981",
            "pro": "#38BDF8",
            "enterprise": "#F59E0B",
            "officer": "#A78BFA"
        }
        color = tier_colors.get(tier_name, "#2DD4BF")
        
        with st.expander(f"⚙️ Configure {tier_name.upper()} Tier", expanded=True):
            # Feature Flags
            st.markdown("**Feature Flags**")
            
            flags = json.loads(config.feature_flags) if config.feature_flags else {}
            rate_limits = json.loads(config.rate_limits) if config.rate_limits else {}
            
            # Get all possible features from defaults
            all_features = set()
            for tc in DEFAULT_TIER_CONFIGS.values():
                all_features.update(tc["feature_flags"].keys())
            
            # Feature flag checkboxes
            new_flags = {}
            feature_cols = st.columns(3)
            
            for idx, feature in enumerate(sorted(all_features)):
                with feature_cols[idx % 3]:
                    current = flags.get(feature, False)
                    if isinstance(current, (int, float)):
                        # Rate limit feature (show as number input)
                        new_val = st.number_input(
                            feature.replace("_", " ").title(),
                            value=current,
                            min_value=-1,
                            step=1,
                            help="-1 = unlimited",
                            key=f"flag_{tier_name}_{feature}"
                        )
                        new_flags[feature] = new_val
                    else:
                        new_val = st.checkbox(
                            feature.replace("_", " ").title(),
                            value=current,
                            key=f"flag_{tier_name}_{feature}"
                        )
                        new_flags[feature] = new_val
            
            # Rate Limits
            st.markdown("**Rate Limits**")
            new_rate_limits = {}
            rl_cols = st.columns(3)
            for idx, (rl_name, rl_val) in enumerate(rate_limits.items()):
                with rl_cols[idx % 3]:
                    new_val = st.number_input(
                        rl_name.replace("_", " ").title(),
                        value=rl_val if isinstance(rl_val, (int, float)) else -1,
                        min_value=-1,
                        step=1,
                        help="-1 = unlimited",
                        key=f"rl_{tier_name}_{rl_name}"
                    )
                    new_rate_limits[rl_name] = new_val
            
            # Pricing
            pricing = config.pricing_inr
            if isinstance(pricing, str):
                try:
                    pricing = json.loads(pricing)
                except:
                    pricing = 0
            
            new_pricing = st.number_input(
                f"Monthly Price (₹) - {tier_name}",
                value=pricing,
                min_value=0,
                step=100,
                key=f"pricing_{tier_name}"
            )
            
            # Save button
            if st.button(f":material/save: Save {tier_name.title()} Tier", key=f"save_{tier_name}", type="primary", width='stretch'):
                update_tier_config(
                    tier=tier_name,
                    feature_flags=new_flags,
                    rate_limits=new_rate_limits,
                    pricing_inr=new_pricing
                )
                st.success(f"{tier_name.title()} tier updated!")
                st.rerun()


def render_revenue_analytics_tab():
    """Render revenue analytics dashboard."""
    st.markdown("#### :material/paid: Revenue Analytics (30-Day Window)")
    
    summary = get_revenue_summary()
    
    # KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Revenue (30d)", f"₹{summary['total_30d']:,.0f}")
    with k2:
        st.metric("Est. MRR", f"₹{summary['mrr_estimate']:,.0f}")
    with k3:
        total_subs = sum(summary['by_metric'].get('subscriptions', {}).values()) if isinstance(summary['by_metric'].get('subscriptions'), dict) else 0
        st.metric("Active Subscriptions", f"{total_subs}")
    with k4:
        st.metric("Affiliate Commission", f"₹{summary['by_metric'].get('affiliate_commission', 0):,.0f}")
    
    st.markdown("---")
    
    # Revenue by Tier
    st.markdown("##### Revenue by Tier (30d)")
    if summary['by_tier']:
        tier_df = pd.DataFrame(
            list(summary['by_tier'].items()),
            columns=['Tier', 'Revenue (₹)']
        )
        st.bar_chart(tier_df.set_index('Tier'))
    else:
        st.info("No revenue data recorded yet. Use 'Record Test Revenue' below to simulate data.")
    
    st.markdown("---")
    
    # Revenue by Metric
    st.markdown("##### Revenue by Metric (30d)")
    if summary['by_metric']:
        metric_df = pd.DataFrame(
            list(summary['by_metric'].items()),
            columns=['Metric', 'Revenue (₹)']
        )
        st.bar_chart(metric_df.set_index('Metric'))
    
    st.markdown("---")
    
    # Record test revenue (for demo)
    st.markdown("##### Record Revenue (Demo)")
    with st.form("record_revenue"):
        rcol1, rcol2, rcol3 = st.columns(3)
        with rcol1:
            tier = st.selectbox("Tier", ["free", "pro", "enterprise", "officer"])
        with rcol2:
            metric = st.selectbox("Metric", ["subscriptions", "affiliate_commission", "saas_revenue", "purifier_affiliate"])
        with rcol3:
            value = st.number_input("Amount (₹)", min_value=0, value=1000, step=100)
        
        if st.form_submit_button("📝 Record Revenue", type="primary"):
            record_revenue_metric(tier, metric, value)
            st.success(f"Recorded ₹{value:,} for {tier} / {metric}")
            st.rerun()
    
    # Recent Revenue Records
    st.markdown("---")
    st.markdown("##### Recent Revenue Records")
    recent = get_revenue_metrics(days=30)
    if recent:
        df = pd.DataFrame([
            {
                "Date": m.metric_date,
                "Tier": m.tier,
                "Metric": m.metric_name,
                "Amount (₹)": f"{m.value:,.0f}",
            }
            for m in recent
        ])
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No revenue records yet.")


def render_system_metrics_tab():
    """Render system-wide metrics."""
    st.markdown("#### :material/bar_chart: System Metrics")
    
    # Get counts from SQLite
    from src.data.sqlite_store import get_db as get_sqlite_db
    
    with get_sqlite_db() as conn:
        cursor = conn.cursor()
        
        # Complaints
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total_complaints = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('Submitted', 'Under Review', 'Assigned', 'In Progress')")
        open_complaints = cursor.fetchone()[0]
        
        # Buildings & Rooms
        cursor.execute("SELECT COUNT(*) FROM buildings")
        total_buildings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM rooms")
        total_rooms = cursor.fetchone()[0]
        
        # Indoor readings
        cursor.execute("SELECT COUNT(*) FROM indoor_readings")
        total_readings = cursor.fetchone()[0]
        
        # Deployments
        cursor.execute("SELECT COUNT(*) FROM deployments")
        total_deployments = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM deployments WHERE status IN ('Dispatched', 'On-Site', 'Action Taken')")
        active_deployments = cursor.fetchone()[0]
        
        # Teams
        cursor.execute("SELECT COUNT(*) FROM inspection_teams WHERE active = 1")
        active_teams = cursor.fetchone()[0]
        
        # Alerts
        cursor.execute("SELECT COUNT(*) FROM expected_alerts WHERE acknowledged = 0 AND valid_until > datetime('now')")
        active_alerts = cursor.fetchone()[0]
        
        # Users (from preferences as proxy)
        cursor.execute("SELECT COUNT(*) FROM user_preferences")
        total_users = cursor.fetchone()[0]
    
    # Display metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Complaints", total_complaints)
        st.metric("Open Complaints", open_complaints, delta_color="inverse")
    with m2:
        st.metric("Buildings", total_buildings)
        st.metric("Rooms", total_rooms)
    with m3:
        st.metric("Indoor Readings", total_readings)
        st.metric("Active Deployments", active_deployments)
    with m4:
        st.metric("Inspection Teams", active_teams)
        st.metric("Active Alerts", active_alerts, delta_color="inverse")
    
    st.markdown("---")
    
    # Complaint Status Breakdown
    st.markdown("##### Complaint Status Distribution")
    with get_sqlite_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM complaints GROUP BY status")
        status_data = cursor.fetchall()
    
    if status_data:
        status_df = pd.DataFrame(status_data, columns=['Status', 'Count'])
        st.bar_chart(status_df.set_index('Status'))
    
    # Deployment Status Breakdown
    st.markdown("##### Deployment Status Distribution")
    with get_sqlite_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM deployments GROUP BY status")
        dep_data = cursor.fetchall()
    
    if dep_data:
        dep_df = pd.DataFrame(dep_data, columns=['Status', 'Count'])
        st.bar_chart(dep_df.set_index('Status'))


def render_system_settings_tab():
    """Render system settings."""
    st.markdown("#### :material/settings: System Settings")
    
    st.markdown("##### Admin Password")
    with st.form("change_password"):
        current_pwd = st.text_input("Current Password", type="password")
        new_pwd = st.text_input("New Password", type="password")
        confirm_pwd = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("🔑 Change Password", type="primary"):
            global ADMIN_PASSWORD
            if current_pwd == ADMIN_PASSWORD:
                if new_pwd == confirm_pwd and len(new_pwd) >= 8:
                    ADMIN_PASSWORD = new_pwd
                    st.success("Password changed successfully!")
                else:
                    st.error("Passwords don't match or too short (min 8 chars)")
            else:
                st.error("Current password incorrect")
    
    st.markdown("---")
    
    st.markdown("##### Database Management")
    col1, col2 = st.columns(2)
    with col1:
        if st.button(":material/restart_alt: Re-initialize Default Data", width='stretch'):
            from src.data.sqlite_store import seed_default_teams, seed_tier_configs
            seed_default_teams()
            seed_tier_configs()
            st.success("Default teams and tier configs re-initialized!")
            st.rerun()
    
    with col2:
        if st.button(":material/delete: Clear All Revenue Metrics", width='stretch'):
            with get_sqlite_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM revenue_metrics")
                conn.commit()
            st.warning("All revenue metrics cleared!")
            st.rerun()
    
    st.markdown("---")
    
    st.markdown("##### API Key Status")
    from config import get_serpapi_key, get_groq_key, get_openmeteo_key
    
    serpapi_key = get_serpapi_key()
    groq_key = get_groq_key()
    openmeteo_key = get_openmeteo_key()
    
    st.write(f"**SerpApi:** {':material/check_circle: Configured' if serpapi_key else ':material/cancel: Not configured'}")
    st.write(f"**Groq API:** {':material/check_circle: Configured' if groq_key else ':material/cancel: Not configured'}")
    st.write(f"**Open-Meteo:** {':material/check_circle: Configured' if openmeteo_key else ':material/info: Optional (keyless works)'}")
    
    st.markdown("---")
    
    st.markdown("##### Environment Variables")
    st.code("""
# Required for hackathon
SERPAPI_KEY=your_serpapi_key_here

# Required for AI features
GROQ_API_KEY=your_groq_api_key_here

# Optional (for higher rate limits)
OPENMETEO_API_KEY=your_openmeteo_key_here

# Optional (for additional shopping search)
YOU_API_KEY=your_you_com_key_here
""", language="bash")


# Simple function to check tier access (used by other modules)
def has_feature_access(tier: str, feature_key: str) -> bool:
    """Check if a tier has access to a feature."""
    config = get_tier_config(tier)
    if not config:
        return False
    
    flags = json.loads(config.feature_flags) if config.feature_flags else {}
    return flags.get(feature_key, False)


def get_rate_limit(tier: str, limit_key: str) -> int:
    """Get rate limit for a tier."""
    config = get_tier_config(tier)
    if not config:
        return -1
    
    limits = json.loads(config.rate_limits) if config.rate_limits else {}
    return limits.get(limit_key, -1)


if __name__ == "__main__":
    st.set_page_config(page_title="Atmosphere360 Admin", layout="wide")
    render_admin_panel()