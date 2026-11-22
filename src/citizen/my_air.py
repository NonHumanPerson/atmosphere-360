"""
My Air — Personal AQI Intelligence (Module 1)
Citizen-facing personal air quality dashboard.
"""
import streamlit as st
import math
from html import escape
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from config import AQI_CATEGORIES
from theme import COLORS, get_aqi_category_color
from src.utils.cadr_calculator import calculate_required_cadr
from src.llm import get_gemini_client, GeminiResponse


def get_aqi_category(aqi: float) -> Tuple[str, str]:
    """Get AQI category name and color."""
    for cat, (low, high, color) in AQI_CATEGORIES.items():
        if low <= aqi <= high:
            return cat, color
    return "Unknown", "#6B7280"


def get_activity_recommendation(aqi: float) -> Dict[str, str]:
    """Get outdoor activity recommendations based on AQI."""
    if aqi <= 50:
        return {
            "level": "Safe for all activities",
            "general": "Enjoy outdoor activities normally.",
            "sensitive": "No restrictions needed.",
            "icon": "check_circle"
        }
    elif aqi <= 100:
        return {
            "level": "Moderate — sensitive groups take care",
            "general": "Consider reducing prolonged outdoor exertion.",
            "sensitive": "Reduce prolonged outdoor exertion. Keep medications handy.",
            "icon": "warning"
        }
    elif aqi <= 200:
        return {
            "level": "Unhealthy for sensitive groups",
            "general": "Reduce prolonged outdoor exertion. Consider indoor alternatives.",
            "sensitive": "Avoid prolonged outdoor exertion. Stay indoors with air filtration.",
            "icon": "warning"
        }
    elif aqi <= 300:
        return {
            "level": "Unhealthy — everyone should limit outdoor activity",
            "general": "Avoid prolonged outdoor exertion. Move activities indoors.",
            "sensitive": "Avoid all outdoor physical activity. Use air purifier indoors.",
            "icon": "cancel"
        }
    else:
        return {
            "level": "Hazardous — stay indoors",
            "general": "Avoid all outdoor activity. Keep windows closed.",
            "sensitive": "Remain indoors with air filtration. Seek medical advice if symptomatic.",
            "icon": "dangerous"
        }


def calculate_air_score(aqi: float, pm25: float, pm10: float) -> int:
    """
    Calculate simple 'Your Air Score' (0-100, higher = better).
    Inverse of pollution level.
    """
    # Normalize: AQI 0-500 -> score 100-0
    aqi_score = max(0, 100 - (aqi / 5))
    # PM2.5 component (WHO guideline 5 µg/m³ annual, 15 24h)
    pm25_score = max(0, 100 - (pm25 / 0.75))
    # PM10 component (WHO guideline 15 µg/m³ annual, 45 24h)
    pm10_score = max(0, 100 - (pm10 / 2.25))
    
    # Weighted average
    score = int(0.5 * aqi_score + 0.3 * pm25_score + 0.2 * pm10_score)
    return max(0, min(100, score))


def _delta_html(delta, suffix: str = "vs 3yr avg") -> str:
    """Formats a baseline delta; missing or non-finite values render nothing."""
    try:
        value = float(delta)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(value):
        return ""
    colour = COLORS["critical"] if value > 0 else COLORS["success"]
    return (
        f' <span class="cp-delta" style="color: {colour};">'
        f'({value:+.1f} {suffix})</span>'
    )


def render_my_air_tab(
    daily_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    station_name: str,
    decision_date: str,
    live_context: Optional[Dict[str, Any]] = None
):
    """Render My Air - Personal AQI Intelligence tab."""
    st.markdown("### :material/home: My Air — personal AQI intelligence")
    
    # Show live vs historical context
    if live_context:
        labels = live_context.get("labels", {})
        st.caption(f":material/location_on: {station_name} · {labels.get('current', 'Live Model')} vs {labels.get('baseline', '3yr Baseline')} · Replay: {decision_date}")
    else:
        st.caption(f"Real-time air quality for **{station_name}** • Decision replay: {decision_date}")
    
    # Get latest data for this station
    station_daily = daily_df[daily_df["canonical_station"] == station_name].sort_values("date")
    station_preds = preds_df[preds_df["canonical_station"] == station_name].sort_values("date")
    
    if station_daily.empty:
        st.warning(f"No data available for {station_name}")
        return
    
    latest = station_daily.iloc[-1]
    latest_pred = station_preds.iloc[-1] if not station_preds.empty else None
    
    # Current AQI metrics - prefer live data if available
    if live_context and live_context.get("current"):
        cur = live_context["current"]
        aqi = cur.get("us_aqi") or cur.get("european_aqi") or latest.get("aqi_mean", 0)
        pm25 = cur.get("pm25") or latest.get("pm25_mean", 0)
        pm10 = cur.get("pm10") or latest.get("pm10_mean", 0)
        temp = cur.get("temperature") or latest.get("temp_mean", 0)
        humidity = cur.get("humidity") or latest.get("humidity_mean", 0)
        wind = cur.get("wind_speed") or latest.get("wind_speed_mean", 0)
        data_source = "Live (Open-Meteo Model)"
    else:
        aqi = latest.get("aqi_mean", 0)
        pm25 = latest.get("pm25_mean", 0)
        pm10 = latest.get("pm10_mean", 0)
        temp = latest.get("temp_mean", 0)
        humidity = latest.get("humidity_mean", 0)
        wind = latest.get("wind_speed_mean", 0)
        data_source = "Historical Replay (CPCB Measured)"
    
    # Baseline comparison
    baseline = live_context.get("baseline", {}) if live_context else {}
    deltas = live_context.get("deltas", {}) if live_context else {}
    
    category, color = get_aqi_category(aqi)
    activity = get_activity_recommendation(aqi)
    air_score = calculate_air_score(aqi, pm25, pm10)
    
    # Top row: AQI Card + Air Score + Category
    col1, col2, col3 = st.columns([1.5, 1, 1])
    
    with col1:
        # Main AQI Display
        updated = (
            latest["date"].strftime("%d %b %Y, %H:%M")
            if hasattr(latest["date"], "strftime") else str(latest["date"])[:16]
        )
        st.markdown(
            f'<div class="cp-hero-card" style="--cp-card-accent: {color};">'
            '<div class="cp-hero-label">Current AQI</div>'
            f'<div class="cp-hero-value">{aqi:.0f}</div>'
            f'<div class="cp-hero-sub">{escape(str(category))}</div>'
            f'<div class="cp-hero-meta">Updated: {escape(str(updated))}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    
    with col2:
        # Air Score
        score_color = "#10B981" if air_score >= 70 else "#F59E0B" if air_score >= 40 else "#EF4444"
        st.markdown(
            f'<div class="cp-hero-card" style="--cp-card-accent: {score_color};">'
            '<div class="cp-hero-label">Your air score</div>'
            f'<div class="cp-hero-value">{air_score}</div>'
            '<div class="cp-hero-sub">/ 100 · '
            f'{"Good" if air_score >= 70 else "Fair" if air_score >= 40 else "Poor"}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    
    with col3:
        # Activity Recommendation
        st.markdown(
            f'<div class="cp-guidance-card" style="--cp-card-accent: {color};">'
            f'<span class="cp-guidance-icon" aria-hidden="true">{activity["icon"]}</span>'
            '<div class="cp-hero-label">Activity guidance</div>'
            f'<div class="cp-guidance-title">{escape(str(activity["level"]))}</div>'
            f'<div class="cp-guidance-body"><strong>General:</strong> '
            f'{escape(str(activity["general"]))}<br>'
            f'<strong>Sensitive:</strong> {escape(str(activity["sensitive"]))}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    
    st.markdown("---")
    
    # Second row: Pollutants + Weather + Forecast
    col_p, col_w, col_f = st.columns(3)
    
    with col_p:
        st.markdown("#### :material/air: Key pollutants")
        pm25_cat, pm25_color = get_aqi_category(pm25 * 2)  # Rough conversion
        pm10_cat, pm10_color = get_aqi_category(pm10 * 1.5)
        
        # Baseline deltas
        pm25_delta = deltas.get("pm25")
        pm10_delta = deltas.get("pm10")
        
        # Compute delta colors and strings
        pm25_delta_str = _delta_html(pm25_delta)
        pm10_delta_str = _delta_html(pm10_delta)
        
        st.markdown(
            '<dl class="cp-detail-card">'
            f'<div class="cp-detail-row"><dt>PM2.5</dt><dd style="color: {pm25_color};">'
            f'{pm25:.1f} µg/m³{pm25_delta_str}</dd></div>'
            f'<div class="cp-detail-row"><dt>PM10</dt><dd style="color: {pm10_color};">'
            f'{pm10:.1f} µg/m³{pm10_delta_str}</dd></div>'
            f'<div class="cp-detail-note">WHO 24h guideline: PM2.5 ≤ 15, PM10 ≤ 45 µg/m³ · '
            f'Source: {escape(str(data_source))}</div>'
            '</dl>',
            unsafe_allow_html=True,
        )
    
    with col_w:
        st.markdown("#### :material/partly_cloudy_day: Current weather")
        temp_delta = deltas.get("temperature")
        hum_delta = deltas.get("humidity")
        
        temp_delta_str = _delta_html(temp_delta)
        hum_delta_str = _delta_html(hum_delta)
        
        dispersion = "Good dispersion" if wind > 10 else "Poor dispersion — pollution may accumulate"
        st.markdown(
            '<dl class="cp-detail-card">'
            f'<div class="cp-detail-row"><dt>Temperature</dt><dd>{temp:.1f} °C{temp_delta_str}</dd></div>'
            f'<div class="cp-detail-row"><dt>Humidity</dt><dd>{humidity:.0f} %{hum_delta_str}</dd></div>'
            f'<div class="cp-detail-row"><dt>Wind speed</dt><dd>{wind:.1f} km/h</dd></div>'
            f'<div class="cp-detail-note">{escape(dispersion)} · Source: {escape(str(data_source))}</div>'
            '</dl>',
            unsafe_allow_html=True,
        )
    
    with col_f:
        st.markdown("#### :material/query_stats: Tomorrow's forecast")
        
        # Prefer live Open-Meteo forecast
        live_fc_aqi = None
        live_fc_pm25 = None
        live_fc_source = "LightGBM (Historical Model)"
        
        if live_context and live_context.get("aqi_forecast") and "daily" in live_context["aqi_forecast"]:
            daily_fc = live_context["aqi_forecast"]["daily"]
            if "us_aqi_max" in daily_fc and daily_fc["us_aqi_max"]:
                live_fc_aqi = daily_fc["us_aqi_max"][0] if daily_fc["us_aqi_max"] else None
                live_fc_source = "Open-Meteo AQI Forecast (Model)"
            elif "european_aqi_max" in daily_fc and daily_fc["european_aqi_max"]:
                live_fc_aqi = daily_fc["european_aqi_max"][0] if daily_fc["european_aqi_max"] else None
                live_fc_source = "Open-Meteo AQI Forecast (Model)"
            if "pm2_5_max" in daily_fc and daily_fc["pm2_5_max"]:
                live_fc_pm25 = daily_fc["pm2_5_max"][0] if daily_fc["pm2_5_max"] else None
        
        # Fallback to LightGBM
        pred_aqi = live_fc_aqi if live_fc_aqi is not None else (latest_pred.get("pred_gb", aqi) if latest_pred is not None else aqi)
        pred_cat, pred_color = get_aqi_category(pred_aqi)
        delta = pred_aqi - aqi
        delta_str = f"{delta:+.0f}" if delta != 0 else "No change"
        delta_color = "#EF4444" if delta > 10 else "#F59E0B" if delta > 0 else "#10B981"
        
        pm_note = f"PM2.5 max: {live_fc_pm25:.1f} µg/m³" if live_fc_pm25 else ""
        st.markdown(
            '<dl class="cp-detail-card">'
            f'<div class="cp-detail-row"><dt>Predicted AQI</dt><dd style="color: {pred_color};">{pred_aqi:.0f}</dd></div>'
            f'<div class="cp-detail-row"><dt>Category</dt><dd style="color: {pred_color};">{escape(str(pred_cat))}</dd></div>'
            f'<div class="cp-detail-row"><dt>Change</dt><dd style="color: {delta_color};">{delta_str}</dd></div>'
            f'<div class="cp-detail-note">{escape(str(live_fc_source))}{" · " + pm_note if pm_note else ""}</div>'
            '</dl>',
            unsafe_allow_html=True,
        )
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("#### :material/bolt: Quick actions")
    qcol1, qcol2, qcol3 = st.columns(3)
    
    with qcol1:
        if st.button(":material/medical_services: Get personalized advice", width='stretch', type="primary"):
            st.session_state.show_aircare = True
            st.session_state.aircare_context = "home"
            st.rerun()
    
    with qcol2:
        if st.button(":material/search: Find an air purifier", width='stretch'):
            st.session_state.show_purifier = True
            st.rerun()
    
    with qcol3:
        if st.button(":material/location_on: Report pollution", width='stretch'):
            st.session_state.show_civic = True
            st.rerun()


def render_aircare_tab(
    daily_df: pd.DataFrame,
    preds_df: pd.DataFrame,
    station_name: str,
    decision_date: str,
    live_context: Optional[Dict[str, Any]] = None
):
    """Render AirCare - AI Personal Action Assistant tab."""
    st.markdown("### :material/medical_services: AirCare — personal action assistant")
    
    if live_context:
        labels = live_context.get("labels", {})
        st.caption(f":material/location_on: {station_name} · {labels.get('current', 'Live Model')} · Get personalized advice")
    else:
        st.caption("Get personalized air quality guidance based on your context and current conditions")
    
    # Get latest data - prefer live if available
    station_daily = daily_df[daily_df["canonical_station"] == station_name].sort_values("date")
    if station_daily.empty:
        st.warning("No data available")
        return
    
    latest = station_daily.iloc[-1]
    
    # Use live data if available
    if live_context and live_context.get("current"):
        cur = live_context["current"]
        aqi = cur.get("us_aqi") or cur.get("european_aqi") or latest.get("aqi_mean", 0)
        pm25 = cur.get("pm25") or latest.get("pm25_mean", 0)
        pm10 = cur.get("pm10") or latest.get("pm10_mean", 0)
        temp = cur.get("temperature") or latest.get("temp_mean", 0)
        humidity = cur.get("humidity") or latest.get("humidity_mean", 0)
        wind = cur.get("wind_speed") or latest.get("wind_speed_mean", 0)
        data_source = "Live (Open-Meteo Model)"
    else:
        aqi = latest.get("aqi_mean", 0)
        pm25 = latest.get("pm25_mean", 0)
        pm10 = latest.get("pm10_mean", 0)
        temp = latest.get("temp_mean", 0)
        humidity = latest.get("humidity_mean", 0)
        wind = latest.get("wind_speed_mean", 0)
        data_source = "Historical Replay (CPCB Measured)"
    
    # Context selector
    st.markdown("#### :material/person_pin_circle: Where are you right now?")
    contexts = {
        "home": "🏠 At Home",
        "office": "🏢 At Office/Work",
        "school": "🏫 At School/College",
        "outdoors": "🚶 Outdoors/Commuting",
    }
    
    selected_context = st.segmented_control(
        "Context",
        options=list(contexts.keys()),
        format_func=lambda x: contexts[x],
        default=st.session_state.get("aircare_context", "home"),
        label_visibility="collapsed"
    )
    
    if selected_context:
        st.session_state.aircare_context = selected_context
    
    # Generate AI advice with enhanced context
    client = get_gemini_client()
    
    # Build enhanced context for AI
    forecast_summary = "No forecast available"
    if live_context and live_context.get("aqi_forecast") and "daily" in live_context["aqi_forecast"]:
        daily_fc = live_context["aqi_forecast"]["daily"]
        if "us_aqi_max" in daily_fc and daily_fc["us_aqi_max"]:
            fc_aqi = daily_fc["us_aqi_max"][0] if daily_fc["us_aqi_max"] else None
            if fc_aqi:
                trend = "rising" if fc_aqi > aqi else "falling" if fc_aqi < aqi else "stable"
                forecast_summary = f"Tomorrow max AQI: {fc_aqi:.0f} ({trend})"
    
    news_summary = ""
    if live_context and live_context.get("news"):
        news_items = live_context["news"][:2]
        news_summary = "; ".join([n.get("title", "")[:80] for n in news_items if n.get("title")])
    
    cpcb_summary = ""
    if live_context and live_context.get("cpcb_live"):
        cpcb_items = live_context["cpcb_live"][:2]
        cpcb_summary = "; ".join([c.get("title", "")[:80] for c in cpcb_items if c.get("title")])
    
    if st.button(":material/smart_toy: Get personalized recommendations", width='stretch', type="primary"):
        with st.spinner("Analyzing air quality and generating advice..."):
            response = client.generate_aircare_advice(
                context=selected_context,
                aqi=int(aqi),
                pm25=pm25,
                pm10=pm10,
                temp=temp,
                humidity=humidity,
                wind_speed=wind,
                forecast_summary=forecast_summary,
                news_summary=news_summary,
                cpcb_summary=cpcb_summary,
                data_source=data_source
            )
        
        if response.success:
            st.markdown("#### :material/lightbulb: Your personalized action plan")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #2DD4BF22, #2DD4BF11); 
                        border: 1px solid #2DD4BF; border-radius: 12px; padding: 20px;">
                {response.content.replace(chr(10), '<br>')}
            </div>
            """, unsafe_allow_html=True)
            
            # Add context-specific tips
            st.markdown("---")
            st.markdown("#### :material/checklist: Context-specific checklist")
            _render_context_checklist(selected_context, aqi)
        else:
            st.error(f"Failed to generate advice: {response.error}")
            _render_fallback_advice(selected_context, aqi)
    
    # Show cached/fallback advice immediately
    if "aircare_last_advice" in st.session_state:
        st.markdown("#### :material/lightbulb: Your personalized action plan")
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #2DD4BF22, #2DD4BF11); 
                    border: 1px solid #2DD4BF; border-radius: 12px; padding: 20px;">
            {st.session_state.aircare_last_advice.replace(chr(10), '<br>')}
        </div>
        """, unsafe_allow_html=True)
        _render_context_checklist(selected_context, aqi)


def _render_context_checklist(context: str, aqi: float):
    """Render context-specific action checklist."""
    checklists = {
        "home": [
            ("Keep windows closed" if aqi > 100 else "Ventilate during cleaner hours", "windows"),
            ("Run air purifier on high" if aqi > 150 else "Run air purifier on auto", "purifier"),
            ("Avoid cooking fumes - use exhaust", "cooking"),
            ("Stay hydrated", "water"),
            ("Monitor symptoms (cough, irritation)", "health"),
        ],
        "office": [
            ("Check if building HVAC has MERV-13+ filters", "hvac"),
            ("Request portable purifier for workspace" if aqi > 150 else "Current filtration adequate", "purifier"),
            ("Limit outdoor breaks" if aqi > 100 else "Normal outdoor breaks OK", "breaks"),
            ("Report IAQ concerns to facilities", "report"),
            ("Stay hydrated", "water"),
        ],
        "school": [
            ("Move outdoor activities indoors" if aqi > 100 else "Monitor outdoor time", "outdoor"),
            ("Check classroom ventilation/CO2 levels", "ventilation"),
            ("Ensure sensitive students have action plans", "students"),
            ("Communicate with parents if AQI > 200", "parents"),
            ("Have masks available for staff/students", "masks"),
        ],
        "outdoors": [
            ("Wear N95/KN95 mask" if aqi > 100 else "Consider mask if sensitive", "mask"),
            ("Limit exertion - walk don't run" if aqi > 150 else "Normal pace OK", "pace"),
            ("Choose routes away from heavy traffic", "route"),
            ("Check real-time AQI along route", "check"),
            ("Shower and change clothes after returning", "shower"),
        ],
    }
    
    items = checklists.get(context, checklists["home"])
    
    for text, key in items:
        checked = st.checkbox(text, key=f"checklist_{context}_{key}")


def _render_fallback_advice(context: str, aqi: float):
    """Fallback advice when AI is unavailable."""
    category, _ = get_aqi_category(aqi)
    
    advice_map = {
        "home": f"At home with AQI {aqi} ({category}): Keep windows closed if AQI > 100. Use air purifier if available. Stay hydrated.",
        "office": f"At work with AQI {aqi} ({category}): Check building filtration. Limit outdoor breaks if AQI > 100. Request portable purifier if needed.",
        "school": f"At school with AQI {aqi} ({category}): Move recess indoors if AQI > 100. Ensure sensitive students have care plans. Monitor CO2 in classrooms.",
        "outdoors": f"Outdoors with AQI {aqi} ({category}): Wear N95 mask if AQI > 100. Limit strenuous activity. Choose less trafficked routes.",
    }
    
    st.warning(f":material/warning: AI service unavailable. General guidance:\n\n{advice_map.get(context, advice_map['home'])}")


if __name__ == "__main__":
    # Quick test
    print("My Air / AirCare module loaded")
    print(f"AQI Categories: {len(AQI_CATEGORIES)}")
    print(f"Activity recommendations tested for AQI 25: {get_activity_recommendation(25)}")
    print(f"Activity recommendations tested for AQI 150: {get_activity_recommendation(150)}")
    print(f"Activity recommendations tested for AQI 350: {get_activity_recommendation(350)}")
    print(f"Air Score for AQI=50, PM2.5=12, PM10=20: {calculate_air_score(50, 12, 20)}")
    print(f"Air Score for AQI=200, PM2.5=85, PM10=150: {calculate_air_score(200, 85, 150)}")