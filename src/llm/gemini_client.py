"""
Google Gemini LLM Client for Atmosphere360
Replaces Groq with Gemini for AI-powered recommendations and briefings.
"""
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from config import get_gemini_key


@dataclass
class GeminiResponse:
    """Standardized response wrapper."""
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    model: str = ""
    usage: Optional[Dict] = None


class GeminiClient:
    """
    Google Gemini client for generating recommendations and briefings.
    
    Models available:
    - gemini-3.8-flash (fast, cost-effective, latest)
    - gemini-1.5-pro (best quality)
    - gemini-1.5-flash (fallback)
    - gemini-1.0-pro (legacy)
    """
    
    DEFAULT_MODEL = "gemini-3.8-flash"
    PRO_MODEL = "gemini-1.5-pro"
    FALLBACK_MODEL = "gemini-1.5-flash"
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or get_gemini_key()
        self.model_name = model
        self.model = None
        
        if genai and self.api_key:
            genai.configure(api_key=self.api_key)
            try:
                self.model = genai.GenerativeModel(model)
                self.model_name = model
            except Exception as e:
                print(f"⚠️  Model '{model}' not available, falling back to {FALLBACK_MODEL}: {e}")
                self.model = genai.GenerativeModel(FALLBACK_MODEL)
                self.model_name = FALLBACK_MODEL
        elif not self.api_key:
            print("⚠️  Gemini API key not found. Set GEMINI_API_KEY in .env or Streamlit secrets.")
    
    def _call(self, prompt: str, system_prompt: Optional[str] = None, 
              temperature: float = 0.3, max_tokens: int = 1024) -> GeminiResponse:
        """Make API call to Gemini."""
        if not self.model:
            return GeminiResponse(False, error="Gemini client not initialized (missing API key or package)")
        
        try:
            # Combine system prompt and user prompt
            full_prompt = ""
            if system_prompt:
                full_prompt += f"System: {system_prompt}\n\n"
            full_prompt += f"User: {prompt}"
            
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
            )
            
            # Extract usage metadata if available
            usage = None
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            
            return GeminiResponse(
                True,
                content=response.text,
                model=self.model_name,
                usage=usage
            )
        except Exception as e:
            return GeminiResponse(False, error=str(e))
    
    def _chat_call(self, messages: List[Dict[str, str]], 
                   temperature: float = 0.3, max_tokens: int = 1024) -> GeminiResponse:
        """Make chat-style API call to Gemini."""
        if not self.model:
            return GeminiResponse(False, error="Gemini client not initialized")
        
        try:
            # Convert messages to Gemini format
            chat = self.model.start_chat(history=[])
            
            # Send all messages except the last one as history
            for msg in messages[:-1]:
                role = "model" if msg["role"] == "assistant" else "user"
                chat.send_message(msg["content"])
            
            # Send the last message
            last_msg = messages[-1]
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            response = chat.send_message(last_msg["content"], generation_config=generation_config)
            
            usage = None
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
            
            return GeminiResponse(
                True,
                content=response.text,
                model=self.model_name,
                usage=usage
            )
        except Exception as e:
            return GeminiResponse(False, error=str(e))
    
    # ==================== AirCare: Personal Action Assistant ====================
    
    def generate_aircare_advice(self, context: str, aqi: int, pm25: float, 
                                pm10: float, temp: float, humidity: float,
                                wind_speed: float,
                                forecast_summary: str = "",
                                news_summary: str = "",
                                cpcb_summary: str = "",
                                data_source: str = "") -> GeminiResponse:
        """
        Generate personalized air quality advice for a citizen.
        """
        context_descriptions = {
            "home": "at home indoors",
            "office": "at work in an office",
            "school": "at school or university",
            "outdoors": "outdoors or commuting",
        }
        ctx_desc = context_descriptions.get(context, context)
        
        if aqi <= 50:
            category = "Good"
        elif aqi <= 100:
            category = "Satisfactory"
        elif aqi <= 200:
            category = "Moderate"
        elif aqi <= 300:
            category = "Poor"
        elif aqi <= 400:
            category = "Very Poor"
        else:
            category = "Severe"
        
        system_prompt = """You are an air quality health advisor. Provide clear, practical, 
        evidence-based recommendations. Be concise (max 3 short paragraphs). 
        Never give medical advice - always recommend consulting a healthcare professional for health concerns.
        Do not make definitive health claims. Use cautious language: 'consider', 'may help', 'recommended to'."""
        
        extra_context = ""
        if forecast_summary:
            extra_context += f"\n- Forecast: {forecast_summary}"
        if news_summary:
            extra_context += f"\n- Recent News: {news_summary}"
        if cpcb_summary:
            extra_context += f"\n- CPCB Bulletins: {cpcb_summary}"
        if data_source:
            extra_context += f"\n- Data Source: {data_source}"
        
        user_prompt = f"""Current air quality at user's location ({ctx_desc}):
- AQI: {aqi} ({category})
- PM2.5: {pm25:.1f} µg/m³
- PM10: {pm10:.1f} µg/m³
- Temperature: {temp:.1f}°C
- Humidity: {humidity:.0f}%
- Wind: {wind_speed:.1f} km/h{extra_context}

Provide 3 practical precautions for someone {ctx_desc}. Include:
1. Outdoor activity guidance
2. Indoor ventilation/filtration advice
3. When to consider an air purifier

Keep each point to 1-2 sentences. Start with the AQI category context."""
        
        return self._call(prompt=user_prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=500)
    
    def generate_purifier_explanation(self, room_sqft: int, ceiling_ft: int, 
                                      required_cadr: float, budget: int,
                                      products: List[Dict]) -> GeminiResponse:
        """Explain why recommended purifiers match the user's needs."""
        products_desc = "\n".join([
            f"- {p['name']}: CADR {p.get('cadr_cfm', 'N/A')} CFM, "
            f"covers {p.get('room_coverage_sqft', 'N/A')} sq ft, "
            f"{p.get('filter_type', 'HEPA')}, ₹{p.get('price_inr', 'N/A')}"
            for p in products
        ])
        
        system_prompt = """You are an air purifier expert. Explain why the recommended 
        products are suitable for the user's room. Be specific about CADR, room coverage, 
        and filtration. Do NOT claim purifiers reduce outdoor AQI. Clarify they improve 
        indoor air under suitable conditions. Max 3 short paragraphs."""
        
        user_prompt = f"""User's requirements:
- Room: {room_sqft} sq ft × {ceiling_ft} ft ceiling
- Required CADR: {required_cadr:.0f} CFM (for 5 ACH)
- Budget: ₹{budget:,}
- Main concern: PM2.5 / allergens

Recommended products:
{products_desc}

Explain why each product fits. Mention:
1. CADR adequacy for room size
2. Filter type (HEPA) relevance
3. Budget alignment
4. Any trade-offs (noise, filter cost, energy)"""
        
        return self._call(prompt=user_prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=600)
    
    # ==================== Command Center: Officer Briefings ====================
    
    def generate_officer_briefing(self, top_zones: List[Dict], 
                                  complaints: List[Dict],
                                  forecast_summary: str) -> GeminiResponse:
        """Generate daily briefing for municipal officers."""
        zones_desc = "\n".join([
            f"- {z['station']}: AQI {z.get('latest_aqi', 'N/A'):.0f}, "
            f"Priority #{z.get('rank', 'N/A')}, Score {z.get('priority_score', 0):.1f}"
            for z in top_zones[:5]
        ])
        
        complaints_desc = "\n".join([
            f"- {c.get('category', 'Unknown')}: {c.get('location', 'Unknown')} "
            f"({c.get('status', 'Submitted')})"
            for c in complaints[:5]
        ]) if complaints else "No new complaints"
        
        system_prompt = """You are an environmental intelligence analyst for BMC/MPCB. 
        Write a concise daily briefing (3-4 sentences max) for field officers. 
        Be action-oriented. Prioritize what needs immediate attention."""
        
        user_prompt = f"""Today's air quality situation:

TOP 5 PRIORITY ZONES:
{zones_desc}

CITIZEN COMPLAINTS:
{complaints_desc}

FORECAST:
{forecast_summary}

Write a 3-sentence daily briefing for field inspection teams."""
        
        return self._call(prompt=user_prompt, system_prompt=system_prompt, temperature=0.2, max_tokens=300)
    
    def categorize_complaint(self, description: str, location: str, 
                             photo_description: str = "") -> GeminiResponse:
        """Categorize a citizen pollution complaint using AI."""
        from config import COMPLAINT_CATEGORIES
        
        categories_str = ", ".join(COMPLAINT_CATEGORIES)
        
        system_prompt = f"""You are a pollution complaint classifier. 
        Categorize the complaint into ONE of these categories: {categories_str}.
        Respond with ONLY the category name, nothing else."""
        
        user_prompt = f"""Complaint: {description}
Location: {location}
Photo context: {photo_description if photo_description else 'No photo provided'}

Category:"""
        
        return self._call(prompt=user_prompt, system_prompt=system_prompt, temperature=0.1, max_tokens=50)
    
    # ==================== Enterprise: AirSense Reports ====================
    
    def generate_enterprise_report(self, building_name: str, 
                                   rooms_data: List[Dict],
                                   outdoor_aqi: int, outdoor_pm25: float) -> GeminiResponse:
        """Generate environmental report for enterprise building."""
        rooms_desc = "\n".join([
            f"- {r['name']} ({r['type']}): Indoor PM2.5 {r.get('indoor_pm25', 'N/A')} µg/m³, "
            f"Outdoor PM2.5 {r.get('outdoor_pm25', 'N/A')} µg/m³, "
            f"Ratio {r.get('indoor_outdoor_ratio', 'N/A'):.2f}"
            for r in rooms_data
        ])
        
        system_prompt = """You are an indoor air quality consultant. 
        Generate a professional summary for building management. 
        Highlight rooms needing attention. Recommend ventilation/filtration actions.
        Max 4 short paragraphs. Be specific and actionable."""
        
        user_prompt = f"""Building: {building_name}
Outdoor reference: AQI {outdoor_aqi}, PM2.5 {outdoor_pm25:.1f} µg/m³

Room-level data:
{rooms_desc}

Generate executive summary with recommendations."""
        
        return self._call(prompt=user_prompt, system_prompt=system_prompt, temperature=0.3, max_tokens=600)


# Singleton
_client_instance: Optional[GeminiClient] = None

def get_gemini_client() -> GeminiClient:
    """Get or create singleton Gemini client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GeminiClient()
    return _client_instance


def test_gemini():
    """Test Gemini client with sample prompts."""
    client = get_gemini_client()
    
    if not client.api_key:
        print("❌ No Gemini API key configured")
        return
    
    print("Testing Gemini LLM...")
    
    # Test AirCare
    print("\n1. AirCare Advice:")
    r = client.generate_aircare_advice("home", 156, 68.5, 112.3, 28.5, 65, 12.3)
    print(f"   Success: {r.success}")
    if r.success:
        print(f"   Response: {r.content[:200]}...")
    
    # Test Officer Briefing
    print("\n2. Officer Briefing:")
    r = client.generate_officer_briefing(
        [{"station": "Bandra Kurla Complex", "latest_aqi": 185, "rank": 1, "priority_score": 87.3}],
        [{"category": "Construction Dust", "location": "BKC", "status": "Submitted"}],
        "PM2.5 expected to rise 15% tomorrow due to low wind"
    )
    print(f"   Success: {r.success}")
    if r.success:
        print(f"   Response: {r.content}")
    
    print("\n✅ Gemini tests completed")


if __name__ == "__main__":
    test_gemini()