# Shamba AI — Implementation Progress Report

**Last updated:** 2026-05-11

This document tracks every recommended improvement applied to the Shamba AI project — what changed, why, and which files were affected.

---

## Session 1 Changes (Initial recommendations)

### ✅ Fix 0 — Empty Send Button
| Field | Detail |
|---|---|
| **File** | `frontend/src/components/VoiceInput.jsx` |
| **Change** | Added an SVG paper-plane icon inside the blank send button. |

### ✅ Fix 1 — Deployment Workflow Optimization
| Field | Detail |
|---|---|
| **File** | `backend/entrypoint.sh` |
| **Change** | Removed `--reload` from uvicorn (dev-only flag). `ingest.py` already has a built-in guard that skips re-embedding when the ChromaDB collection is populated — the script comment now makes this explicit. |

### ✅ Fix 2 — Local Dev Proxy Fix
| Field | Detail |
|---|---|
| **Files** | `frontend/package.json`, `frontend/.env` (new), `frontend/.env.example` (new), `docker-compose.yml` |
| **Change** | Removed broken `"proxy": "http://backend:8000"`. API URL is now configured via `REACT_APP_API_URL` — `frontend/.env` for local dev, `docker-compose.yml` environment block for Docker. |

### ✅ Fix 3 — Async Voice File Handling
| Field | Detail |
|---|---|
| **Files** | `backend/app.py`, `backend/requirements.txt` |
| **Change** | `/voice-query` endpoint rewritten with `aiofiles` + `pathlib`. Added `logging` module in place of `print()`. `aiofiles` added to `requirements.txt`. |

### ✅ Fix 4 — Global Busy State for Voice Transcription
| Field | Detail |
|---|---|
| **Files** | `frontend/src/App.jsx`, `frontend/src/components/VoiceInput.jsx` |
| **Change** | `transcribing` state lifted from `VoiceInput` to `App`. `isBusy = loading \|\| transcribing` disables language switcher, clear button, and text input globally during voice processing. |

---

## Session 2 Changes (Next recommended steps)

### ✅ Fix 5 — Proper Logging in `rag_pipeline.py`
| Field | Detail |
|---|---|
| **File** | `backend/rag_pipeline.py` |
| **Change** | Added `logging.basicConfig()` and `logger = logging.getLogger("rag_pipeline")`. Replaced all `print()` calls with `logger.info()`, `logger.error()`, and `logger.warning()`. |

### ✅ Fix 6 — Proper Logging in `ingest.py`
| Field | Detail |
|---|---|
| **File** | `backend/ingest.py` |
| **Change** | Added `logging.basicConfig()` and `logger = logging.getLogger("ingest")`. Replaced all `print()` calls with appropriate log levels. |

### ✅ Fix 7 — Pytest Unit Tests (Backend)
| Field | Detail |
|---|---|
| **Files created** | `backend/tests/conftest.py`, `backend/tests/test_utils.py`, `backend/tests/test_db_init.py`, `backend/tests/test_rag_pipeline.py`, `backend/tests/test_app.py`, `backend/pytest.ini` |

**Test coverage:**

| File | What's tested |
|---|---|
| `test_utils.py` | `detect_location`, `detect_crop`, `get_weather` (mocked HTTP), `get_market_prices`, `get_safety_disclaimer` |
| `test_db_init.py` | ChromaDB init (create/skip/reset/fail), PostgreSQL init (create table/drop/reset/URL DSN) |
| `test_rag_pipeline.py` | `is_greeting()`, `get_history/save_message/clear_history` (mocked DB), `query_rag()` greeting path, LLM path, safety disclaimer, error fallback |
| `test_app.py` | GET `/`, POST `/text-query`, POST `/clear-history`, GET `/history/{id}`, POST `/sms` webhook, `truncate_sms()` |
| `conftest.py` | Shared `mock_env`, `mock_pg_conn`, `mock_chroma_client` fixtures |

**To run:**
```bash
cd backend
pip install pytest httpx
pytest
```

### ✅ Fix 8 — React Component Tests (Frontend)
| Field | Detail |
|---|---|
| **Files created** | `frontend/src/__tests__/VoiceInput.test.jsx`, `frontend/src/__tests__/ChatBox.test.jsx`, `frontend/src/setupTests.js` |
| **`package.json`** | Added `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` as devDependencies. Added `"test"` and `"test:watch"` scripts. |

**Test coverage:**

| Component | What's tested |
|---|---|
| `VoiceInput` | Renders mic button, Swahili/Kikuyu placeholders, send disabled when empty, send enabled with text, `onSend` called on click and Enter, input cleared after send, transcribing labels, disabled states during loading/transcribing |
| `ChatBox` | Empty state, single/multiple messages, Swahili/Kikuyu thinking indicators, loading indicator hidden when not loading, error message rendering |

**To run:**
```bash
cd frontend
npm install
npm test
```

### ✅ Fix 9 — `.gitignore` Rule for `frontend/.env`
| Field | Detail |
|---|---|
| **File** | `.gitignore` |
| **Change** | Added explicit `frontend/.env` entry under SECRETS section so the local API URL config is never accidentally committed. The root `.env` was already covered. |

### ℹ️ Fix 10 — Pre-run Ingestion (Manual step required)
| Field | Detail |
|---|---|
| **Action required** | Run ingestion locally and commit the output so Render never has to rebuild vectors on cold start. |

**Steps:**
```bash
# 1. Start ChromaDB locally (or use persistent mode)
cd luna
docker-compose up chromadb -d

# 2. Run ingestion from the backend directory
cd backend
python ingest.py

# 3. Commit the generated chroma_data folder
cd ..
git add vectordb/chroma_data
git commit -m "chore: pre-index ChromaDB for production deployment"
git push
```

> **Note:** If your `vectordb/chroma_data` folder is in `.gitignore`, you'll need to temporarily remove that exclusion, commit the data, then restore the rule for local development.

---

## Summary Table

| # | Item | Status | Files |
|---|---|---|---|
| 0 | Empty send button | ✅ Done | `VoiceInput.jsx` |
| 1 | Entrypoint optimization + remove --reload | ✅ Done | `entrypoint.sh` |
| 2 | Local dev proxy fix + env files | ✅ Done | `package.json`, `frontend/.env`, `frontend/.env.example`, `docker-compose.yml` |
| 3 | Async pathlib voice handling + logging | ✅ Done | `app.py`, `requirements.txt` |
| 4 | Global busy state for transcription | ✅ Done | `App.jsx`, `VoiceInput.jsx` |
| 5 | Logging in `rag_pipeline.py` | ✅ Done | `rag_pipeline.py` |
| 6 | Logging in `ingest.py` | ✅ Done | `ingest.py` |
| 7 | Pytest backend tests (4 test files) | ✅ Done | `backend/tests/` |
| 8 | React component tests | ✅ Done | `frontend/src/__tests__/` |
| 9 | `.gitignore` `frontend/.env` rule | ✅ Done | `.gitignore` |
| 10 | Pre-run ingestion locally | ⏳ Manual | Run `python ingest.py`, commit `vectordb/chroma_data` |


This document tracks every recommended improvement applied to the Shamba AI
project, what changed, why it changed, and which files were affected.

---

## ✅ Fix 0 — Empty Send Button (Pre-existing fix)

| Field | Detail |
|---|---|
| **Status** | ✅ Complete |
| **File** | `frontend/src/components/VoiceInput.jsx` |

### What was wrong
The send button (`<button onClick={handleSend}>`) had no child content — it rendered as an invisible, unclickable circle in the UI.

### What changed
Added an SVG paper-plane icon (`<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>`) inside the button so users can see and click it.

---

## ✅ Fix 1 — Deployment Workflow Optimization

| Field | Detail |
|---|---|
| **Status** | ✅ Complete |
| **Files** | `backend/entrypoint.sh` |

### What was wrong
`entrypoint.sh` ran `python ingest.py` unconditionally every time the container started. On Render (and any Docker host), this meant re-embedding all PDFs and text files from scratch on every cold start — taking several minutes and consuming HuggingFace API quota unnecessarily.

The `uvicorn` command also used `--reload`, which is a development-only flag that spawns a file-watcher process. In production this wastes memory and can cause instability.

### What changed
- Removed `--reload` from the `uvicorn` start command.
- Added a comment explaining that `ingest.py` already has a built-in guard: it queries ChromaDB's collection count and **skips ingestion** when vectors already exist.  Pass `--force` on the command line to override.
- `db_init.py` is still run every startup because it is fully idempotent (uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`).

### How to force re-ingest
```bash
docker-compose exec backend python ingest.py --force
```

---

## ✅ Fix 2 — Local Dev Proxy Fix

| Field | Detail |
|---|---|
| **Status** | ✅ Complete |
| **Files** | `frontend/package.json`, `frontend/.env` (new), `frontend/.env.example` (new), `docker-compose.yml` |

### What was wrong
`frontend/package.json` contained `"proxy": "http://backend:8000"`. This hostname only resolves inside the Docker network. Running `npm start` locally (outside Docker) silently failed because `backend` is not a valid hostname on the developer's machine.

### What changed

**`frontend/package.json`** — `"proxy"` field removed entirely.

**`frontend/.env`** (new) — provides the API URL for local development:
```
REACT_APP_API_URL=http://localhost:8000
```

**`frontend/.env.example`** (new) — template for new contributors to copy.

**`docker-compose.yml`** — the `frontend` service now receives the correct URL at container runtime:
```yaml
environment:
  - REACT_APP_API_URL=http://backend:8000
```

`App.jsx` already reads `process.env.REACT_APP_API_URL` correctly, so no React code changes were needed.

---

## ✅ Fix 3 — Async Voice File Handling with pathlib

| Field | Detail |
|---|---|
| **Status** | ✅ Complete |
| **Files** | `backend/app.py`, `backend/requirements.txt` |

### What was wrong
The `/voice-query` endpoint used synchronous `open()` and `os.unlink()` calls inside an `async` FastAPI route. Blocking I/O in an async function stalls the event loop, preventing the server from handling other requests while a voice upload is being written to disk.

### What changed

**`backend/requirements.txt`** — added `aiofiles`.

**`backend/app.py`** — `/voice-query` endpoint rewritten:
- Uses `aiofiles.open()` for all disk reads and writes (non-blocking).
- Uses `pathlib.Path` for temp file path management (`Path(tempfile.mktemp(suffix=suffix))`).
- Derives the correct file extension from the original upload filename (`.webm`, `.ogg`, `.m4a`) instead of hardcoding `.wav`.
- Cleanup uses `tmp_path.exists()` + `tmp_path.unlink()` (pathlib) instead of `os.unlink()`.
- Added a `logger.info()` call for observability.

Also added at module level:
- `import logging` and a `basicConfig` setup replacing all `print()` calls with a proper logger named `shamba_ai`.

---

## ✅ Fix 4 — Global Busy / Loading State for Voice Transcription

| Field | Detail |
|---|---|
| **Status** | ✅ Complete |
| **Files** | `frontend/src/App.jsx`, `frontend/src/components/VoiceInput.jsx` |

### What was wrong
`VoiceInput.jsx` managed a local `transcribing` state, but `App.jsx` had no knowledge of it. This meant:
- The language switcher buttons remained active while a voice note was being sent.
- The "Clear Chat" button could be pressed mid-transcription, wiping conversation history unexpectedly.
- The quick-topic buttons could fire a second query that would race the voice query.

### What changed

**`App.jsx`**:
- Added `const [transcribing, setTranscribing] = useState(false)`.
- Added `const isBusy = loading || transcribing` — a single derived flag.
- Passed `transcribing` and `setTranscribing` down to `<VoiceInput>`.
- Language switcher buttons: `disabled={isBusy}` + `onClick` guard.
- "Clear Chat" button: `disabled={isBusy}` + reduced opacity when busy.

**`VoiceInput.jsx`**:
- Removed local `const [transcribing, setTranscribing] = useState(false)`.
- Now accepts `transcribing` and `setTranscribing` as props from `App`.

---

## Summary Table

| # | Recommendation | Status | Files Changed |
|---|---|---|---|
| 0 | Empty send button | ✅ Done | `VoiceInput.jsx` |
| 1 | Entrypoint optimization + no --reload | ✅ Done | `entrypoint.sh` |
| 2 | Local dev proxy fix + frontend env files | ✅ Done | `package.json`, `.env`, `.env.example`, `docker-compose.yml` |
| 3 | Async pathlib voice handling + logging | ✅ Done | `app.py`, `requirements.txt` |
| 4 | Global busy state for voice transcription | ✅ Done | `App.jsx`, `VoiceInput.jsx` |

---

## Next Recommended Steps

- [ ] Implement proper `logging` in `rag_pipeline.py` and `ingest.py` (currently using `print()`).
- [ ] Add `pytest` unit tests for `rag_pipeline.py`, `utils.py`, and `db_init.py`.
- [ ] Add React component tests using React Testing Library for `VoiceInput` and `ChatBox`.
- [ ] Add a `.gitignore` rule to ensure `frontend/.env` is excluded from commits (secrets).
- [ ] Pre-run `python ingest.py` locally and commit the `vectordb/chroma_data` folder to avoid cold-start ingestion on Render.
## 🛠️ Troubleshooting: Docker Volume Mounts (Windows)

If you encounter an error like `not a directory` when running `docker-compose up`, follow these steps:

1.  **Restart Docker Desktop:** This fixes the "system cannot find the file specified" pipe error.
2.  **Clean up:** Run `docker-compose down` to stop any hanging containers.
3.  **Reset folders:** Manually delete the `vectordb` directory and recreate it using `mkdir -p vectordb/chroma_data` to ensure it's a valid directory.
4.  **Healthchecks:** I've added a healthcheck to `chromadb` in `docker-compose.yml` so the backend waits for the database to be fully initialized before attempting to connect.
