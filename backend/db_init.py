"""
db_init.py

Step 1 in the startup sequence.

Initializes TWO databases:
  1. ChromaDB  — creates the vector collection for agriculture knowledge
  2. PostgreSQL — creates the conversation_history table for chat memory

Safe to re-run: skips creation if things already exist.

Run manually:
  docker-compose exec backend python db_init.py

Run with reset (wipes and recreates everything):
  docker-compose exec backend python db_init.py --reset
"""

import os
import sys
import argparse
import chromadb
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

#  ChromaDB config 
CHROMA_SERVER_MODE = os.getenv("CHROMA_SERVER_MODE", "http") # 'http' or 'persistent'
CHROMA_HOST        = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT        = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_DIR         = os.getenv("CHROMA_DIR", "./vectordb/chroma_data")
COLLECTION_NAME    = os.getenv("CHROMA_COLLECTION", "shamba_rag")

#  PostgreSQL config 
PG_HOST     = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT     = os.getenv("POSTGRES_PORT", "5432")
PG_USER     = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB       = os.getenv("POSTGRES_DB", "shambadb")


#  1. ChromaDB 
def init_chromadb(reset: bool = False):
    try:
        if CHROMA_SERVER_MODE == "persistent":
            print(f"  [ChromaDB] Connecting in PERSISTENT mode at {CHROMA_DIR}...")
            client = chromadb.PersistentClient(path=CHROMA_DIR)
        else:
            print(f"  [ChromaDB] Connecting to {CHROMA_HOST}:{CHROMA_PORT}...")
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            client.heartbeat()
        print("  [ChromaDB]  Connection healthy")
    except Exception as e:
        print(f"  [ChromaDB]  Connection failed: {e}")
        sys.exit(1)

    existing = [c.name for c in client.list_collections()]

    if reset and COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
        print(f"  [ChromaDB]   Collection '{COLLECTION_NAME}' deleted (reset)")
        existing = []

    if COLLECTION_NAME not in existing:
        client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Shamba AI agriculture knowledge base"}
        )
        print(f"  [ChromaDB]  Collection '{COLLECTION_NAME}' created")
    else:
        count = client.get_collection(COLLECTION_NAME).count()
        print(f"  [ChromaDB]  Collection '{COLLECTION_NAME}' exists ({count} vectors)")


#  2. PostgreSQL 
def init_postgres(reset: bool = False):
    print(f"  [PostgreSQL] Connecting to {PG_HOST}:{PG_PORT}...")
    try:
        if PG_HOST.startswith("postgresql://") or PG_HOST.startswith("postgres://"):
            conn = psycopg2.connect(PG_HOST)
        else:
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                user=PG_USER,
                password=PG_PASSWORD,
                dbname=PG_DB
            )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        print("  [PostgreSQL]  Connection healthy")
    except Exception as e:
        print(f"  [PostgreSQL]  Connection failed: {e}")
        sys.exit(1)

    if reset:
        cur.execute("DROP TABLE IF EXISTS conversation_history;")
        print("  [PostgreSQL]   Table 'conversation_history' dropped (reset)")

    # Create conversation history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id          SERIAL PRIMARY KEY,
            session_id  VARCHAR(64)  NOT NULL,
            role        VARCHAR(16)  NOT NULL,   -- 'user' or 'assistant'
            content     TEXT         NOT NULL,
            language    VARCHAR(8)   NOT NULL DEFAULT 'sw',
            created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
        );
    """)

    # Index for fast session lookups
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_session_id
        ON conversation_history (session_id, created_at);
    """)

    print("  [PostgreSQL]  Table 'conversation_history' ready")

    cur.close()
    conn.close()


#  Main 
def init_db(reset: bool = False):
    init_chromadb(reset)
    print()
    init_postgres(reset)
    print()
    print("   All databases initialized\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe and recreate everything")
    args = parser.parse_args()
    init_db(reset=args.reset)
