"""
SerpApi Client Wrapper for Atmosphere360
Provides unified access to Google Search, Maps, Shopping, News, and Extract APIs.
"""
import os
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

try:
    from serpapi import GoogleSearch
except ImportError:
    GoogleSearch = None

from config import get_serpapi_key, SERPAPI_ENGINES


@dataclass
class SerpApiResponse:
    """Standardized response wrapper."""
    success: bool
    data: Optional[Dict[Any, Any]] = None
    error: Optional[str] = None
    engine: str = ""
    query: str = ""
    cached: bool = False


class SerpApiClient:
    """
    Unified SerpApi client with caching, error handling, and rate limiting.
    
    Usage:
        client = SerpApiClient()
        results = client.search("air pollution Mumbai today")
        places = client.maps("factories near Bandra Kurla Complex Mumbai")
        products = client.shopping("air purifier HEPA 150 sq ft")
        news = client.news("Mumbai air quality alert")
        extracted = client.extract("https://cpcb.nic.in/")
    """
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        self.api_key = api_key or get_serpapi_key()
        self.cache_dir = Path(cache_dir) if cache_dir else Path("data/cache/serpapi")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_call = 0
        self._min_interval = 1.0  # Minimum seconds between calls
        
        if not self.api_key:
            print("WARNING: SerpApi key not found. Set SERPAPI_KEY in .env or Streamlit secrets.")
    
    def _rate_limit(self):
        """Enforce minimum interval between API calls."""
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()
    
    def _get_cache_path(self, engine: str, query: str) -> Path:
        """Generate cache file path."""
        import hashlib
        key = hashlib.md5(f"{engine}:{query}".encode()).hexdigest()[:16]
        return self.cache_dir / f"{engine}_{key}.json"
    
    def _load_cache(self, cache_path: Path, max_age_hours: int = 24) -> Optional[Dict]:
        """Load cached response if fresh enough."""
        if not cache_path.exists():
            return None
        try:
            age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
            if age_hours > max_age_hours:
                return None
            with open(cache_path, 'r') as f:
                data = json.load(f)
            data["_cached"] = True
            return data
        except Exception:
            return None
    
    def _save_cache(self, cache_path: Path, data: Dict):
        """Save response to cache."""
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def _call_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make actual API call."""
        if GoogleSearch is None:
            return {"error": "serpapi package not installed. Run: pip install serpapi"}
        
        if not self.api_key:
            return {"error": "SerpApi key not configured"}
        
        self._rate_limit()
        params["api_key"] = self.api_key
        
        try:
            search = GoogleSearch(params)
            return search.get_dict()
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, query: str, **kwargs) -> SerpApiResponse:
        """
        Google Search API.
        
        Args:
            query: Search query string
            **kwargs: Additional params (num, gl, hl, location, etc.)
        
        Returns:
            SerpApiResponse with organic_results, answer_box, knowledge_graph, etc.
        """
        cache_path = self._get_cache_path("search", query)
        cached = self._load_cache(cache_path)
        if cached:
            return SerpApiResponse(True, cached, engine="google_search", query=query, cached=True)
        
        params = {
            "engine": "google",
            "q": query,
            "num": kwargs.get("num", 10),
            "gl": kwargs.get("gl", "in"),
            "hl": kwargs.get("hl", "en"),
            "location": kwargs.get("location", "Mumbai, Maharashtra, India"),
        }
        
        result = self._call_api(params)
        self._save_cache(cache_path, result)
        
        if "error" in result:
            return SerpApiResponse(False, error=result["error"], engine="google_search", query=query)
        
        return SerpApiResponse(True, result, engine="google_search", query=query)
    
    def maps(self, query: str, **kwargs) -> SerpApiResponse:
        """
        Google Maps API - find places, businesses, pollution sources.
        
        Args:
            query: Search query (e.g., "factories near Bandra Mumbai")
            **kwargs: Additional params (type, ll, zoom, etc.)
        
        Returns:
            SerpApiResponse with local_results, place_results, etc.
        """
        cache_path = self._get_cache_path("maps", query)
        cached = self._load_cache(cache_path)
        if cached:
            return SerpApiResponse(True, cached, engine="google_maps", query=query, cached=True)
        
        params = {
            "engine": "google_maps",
            "q": query,
            "type": kwargs.get("type", "search"),
            "ll": kwargs.get("ll", "@19.0760,72.8777,11z"),  # Mumbai center
            "hl": kwargs.get("hl", "en"),
        }
        
        result = self._call_api(params)
        self._save_cache(cache_path, result)
        
        if "error" in result:
            return SerpApiResponse(False, error=result["error"], engine="google_maps", query=query)
        
        return SerpApiResponse(True, result, engine="google_maps", query=query)
    
    def shopping(self, query: str, **kwargs) -> SerpApiResponse:
        """
        Google Shopping API - live product prices and availability.
        
        Args:
            query: Product search (e.g., "air purifier HEPA 150 sq ft")
            **kwargs: Additional params (num, gl, hl, etc.)
        
        Returns:
            SerpApiResponse with shopping_results, product_details, etc.
        """
        cache_path = self._get_cache_path("shopping", query)
        cached = self._load_cache(cache_path, max_age_hours=6)  # Prices change faster
        if cached:
            return SerpApiResponse(True, cached, engine="google_shopping", query=query, cached=True)
        
        params = {
            "engine": "google_shopping",
            "q": query,
            "num": kwargs.get("num", 20),
            "gl": kwargs.get("gl", "in"),
            "hl": kwargs.get("hl", "en"),
            "currency": kwargs.get("currency", "INR"),
        }
        
        result = self._call_api(params)
        self._save_cache(cache_path, result)
        
        if "error" in result:
            return SerpApiResponse(False, error=result["error"], engine="google_shopping", query=query)
        
        return SerpApiResponse(True, result, engine="google_shopping", query=query)
    
    def news(self, query: str, **kwargs) -> SerpApiResponse:
        """
        Google News API - pollution alerts, policy announcements.
        
        Args:
            query: News search query
            **kwargs: Additional params (num, gl, hl, tbs for time range, etc.)
        
        Returns:
            SerpApiResponse with news_results, etc.
        """
        cache_path = self._get_cache_path("news", query)
        cached = self._load_cache(cache_path, max_age_hours=4)  # News ages fast
        if cached:
            return SerpApiResponse(True, cached, engine="google_news", query=query, cached=True)
        
        params = {
            "engine": "google_news",
            "q": query,
            "num": kwargs.get("num", 10),
            "gl": kwargs.get("gl", "in"),
            "hl": kwargs.get("hl", "en"),
            "tbs": kwargs.get("tbs", "qdr:d"),  # Past day by default
        }
        
        result = self._call_api(params)
        self._save_cache(cache_path, result)
        
        if "error" in result:
            return SerpApiResponse(False, error=result["error"], engine="google_news", query=query)
        
        return SerpApiResponse(True, result, engine="google_news", query=query)
    
    def extract(self, url: str, **kwargs) -> SerpApiResponse:
        """
        Extract API - scrape structured data from any URL.
        
        Args:
            url: URL to extract (e.g., CPCB live data page)
            **kwargs: Additional params (mode, css_selector, etc.)
        
        Returns:
            SerpApiResponse with extracted content, metadata, etc.
        """
        cache_path = self._get_cache_path("extract", url)
        cached = self._load_cache(cache_path, max_age_hours=2)  # Live data
        if cached:
            return SerpApiResponse(True, cached, engine="extract", query=url, cached=True)
        
        params = {
            "engine": "extract",
            "url": url,
            "mode": kwargs.get("mode", "crawl"),
            "css_selector": kwargs.get("css_selector", ""),
        }
        
        result = self._call_api(params)
        self._save_cache(cache_path, result)
        
        if "error" in result:
            return SerpApiResponse(False, error=result["error"], engine="extract", query=url)
        
        return SerpApiResponse(True, result, engine="extract", query=url)
    
    # Convenience methods for Atmosphere360 use cases
    
    def search_pollution_alerts(self, location: str = "Mumbai") -> SerpApiResponse:
        """Search for real-time pollution alerts and news."""
        query = f"air pollution alert {location} today AQI PM2.5"
        return self.search(query)
    
    def search_policy_announcements(self, location: str = "Mumbai") -> SerpApiResponse:
        """Search for government policy announcements on air quality."""
        query = f"air quality policy announcement {location} BMC MPCB CPCB"
        return self.search(query)
    
    def find_pollution_sources(self, station_name: str, radius_km: int = 5) -> SerpApiResponse:
        """Find potential pollution sources near a monitoring station."""
        query = f"factories industrial construction near {station_name} Mumbai"
        return self.maps(query)
    
    def search_air_purifiers(self, room_sqft: int, budget_inr: int, concern: str = "PM2.5") -> SerpApiResponse:
        """Search for air purifiers matching room size and budget."""
        query = f"air purifier HEPA {room_sqft} sq ft under {budget_inr} {concern}"
        return self.shopping(query)
    
    def get_pollution_news(self, location: str = "Mumbai") -> SerpApiResponse:
        """Get latest pollution-related news."""
        query = f"air pollution {location} AQI"
        return self.news(query, tbs="qdr:d")  # Past day


# Singleton instance for easy import
_client_instance: Optional[SerpApiClient] = None

def get_client() -> SerpApiClient:
    """Get or create singleton SerpApi client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = SerpApiClient()
    return _client_instance


# Quick test function
def test_serpapi():
    """Test all SerpApi engines with sample queries."""
    client = get_client()
    
    if not client.api_key:
        print("❌ No SerpApi key configured")
        return
    
    print("Testing SerpApi engines...")
    
    # Test Search
    print("\n1. Google Search:")
    r = client.search_pollution_alerts("Mumbai")
    print(f"   Success: {r.success}, Cached: {r.cached}")
    if r.success and r.data:
        organic = r.data.get("organic_results", [])
        print(f"   Results: {len(organic)} organic results")
    
    # Test Maps
    print("\n2. Google Maps:")
    r = client.find_pollution_sources("Bandra Kurla Complex")
    print(f"   Success: {r.success}, Cached: {r.cached}")
    if r.success and r.data:
        local = r.data.get("local_results", [])
        print(f"   Places: {len(local)} local results")
    
    # Test Shopping
    print("\n3. Google Shopping:")
    r = client.search_air_purifiers(150, 10000)
    print(f"   Success: {r.success}, Cached: {r.cached}")
    if r.success and r.data:
        shopping = r.data.get("shopping_results", [])
        print(f"   Products: {len(shopping)} shopping results")
    
    # Test News
    print("\n4. Google News:")
    r = client.get_pollution_news("Mumbai")
    print(f"   Success: {r.success}, Cached: {r.cached}")
    if r.success and r.data:
        news = r.data.get("news_results", [])
        print(f"   Articles: {len(news)} news results")
    
    print("\n✅ All engine tests completed")


if __name__ == "__main__":
    test_serpapi()