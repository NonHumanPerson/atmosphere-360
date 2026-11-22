"""
Citizen Module for Atmosphere360
My Air, AirCare, and PurifierMatch for personal air quality intelligence.
"""
from src.citizen.my_air import (
    render_my_air_tab,
    render_aircare_tab,
    get_aqi_category,
    get_activity_recommendation,
    calculate_air_score,
)
from src.citizen.purifier_match import (
    render_purifier_match_tab,
    PurifierProduct,
    filter_products,
    select_top_3_recommendations,
)

__all__ = [
    "render_my_air_tab",
    "render_aircare_tab",
    "get_aqi_category",
    "get_activity_recommendation",
    "calculate_air_score",
    "render_purifier_match_tab",
    "PurifierProduct",
    "filter_products",
    "select_top_3_recommendations",
]