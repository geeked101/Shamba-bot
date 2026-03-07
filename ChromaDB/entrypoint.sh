#!/bin/bash
set -e

echo "============================================"
echo "   Shamba AI - Starting up..."
echo "============================================"

echo ""
echo "Step 1/3: Initializing database..."
python db_init.py

echo ""
echo "Step 2/3: Ingesting documents..."
python ingest.py

echo ""
echo "Step 3/3: Starting API server..."
exec uvicorn app:app --host 0.0.0.0 --port 8000 --reload
