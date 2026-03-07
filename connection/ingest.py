"""
ingest.py - Shamba AI Document Ingestion
Embeds documents in small batches to avoid HF API errors.
"""

import os
import sys
import time
import argparse
import chromadb
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_core.documents import Document
from langchain_core.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

CHROMA_HOST     = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", 8000))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "shamba_rag")
HF_API_KEY      = os.getenv("HF_API_KEY", "")
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
CHUNK_SIZE      = 400
CHUNK_OVERLAP   = 40
BATCH_SIZE      = 16   # Small batches — HF API is picky with large requests

DATA_DIRS = {
    "sw": "/app/data/swahili",
    "ki": "/app/data/kikuyu",
    "en": "/app/data/pdfs",
}

#  Seed data fallback 
SEED_DOCS = [
    Document(page_content="Mbolea ya Mahindi: DAP mfuko 1 (50kg) kwa ekari wakati wa kupanda. CAN mfuko 1 topdress wiki 4-6.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="East Coast Fever (Ndigana Kali): Homa kali, uvimbe tezi, kupumua kwa shida. Matibabu: Butalex sindano. Chanjo ITM mara moja.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Newcastle (Mdondo) wa Kuku: Shingo kupinda, kupumua kwa nguvu, kuhara kijani. Chanjo kila miezi 3.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Fall Armyworm: Viwavi vamizi - madirisha kwenye majani. Dawa: Coragen au Ampligo. Angalia shamba kila siku.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Late Blight ya Viazi: Madoa meusi kwenye majani, harufu mbaya. Dawa: Ridomil Gold MZ kila siku 7-10.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Coffee Berry Disease (CBD): Matunda ya kahawa yanageuka meusi. Piga dawa ya shaba mara 4 kwa msimu.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Msimu wa kupanda mahindi Central Kenya: Masika Februari-Machi. Vuli Oktoba-Novemba. Panda siku 2-3 baada ya mvua.", metadata={"language": "sw", "source": "seed"}),
    Document(page_content="Kahawa aina: SL34 na SL28 nyanda za juu. Ruiru 11 inafaa kila eneo, ina kinga dhidi ya magonjwa. Batian aina mpya ya kisasa.", metadata={"language": "sw", "source": "seed"}),
]


def embed_texts_hf(texts: list[str]) -> list[list[float]]:
    """Call HuggingFace Inference API directly — more reliable than LangChain wrapper."""
    import requests
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    url = f"https://api-inference.huggingface.co/models/{EMBEDDING_MODEL}"
    
    all_embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        for attempt in range(3):
            try:
                resp = requests.post(url, headers=headers, json={"inputs": batch}, timeout=60)
                if resp.status_code == 200:
                    result = resp.json()
                    # HF returns list of embeddings
                    if isinstance(result, list) and len(result) == len(batch):
                        all_embeddings.extend(result)
                        print(f"     Embedded batch {i//BATCH_SIZE + 1} ({len(batch)} chunks)")
                        break
                    else:
                        print(f"      Unexpected response shape, retrying...")
                elif resp.status_code == 503:
                    wait = 20 + attempt * 10
                    print(f"     HF model loading, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"      HF API error {resp.status_code}: {resp.text[:100]}")
                    time.sleep(5)
            except Exception as e:
                print(f"      Request error: {e}, retrying...")
                time.sleep(5)
        else:
            print(f"     Failed to embed batch {i//BATCH_SIZE + 1} after 3 attempts")
            return []
        time.sleep(1)  # Be nice to the API
    
    return all_embeddings


def load_txt_files(folder: str, language: str) -> list:
    if not os.path.exists(folder):
        return []
    docs = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith(".txt"):
            path = os.path.join(folder, fname)
            try:
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["language"] = language
                    doc.metadata["source"] = fname
                docs.extend(loaded)
                print(f"     {fname}")
            except Exception as e:
                print(f"      {fname}: {e}")
    return docs


def load_en_files(folder: str) -> list:
    if not os.path.exists(folder):
        return []
    docs = []
    for fname in sorted(os.listdir(folder)):
        path = os.path.join(folder, fname)
        try:
            if fname.endswith(".pdf"):
                loader = PyMuPDFLoader(path)
                loaded = loader.load()
            elif fname.endswith(".txt"):
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
            else:
                continue
            for doc in loaded:
                doc.metadata["language"] = "en"
                doc.metadata["source"] = fname
            docs.extend(loaded)
            print(f"     {fname} ({len(loaded)} pages)")
        except Exception as e:
            print(f"      {fname}: {e}")
    return docs


def ingest(force: bool = False):

    # Check if already ingested
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    if not force:
        try:
            collection = client.get_collection(COLLECTION_NAME)
            if collection.count() > 0:
                print(f"   Already ingested ({collection.count()} vectors). Use --force to re-ingest.\n")
                return
        except Exception:
            pass

    # Load all documents
    print("\n  Loading Swahili documents...")
    sw = load_txt_files(DATA_DIRS["sw"], "sw")
    print(f"  → {len(sw)} docs\n")

    print("  Loading Kikuyu documents...")
    ki = load_txt_files(DATA_DIRS["ki"], "ki")
    print(f"  → {len(ki)} docs\n")

    print("  Loading English/PDF documents...")
    en = load_en_files(DATA_DIRS["en"])
    print(f"  → {len(en)} docs\n")

    all_docs = sw + ki + en

    if not all_docs:
        print("    No files found — using seed data")
        all_docs = SEED_DOCS

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    chunks = splitter.split_documents(all_docs)
    print(f"   {len(chunks)} chunks to embed\n")

    # Extract texts and metadata
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    ids = [f"chunk_{i}" for i in range(len(chunks))]

    # Embed via HF API
    if not HF_API_KEY:
        print("    No HF_API_KEY — storing chunks without embeddings (search will use fallback)")
        embeddings = None
    else:
        print("   Embedding via HuggingFace API (small batches)...")
        embeddings = embed_texts_hf(texts)
        if not embeddings:
            print("    Embedding failed — storing without vectors")
            embeddings = None

    # Store in ChromaDB
    print("\n   Storing in ChromaDB...")
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    # Store in batches
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_meta  = metadatas[i:i + batch_size]
        batch_ids   = ids[i:i + batch_size]

        if embeddings:
            batch_emb = embeddings[i:i + batch_size]
            collection.add(
                documents=batch_texts,
                embeddings=batch_emb,
                metadatas=batch_meta,
                ids=batch_ids
            )
        else:
            collection.add(
                documents=batch_texts,
                metadatas=batch_meta,
                ids=batch_ids
            )

        print(f"    Stored {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    final = collection.count()
    print(f"\n   Done! {final} vectors in ChromaDB\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    ingest(force=args.force)