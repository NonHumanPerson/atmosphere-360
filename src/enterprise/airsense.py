"""
AirSense Enterprise — Indoor Air Intelligence (Module 6)
Building/room registration, indoor vs outdoor comparison, environmental reports.
"""
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import io

from config import BUILDING_TYPES, ROOM_TYPES
from src.data.sqlite_store import (
    create_building, get_building, get_buildings, update_building,
    create_room, get_room, get_rooms,
    add_indoor_reading, get_latest_reading, get_readings_history,
)
from src.llm import get_gemini_client


def get_aqi_category(aqi: float) -> tuple:
    """Get AQI category from config."""
    from config import AQI_CATEGORIES
    for cat, (low, high, color) in AQI_CATEGORIES.items():
        if low <= aqi <= high:
            return cat, color
    return "Unknown", "#6B7280"


def render_airsense_tab(
    daily_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    station_name: str,
    decision_date: str
):
    """Render AirSense Enterprise - Indoor Air Intelligence tab."""
    st.markdown("### :material/business: AirSense Enterprise — Indoor Air Intelligence")
    st.caption("Monitor indoor air quality across buildings • Compare with outdoor • Generate compliance reports")
    
    # Important disclaimer
    st.warning("""
    ⚠️ **Important:** Outdoor AQI ≠ Indoor Air Quality. 
    Indoor readings MUST be separately measured or entered. 
    This tool helps you track and compare — it does NOT estimate indoor from outdoor.
    """, icon="⚠️")
    
    # Get outdoor reference data
    station_daily = daily_df[daily_df["canonical_station"] == station_name].sort_values("date")
    outdoor_aqi = station_daily.iloc[-1].get("aqi_mean", 0) if not station_daily.empty else 0
    outdoor_pm25 = station_daily.iloc[-1].get("pm25_mean", 0) if not station_daily.empty else 0
    
    # Building selector / creator
    buildings = get_buildings()
    
    st.markdown("#### :material/business: Building Management")
    
    bcol1, bcol2 = st.columns([2, 1])
    with bcol1:
        if buildings:
            building_options = {f"{b.name} ({b.building_type})": b.id for b in buildings}
            building_options["➕ Create New Building"] = "new"
            selected = st.selectbox("Select Building", list(building_options.keys()))
            building_id = building_options[selected]
        else:
            st.info("No buildings registered yet")
            building_id = "new"
            selected = "➕ Create New Building"
    
    with bcol2:
        if st.button(":material/description: Generate Building Report", width='stretch', disabled=building_id == "new"):
            st.session_state.generate_report = building_id
    
    # Create new building form
    if building_id == "new":
        with st.form("new_building_form"):
            st.markdown("**Register New Building**")
            bc1, bc2 = st.columns(2)
            with bc1:
                b_name = st.text_input("Building Name *", placeholder="e.g., TechCorp HQ Tower A")
                b_type = st.selectbox("Building Type *", BUILDING_TYPES)
                b_address = st.text_area("Address *", placeholder="Full address with landmarks")
            with bc2:
                b_lat = st.number_input("Latitude", format="%.6f", value=0.0)
                b_lon = st.number_input("Longitude", format="%.6f", value=0.0)
                b_contact = st.text_input("Contact Person")
                b_email = st.text_input("Contact Email")
            
            if st.form_submit_button("✅ Register Building", type="primary", width='stretch'):
                if b_name and b_address:
                    building = create_building(
                        name=b_name,
                        building_type=b_type,
                        address=b_address,
                        latitude=b_lat if b_lat != 0 else None,
                        longitude=b_lon if b_lon != 0 else None,
                        contact_name=b_contact or None,
                        contact_email=b_email or None,
                    )
                    st.success(f"Building registered: {building.name}")
                    st.rerun()
                else:
                    st.error("Name and address are required")
        return  # Don't show rest until building selected
    
    # Get selected building
    building = get_building(building_id)
    if not building:
        st.error("Building not found")
        return
    
    # Building header
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #2DD4BF15, #2DD4BF08); border: 1px solid #2DD4BF; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
        <div style="font-size: 1.2rem; font-weight: 700; color: #FFFFFF;">{building.name}</div>
        <div style="color: #9CA3AF; margin-top: 4px;">{building.building_type} • {building.address}</div>
        <div style="color: #6B7280; font-size: 0.85rem; margin-top: 4px;">Outdoor Reference: AQI {outdoor_aqi:.0f} | PM2.5 {outdoor_pm25:.1f} µg/m³ ({station_name})</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Room management
    st.markdown("#### :material/logout: Room Management")
    
    rooms = get_rooms(building_id)
    
    # Add room form
    with st.expander("➕ Add Room", expanded=len(rooms) == 0):
        with st.form("add_room_form"):
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                r_name = st.text_input("Room Name *", placeholder="e.g., Conference Room A, Floor 3")
                r_type = st.selectbox("Room Type *", ROOM_TYPES)
                r_floor = st.number_input("Floor", min_value=-5, max_value=100, value=1)
            with rc2:
                r_area = st.number_input("Area (sq ft)", min_value=50, max_value=10000, value=300, step=50)
                r_ceiling = st.number_input("Ceiling Height (ft)", min_value=7, max_value=30, value=9)
                r_purifier = st.checkbox("Has Air Purifier")
            with rc3:
                r_model = st.text_input("Purifier Model", placeholder="e.g., Philips AC1215") if r_purifier else ""
                r_notes = st.text_area("Notes", placeholder="HVAC details, occupancy, etc.")
            
            if st.form_submit_button("✅ Add Room", type="primary"):
                if r_name:
                    room = create_room(
                        building_id=building_id,
                        name=r_name,
                        room_type=r_type,
                        floor=r_floor,
                        area_sqft=r_area,
                        ceiling_ft=r_ceiling,
                        has_purifier=r_purifier,
                        purifier_model=r_model if r_purifier else None,
                    )
                    st.success(f"Room added: {room.name}")
                    st.rerun()
                else:
                    st.error("Room name required")
    
    # Room list with inline reading entry
    if rooms:
        st.markdown("#### :material/bar_chart: Room Status Dashboard")
        
        # Collect data for each room
        room_data = []
        for room in rooms:
            latest = get_latest_reading(room.id)
            indoor_pm25 = latest.pm25 if latest else None
            indoor_pm10 = latest.pm10 if latest else None
            
            # Calculate indoor/outdoor ratio
            io_ratio = None
            if indoor_pm25 and outdoor_pm25 > 0:
                io_ratio = indoor_pm25 / outdoor_pm25
            
            # Status determination
            if indoor_pm25 is None:
                status = "📭 No Data"
                status_color = "#6B7280"
            elif indoor_pm25 <= 15:
                status = "✅ Good"
                status_color = "#10B981"
            elif indoor_pm25 <= 35:
                status = "⚠️ Moderate"
                status_color = "#F59E0B"
            elif indoor_pm25 <= 75:
                status = "🟠 Poor"
                status_color = "#EF4444"
            else:
                status = "🔴 Hazardous"
                status_color = "#DC2626"
            
            room_data.append({
                "room": room,
                "latest": latest,
                "indoor_pm25": indoor_pm25,
                "indoor_pm10": indoor_pm10,
                "io_ratio": io_ratio,
                "status": status,
                "status_color": status_color,
            })
        
        # Summary metrics
        rooms_with_data = [r for r in room_data if r["indoor_pm25"] is not None]
        if rooms_with_data:
            avg_indoor = np.mean([r["indoor_pm25"] for r in rooms_with_data])
            avg_ratio = np.mean([r["io_ratio"] for r in rooms_with_data if r["io_ratio"]])
            concerning = len([r for r in rooms_with_data if r["indoor_pm25"] > 35])
            
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Rooms Monitored", f"{len(rooms_with_data)}/{len(rooms)}")
            with m2:
                st.metric("Avg Indoor PM2.5", f"{avg_indoor:.1f} µg/m³")
            with m3:
                st.metric("Avg I/O Ratio", f"{avg_ratio:.2f}" if avg_ratio else "N/A")
            with m4:
                st.metric("Rooms > 35 µg/m³", concerning, delta_color="inverse")
        
        # Room cards
        for rd in room_data:
            room = rd["room"]
            latest = rd["latest"]
            
            with st.container():
                cols = st.columns([2, 1, 1, 1, 1, 1])
                
                with cols[0]:
                    st.markdown(f"**{room.name}** ({room.room_type}, Floor {room.floor})")
                    if room.has_purifier and room.purifier_model:
                        st.caption(f":material/build: Purifier: {room.purifier_model}")
                
                with cols[1]:
                    if rd["indoor_pm25"] is not None:
                        st.metric("PM2.5", f"{rd['indoor_pm25']:.1f} µg/m³")
                    else:
                        st.metric("PM2.5", "—")
                
                with cols[2]:
                    if rd["indoor_pm10"] is not None:
                        st.metric("PM10", f"{rd['indoor_pm10']:.1f} µg/m³")
                    else:
                        st.metric("PM10", "—")
                
                with cols[3]:
                    if rd["io_ratio"] is not None:
                        ratio_color = "#10B981" if rd["io_ratio"] < 0.5 else "#F59E0B" if rd["io_ratio"] < 1.0 else "#EF4444"
                        st.markdown(f"<div style='color: {ratio_color}; font-weight: 600;'>I/O: {rd['io_ratio']:.2f}</div>", unsafe_allow_html=True)
                    else:
                        st.write("I/O: —")
                
                with cols[4]:
                    st.markdown(f"<div style='color: {rd['status_color']}; font-weight: 600;'>{rd['status']}</div>", unsafe_allow_html=True)
                
                with cols[5]:
                    # Quick reading entry
                    with st.popover("📝 Log Reading"):
                        with st.form(f"reading_form_{room.id}"):
                            r_pm25 = st.number_input("PM2.5 (µg/m³)", min_value=0.0, max_value=500.0, value=0.0, step=0.5)
                            r_pm10 = st.number_input("PM10 (µg/m³)", min_value=0.0, max_value=600.0, value=0.0, step=0.5)
                            r_co2 = st.number_input("CO2 (ppm)", min_value=300, max_value=5000, value=400, step=50)
                            r_temp = st.number_input("Temp (°C)", min_value=10.0, max_value=40.0, value=24.0, step=0.5)
                            r_humidity = st.number_input("Humidity (%)", min_value=10, max_value=90, value=50)
                            
                            if st.form_submit_button("Save Reading", type="primary"):
                                add_indoor_reading(
                                    room_id=room.id,
                                    pm25=r_pm25,
                                    pm10=r_pm10 if r_pm10 > 0 else None,
                                    co2=r_co2 if r_co2 > 400 else None,
                                    temperature=r_temp,
                                    humidity=r_humidity,
                                )
                                st.success("Reading saved!")
                                st.rerun()
        
        # Indoor vs Outdoor Comparison Chart
        st.markdown("---")
        st.markdown("#### :material/trending_up: Indoor vs Outdoor Comparison")
        
        chart_data = []
        for rd in room_data:
            if rd["indoor_pm25"] is not None:
                chart_data.append({
                    "Room": rd["room"].name,
                    "Indoor PM2.5": rd["indoor_pm25"],
                    "Outdoor PM2.5": outdoor_pm25,
                    "I/O Ratio": rd["io_ratio"] or 0,
                })
        
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Indoor PM2.5",
                x=df_chart["Room"],
                y=df_chart["Indoor PM2.5"],
                marker_color="#2DD4BF",
            ))
            fig.add_trace(go.Bar(
                name="Outdoor PM2.5 (Reference)",
                x=df_chart["Room"],
                y=df_chart["Outdoor PM2.5"],
                marker_color="#F59E0B",
                opacity=0.6,
            ))
            fig.add_hline(y=15, line_dash="dash", line_color="#10B981", 
                          annotation_text="WHO 24h Guideline (15 µg/m³)")
            fig.add_hline(y=35, line_dash="dash", line_color="#EF4444",
                          annotation_text="Interim Target-1 (35 µg/m³)")
            
            fig.update_layout(
                barmode="group",
                yaxis_title="PM2.5 (µg/m³)",
                template="plotly_dark",
                height=400,
                margin=dict(l=40, r=20, t=30, b=40),
            )
            st.plotly_chart(fig, width='stretch')
            
            # I/O Ratio chart
            if len(df_chart) > 0:
                fig2 = px.bar(
                    df_chart, 
                    x="Room", 
                    y="I/O Ratio",
                    title="Indoor/Outdoor PM2.5 Ratio (Lower = Better Filtration)",
                    color="I/O Ratio",
                    color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"],
                )
                fig2.add_hline(y=0.5, line_dash="dash", line_color="#10B981", annotation_text="Good filtration (<0.5)")
                fig2.add_hline(y=1.0, line_dash="dash", line_color="#EF4444", annotation_text="No filtration benefit (=1.0)")
                fig2.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig2, width='stretch')
        else:
            st.info("Add indoor readings to see comparison charts")
        
        # Generate Report
        if st.session_state.get("generate_report") == building_id:
            st.markdown("---")
            st.markdown("#### :material/description: Environmental Report")
            
            client = get_gemini_client()
            
            if st.button(":material/smart_toy: Generate AI-Powered Report", type="primary", width='stretch'):
                if client.api_key:
                    with st.spinner("Generating report..."):
                        rooms_for_report = []
                        for rd in room_data:
                            if rd["indoor_pm25"] is not None:
                                rooms_for_report.append({
                                    "name": rd["room"].name,
                                    "type": rd["room"].room_type,
                                    "indoor_pm25": rd["indoor_pm25"],
                                    "outdoor_pm25": outdoor_pm25,
                                    "indoor_outdoor_ratio": rd["io_ratio"] or 0,
                                })
                        
                        response = client.generate_enterprise_report(
                            building_name=building.name,
                            rooms_data=rooms_for_report,
                            outdoor_aqi=int(outdoor_aqi),
                            outdoor_pm25=outdoor_pm25,
                        )
                        
                        if response.success:
                            st.session_state.airsense_report = response.content
                        else:
                            st.error(f"Failed: {response.error}")
                else:
                    st.warning("Configure Groq API for AI reports")
            
            # Show report
            if "airsense_report" in st.session_state:
                st.markdown(f"""
                <div style="background: rgba(22,34,53,0.7); border: 1px solid #2DD4BF; border-radius: 12px; padding: 20px;">
                    {st.session_state.airsense_report.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
                
                # Download as text
                report_text = f"""AirSense Environmental Report
Building: {building.name}
Date: {datetime.now().strftime('%d %b %Y')}
Outdoor Reference: AQI {outdoor_aqi:.0f}, PM2.5 {outdoor_pm25:.1f} µg/m³ ({station_name})

{st.session_state.airsense_report}
"""
                st.download_button(
                    "📥 Download Report (TXT)",
                    report_text,
                    f"AirSense_Report_{building.name}_{datetime.now().strftime('%Y%m%d')}.txt",
                    "text/plain",
                    width='stretch'
                )
    else:
        st.info("No rooms added yet. Use 'Add Room' above to get started.")


def render_building_portfolio():
    """Render portfolio view of all buildings."""
    st.markdown("### :material/bar_chart: Building Portfolio Overview")
    
    buildings = get_buildings()
    
    if not buildings:
        st.info("No buildings registered. Go to AirSense tab to add your first building.")
        return
    
    # Portfolio metrics
    portfolio_data = []
    for building in buildings:
        rooms = get_rooms(building.id)
        rooms_with_data = 0
        avg_pm25 = 0
        max_pm25 = 0
        
        for room in rooms:
            latest = get_latest_reading(room.id)
            if latest:
                rooms_with_data += 1
                avg_pm25 += latest.pm25
                max_pm25 = max(max_pm25, latest.pm25)
        
        if rooms_with_data > 0:
            avg_pm25 = avg_pm25 / rooms_with_data
        
        portfolio_data.append({
            "Building": building.name,
            "Type": building.building_type,
            "Rooms": len(rooms),
            "Monitored": rooms_with_data,
            "Avg PM2.5": f"{avg_pm25:.1f}" if rooms_with_data else "—",
            "Max PM2.5": f"{max_pm25:.1f}" if rooms_with_data else "—",
            "Status": "✅ Good" if (rooms_with_data and avg_pm25 <= 15) else 
                      "⚠️ Review" if (rooms_with_data and avg_pm25 <= 35) else
                      "🔴 Action Needed" if rooms_with_data else "📭 No Data",
        })
    
    df = pd.DataFrame(portfolio_data)
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Quick stats
    monitored = sum(1 for b in buildings if get_rooms(b.id) and any(get_latest_reading(r.id) for r in get_rooms(b.id)))
    st.caption(f"{monitored}/{len(buildings)} buildings have active monitoring")


if __name__ == "__main__":
    print("AirSense Enterprise module loaded")