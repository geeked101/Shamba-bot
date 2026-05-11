"""
tests/test_app.py

Unit tests for app.py API routes:
  - GET  /           — health check
  - POST /text-query — text → RAG
  - POST /clear-history
  - GET  /history/{session_id}
  - POST /sms        — Africa's Talking webhook
  - POST /whatsapp   — Twilio webhook
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="module")
def client():
    """
    Build a FastAPI TestClient with all external services mocked.
    Imports are deferred until the fixture runs so env vars are set first.
    """
    with patch("chromadb.PersistentClient"), \
         patch("groq.Groq"), \
         patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
         patch("langchain_community.vectorstores.Chroma"), \
         patch("psycopg2.connect"):
        from fastapi.testclient import TestClient
        from app import app
        yield TestClient(app)


class TestHealthCheck:
    """Tests for GET /"""

    def test_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_response_has_status_running(self, client):
        data = client.get("/").json()
        assert data["status"] == "running"

    def test_response_has_expected_fields(self, client):
        data = client.get("/").json()
        assert "bot" in data
        assert "languages" in data
        assert "channels" in data
        assert "version" in data


class TestTextQuery:
    """Tests for POST /text-query"""

    def test_returns_answer(self, client):
        with patch("app.query_rag", return_value="Tumia mbolea ya DAP."):
            response = client.post(
                "/text-query",
                data={"question": "Nitumie mbolea gani?", "language": "sw", "session_id": "s1"},
            )
        assert response.status_code == 200
        assert response.json()["answer"] == "Tumia mbolea ya DAP."

    def test_echoes_question_and_language(self, client):
        with patch("app.query_rag", return_value="OK"):
            response = client.post(
                "/text-query",
                data={"question": "test", "language": "ki", "session_id": "s2"},
            )
        data = response.json()
        assert data["question"] == "test"
        assert data["language"] == "ki"

    def test_default_language_is_sw(self, client):
        with patch("app.query_rag", return_value="OK"):
            response = client.post("/text-query", data={"question": "habari"})
        assert response.json()["language"] == "sw"


class TestClearHistory:
    """Tests for POST /clear-history"""

    def test_returns_cleared_status(self, client):
        with patch("app.clear_history"):
            response = client.post("/clear-history", data={"session_id": "sess1"})
        assert response.status_code == 200
        assert response.json()["status"] == "cleared"


class TestGetHistory:
    """Tests for GET /history/{session_id}"""

    def test_returns_messages_list(self, client):
        fake_history = [{"role": "user", "content": "Habari"}]
        with patch("app.get_history", return_value=fake_history):
            response = client.get("/history/sess_abc")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "sess_abc"
        assert data["messages"] == fake_history


class TestSMSWebhook:
    """Tests for POST /sms (Africa's Talking webhook)."""

    def test_stop_command_clears_history(self, client):
        with patch("app.clear_history") as mock_clear, \
             patch("app.send_sms_at"):
            response = client.post("/sms", data={"from": "+254700000001", "text": "stop"})
        assert response.status_code == 200
        mock_clear.assert_called_once()

    def test_normal_message_calls_rag(self, client):
        with patch("app.query_rag", return_value="Jibu la kilimo.") as mock_rag, \
             patch("app.send_sms_at"):
            client.post("/sms", data={"from": "+254700000002", "text": "mahindi yana ugonjwa"})
        mock_rag.assert_called_once()

    def test_empty_message_returns_empty_response(self, client):
        response = client.post("/sms", data={"from": "+254700000003", "text": ""})
        assert response.status_code == 200
        assert response.content == b""


class TestTruncateSMS:
    """Tests for the truncate_sms() helper."""

    def test_short_message_unchanged(self):
        with patch("chromadb.PersistentClient"), \
             patch("groq.Groq"), \
             patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
             patch("langchain_community.vectorstores.Chroma"), \
             patch("psycopg2.connect"):
            from app import truncate_sms

        msg = "Short message."
        assert truncate_sms(msg) == msg

    def test_long_message_is_truncated(self):
        with patch("chromadb.PersistentClient"), \
             patch("groq.Groq"), \
             patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
             patch("langchain_community.vectorstores.Chroma"), \
             patch("psycopg2.connect"):
            from app import truncate_sms

        long_msg = "A" * 500
        result = truncate_sms(long_msg)
        assert len(result) <= 459
        assert "[...]" in result
