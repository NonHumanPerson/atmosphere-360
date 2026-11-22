"""
CivicPulse — Pollution Complaint & Response (Module 4)
Citizen pollution reporting with AI categorization and status tracking.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import COMPLAINT_CATEGORIES, COMPLAINT_STATUSES
from src.data.sqlite_store import (
    create_complaint,
    get_complaint,
    get_complaints,
    update_complaint_status,
    get_complaint_stats,
)
from src.llm import get_gemini_client
from serpapi_client import get_client as get_serpapi_client


def render_civic_pulse_tab():
    """Render CivicPulse - Pollution Complaint & Response tab."""
    st.markdown("### :material/location_on: CivicPulse — Pollution Complaint & Response")
    st.caption("Report visible pollution sources • Track status • Get reference ID")
    
    # Tabs for Report vs Track
    report_tab, track_tab, dashboard_tab = st.tabs([
        "📝 Report Pollution", 
        "🔍 Track Complaint", 
        "📊 Complaint Dashboard"
    ])
    
    # ==================== REPORT TAB ====================
    with report_tab:
        st.markdown("#### Report a Pollution Source")
        st.info("Your report helps authorities identify and address pollution hotspots. "
                "Photos and precise locations improve response time.")
        
        with st.form("complaint_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                category = st.selectbox(
                    "Pollution Category *",
                    COMPLAINT_CATEGORIES,
                    help="Select the type of pollution you're observing"
                )
                
                location = st.text_input(
                    "Location *",
                    placeholder="e.g., Near Bandra Kurla Complex metro station, Mumbai",
                    help="Be as specific as possible - landmark, road, building"
                )
                
                description = st.text_area(
                    "Description *",
                    placeholder="Describe what you see: thick black smoke from chimney, dust clouds from construction, burning waste, etc.",
                    height=100,
                    help="Include details: color, smell, time of day, duration"
                )
            
            with col2:
                # Location coordinates (optional)
                st.markdown("**Location Coordinates (Optional)**")
                lat = st.number_input("Latitude", format="%.6f", value=0.0)
                lon = st.number_input("Longitude", format="%.6f", value=0.0)
                
                use_gps = st.checkbox("Use my current location (if browser allows)")
                
                # Photo upload
                st.markdown("**Photo Evidence (Optional)**")
                photo = st.file_uploader(
                    "Upload photo of pollution source",
                    type=["jpg", "jpeg", "png"],
                    help="Clear photos help with categorization and verification"
                )
                
                # Priority (auto-assigned but can be indicated)
                urgency = st.select_slider(
                    "Urgency Level",
                    options=["Low", "Medium", "High"],
                    value="Medium",
                    help="High = immediate health risk, visible emissions, near sensitive area"
                )
            
            submitted = st.form_submit_button("🚀 Submit Complaint", type="primary", width='stretch')
        
        if submitted:
            if not location.strip() or not description.strip():
                st.error("Please fill in location and description")
            else:
                # Map urgency to priority
                priority_map = {"Low": 3, "Medium": 2, "High": 1}
                
                # AI Categorization (if description doesn't match category)
                client = get_gemini_client()
                ai_category = category
                if client.api_key and category == "Other":
                    with st.spinner("AI categorizing complaint..."):
                        response = client.categorize_complaint(description, location)
                        if response.success:
                            ai_category = response.content.strip()
                            if ai_category not in COMPLAINT_CATEGORIES:
                                ai_category = "Other"
                
                # Save photo if uploaded
                photo_path = None
                if photo:
                    # In production, save to cloud storage
                    photo_path = f"uploads/complaint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                
                # Create complaint
                complaint = create_complaint(
                    category=ai_category,
                    location=location,
                    description=description,
                    latitude=lat if lat != 0 else None,
                    longitude=lon if lon != 0 else None,
                    photo_path=photo_path,
                    priority=priority_map[urgency]
                )
                
                st.success(f"""
                ✅ **Complaint Submitted Successfully!**
                
                **Reference ID:** `{complaint.reference_id}`
                **Category:** {complaint.category}
                **Status:** {complaint.status}
                **Priority:** {'High' if complaint.priority == 1 else 'Medium' if complaint.priority == 2 else 'Low'}
                
                Save your Reference ID to track status. You'll receive updates as the complaint is processed.
                """)
                
                # Show AI categorization note
                if ai_category != category:
                    st.info(f":material/smart_toy: AI re-categorized as: **{ai_category}** (was: {category})")
    
    # ==================== TRACK TAB ====================
    with track_tab:
        st.markdown("#### Track Your Complaint")
        
        reference_id = st.text_input(
            "Enter Reference ID",
            placeholder="e.g., CP-20261122-001",
            help="Found in your submission confirmation"
        )
        
        if st.button(":material/search: Look Up", width='stretch') and reference_id:
            complaint = get_complaint(reference_id.strip().upper())
            
            if complaint:
                status_colors = {
                    "Submitted": "#38BDF8",
                    "Under Review": "#F59E0B",
                    "Assigned": "#2DD4BF",
                    "In Progress": "#A78BFA",
                    "Resolved": "#10B981",
                    "Closed": "#6B7280",
                }
                status_color = status_colors.get(complaint.status, "#2DD4BF")
                
                # Progress indicator
                status_order = COMPLAINT_STATUSES
                current_idx = status_order.index(complaint.status) if complaint.status in status_order else 0
                
                st.markdown(f"""
                <div style="background: rgba(22, 34, 53, 0.7); border: 1px solid {status_color}; border-radius: 12px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <div>
                            <div style="font-size: 0.75rem; color: #9CA3AF;">Reference ID</div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.2rem;">{complaint.reference_id}</div>
                        </div>
                        <div style="background: {status_color}22; border: 1px solid {status_color}; border-radius: 8px; padding: 8px 16px;">
                            <div style="color: {status_color}; font-weight: 700;">{complaint.status}</div>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 4px; margin-bottom: 16px;">
                """, unsafe_allow_html=True)
                
                # Progress bar
                for i, status in enumerate(status_order):
                    is_current = i == current_idx
                    is_past = i < current_idx
                    bg = status_color if is_current or is_past else "#374151"
                    st.markdown(f"""
                        <div style="flex: 1; text-align: center; padding: 8px 4px;">
                            <div style="width: 12px; height: 12px; border-radius: 50%; background: {bg}; margin: 0 auto;"></div>
                            <div style="font-size: 0.65rem; color: {'#FFFFFF' if is_current or is_past else '#6B7280'}; margin-top: 4px;">{status[:3]}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Details
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Category:** {complaint.category}  
                    **Location:** {complaint.location}  
                    **Priority:** {'🔴 High' if complaint.priority == 1 else '🟡 Medium' if complaint.priority == 2 else '🟢 Low'}  
                    **Submitted:** {complaint.created_at[:19].replace('T', ' ')}
                    """)
                with col2:
                    st.markdown(f"""
                    **Status:** {complaint.status}  
                    **Last Updated:** {complaint.updated_at[:19].replace('T', ' ')}  
                    **Assigned To:** {complaint.assigned_to or '—'}  
                    **Resolution:** {complaint.resolution_notes or 'Pending'}
                    """)
                
                if complaint.description:
                    with st.expander("📝 Full Description"):
                        st.write(complaint.description)
            else:
                st.error("Complaint not found. Check the Reference ID.")
    
    # ==================== DASHBOARD TAB ====================
    with dashboard_tab:
        st.markdown("#### Complaint Analytics Dashboard")
        
        stats = get_complaint_stats()
        
        # KPI cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Complaints", stats["total"])
        with c2:
            st.metric("Last 7 Days", stats["recent_7_days"])
        with c3:
            st.metric("High Priority Open", stats["high_priority_open"], delta_color="inverse")
        with c4:
            resolved = stats["by_status"].get("Resolved", 0) + stats["by_status"].get("Closed", 0)
            resolution_rate = (resolved / stats["total"] * 100) if stats["total"] > 0 else 0
            st.metric("Resolution Rate", f"{resolution_rate:.0f}%")
        
        # Status breakdown
        if stats["by_status"]:
            st.markdown("##### Status Distribution")
            status_df = pd.DataFrame(
                list(stats["by_status"].items()), 
                columns=["Status", "Count"]
            )
            st.bar_chart(status_df.set_index("Status"))
        
        # Category breakdown
        if stats["by_category"]:
            st.markdown("##### Category Distribution")
            cat_df = pd.DataFrame(
                list(stats["by_category"].items()), 
                columns=["Category", "Count"]
            )
            st.bar_chart(cat_df.set_index("Category"))
        
        # Recent complaints table
        st.markdown("##### Recent Complaints")
        recent = get_complaints(limit=20)
        if recent:
            df_data = []
            for c in recent:
                df_data.append({
                    "Ref ID": c.reference_id,
                    "Category": c.category,
                    "Location": c.location[:40] + "..." if len(c.location) > 40 else c.location,
                    "Status": c.status,
                    "Priority": "🔴" if c.priority == 1 else "🟡" if c.priority == 2 else "🟢",
                    "Date": c.created_at[:10],
                })
            st.dataframe(pd.DataFrame(df_data), width='stretch', hide_index=True)
        else:
            st.info("No complaints yet")


def render_officer_complaint_queue():
    """Render officer-facing complaint queue management."""
    st.markdown("#### :material/checklist: Officer Complaint Queue")
    
    # Filter controls
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        status_filter = st.selectbox("Filter by Status", ["All"] + COMPLAINT_STATUSES)
    with fcol2:
        category_filter = st.selectbox("Filter by Category", ["All"] + COMPLAINT_CATEGORIES)
    with fcol3:
        priority_filter = st.selectbox("Filter by Priority", ["All", "High (1)", "Medium (2)", "Low (3)"])
    
    complaints = get_complaints(
        status=None if status_filter == "All" else status_filter,
        category=None if category_filter == "All" else category_filter,
        limit=50
    )
    
    # Apply priority filter
    if priority_filter != "All":
        p = int(priority_filter.split("(")[1][0])
        complaints = [c for c in complaints if c.priority == p]
    
    if not complaints:
        st.info("No complaints match the current filters")
        return
    
    # Action buttons for each complaint
    for complaint in complaints:
        status_colors = {
            "Submitted": "#38BDF8",
            "Under Review": "#F59E0B",
            "Assigned": "#2DD4BF",
            "In Progress": "#A78BFA",
            "Resolved": "#10B981",
            "Closed": "#6B7280",
        }
        color = status_colors.get(complaint.status, "#2DD4BF")
        priority_icon = "🔴" if complaint.priority == 1 else "🟡" if complaint.priority == 2 else "🟢"
        
        with st.expander(f"{priority_icon} {complaint.reference_id} • {complaint.category} • {complaint.status} • {complaint.location[:50]}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                **Location:** {complaint.location}  
                **Description:** {complaint.description}  
                **Category:** {complaint.category}  
                **Submitted:** {complaint.created_at[:19].replace('T', ' ')}  
                **Last Updated:** {complaint.updated_at[:19].replace('T', ' ')}
                """)
                
                if complaint.photo_path:
                    st.image(complaint.photo_path, caption="Submitted photo")
            
            with col2:
                st.markdown(f"""
                **Current Status:** 
                <span style="background: {color}22; border: 1px solid {color}; 
                            border-radius: 6px; padding: 4px 12px; color: {color}; font-weight: 600;">
                    {complaint.status}
                </span>
                """, unsafe_allow_html=True)
                
                # Status transition buttons
                current_idx = COMPLAINT_STATUSES.index(complaint.status) if complaint.status in COMPLAINT_STATUSES else 0
                
                if current_idx < len(COMPLAINT_STATUSES) - 1:
                    next_status = COMPLAINT_STATUSES[current_idx + 1]
                    if st.button(f":material/arrow_forward: Move to {next_status}", key=f"next_{complaint.id}"):
                        update_complaint_status(complaint.reference_id, next_status, assigned_to="Officer")
                        st.success(f"Updated to {next_status}")
                        st.rerun()
                
                if complaint.status not in ["Resolved", "Closed"]:
                    if st.button(f":material/check_circle: Resolve", key=f"resolve_{complaint.id}", type="primary"):
                        update_complaint_status(complaint.reference_id, "Resolved", assigned_to="Officer")
                        st.success("Marked as Resolved")
                        st.rerun()
                
                # Resolution notes
                notes = st.text_area("Resolution Notes", key=f"notes_{complaint.id}", 
                                     value=complaint.resolution_notes or "",
                                     placeholder="Actions taken, outcome...")
                if st.button(":material/save: Save Notes", key=f"save_{complaint.id}"):
                    update_complaint_status(complaint.reference_id, complaint.status, 
                                           resolution_notes=notes)
                    st.success("Notes saved")


if __name__ == "__main__":
    print("CivicPulse module loaded")