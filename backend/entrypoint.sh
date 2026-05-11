#!/bin/bash
set -e

echo "============================================"
echo "   Shamba AI - Starting up..."
echo "============================================"

echo ""
echo "Step 1/3: Initializing database..."
python db_init.py

echo ""
echo "Step 2/3: Checking if ingestion is needed..."
# ingest.py has a built-in guard: if the ChromaDB collection already
# has vectors it skips re-embedding. Pass --force to override.
python ingest.py

echo ""
echo "Step 3/3: Starting API server..."
# --reload is dev-only; omit it in production so the process is stable
exec uvicorn app:app --host 0.0.0.0 --port 8000
