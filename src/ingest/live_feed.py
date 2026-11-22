"""
Live Data Feed Module for Atmosphere360
Fetches real-time weather, air quality forecast, and live CPCB/news data.
Combines with 3-year historical baseline for analytics.
"""
import streamlit as st
import math
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from config import get_openmeteo_key, get_serpapi_key
from serpapi_client import get_client as get_serpapi_client

def _format_delta(delta) -> str | None:
    """Returns a display string for a baseline delta, or None when unavailable."""
    try:
        value = float(delta)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return f"({value:+.1f} vs 3yr avg)"


# Mumbai coordinates for different stations
MUMBAI_STATION_COORDS = {
    "Bandra Kurla Complex": (19.0596, 72.8656),
    "Colaba": (18.9217, 72.8347),
    "Worli": (19.0076, 72.8261),
    "Andheri": (19.1197, 72.8464),
    "Borivali": (19.2388, 72.8567),
    "Navi Mumbai": (19.0330, 73.0297),
    "Thane": (19.2183, 72.9781),
    "Vasai": (19.4915, 72.8054),
    "Kalyan": (19.2437, 73.1355),
    "Mumbai Central": (19.0760, 72.8777),
}

DEFAULT_COORDS = (19.0760, 72.8777)  # Mumbai Central


@st.cache_data(ttl=1800)  # 30 minutes
def fetch_openmeteo_forecast(lat: float, lon: float, days: int = 2) -> Optional[Dict[str, Any]]:
    """
    Fetch weather forecast from Open-Meteo (keyless, free).
    Returns hourly: temp, humidity, wind, precipitation + daily max/min.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,rain,pressure_msl",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
            "timezone": "Asia/Kolkata",
            "forecast_days": days,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        data["_source"] = "Open-Meteo Forecast (Model)"
        data["_fetched_at"] = datetime.now().isoformat()
        return data
    except Exception as e:
        st.warning(f"Open-Meteo forecast fetch failed: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_openmeteo_air_quality(lat: float, lon: float, days: int = 2) -> Optional[Dict[str, Any]]:
    """
    Fetch air quality forecast from Open-Meteo Air Quality API (keyless).
    Returns hourly: pm2_5, pm10, european_aqi, us_aqi, no2, o3, so2, co.
    """
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    # Try minimal request first (most compatible)
    for attempt in range(3):
        try:
            if attempt == 0:
                # Minimal: just the basics that definitely work
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "pm2_5,pm10,us_aqi",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": days,
                }
            elif attempt == 1:
                # Add european_aqi
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "pm2_5,pm10,us_aqi,european_aqi",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": days,
                }
            else:
                # Full set
                params = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "pm2_5,pm10,us_aqi,european_aqi,no2,o3,so2,co",
                    "timezone": "Asia/Kolkata",
                    "forecast_days": days,
                }
            
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            data["_source"] = f"Open-Meteo Air Quality (Model - attempt {attempt+1})"
            data["_fetched_at"] = datetime.now().isoformat()
            return data
        except Exception as e:
            if attempt == 2:
                st.warning(f"Open-Meteo air quality fetch failed after 3 attempts: {e}")
                return None
            continue
    
    return None


@st.cache_data(ttl=3600)  # 1 hour
def fetch_live_cpcb_analytics() -> Optional[List[Dict[str, Any]]]:
    """
    Use SerpApi Extract to scrape live CPCB/SAFAR bulletins.
    Returns list of {title, url, snippet, source, timestamp}.
    """
    serpapi = get_serpapi_client()
    if not serpapi.api_key:
        return None
    
    try:
        # Search for live CPCB AQI bulletins
        response = serpapi.search("CPCB AQI bulletin Mumbai today live air quality")
        if not response.success or not response.data:
            return None
        
        organic = response.data.get("organic_results", [])
        results = []
        for item in organic[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "CPCB/SAFAR (via SerpApi)",
                "timestamp": datetime.now().isoformat(),
            })
        return results
    except Exception as e:
        st.warning(f"Live CPCB analytics fetch failed: {e}")
        return None


@st.cache_data(ttl=1800)
def fetch_pollution_news_serpapi(location: str = "Mumbai") -> Optional[List[Dict[str, Any]]]:
    """
    Fetch latest pollution news via SerpApi Google News.
    """
    serpapi = get_serpapi_client()
    if not serpapi.api_key:
        return None
    
    try:
        response = serpapi.get_pollution_news(location)
        if not response.success or not response.data:
            return None
        
        news = response.data.get("news_results", [])
        results = []
        for item in news[:5]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", ""),
                "published": item.get("date", ""),
            })
        return results
    except Exception as e:
        st.warning(f"Pollution news fetch failed: {e}")
        return None


@st.cache_data(ttl=3600)
def fetch_pollution_sources_near_station(station_name: str) -> Optional[List[Dict[str, Any]]]:
    """
    Use SerpApi Google Maps to find pollution sources near a monitoring station.
    """
    serpapi = get_serpapi_client()
    if not serpapi.api_key:
        return None
    
    try:
        response = serpapi.find_pollution_sources(station_name)
        if not response.success or not response.data:
            return None
        
        local = response.data.get("local_results", [])
        results = []
        for place in local[:10]:
            results.append({
                "name": place.get("title", ""),
                "address": place.get("address", ""),
                "type": place.get("type", ""),
                "rating": place.get("rating", 0),
            })
        return results
    except Exception as e:
        st.warning(f"Pollution sources fetch failed: {e}")
        return None


def get_station_coordinates(station_name: str) -> tuple:
    """Get lat/lon for a station, fallback to Mumbai Central."""
    return MUMBAI_STATION_COORDS.get(station_name, DEFAULT_COORDS)


def compute_seasonal_baseline(historical_df: pd.DataFrame, station_name: str, 
                              target_date: datetime) -> Dict[str, float]:
    """
    Compute 3-year historical baseline for the given date (day of year).
    Returns average AQI, PM2.5, PM10, temp, humidity for that day-of-year.
    """
    station_data = historical_df[historical_df["canonical_station"] == station_name].copy()
    if station_data.empty:
        return {}
    
    doy = target_date.timetuple().tm_yday
    # Filter to same day-of-year across years
    station_data["doy"] = station_data["date"].dt.dayofyear
    same_doy = station_data[station_data["doy"] == doy]
    
    if same_doy.empty:
        # Expand to +/- 3 days
        same_doy = station_data[station_data["doy"].between(doy - 3, doy + 3)]
    
    if same_doy.empty:
        return {}
    
    return {
        "avg_aqi": same_doy["aqi_mean"].mean(),
        "avg_pm25": same_doy.get("pm25_mean", pd.Series()).mean(),
        "avg_pm10": same_doy.get("pm10_mean", pd.Series()).mean(),
        "avg_temp": same_doy.get("temp_mean", pd.Series()).mean(),
        "avg_humidity": same_doy.get("humidity_mean", pd.Series()).mean(),
        "sample_years": same_doy["date"].dt.year.nunique(),
    }


def build_live_context(station_name: str, historical_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Build complete live context for a station:
    - Live forecast (weather + AQI)
    - Seasonal baseline (3-year)
    - Delta cards (Live vs Baseline)
    - CPCB live analytics
    - Pollution news
    All clearly labeled as Measured/Model/Live Scraped.
    """
    lat, lon = get_station_coordinates(station_name)
    now = datetime.now()
    
    # Fetch live data (cached)
    weather_fc = fetch_openmeteo_forecast(lat, lon)
    aqi_fc = fetch_openmeteo_air_quality(lat, lon)
    cpcb_live = fetch_live_cpcb_analytics()
    news = fetch_pollution_news_serpapi("Mumbai")
    
    # Seasonal baseline
    baseline = compute_seasonal_baseline(historical_df, station_name, now)
    
    # Current live values (first hour of forecast)
    current = {}
    if weather_fc and "hourly" in weather_fc:
        h = weather_fc["hourly"]
        idx = 0  # current hour
        current["temperature"] = h["temperature_2m"][idx] if h["temperature_2m"] else None
        current["humidity"] = h["relative_humidity_2m"][idx] if h["relative_humidity_2m"] else None
        current["wind_speed"] = h["wind_speed_10m"][idx] if h["wind_speed_10m"] else None
        current["wind_dir"] = h["wind_direction_10m"][idx] if h["wind_direction_10m"] else None
        current["precipitation"] = h["precipitation"][idx] if h["precipitation"] else 0
    
    if aqi_fc and "hourly" in aqi_fc:
        h = aqi_fc["hourly"]
        idx = 0
        current["pm25"] = h["pm2_5"][idx] if h.get("pm2_5") else None
        current["pm10"] = h["pm10"][idx] if h.get("pm10") else None
        current["us_aqi"] = h["us_aqi"][idx] if h.get("us_aqi") else None
        current["european_aqi"] = h["european_aqi"][idx] if h.get("european_aqi") else None
    
    # Compute deltas vs baseline
    deltas = {}
    if baseline:
        for key in ["pm25", "pm10", "temperature", "humidity"]:
            baseline_key = f"avg_{key}" if key != "us_aqi" else "avg_aqi"
            if key in current and current[key] is not None and baseline_key in baseline:
                deltas[key] = current[key] - baseline[baseline_key]
    
    return {
        "station": station_name,
        "coordinates": {"lat": lat, "lon": lon},
        "timestamp": now.isoformat(),
        "current": current,
        "baseline": baseline,
        "deltas": deltas,
        "weather_forecast": weather_fc,
        "aqi_forecast": aqi_fc,
        "cpcb_live": cpcb_live,
        "news": news,
        "labels": {
            "current": "Live (Open-Meteo Model)",
            "baseline": "3-Year Historical Average (CPCB Measured)",
            "forecast": "48h Forecast (Open-Meteo Model)",
            "cpcb_live": "Live Scraped (CPCB/SAFAR via SerpApi)",
            "news": "Live News (Google News via SerpApi)",
        }
    }


def render_live_city_pulse_strip(context: Dict[str, Any]) -> None:
    """Renders a compact, two-row live city pulse readout for the sidebar."""
    if not context or not context.get("current"):
        return

    cur = context["current"]
    deltas = context.get("deltas", {})
    labels = context.get("labels", {})

    st.markdown("#### :material/rss_feed: Live city pulse")
    row1, row2 = st.columns(2, gap="small"), st.columns(2, gap="small")

    pm25 = cur.get("pm25")
    pm10 = cur.get("pm10")
    aqi = cur.get("us_aqi") or cur.get("european_aqi")
    wind = cur.get("wind_speed")

    with row1[0]:
        st.metric("PM2.5 (µg/m³)", f"{pm25:.1f}" if pm25 else "—",
                  delta=_format_delta(deltas.get("pm25")), delta_color="inverse")
    with row1[1]:
        st.metric("PM10 (µg/m³)", f"{pm10:.1f}" if pm10 else "—",
                  delta=_format_delta(deltas.get("pm10")), delta_color="inverse")
    with row2[0]:
        st.metric("AQI", f"{aqi:.0f}" if aqi else "—")
    with row2[1]:
        st.metric("Wind (km/h)", f"{wind:.1f}" if wind else "—")

    st.caption(f"Source: {labels.get('current', 'Live model')}")


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.insert(0, ".")
    
    print("Testing live feed...")
    lat, lon = 19.0760, 72.8777
    
    w = fetch_openmeteo_forecast(lat, lon)
    print(f"Weather forecast: {'OK' if w else 'FAIL'}")
    
    a = fetch_openmeteo_air_quality(lat, lon)
    print(f"AQI forecast: {'OK' if a else 'FAIL'}")