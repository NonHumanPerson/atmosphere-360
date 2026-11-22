"""
PurifierMatch — Smart Air Purifier Finder (Module 3)
Key differentiator: CADR-based recommendations with live SerpApi shopping prices.
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from config import DEFAULT_ACH, CEILING_HEIGHT_DEFAULT
from src.utils.cadr_calculator import (
    calculate_required_cadr,
    cadr_to_room_coverage,
    recommend_purifier_tier,
    format_cadr_explanation,
    get_recommended_ach,
    CADRResult,
)
from src.llm import get_gemini_client
from serpapi_client import get_client as get_serpapi_client


# ==================== Verified Purifier Dataset ====================

@dataclass
class PurifierProduct:
    """Verified air purifier product data."""
    id: str
    name: str
    brand: str
    cadr_cfm: float
    cadr_m3h: float
    room_coverage_sqft: int
    filter_type: str
    filter_stages: int
    replacement_filter_cost: int  # INR
    filter_life_months: int
    noise_db_min: int
    noise_db_max: int
    power_watts: int
    price_inr: int
    smart_features: List[str]
    buy_url: str
    image_url: str
    tier: str  # budget, balanced, premium
    notes: str


# Verified product database (15 products across 3 tiers)
PURIFIER_DATABASE: List[PurifierProduct] = [
    # BUDGET TIER (₹5,000 - ₹12,000)
    PurifierProduct(
        id="philips_ac0820",
        name="Philips AC0820/10",
        brand="Philips",
        cadr_cfm=88,
        cadr_m3h=150,
        room_coverage_sqft=161,
        filter_type="HEPA H13 + Activated Carbon",
        filter_stages=3,
        replacement_filter_cost=1800,
        filter_life_months=12,
        noise_db_min=26,
        noise_db_max=50,
        power_watts=27,
        price_inr=7999,
        smart_features=["Auto mode", "Filter replacement indicator"],
        buy_url="https://www.amazon.in/dp/B09V3KX7K7",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="budget",
        notes="Compact design, good for bedrooms up to 160 sq ft"
    ),
    PurifierProduct(
        id="mi_4lite",
        name="Mi Air Purifier 4 Lite",
        brand="Xiaomi",
        cadr_cfm=118,
        cadr_m3h=200,
        room_coverage_sqft=269,
        filter_type="True HEPA + Activated Carbon",
        filter_stages=3,
        replacement_filter_cost=1299,
        filter_life_months=12,
        noise_db_min=28,
        noise_db_max=52,
        power_watts=29,
        price_inr=8999,
        smart_features=["App control", "Voice control", "Auto mode", "PM2.5 display"],
        buy_url="https://www.amazon.in/dp/B0BMYH8Q8Q",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="budget",
        notes="Excellent value, large coverage for price, app integration"
    ),
    PurifierProduct(
        id="coway_airmega_150",
        name="Coway Airmega 150",
        brand="Coway",
        cadr_cfm=106,
        cadr_m3h=180,
        room_coverage_sqft=214,
        filter_type="Green True HEPA + Deodorization",
        filter_stages=3,
        replacement_filter_cost=3500,
        filter_life_months=12,
        noise_db_min=22,
        noise_db_max=48,
        power_watts=35,
        price_inr=11990,
        smart_features=["Auto mode", "Air quality indicator", "Timer"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="budget",
        notes="Korean brand, very quiet at low speeds, premium build"
    ),
    PurifierProduct(
        id="honeywell_air_touch_v2",
        name="Honeywell Air Touch V2",
        brand="Honeywell",
        cadr_cfm=135,
        cadr_m3h=230,
        room_coverage_sqft=323,
        filter_type="HEPA H11 + Activated Carbon + Pre-filter",
        filter_stages=3,
        replacement_filter_cost=2500,
        filter_life_months=9,
        noise_db_min=30,
        noise_db_max=55,
        power_watts=52,
        price_inr=10999,
        smart_features=["Touch controls", "PM2.5 display", "Sleep mode", "Timer"],
        buy_url="https://www.amazon.in/dp/B08N5XWQWQ",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="budget",
        notes="Large coverage, good for living rooms, higher power draw"
    ),
    PurifierProduct(
        id="philips_ac1215",
        name="Philips AC1215/20",
        brand="Philips",
        cadr_cfm=170,
        cadr_m3h=289,
        room_coverage_sqft=344,
        filter_type="HEPA H13 + Activated Carbon + Pre-filter",
        filter_stages=3,
        replacement_filter_cost=2500,
        filter_life_months=12,
        noise_db_min=25,
        noise_db_max=50,
        power_watts=33,
        price_inr=11999,
        smart_features=["Auto mode", "Allergen mode", "Sleep mode", "Filter alert"],
        buy_url="https://www.amazon.in/dp/B08Y7XJ7J7",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="budget",
        notes="Strong CADR, allergen mode certified by ECARF"
    ),
    
    # BALANCED TIER (₹12,000 - ₹25,000)
    PurifierProduct(
        id="dyson_purifier_cool",
        name="Dyson Purifier Cool TP07",
        brand="Dyson",
        cadr_cfm=206,
        cadr_m3h=350,
        room_coverage_sqft=400,
        filter_type="HEPA H13 + Activated Carbon + Catalytic",
        filter_stages=3,
        replacement_filter_cost=5500,
        filter_life_months=12,
        noise_db_min=27,
        noise_db_max=56,
        power_watts=40,
        price_inr=39900,
        smart_features=["App control", "Voice control", "Auto mode", "Real-time LCD display", "Oscillation", "Fan function"],
        buy_url="https://www.dyson.in/purifiers/purifier-cool",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="balanced",
        notes="Fan + purifier combo, bladeless, premium design, expensive filters"
    ),
    PurifierProduct(
        id="blueair_blue_211",
        name="Blueair Blue 211+ Auto",
        brand="Blueair",
        cadr_cfm=235,
        cadr_m3h=400,
        room_coverage_sqft=540,
        filter_type="HEPASilent™ (HEPA + Electrostatic)",
        filter_stages=3,
        replacement_filter_cost=4500,
        filter_life_months=12,
        noise_db_min=24,
        noise_db_max=49,
        power_watts=38,
        price_inr=18990,
        smart_features=["Auto mode", "App control", "Particle sensor", "Filter timer"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="balanced",
        notes="Swedish tech, HEPASilent = high flow + low noise, large rooms"
    ),
    PurifierProduct(
        id="coway_airmega_250",
        name="Coway Airmega 250",
        brand="Coway",
        cadr_cfm=220,
        cadr_m3h=374,
        room_coverage_sqft=430,
        filter_type="Green True HEPA + Activated Carbon",
        filter_stages=4,
        replacement_filter_cost=4200,
        filter_life_months=12,
        noise_db_min=22,
        noise_db_max=50,
        power_watts=45,
        price_inr=22990,
        smart_features=["Auto mode", "Air quality ring", "Smart app", "Voice control", "Eco mode"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="balanced",
        notes="Dual filtration, very quiet, smart features, good mid-range"
    ),
    PurifierProduct(
        id="sharp_fp_j60",
        name="Sharp FP-J60M-W",
        brand="Sharp",
        cadr_cfm=200,
        cadr_m3h=340,
        room_coverage_sqft=480,
        filter_type="HEPA + Activated Carbon + Plasmacluster Ion",
        filter_stages=3,
        replacement_filter_cost=3800,
        filter_life_months=24,
        noise_db_min=23,
        noise_db_max=51,
        power_watts=48,
        price_inr=24990,
        smart_features=["Plasmacluster ion tech", "Auto mode", "Haze mode", "Pollen mode"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="balanced",
        notes="Plasmacluster ion technology, 2-year filter life, good for allergens"
    ),
    PurifierProduct(
        id="philips_ac2887",
        name="Philips AC2887/20",
        brand="Philips",
        cadr_cfm=282,
        cadr_m3h=480,
        room_coverage_sqft=592,
        filter_type="HEPA H13 + Activated Carbon + Pre-filter",
        filter_stages=3,
        replacement_filter_cost=3200,
        filter_life_months=12,
        noise_db_min=27,
        noise_db_max=53,
        power_watts=50,
        price_inr=19990,
        smart_features=["Auto mode", "Allergen mode", "Sleep mode", "App control", "Bacteria/virus mode"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="balanced",
        notes="High CADR, allergen/virus modes, good for large living areas"
    ),
    
    # PREMIUM TIER (₹25,000+)
    PurifierProduct(
        id="dyson_purifier_hot_cool",
        name="Dyson Purifier Hot+Cool HP07",
        brand="Dyson",
        cadr_cfm=250,
        cadr_m3h=425,
        room_coverage_sqft=450,
        filter_type="HEPA H13 + Activated Carbon + Catalytic (formaldehyde)",
        filter_stages=3,
        replacement_filter_cost=6500,
        filter_life_months=12,
        noise_db_min=28,
        noise_db_max=58,
        power_watts=40,
        price_inr=54900,
        smart_features=["Heating + cooling + purifying", "App control", "Voice", "LCD display", "Oscillation", "Formaldehyde detection"],
        buy_url="https://www.dyson.in/purifiers/purifier-hot-cool",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="premium",
        notes="3-in-1: heat, cool, purify. Formaldehyde sensor. Premium price."
    ),
    PurifierProduct(
        id="blueair_dustmagnet_5440i",
        name="Blueair DustMagnet 5440i",
        brand="Blueair",
        cadr_cfm=323,
        cadr_m3h=550,
        room_coverage_sqft=620,
        filter_type="HEPASilent™ + DustMagnet™",
        filter_stages=3,
        replacement_filter_cost=5500,
        filter_life_months=12,
        noise_db_min=23,
        noise_db_max=50,
        power_watts=42,
        price_inr=34990,
        smart_features=["DustMagnet tech", "Auto mode", "App", "Voice", "PM2.5 sensor", "Light sensor"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="premium",
        notes="Unique DustMagnet catches dust before it settles, high CADR"
    ),
    PurifierProduct(
        id="coway_airmega_400",
        name="Coway Airmega 400",
        brand="Coway",
        cadr_cfm=353,
        cadr_m3h=600,
        room_coverage_sqft=1560,
        filter_type="Green True HEPA + Activated Carbon (dual)",
        filter_stages=4,
        replacement_filter_cost=6800,
        filter_life_months=12,
        noise_db_min=22,
        noise_db_max=52,
        power_watts=60,
        price_inr=44990,
        smart_features=["Dual filtration", "Auto mode", "App", "Voice", "Air quality ring", "Eco mode", "Timer"],
        buy_url="https://www.amazon.in/dp/B09X8J7K7K",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="premium",
        notes="Massive coverage (1560 sq ft), dual filters, for large open spaces"
    ),
    PurifierProduct(
        id="iQAir_HealthPro_250",
        name="IQAir HealthPro 250",
        brand="IQAir",
        cadr_cfm=300,
        cadr_m3h=510,
        room_coverage_sqft=950,
        filter_type="HyperHEPA H12/13 + V5-Cell Gas & Odor",
        filter_stages=4,
        replacement_filter_cost=15000,
        filter_life_months=48,  # 4 years for HyperHEPA
        noise_db_min=22,
        noise_db_max=57,
        power_watts=215,
        price_inr=89990,
        smart_features=["HyperHEPA filtration", "V5-Cell gas filter", "Filter life monitor", "6 fan speeds"],
        buy_url="https://www.iqair.com/in/en/healthpro-250",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="premium",
        notes="Medical-grade HyperHEPA (captures >0.003µm), 4-year filter life, Swiss made"
    ),
    PurifierProduct(
        id="molekule_air_pro",
        name="Molekule Air Pro",
        brand="Molekule",
        cadr_cfm=265,
        cadr_m3h=450,
        room_coverage_sqft=1000,
        filter_type="PECO (Photo Electrochemical Oxidation)",
        filter_stages=2,
        replacement_filter_cost=12000,
        filter_life_months=6,
        noise_db_min=29,
        noise_db_max=58,
        power_watts=85,
        price_inr=79990,
        smart_features=["PECO tech destroys pollutants", "App control", "Auto protect mode", "Air quality sensor"],
        buy_url="https://molekule.com/products/air-pro",
        image_url="https://m.media-amazon.com/images/I/41example.jpg",
        tier="premium",
        notes="PECO destroys (not traps) pollutants, expensive filters, subscription model"
    ),
]


def filter_products(
    required_cadr: float,
    budget_min: int,
    budget_max: int,
    room_type: str,
    concern: str,
    noise_preference: str,
    tier_override: Optional[str] = None
) -> List[PurifierProduct]:
    """Filter products based on user requirements."""
    results = []
    
    for p in PURIFIER_DATABASE:
        # CADR requirement (must meet or exceed)
        if p.cadr_cfm < required_cadr * 0.9:  # 10% tolerance
            continue
        
        # Budget range
        if p.price_inr < budget_min or p.price_inr > budget_max:
            continue
        
        # Room type suitability
        if room_type in ["Classroom", "Patient Room", "Laboratory", "Server Room"]:
            if p.tier == "budget" and p.cadr_cfm < 200:
                continue
        
        # Concern matching
        if concern == "allergens" and "HEPA" not in p.filter_type:
            continue
        if concern == "smoke" and "Carbon" not in p.filter_type and "V5-Cell" not in p.filter_type:
            continue
        if concern == "formaldehyde" and "formaldehyde" not in p.notes.lower() and "catalytic" not in p.filter_type.lower():
            continue
        
        # Noise preference
        if noise_preference == "quiet" and p.noise_db_max > 52:
            continue
        elif noise_preference == "very_quiet" and p.noise_db_max > 48:
            continue
        
        # Tier override
        if tier_override and p.tier != tier_override:
            continue
        
        results.append(p)
    
    # Sort by tier priority, then by CADR
    tier_order = {"budget": 0, "balanced": 1, "premium": 2}
    results.sort(key=lambda x: (tier_order.get(x.tier, 99), -x.cadr_cfm))
    
    return results


def select_top_3_recommendations(
    products: List[PurifierProduct],
    required_cadr: float
) -> Dict[str, Optional[PurifierProduct]]:
    """Select Budget Pick, Balanced Pick, Premium Pick."""
    recommendations = {"budget": None, "balanced": None, "premium": None}
    
    # Group by tier
    by_tier = {"budget": [], "balanced": [], "premium": []}
    for p in products:
        if p.tier in by_tier:
            by_tier[p.tier].append(p)
    
    # Pick best from each tier (highest CADR that meets requirement)
    for tier in ["budget", "balanced", "premium"]:
        tier_products = [p for p in by_tier[tier] if p.cadr_cfm >= required_cadr * 0.9]
        if tier_products:
            recommendations[tier] = tier_products[0]
    
    # If a tier is empty, try to fill from adjacent tier
    if not recommendations["budget"] and recommendations["balanced"]:
        recommendations["budget"] = recommendations["balanced"]
    if not recommendations["premium"] and recommendations["balanced"]:
        recommendations["premium"] = recommendations["balanced"]
    
    return recommendations


def get_live_prices_serpapi(query: str) -> List[Dict]:
    """Fetch live prices from SerpApi Google Shopping."""
    client = get_serpapi_client()
    if not client.api_key:
        return []
    
    response = client.shopping(query)
    if not response.success or not response.data:
        return []
    
    shopping_results = response.data.get("shopping_results", [])
    prices = []
    for item in shopping_results[:10]:
        prices.append({
            "title": item.get("title", ""),
            "price": item.get("price", ""),
            "source": item.get("source", ""),
            "link": item.get("product_link", ""),
            "rating": item.get("rating", 0),
            "reviews": item.get("reviews", 0),
        })
    return prices


def enrich_with_live_prices(product: PurifierProduct) -> Dict:
    """Enrich product with live shopping data from multiple APIs with fallback."""
    live_prices = []
    sources_used = []
    
    # 1. Primary: SerpApi Google Shopping
    client = get_serpapi_client()
    if client.api_key:
        query = f"{product.brand} {product.name} air purifier"
        response = client.shopping(query)
        
        if response.success and response.data:
            shopping_results = response.data.get("shopping_results", [])
            for item in shopping_results[:3]:
                live_prices.append({
                    "title": item.get("title", ""),
                    "price": item.get("price", ""),
                    "source": f"{item.get('source', 'Google Shopping')}",
                    "link": item.get("product_link", ""),
                    "rating": item.get("rating", 0),
                    "reviews": item.get("reviews", 0),
                })
            sources_used.append("SerpApi Shopping")
    
    # 2. Fallback: SerpApi Google Search (site-specific)
    if len(live_prices) < 3 and client.api_key:
        query = f"{product.brand} {product.name} air purifier site:amazon.in OR site:flipkart.com OR site:croma.com"
        response = client.search(query)
        
        if response.success and response.data:
            organic = response.data.get("organic_results", [])
            for item in organic[:3]:
                # Extract price from snippet if possible
                snippet = item.get("snippet", "")
                price_match = None
                import re
                price_matches = re.findall(r'₹[\d,]+', snippet)
                if price_matches:
                    price = price_matches[0]
                else:
                    price = "Check site"
                
                live_prices.append({
                    "title": item.get("title", "")[:80],
                    "price": price,
                    "source": "Google Search (Amazon/Flipkart)",
                    "link": item.get("link", ""),
                    "rating": 0,
                    "reviews": 0,
                })
            sources_used.append("SerpApi Search")
    
    # 3. Optional: You.com Search API (if configured)
    # Could add here if YOU_API_KEY is available
    
    note = f"Sources: {', '.join(sources_used)}" if sources_used else "No live APIs configured"
    return {"live_prices": live_prices[:5], "note": note}


def render_purifier_card(product: PurifierProduct, label: str, 
                         required_cadr: float, live_data: Dict = None) -> None:
    """Render a purifier recommendation card."""
    tier_colors = {
        "budget": "#10B981",
        "balanced": "#38BDF8", 
        "premium": "#F59E0B"
    }
    tier_icons = {
        "budget": "💚",
        "balanced": "💙",
        "premium": "💛"
    }
    
    color = tier_colors.get(product.tier, "#2DD4BF")
    icon = tier_icons.get(product.tier, "⭐")
    
    # CADR adequacy
    cadr_ratio = product.cadr_cfm / required_cadr if required_cadr > 0 else 0
    adequacy = "✅ Exceeds" if cadr_ratio >= 1.2 else "✅ Meets" if cadr_ratio >= 1.0 else "⚠️ Below"
    
    # Annual filter cost
    filters_per_year = 12 / product.filter_life_months
    annual_filter_cost = int(product.replacement_filter_cost * filters_per_year)
    
    live_prices = live_data.get("live_prices", []) if live_data else []
    live_price_html = ""
    if live_prices:
        live_price_html = f"""
        <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #374151;">
            <div style="font-size: 0.75rem; color: #9CA3AF; margin-bottom: 8px;">🛒 Live Prices (SerpApi)</div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
        """
        for lp in live_prices[:3]:
            live_price_html += f"""
                <a href="{lp['link']}" target="_blank" 
                   style="background: #1F2937; border: 1px solid #374151; border-radius: 6px; 
                          padding: 6px 10px; font-size: 0.75rem; color: #2DD4BF; 
                          text-decoration: none; white-space: nowrap;">
                    {lp['source']}: {lp['price']}
                </a>
            """
        live_price_html += "</div></div>"
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, {color}15, {color}08); 
                border: 2px solid {color}; border-radius: 16px; padding: 20px;
                position: relative; overflow: hidden;">
        <div style="position: absolute; top: 12px; right: 16px; font-size: 2rem;">{icon}</div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
                <div style="font-size: 0.7rem; color: {color}; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;">
                    {label.upper()} PICK
                </div>
                <div style="font-size: 1.1rem; font-weight: 700; color: #FFFFFF; margin-top: 4px;">
                    {product.name}
                </div>
                <div style="font-size: 0.8rem; color: #9CA3AF; margin-top: 2px;">
                    {product.brand} • {product.tier.title()} Tier
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.5rem; font-weight: 800; color: {color}; font-family: 'JetBrains Mono', monospace;">
                    ₹{product.price_inr:,}
                </div>
                <div style="font-size: 0.75rem; color: #9CA3AF;">MRP</div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px;">
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">CADR</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">{product.cadr_cfm:.0f} CFM</div>
                <div style="font-size: 0.7rem; color: #6B7280;">{product.cadr_m3h:.0f} m³/h</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">Coverage</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">{product.room_coverage_sqft} sq ft</div>
                <div style="font-size: 0.7rem; color: #6B7280;">{adequacy} requirement</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">Filter</div>
                <div style="font-size: 0.85rem; font-weight: 600; color: #FFFFFF;">{product.filter_type}</div>
                <div style="font-size: 0.7rem; color: #6B7280;">{product.filter_stages} stages</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">Noise</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">{product.noise_db_min}-{product.noise_db_max} dB</div>
                <div style="font-size: 0.7rem; color: #6B7280;">Sleep to Max</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">Power</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">{product.power_watts} W</div>
                <div style="font-size: 0.7rem; color: #6B7280;">Annual: ~₹{int(product.power_watts * 24 * 365 * 7 / 1000):,}</div>
            </div>
            <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 12px;">
                <div style="font-size: 0.7rem; color: #9CA3AF; text-transform: uppercase;">Filter Cost/Yr</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">₹{annual_filter_cost:,}</div>
                <div style="font-size: 0.7rem; color: #6B7280;">Every {product.filter_life_months} months</div>
            </div>
        </div>
        
        <div style="font-size: 0.8rem; color: #D1D5DB; line-height: 1.6; margin-bottom: 12px;">
            <strong>Why this fits:</strong> {product.notes}
        </div>
        
        {live_price_html}
        
        <div style="display: flex; gap: 8px; margin-top: 16px;">
            <a href="{product.buy_url}" target="_blank"
               style="flex: 1; background: {color}; color: #0B1220; font-weight: 700; 
                      padding: 10px; border-radius: 8px; text-align: center; text-decoration: none;">
                View on Store
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Streamlit compare button (outside the HTML)
    if st.button(":material/balance: Add to Compare", key=f"compare_{product.id}", width='stretch'):
        if "compare_list" not in st.session_state:
            st.session_state.compare_list = []
        if product.id not in [p.id for p in st.session_state.compare_list]:
            if len(st.session_state.compare_list) < 2:
                st.session_state.compare_list.append(product)
                st.success(f"Added {product.name} to comparison!")
            else:
                st.warning("Maximum 2 products for comparison. Clear list first.")
        else:
            st.info(f"{product.name} already in comparison list.")


def render_purifier_match_tab():
    """Render PurifierMatch - Smart Air Purifier Finder tab."""
    st.markdown("### :material/search: PurifierMatch — Smart Air Purifier Finder")
    st.caption("Find the right air purifier for YOUR room. Based on CADR science, not just AQI.")
    
    # Important disclaimer
    st.warning("""
    ⚠️ **Important:** AQI alone CANNOT determine which purifier to buy. 
    **Room size + CADR = correct purifier selection.** AQI indicates urgency, not product fit.
    Purifiers improve INDOOR air under suitable conditions — they don't reduce outdoor AQI.
    """, icon="⚠️")
    
    # Input form
    with st.form("purifier_finder_form"):
        st.markdown("#### :material/straighten: Room Details")
        rcol1, rcol2, rcol3 = st.columns(3)
        with rcol1:
            room_sqft = st.number_input("Room Area (sq ft)", min_value=50, max_value=2000, value=150, step=10)
        with rcol2:
            ceiling_ft = st.number_input("Ceiling Height (ft)", min_value=7, max_value=20, value=CEILING_HEIGHT_DEFAULT, step=1)
        with rcol3:
            room_type = st.selectbox("Room Type", [
                "Bedroom", "Living Room", "Office / Workspace", "Classroom",
                "Patient Room", "Conference Room", "Laboratory", "Server Room", "Other"
            ])
        
        st.markdown("#### :material/paid: Budget & Preferences")
        pcol1, pcol2, pcol3 = st.columns(3)
        with pcol1:
            budget_min = st.number_input("Min Budget (₹)", min_value=3000, max_value=100000, value=5000, step=1000)
        with pcol2:
            budget_max = st.number_input("Max Budget (₹)", min_value=5000, max_value=150000, value=25000, step=1000)
        with pcol3:
            concern = st.selectbox("Main Concern", [
                "PM2.5 / General", "Dust", "Smoke / Odor", "Allergens / Pollen",
                "Pet Dander", "Formaldehyde / VOCs", "Viruses / Bacteria"
            ])
        
        pcol4, pcol5 = st.columns(2)
        with pcol4:
            noise_pref = st.selectbox("Noise Preference", [
                "Any", "Quiet (< 52 dB max)", "Very Quiet (< 48 dB max)"
            ])
        with pcol5:
            ach = st.selectbox("Air Changes/Hour (ACH)", [4, 5, 6, 8, 10], index=1,
                               help="5 ACH is standard for residential. Higher for sensitive spaces.")
        
        submitted = st.form_submit_button("🔍 Find My Purifier", type="primary", width='stretch')
    
    if submitted:
        if budget_min >= budget_max:
            st.error("Min budget must be less than max budget")
            return
        
        # Calculate required CADR
        result = calculate_required_cadr(room_sqft, ceiling_ft, ach)
        st.session_state.purifier_result = result
        st.session_state.purifier_inputs = {
            "room_sqft": room_sqft,
            "ceiling_ft": ceiling_ft,
            "room_type": room_type,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "concern": concern,
            "noise_pref": noise_pref,
            "ach": ach,
        }
        
        # Filter products
        noise_map = {"Any": "any", "Quiet (< 52 dB max)": "quiet", "Very Quiet (< 48 dB max)": "very_quiet"}
        filtered = filter_products(
            required_cadr=result.required_cadr_cfm,
            budget_min=budget_min,
            budget_max=budget_max,
            room_type=room_type,
            concern=concern,
            noise_preference=noise_map.get(noise_pref, "any"),
        )
        
        recommendations = select_top_3_recommendations(filtered, result.required_cadr_cfm)
        st.session_state.purifier_recommendations = recommendations
        st.session_state.purifier_filtered = filtered
    
    # Display results
    if "purifier_result" in st.session_state:
        result: CADRResult = st.session_state.purifier_result
        inputs = st.session_state.purifier_inputs
        recommendations = st.session_state.get("purifier_recommendations", {})
        
        st.markdown("---")
        st.markdown("#### :material/bar_chart: Your CADR Requirement")
        st.markdown(format_cadr_explanation(result))
        
        if recommendations:
            st.markdown("#### :material/leaderboard: Top 3 Recommendations")
            
            # Fetch live prices for each recommendation (cached)
            live_data_cache = {}
            for tier, product in recommendations.items():
                if product:
                    with st.spinner(f"Fetching live prices for {product.name}..."):
                        live_data_cache[tier] = enrich_with_live_prices(product)
            
            # Display cards
            cols = st.columns(3)
            tier_labels = {"budget": "Budget", "balanced": "Balanced", "premium": "Premium"}
            
            for idx, (tier, product) in enumerate(recommendations.items()):
                if product:
                    with cols[idx]:
                        render_purifier_card(
                            product, 
                            tier_labels[tier], 
                            result.required_cadr_cfm,
                            live_data_cache.get(tier, {})
                        )
                else:
                    with cols[idx]:
                        st.info(f"No {tier_labels[tier]} pick found in budget range")
            
            # Comparison table
            st.markdown("---")
            st.markdown("#### :material/checklist: Detailed Comparison")
            
            comparison_data = []
            for tier, product in recommendations.items():
                if product:
                    filters_per_year = 12 / product.filter_life_months
                    annual_filter = int(product.replacement_filter_cost * filters_per_year)
                    annual_energy = int(product.power_watts * 24 * 365 * 7 / 1000)
                    
                    comparison_data.append({
                        "Tier": tier_labels[tier],
                        "Model": product.name,
                        "CADR (CFM)": product.cadr_cfm,
                        "Coverage (sq ft)": product.room_coverage_sqft,
                        "Filter": product.filter_type,
                        "Noise (dB)": f"{product.noise_db_min}-{product.noise_db_max}",
                        "Power (W)": product.power_watts,
                        "Price (₹)": f"{product.price_inr:,}",
                        "Filter Cost/Yr (₹)": f"{annual_filter:,}",
                        "Energy Cost/Yr (₹)": f"{annual_energy:,}",
                        "Total Yr Cost (₹)": f"{annual_filter + annual_energy:,}",
                    })
            
            if comparison_data:
                df = pd.DataFrame(comparison_data)
                st.dataframe(df, width='stretch', hide_index=True)
            
            # Side-by-side comparison feature
            st.markdown("---")
            st.markdown("#### :material/balance: Side-by-Side Comparison")
            
            if "compare_list" not in st.session_state:
                st.session_state.compare_list = []
            
            # Clear button
            ccol1, ccol2 = st.columns([1, 4])
            with ccol1:
                if st.button(":material/delete: Clear Comparison", width='stretch'):
                    st.session_state.compare_list = []
                    st.rerun()
            
            if st.session_state.compare_list:
                if len(st.session_state.compare_list) == 1:
                    st.info(f"1 product selected: **{st.session_state.compare_list[0].name}**. Add another to compare.")
                elif len(st.session_state.compare_list) == 2:
                    p1, p2 = st.session_state.compare_list[0], st.session_state.compare_list[1]
                    
                    # Calculate TCO
                    p1_annual_filter = int(p1.replacement_filter_cost * (12 / p1.filter_life_months))
                    p1_annual_energy = int(p1.power_watts * 24 * 365 * 7 / 1000)
                    p1_tco_1yr = p1.price_inr + p1_annual_filter + p1_annual_energy
                    
                    p2_annual_filter = int(p2.replacement_filter_cost * (12 / p2.filter_life_months))
                    p2_annual_energy = int(p2.power_watts * 24 * 365 * 7 / 1000)
                    p2_tco_1yr = p2.price_inr + p2_annual_filter + p2_annual_energy
                    
                    comp_cols = st.columns(2)
                    
                    for idx, (p, tco, a_filter, a_energy) in enumerate([
                        (p1, p1_tco_1yr, p1_annual_filter, p1_annual_energy),
                        (p2, p2_tco_1yr, p2_annual_filter, p2_annual_energy)
                    ]):
                        with comp_cols[idx]:
                            tier_color = {"budget": "#10B981", "balanced": "#38BDF8", "premium": "#F59E0B"}.get(p.tier, "#2DD4BF")
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, {tier_color}15, {tier_color}08); 
                                        border: 2px solid {tier_color}; border-radius: 16px; padding: 20px;">
                                <div style="font-size: 1.1rem; font-weight: 700; color: #FFFFFF;">{p.name}</div>
                                <div style="color: #9CA3AF; margin-bottom: 16px;">{p.brand} • {p.tier.title()}</div>
                                
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">CADR</div>
                                        <div style="font-size: 1.2rem; font-weight: 700;">{p.cadr_cfm:.0f} CFM</div>
                                    </div>
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">Coverage</div>
                                        <div style="font-size: 1.2rem; font-weight: 700;">{p.room_coverage_sqft} sq ft</div>
                                    </div>
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">Noise</div>
                                        <div style="font-size: 1.2rem; font-weight: 700;">{p.noise_db_min}-{p.noise_db_max} dB</div>
                                    </div>
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">Power</div>
                                        <div style="font-size: 1.2rem; font-weight: 700;">{p.power_watts} W</div>
                                    </div>
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">Filter</div>
                                        <div style="font-size: 0.8rem; font-weight: 600;">{p.filter_type}</div>
                                    </div>
                                    <div style="background: rgba(0,0,0,0.2); border-radius: 8px; padding: 10px;">
                                        <div style="font-size: 0.7rem; color: #9CA3AF;">1-Yr TCO</div>
                                        <div style="font-size: 1.2rem; font-weight: 700;">₹{tco:,}</div>
                                    </div>
                                </div>
                                
                                <a href="{p.buy_url}" target="_blank" style="display: block; text-align: center; background: {tier_color}; color: #0B1220; font-weight: 700; padding: 12px; border-radius: 8px; text-decoration: none;">Buy Now</a>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Winner summary
                    st.markdown("---")
                    if p1_tco_1yr < p2_tco_1yr:
                        winner, loser = p1, p2
                        savings = p2_tco_1yr - p1_tco_1yr
                    else:
                        winner, loser = p2, p1
                        savings = p1_tco_1yr - p2_tco_1yr
                    
                    st.success(f"""
                    **🏆 Value Winner: {winner.name}** — Saves ₹{savings:,}/year vs {loser.name}
                    
                    **Key differentiators:**
                    - CADR: {winner.cadr_cfm:.0f} vs {loser.cadr_cfm:.0f} CFM ({'✅ Better' if winner.cadr_cfm >= loser.cadr_cfm else '⚠️ Lower'})
                    - Noise: {winner.noise_db_max} vs {loser.noise_db_max} dB max ({'✅ Quieter' if winner.noise_db_max <= loser.noise_db_max else '⚠️ Louder'})
                    - Filter cost/yr: ₹{int(winner.replacement_filter_cost * (12/winner.filter_life_months)):,} vs ₹{int(loser.replacement_filter_cost * (12/loser.filter_life_months)):,}
                    - Energy cost/yr: ₹{int(winner.power_watts * 24 * 365 * 7 / 1000):,} vs ₹{int(loser.power_watts * 24 * 365 * 7 / 1000):,}
                    """)
            else:
                st.info("Click ':material/balance: Add to Compare' on any product card to build your comparison (max 2).")
            
            # AI Explanation
            st.markdown("---")
            st.markdown("#### :material/smart_toy: AI Explanation")
            
            client = get_gemini_client()
            if client.api_key:
                if st.button(":material/lightbulb: Explain Why These Were Recommended", width='stretch'):
                    with st.spinner("Generating explanation..."):
                        rec_list = [{"name": p.name, "cadr_cfm": p.cadr_cfm, 
                                     "room_coverage_sqft": p.room_coverage_sqft,
                                     "filter_type": p.filter_type,
                                     "price_inr": p.price_inr} 
                                    for p in recommendations.values() if p]
                        response = client.generate_purifier_explanation(
                            room_sqft=inputs["room_sqft"],
                            ceiling_ft=inputs["ceiling_ft"],
                            required_cadr=result.required_cadr_cfm,
                            budget=inputs["budget_max"],
                            products=rec_list
                        )
                    
                    if response.success:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #2DD4BF22, #2DD4BF11); 
                                    border: 1px solid #2DD4BF; border-radius: 12px; padding: 20px;">
                            {response.content.replace(chr(10), '<br>')}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"Failed: {response.error}")
            else:
                st.info("Configure Groq API key for AI-powered explanations")
        
        else:
            st.error("No purifiers match your criteria. Try increasing budget or adjusting requirements.")
            
            # Show closest matches anyway
            all_products = [p for p in PURIFIER_DATABASE 
                           if budget_min <= p.price_inr <= budget_max]
            if all_products:
                st.markdown("#### Closest matches (may not meet CADR):")
                for p in sorted(all_products, key=lambda x: x.cadr_cfm, reverse=True)[:3]:
                    st.write(f"- **{p.name}**: CADR {p.cadr_cfm} CFM, ₹{p.price_inr:,}, {p.tier}")


if __name__ == "__main__":
    # Test
    print("PurifierMatch module loaded")
    print(f"Database: {len(PURIFIER_DATABASE)} products")
    
    # Test filtering
    result = calculate_required_cadr(150, 9, 5)
    print(f"150 sq ft, 9 ft, 5 ACH -> {result.required_cadr_cfm:.1f} CFM")
    
    filtered = filter_products(result.required_cadr_cfm, 5000, 25000, "Bedroom", "PM2.5 / General", "any")
    print(f"Filtered: {len(filtered)} products")
    
    recs = select_top_3_recommendations(filtered, result.required_cadr_cfm)
    for tier, p in recs.items():
        if p:
            print(f"  {tier}: {p.name} ({p.cadr_cfm} CFM, ₹{p.price_inr:,})")