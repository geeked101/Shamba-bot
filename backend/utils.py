"""
utils.py

Helper functions for Shamba-bot:
- Location and Crop detection
- Weather data fetching (Mock/OpenWeatherMap)
- Market price simulation
- Safe dosage guardrails
"""

import os
import re
import requests
from typing import Optional, Dict, Any

def detect_location(text: str) -> Optional[str]:
    """
    Detects Kenyan counties or major towns in the text.
    """
    kenyan_locations = [
        "Nairobi", "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta",
        "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka-Nithi",
        "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga",
        "Murang'a", "Kiambu", "Turkana", "West Pokot", "Samburu", "Trans Nzoia",
        "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia", "Nakuru",
        "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma",
        "Busia", "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira"
    ]
    
    text_lower = text.lower()
    for loc in kenyan_locations:
        if loc.lower() in text_lower:
            return loc
    return None

def detect_crop(text: str) -> Optional[str]:
    """
    Detects common Kenyan crops in the text.
    """
    crops = {
        "sw": ["mahindi", "maharagwe", "kahawa", "chai", "nyanya", "viazi", "sukuma wiki", "kitunguu", "ndizi", "mwembe"],
        "en": ["maize", "beans", "coffee", "tea", "tomatoes", "potatoes", "kale", "onions", "bananas", "mangoes"],
        "ki": ["mbembe", "mang'ũ", "kahũa", "chai", "nyanya", "ngwaci", "sukuma", "gitunguru", "marigũ", "mĩembe"]
    }
    
    text_lower = text.lower()
    for lang, crop_list in crops.items():
        for crop in crop_list:
            if crop.lower() in text_lower:
                # Return English name for consistency in backend logic if needed
                return crop
    return None

def get_weather(location: str) -> str:
    """
    Fetches real weather for a location if API key exists, otherwise returns a general seasonal message.
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Hali ya hewa ni ya msimu. Kumbuka kupanda kabla ya mvua kuanza."
        
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location},KE&appid={api_key}&units=metric"
        res = requests.get(url, timeout=5)
        data = res.json()
        if res.status_code == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"Hali ya hewa kule {location}: {temp}°C, {desc}."
    except Exception:
        pass
    return f"Nimeshindwa kupata hali ya hewa ya sasa kule {location}."

def get_market_prices(crop: str) -> str:
    """
    Returns simulated market prices for Kenyan markets.
    """
    # In a real app, this would fetch from an API like Esoko or M-Farm
    prices = {
        "maize": "KSh 3,200 - 3,800 kwa gunia la 90kg",
        "mahindi": "KSh 3,200 - 3,800 kwa gunia la 90kg",
        "beans": "KSh 8,000 - 12,000 kwa gunia",
        "maharagwe": "KSh 8,000 - 12,000 kwa gunia",
        "tomatoes": "KSh 4,500 kwa kreti",
        "nyanya": "KSh 4,500 kwa kreti"
    }
    return prices.get(crop.lower(), "Bei za soko zinatofautiana. Angalia soko lako la karibu (NCPB).")

def get_safety_disclaimer(language: str) -> str:
    """
    Returns the standard safety disclaimer.
    """
    disclaimers = {
        "sw": "\n\n[!] *Kumbuka: Daima soma maelezo kwenye lebo ya dawa kabla ya kutumia. Wasiliana na afisa wa kilimo kwa uthibitisho zaidi.*",
        "ki": "\n\n[!] *Kumbuka: Thoma maelezo ma dawa mbere ya gũtũmia. Aria na afisa wa ûrĩmi nĩguo ûmenye ûhoro mwerũ.*",
        "en": "\n\n[!] *Disclaimer: Always read chemical labels before use. Consult your local extension officer for professional confirmation.**"
    }
    return disclaimers.get(language, disclaimers["sw"])
