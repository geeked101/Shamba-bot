"""
tests/conftest.py

Shared pytest fixtures for Shamba AI backend tests.
All external services (PostgreSQL, ChromaDB, Groq, HuggingFace) are mocked
so tests run offline with no real credentials required.
"""

import pytest
from unittest.mock import MagicMock, patch


# ── Environment stubs ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """
    Inject dummy env vars for every test so modules that read os.getenv()
    at import time don't raise errors or hit real services.
    """
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("HF_API_KEY", "test-hf-key")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_DB", "shambadb")
    monkeypatch.setenv("POSTGRES_SSL", "disable")
    monkeypatch.setenv("CHROMA_SERVER_MODE", "persistent")
    monkeypatch.setenv("CHROMA_DIR", "/tmp/test_chroma")
    monkeypatch.setenv("CHROMA_COLLECTION", "test_collection")


# ── Reusable mock objects ──────────────────────────────────────────────────────

@pytest.fixture()
def mock_pg_conn():
    """Returns a mock psycopg2 connection + cursor pair."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture()
def mock_chroma_client():
    """Returns a mock ChromaDB client with a single empty collection."""
    mock_collection = MagicMock()
    mock_collection.count.return_value = 0
    mock_collection.name = "test_collection"

    mock_client = MagicMock()
    mock_client.list_collections.return_value = []
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_client.get_collection.return_value = mock_collection
    return mock_client, mock_collection
