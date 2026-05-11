"""
tests/test_rag_pipeline.py

Unit tests for rag_pipeline.py:
  - is_greeting()
  - get_history() / save_message() / clear_history()
  - query_rag() — greeting shortcut, vector search, LLM call, safety disclaimer
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Helpers that don't need a DB ───────────────────────────────────────────────

class TestIsGreeting:
    """Tests for is_greeting()."""

    def _import(self):
        """Import after env is patched."""
        # Patch heavy dependencies so the module loads without real connections
        with patch("chromadb.PersistentClient"), \
             patch("groq.Groq"), \
             patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
             patch("langchain_community.vectorstores.Chroma"):
            from rag_pipeline import is_greeting
            return is_greeting

    def test_habari_is_swahili_greeting(self):
        is_greeting = self._import()
        assert is_greeting("habari", "sw") is True

    def test_wi_mwega_is_kikuyu_greeting(self):
        is_greeting = self._import()
        assert is_greeting("wĩ mwega", "ki") is True

    def test_long_text_is_not_greeting(self):
        """Greetings are only detected in short messages (< 20 chars)."""
        is_greeting = self._import()
        assert is_greeting("habari gani kuhusu magonjwa ya mahindi leo", "sw") is False

    def test_random_question_is_not_greeting(self):
        is_greeting = self._import()
        assert is_greeting("mahindi yana madoa", "sw") is False


# ── DB helpers ─────────────────────────────────────────────────────────────────

class TestDBHelpers:
    """Tests for get_history, save_message, and clear_history."""

    @pytest.fixture(autouse=True)
    def _patch_module_level(self):
        """Prevent real DB/Chroma/Groq connections at import time."""
        with patch("chromadb.PersistentClient"), \
             patch("groq.Groq"), \
             patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
             patch("langchain_community.vectorstores.Chroma"):
            yield

    def test_get_history_returns_messages(self, mock_pg_conn):
        mock_conn, mock_cursor = mock_pg_conn
        mock_cursor.fetchall.return_value = [
            ("user", "Habari"),
            ("assistant", "Poa!"),
        ]
        with patch("psycopg2.connect", return_value=mock_conn):
            from rag_pipeline import get_history
            result = get_history("session_abc")

        assert len(result) == 2
        assert result[0] == {"role": "user", "content": "Habari"}
        assert result[1] == {"role": "assistant", "content": "Poa!"}

    def test_get_history_returns_empty_on_db_error(self):
        with patch("psycopg2.connect", side_effect=Exception("db down")):
            from rag_pipeline import get_history
            result = get_history("session_xyz")
        assert result == []

    def test_save_message_executes_insert(self, mock_pg_conn):
        mock_conn, mock_cursor = mock_pg_conn
        with patch("psycopg2.connect", return_value=mock_conn):
            from rag_pipeline import save_message
            save_message("sess1", "user", "Habari", "sw")

        sql_calls = " ".join(str(c) for c in mock_cursor.execute.call_args_list)
        assert "INSERT INTO" in sql_calls

    def test_clear_history_executes_delete(self, mock_pg_conn):
        mock_conn, mock_cursor = mock_pg_conn
        with patch("psycopg2.connect", return_value=mock_conn):
            from rag_pipeline import clear_history
            clear_history("sess1")

        sql_calls = " ".join(str(c) for c in mock_cursor.execute.call_args_list)
        assert "DELETE FROM" in sql_calls


# ── query_rag ──────────────────────────────────────────────────────────────────

class TestQueryRAG:
    """Integration-level tests for query_rag() with all I/O mocked."""

    @pytest.fixture(autouse=True)
    def _patch_all(self, mock_pg_conn):
        """
        Patch every external dependency so query_rag() runs fully in-process.
        """
        mock_conn, mock_cursor = mock_pg_conn
        mock_cursor.fetchall.return_value = []

        mock_vectorstore = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "Mahindi yana ugonjwa wa Gray Leaf Spot."
        mock_doc.metadata = {"source": "kalro_guide.pdf"}
        mock_vectorstore.similarity_search.return_value = [mock_doc]

        mock_choice = MagicMock()
        mock_choice.message.content = "Tumia fungicide kama Mancozeb."
        mock_groq_response = MagicMock()
        mock_groq_response.choices = [mock_choice]
        mock_groq = MagicMock()
        mock_groq.chat.completions.create.return_value = mock_groq_response

        with patch("chromadb.PersistentClient"), \
             patch("groq.Groq", return_value=mock_groq), \
             patch("langchain_community.embeddings.HuggingFaceInferenceAPIEmbeddings"), \
             patch("langchain_community.vectorstores.Chroma") as mock_chroma_cls, \
             patch("psycopg2.connect", return_value=mock_conn):
            mock_chroma_cls.return_value = mock_vectorstore
            self.mock_groq = mock_groq
            self.mock_vectorstore = mock_vectorstore
            yield

    def test_greeting_bypasses_llm(self):
        """A greeting should return a canned response without calling Groq."""
        from rag_pipeline import query_rag
        answer = query_rag("habari", "sw", "sess1")
        # Greeting responses are predefined strings
        assert isinstance(answer, str)
        assert len(answer) > 0
        self.mock_groq.chat.completions.create.assert_not_called()

    def test_normal_question_calls_groq(self):
        """A non-greeting question must hit the Groq LLM."""
        from rag_pipeline import query_rag
        answer = query_rag("Mahindi yangu yana madoa ya kijivu", "sw", "sess2")
        assert "Mancozeb" in answer
        self.mock_groq.chat.completions.create.assert_called_once()

    def test_safety_disclaimer_appended_for_chemical_keywords(self):
        """If the question mentions 'dawa', a safety disclaimer must be appended."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Tumia dawa hii."
        self.mock_groq.chat.completions.create.return_value.choices = [mock_choice]

        from rag_pipeline import query_rag
        answer = query_rag("dawa gani ya kutumia", "sw", "sess3")
        # Safety disclaimer always starts with a [!] marker
        assert "[!" in answer or "Kumbuka" in answer

    def test_groq_error_returns_fallback(self):
        """When Groq raises an exception the answer should be a graceful fallback."""
        self.mock_groq.chat.completions.create.side_effect = Exception("rate limit")
        from rag_pipeline import query_rag
        answer = query_rag("Mahindi yana ugonjwa", "sw", "sess4")
        assert "Samahani" in answer or "jaribu" in answer
