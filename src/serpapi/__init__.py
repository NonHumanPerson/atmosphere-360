"""
SerpApi Integration Module for Atmosphere360
Provides access to Google Search, Maps, Shopping, News, and Extract APIs.
"""
from serpapi_client import (
    SerpApiClient,
    SerpApiResponse,
    get_client,
    test_serpapi,
)

__all__ = [
    "SerpApiClient",
    "SerpApiResponse",
    "get_client",
    "test_serpapi",
]