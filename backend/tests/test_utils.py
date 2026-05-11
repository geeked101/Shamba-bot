"""
tests/test_utils.py

Unit tests for utils.py helper functions:
  - detect_location
  - detect_crop
  - get_weather
  - get_market_prices
  - get_safety_disclaimer
"""

import pytest
from unittest.mock import patch, MagicMock

# Add backend directory to path so imports work without installing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    detect_location,
    detect_crop,
    get_weather,
    get_market_prices,
    get_safety_disclaimer,
)


# ── detect_location ────────────────────────────────────────────────────────────

class TestDetectLocation:
    """Tests for detect_location()."""

    def test_detects_nairobi(self):
        assert detect_location("Nina shamba Nairobi") == "Nairobi"

    def test_detects_mombasa(self):
        assert detect_location("Hali ya hewa Mombasa leo") == "Mombasa"

    def test_detects_nyeri_case_insensitive(self):
        """Location detection must be case-insensitive."""
        assert detect_location("niko nyeri") == "Nyeri"

    def test_detects_kisumu(self):
        assert detect_location("Bei za soko Kisumu") == "Kisumu"

    def test_returns_none_when_no_location(self):
        assert detect_location("Mahindi yana ugonjwa wa kuvu") is None

    def test_returns_none_for_empty_string(self):
        assert detect_location("") is None


# ── detect_crop ────────────────────────────────────────────────────────────────

class TestDetectCrop:
    """Tests for detect_crop()."""

    def test_detects_swahili_maize(self):
        assert detect_crop("mahindi yangu yana madoa") == "mahindi"

    def test_detects_english_coffee(self):
        assert detect_crop("my coffee plants are sick") == "coffee"

    def test_detects_kikuyu_beans(self):
        assert detect_crop("mang'ũ wake ni mwega") == "mang'ũ"

    def test_returns_none_for_unknown_crop(self):
        assert detect_crop("hali ya hewa leo ni njema sana") is None

    def test_returns_none_for_empty_string(self):
        assert detect_crop("") is None


# ── get_weather ────────────────────────────────────────────────────────────────

class TestGetWeather:
    """Tests for get_weather()."""

    def test_returns_fallback_when_no_api_key(self):
        """Without an API key the function must return the seasonal fallback."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_weather("Nairobi")
        assert "msimu" in result or "hewa" in result

    def test_returns_real_weather_on_200(self):
        """With a valid API key and a 200 response, return formatted weather."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "main": {"temp": 24},
            "weather": [{"description": "partly cloudy"}],
        }
        with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test_key"}):
            with patch("utils.requests.get", return_value=mock_response):
                result = get_weather("Nairobi")
        assert "24" in result
        assert "Nairobi" in result

    def test_returns_error_message_on_exception(self):
        """Network errors must be swallowed and return a graceful message."""
        with patch.dict("os.environ", {"OPENWEATHERMAP_API_KEY": "test_key"}):
            with patch("utils.requests.get", side_effect=Exception("timeout")):
                result = get_weather("Nakuru")
        assert "Nakuru" in result


# ── get_market_prices ──────────────────────────────────────────────────────────

class TestGetMarketPrices:
    """Tests for get_market_prices()."""

    def test_known_crop_english(self):
        result = get_market_prices("maize")
        assert "KSh" in result

    def test_known_crop_swahili(self):
        result = get_market_prices("mahindi")
        assert "KSh" in result

    def test_known_crop_case_insensitive(self):
        result = get_market_prices("Tomatoes")
        assert "KSh" in result

    def test_unknown_crop_returns_fallback(self):
        result = get_market_prices("avocado")
        assert "NCPB" in result or "soko" in result


# ── get_safety_disclaimer ──────────────────────────────────────────────────────

class TestGetSafetyDisclaimer:
    """Tests for get_safety_disclaimer()."""

    def test_swahili_disclaimer_contains_warning(self):
        result = get_safety_disclaimer("sw")
        assert "Kumbuka" in result or "!" in result

    def test_kikuyu_disclaimer_contains_warning(self):
        result = get_safety_disclaimer("ki")
        assert "!" in result

    def test_english_disclaimer_returned(self):
        result = get_safety_disclaimer("en")
        assert "Disclaimer" in result

    def test_unknown_language_falls_back_to_swahili(self):
        sw_result = get_safety_disclaimer("sw")
        unknown_result = get_safety_disclaimer("xx")
        assert sw_result == unknown_result
