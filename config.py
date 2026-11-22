"""
Atmosphere360: Mumbai — Air Quality & Health Action Platform
Global Configuration for Beyond 9TO5 Buildathon Mumbai Edition
"""
import os
from typing import Optional

EVENT_NAME = "Beyond 9TO5 Buildathon — Mumbai Edition"
TEAM_MEMBERS = "Ratnesh Pathak"
APP_NAME = "Atmosphere360: Mumbai"
APP_TAGLINE = "Air Quality & Health Action Platform"
APP_VERSION = "2.0.0"

DATA_ATTRIBUTION = "CPCB / Open-Meteo / OpenStreetMap contributors (ODbL) / SerpApi / Google Gemini"

DISCLAIMER_TEXT = (
    f"{APP_NAME} is a prototype, not an official warning system. "
    f"Data: {DATA_ATTRIBUTION}. See DATA_SOURCES.md for licences and access dates. "
    f"All AI recommendations require human-in-the-loop verification. "
    f"Synthetic data is clearly labeled and not real PII."
)

# User Modes
USER_MODES = {
    "citizen": ":material/home: Citizen — My Air & Health",
    "officer": ":material/account_balance: Officer — Command Center",
    "enterprise": ":material/business: Enterprise — AirSense",
    "admin": ":material/admin_panel_settings: Admin — Owner Panel",
}

DEFAULT_MODE = "citizen"

# SerpApi Engines
SERPAPI_ENGINES = [
    "google_search",
    "google_maps",
    "google_shopping",
    "google_news",
    "extract",
]

def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Safely retrieves a secret from Streamlit secrets (st.secrets) with
    fallback to OS environment variables. Never raises KeyError.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = st.secrets[key]
            if val is not None and str(val).strip():
                return str(val).strip()
    except Exception:
        pass

    env_val = os.environ.get(key)
    if env_val is not None and env_val.strip():
        return env_val.strip()

    return default

def get_serpapi_key() -> Optional[str]:
    """Get SerpApi key from secrets or environment."""
    # Hardcoded for hackathon demo
    return "a60b14455614046c2486feeac487a1bf3316486b42d2db874757938f74736a16"

def get_groq_key() -> Optional[str]:
    """Get Groq API key from secrets or environment."""
    return get_secret("GROQ_API_KEY")

def get_openmeteo_key() -> Optional[str]:
    """Get Open-Meteo key (optional, for higher rate limits)."""
    return get_secret("OPENMETEO_API_KEY")

def get_gemini_key() -> Optional[str]:
    """Get Google Gemini API key from secrets or environment."""
    return get_secret("GEMINI_API_KEY")

# Default policy weights (from Atmosphere360 1.0)
DEFAULT_WEIGHTS = {
    "w_exp": 0.30,
    "w_pers": 0.25,
    "w_trend": 0.15,
    "w_fore": 0.20,
    "w_gap": 0.10,
}

# AQI Categories (CPCB Standard)
AQI_CATEGORIES = {
    "Good": (0, 50, "#10B981"),
    "Satisfactory": (51, 100, "#38BDF8"),
    "Moderate": (101, 200, "#F59E0B"),
    "Poor": (201, 300, "#EF4444"),
    "Very Poor": (301, 400, "#DC2626"),
    "Severe": (401, 500, "#7F1D1D"),
}

# CADR Calculation Constants
DEFAULT_ACH = 5  # Air Changes per Hour for residential
CEILING_HEIGHT_DEFAULT = 9  # feet

# Complaint Categories
COMPLAINT_CATEGORIES = [
    "Construction Dust",
    "Industrial Emissions",
    "Vehicle Exhaust",
    "Waste Burning",
    "Crop Residue Burning",
    "Road Dust",
    "Diesel Generator",
    "Other",
]

# Complaint Status Flow
COMPLAINT_STATUSES = [
    "Submitted",
    "Under Review",
    "Assigned",
    "In Progress",
    "Resolved",
    "Closed",
]

# Building Types for Enterprise
BUILDING_TYPES = [
    "Office",
    "School",
    "Hospital",
    "Residential Complex",
    "Retail / Mall",
    "Factory / Warehouse",
    "Other",
]

ROOM_TYPES = [
    "Office / Workspace",
    "Classroom",
    "Patient Room",
    "Bedroom",
    "Living Room",
    "Conference Room",
    "Laboratory",
    "Server Room",
    "Other",
]