"""
tests/test_db_init.py

Unit tests for db_init.py:
  - init_chromadb() — creates collection, skips if exists, handles reset
  - init_postgres() — creates table, handles reset, handles connection URL
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── ChromaDB init ──────────────────────────────────────────────────────────────

class TestInitChromaDB:
    """Tests for init_chromadb()."""

    def test_creates_collection_when_not_exists(self, mock_chroma_client):
        """Collection should be created when it does not already exist."""
        mock_client, mock_collection = mock_chroma_client
        mock_client.list_collections.return_value = []

        with patch("chromadb.PersistentClient", return_value=mock_client):
            from db_init import init_chromadb
            init_chromadb(reset=False)

        mock_client.create_collection.assert_called_once()

    def test_skips_creation_when_collection_exists(self, mock_chroma_client):
        """Collection should NOT be recreated when it already exists."""
        mock_client, mock_collection = mock_chroma_client
        existing = MagicMock()
        existing.name = "test_collection"
        mock_client.list_collections.return_value = [existing]
        mock_collection.count.return_value = 42

        with patch("chromadb.PersistentClient", return_value=mock_client):
            from db_init import init_chromadb
            init_chromadb(reset=False)

        mock_client.create_collection.assert_not_called()

    def test_deletes_and_recreates_on_reset(self, mock_chroma_client):
        """On reset=True the existing collection must be deleted first."""
        mock_client, mock_collection = mock_chroma_client
        existing = MagicMock()
        existing.name = "test_collection"
        mock_client.list_collections.return_value = [existing]

        with patch("chromadb.PersistentClient", return_value=mock_client):
            from db_init import init_chromadb
            init_chromadb(reset=True)

        mock_client.delete_collection.assert_called_once()
        mock_client.create_collection.assert_called_once()

    def test_exits_on_connection_failure(self):
        """System should exit if ChromaDB is unreachable."""
        with patch("chromadb.PersistentClient", side_effect=Exception("unreachable")):
            with pytest.raises(SystemExit):
                from db_init import init_chromadb
                init_chromadb(reset=False)


# ── PostgreSQL init ────────────────────────────────────────────────────────────

class TestInitPostgres:
    """Tests for init_postgres()."""

    def test_creates_table_and_index(self, mock_pg_conn):
        """Table and index creation SQL should be executed."""
        mock_conn, mock_cursor = mock_pg_conn

        with patch("psycopg2.connect", return_value=mock_conn):
            from db_init import init_postgres
            init_postgres(reset=False)

        # Check that CREATE TABLE IF NOT EXISTS was called
        all_calls = " ".join(str(c) for c in mock_cursor.execute.call_args_list)
        assert "CREATE TABLE IF NOT EXISTS" in all_calls
        assert "CREATE INDEX IF NOT EXISTS" in all_calls

    def test_drops_table_on_reset(self, mock_pg_conn):
        """On reset=True, DROP TABLE must be called before recreation."""
        mock_conn, mock_cursor = mock_pg_conn

        with patch("psycopg2.connect", return_value=mock_conn):
            from db_init import init_postgres
            init_postgres(reset=True)

        all_calls = " ".join(str(c) for c in mock_cursor.execute.call_args_list)
        assert "DROP TABLE IF EXISTS" in all_calls

    def test_exits_on_connection_failure(self):
        """System should exit if PostgreSQL is unreachable."""
        with patch("psycopg2.connect", side_effect=Exception("connection refused")):
            with pytest.raises(SystemExit):
                from db_init import init_postgres
                init_postgres(reset=False)

    def test_accepts_postgres_url_string(self, mock_pg_conn):
        """When POSTGRES_HOST is a full DSN URL, connect() receives just the URL."""
        mock_conn, mock_cursor = mock_pg_conn

        with patch("psycopg2.connect", return_value=mock_conn) as mock_connect, \
             patch.dict("os.environ", {"POSTGRES_HOST": "postgresql://user:pass@host/db"}):
            from db_init import init_postgres
            init_postgres(reset=False)

        # connect() should have been called with the URL string, not keyword args
        args, kwargs = mock_connect.call_args
        assert len(args) == 1
        assert args[0].startswith("postgresql://")
