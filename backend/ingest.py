"""
ingest.py

Step 2 in the startup sequence.

What it does:
  - Loads .txt files from /app/data/swahili and /app/data/kikuyu
  - Loads .pdf files from /app/data/pdfs
  - Splits documents into chunks
  - Embeds using multilingual-e5-large via HuggingFace Inference API
  - Stores in ChromaDB (skips if already ingested)
  - Falls back to built-in seed data if no files are found

Run manually:
  docker-compose exec backend python ingest.py

Run with force re-ingest:
  docker-compose exec backend python ingest.py --force
"""

import os
import sys
import logging
import argparse
import chromadb
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader, DirectoryLoader
from langchain_core.documents import Document

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ingest")

#  ChromaDB config
CHROMA_SERVER_MODE = os.getenv("CHROMA_SERVER_MODE", "http") # 'http' or 'persistent'
CHROMA_HOST        = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT        = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_DIR         = os.getenv("CHROMA_DIR", "./chroma_data")
COLLECTION_NAME    = os.getenv("CHROMA_COLLECTION", "shamba_rag")

HF_API_KEY      = os.getenv("HF_API_KEY")
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
CHUNK_SIZE      = 500
CHUNK_OVERLAP   = 50

#  Vector DB Toggle
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chroma")
PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX    = os.getenv("PINECONE_INDEX_NAME", "shamba-ai")

DATA_DIRS = {
    "sw": os.path.join(os.path.dirname(__file__), "data", "swahili"),
    "ki": os.path.join(os.path.dirname(__file__), "data", "kikuyu"),
    "en": os.path.join(os.path.dirname(__file__), "data", "pdfs"),
}

# If running locally in the root folder, try fallback
if not os.path.exists(DATA_DIRS["sw"]):
    DATA_DIRS = {
        "sw": "Data/swahili",
        "ki": "Data/kikuyu",
        "en": "Data/pdfs",
    }

#  Seed data (used when no files are found) 
SEED_DOCS = [
    Document(
        page_content=(
            "Ugonjwa wa Gray Leaf Spot unaathiri mahindi. Dalili ni madoa ya kijivu kwenye majani. "
            "Unasababishwa na kuvu Cercospora zeae-maydis. Dawa: tumia fungicide kama Mancozeb. "
            "Zuia kwa kupanda mbegu zinazostahimili ugonjwa huu."
        ),
        metadata={"language": "sw", "topic": "crop_disease", "source": "seed"}
    ),
    Document(
        page_content=(
            "Northern Leaf Blight ya mahindi inaonekana kama madoa marefu ya kahawia kwenye majani. "
            "Inasababishwa na kuvu Exserohilum turcicum. Tumia dawa za kuua kuvu mapema. "
            "Zungushe mazao kila msimu ili kupunguza maambukizi."
        ),
        metadata={"language": "sw", "topic": "crop_disease", "source": "seed"}
    ),
    Document(
        page_content=(
            "Mbolea ya DAP (Diammonium Phosphate) inafaa kwa kupanda. Tumia mfuko 1 kwa ekari moja. "
            "Mbolea ya CAN (Calcium Ammonium Nitrate) inafaa kwa kukuza mimea. "
            "Kenya Farmers Association inashauri kutumia mbolea kulingana na uchunguzi wa udongo."
        ),
        metadata={"language": "sw", "topic": "fertilizer", "source": "seed"}
    ),
    Document(
        page_content=(
            "Msimu wa kupanda mahindi Kenya: Mashariki - Machi hadi Mei (mvua za masika). "
            "Magharibi - Aprili hadi Juni. Nyanda za Juu - Februari hadi Aprili. "
            "Panda mbegu ndani ya siku 2 baada ya mvua ya kwanza."
        ),
        metadata={"language": "sw", "topic": "planting_season", "source": "seed"}
    ),
    Document(
        page_content=(
            "Ng'ombe wanaohitaji chanjo: Ugonjwa wa miguu na mdomo (FMD) - chanjo kila miezi 6. "
            "Sotoka (Anthrax) - chanjo kila mwaka. Dalili za ng'ombe mgonjwa: kutotoa maziwa, "
            "homa, kutokula. Wasiliana na daktari wa mifugo mara moja."
        ),
        metadata={"language": "sw", "topic": "livestock", "source": "seed"}
    ),
    Document(
        page_content=(
            "Mirimu ya Mahindi - Gray Leaf Spot: Nĩ mũrimũ wa kaguta wa mahindi urĩa ũrehaga madoa "
            "ma ngũngũrũ kũrĩa kwa mahindi. Gũtũmia dawa ya fungicide nĩ njĩra ya kũrĩa. "
            "Panda mbegu itigĩrĩte mũrimũ ũyũ."
        ),
        metadata={"language": "ki", "topic": "crop_disease", "source": "seed"}
    ),
    Document(
        page_content=(
            "Mbolea ya mahindi Kenya: DAP nĩ mbolea njega ya gũtangĩria kupanda. "
            "CAN nĩ ya gũcooka gũkũra mahindi. Ũhoro wa mbolea ũgathondekwo na ũhoro wa mũgũnda."
        ),
        metadata={"language": "ki", "topic": "fertilizer", "source": "seed"}
    ),
    Document(
        page_content=(
            "Coffee farming in Kenya: Plant in long rains season March-May. "
            "Use CAN fertilizer after first harvest. Prune annually to maintain yield. "
            "Common disease: Coffee Berry Disease (CBD) - spray copper-based fungicide. "
            "Harvest only red ripe cherries for best quality."
        ),
        metadata={"language": "en", "topic": "coffee_farming", "source": "seed"}
    ),
    Document(
        page_content=(
            "Tea farming in Kenya highlands: Best altitude 1500-2700m. "
            "Pluck every 7-14 days during growing season. "
            "Apply NPK fertilizer 4 times a year. "
            "Watch for blister blight disease - apply copper fungicide when detected."
        ),
        metadata={"language": "en", "topic": "tea_farming", "source": "seed"}
    ),
]


def load_txt_files(folder: str, language: str) -> list[Document]:
    if not os.path.exists(folder):
        return []
    docs = []
    for fname in os.listdir(folder):
        if fname.endswith(".txt"):
            path = os.path.join(folder, fname)
            loader = TextLoader(path, encoding="utf-8")
            loaded = loader.load()
            for doc in loaded:
                doc.metadata["language"] = language
                doc.metadata["source"] = fname
            docs.extend(loaded)
    return docs


def load_pdf_files(folder: str) -> list[Document]:
    if not os.path.exists(folder):
        return []
    docs = []
    for fname in os.listdir(folder):
        if fname.endswith(".pdf"):
            path = os.path.join(folder, fname)
            try:
                loader = PyMuPDFLoader(path)
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["language"] = "en"
                    doc.metadata["source"] = fname
                docs.extend(loaded)
                logger.info("Loaded PDF: %s (%d pages)", fname, len(loaded))
            except Exception as e:
                logger.warning("Could not load %s: %s", fname, e)
        elif fname.endswith(".txt"):
            path = os.path.join(folder, fname)
            try:
                loader = TextLoader(path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    doc.metadata["language"] = "en"
                    doc.metadata["source"] = fname
                docs.extend(loaded)
                print(f"     Loaded TXT: {fname}")
            except Exception as e:
                print(f"      Could not load {fname}: {e}")
    return docs


def ingest(force: bool = False):
    # Check if already ingested (only for Chroma)
    if not force and VECTOR_STORE_TYPE == "chroma":
        try:
            if CHROMA_SERVER_MODE == "persistent":
                client = chromadb.PersistentClient(path=CHROMA_DIR)
            else:
                client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
                
            collection = client.get_collection(COLLECTION_NAME)
            if collection.count() > 0:
                logger.info(
                    "Collection '%s' already has %d vectors — skipping ingest. "
                    "Pass --force to re-ingest.",
                    COLLECTION_NAME, collection.count()
                )
                return
        except Exception:
            pass

    logger.info("Initializing HuggingFace Inference API embeddings...")
    embeddings = HuggingFaceInferenceAPIEmbeddings(
        api_key=HF_API_KEY,
        api_url=f"https://router.huggingface.co/hf-inference/models/{EMBEDDING_MODEL}"
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    all_docs = []

    logger.info("Loading text documents...")
    sw_docs = load_txt_files(DATA_DIRS["sw"], "sw")
    ki_docs = load_txt_files(DATA_DIRS["ki"], "ki")
    logger.info("Swahili: %d documents | Kikuyu: %d documents", len(sw_docs), len(ki_docs))
    all_docs.extend(sw_docs + ki_docs)

    logger.info("Loading PDF documents...")
    pdf_docs = load_pdf_files(DATA_DIRS["en"])
    logger.info("PDFs: %d pages loaded", len(pdf_docs))
    all_docs.extend(pdf_docs)

    if not all_docs:
        logger.warning("No documents found in data folders — using built-in seed data.")
        all_docs = SEED_DOCS
    else:
        all_docs = splitter.split_documents(all_docs)

    logger.info("Total chunks to embed: %d", len(all_docs))
    logger.info("Embedding and storing (this may take a few minutes)...")

    import uuid

    if VECTOR_STORE_TYPE == "pinecone" and PINECONE_API_KEY:
        from langchain_pinecone import PineconeVectorStore
        logger.info("Target: Pinecone Index '%s'", PINECONE_INDEX)
        PineconeVectorStore.from_documents(
            all_docs,
            embeddings,
            index_name=PINECONE_INDEX,
            pinecone_api_key=PINECONE_API_KEY
        )
        logger.info("Pinecone: stored %d chunks", len(all_docs))
    else:
        if CHROMA_SERVER_MODE == "persistent":
            logger.info("Target: Local ChromaDB (Persistent) at %s", CHROMA_DIR)
            client = chromadb.PersistentClient(path=CHROMA_DIR)
        else:
            logger.info("Target: Remote ChromaDB (HTTP) at %s", CHROMA_HOST)
            client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            
        collection = client.get_or_create_collection(COLLECTION_NAME)

        BATCH_SIZE = 32
        for i in range(0, len(all_docs), BATCH_SIZE):
            batch = all_docs[i:i+BATCH_SIZE]
            logger.info(
                "Batch %d/%d...",
                i // BATCH_SIZE + 1,
                (len(all_docs) + BATCH_SIZE - 1) // BATCH_SIZE
            )
            texts = [doc.page_content for doc in batch]
            metadatas = [doc.metadata for doc in batch]
            ids = [str(uuid.uuid4()) for _ in batch]

            success = False
            for attempt in range(10):
                try:
                    out = embeddings.embed_documents(texts)
                    collection.add(
                        documents=texts,
                        embeddings=out,
                        metadatas=metadatas,
                        ids=ids
                    )
                    success = True
                    break
                except Exception as e:
                    logger.warning("Batch embedding error (attempt %d): %s", attempt + 1, e)
                    import time
                    time.sleep(15)
            
            if not success:
                logger.error("Failed to embed batch — aborting.")
                sys.exit(1)

        logger.info("%d chunks stored in ChromaDB", len(all_docs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-ingest even if data exists")
    args = parser.parse_args()
    ingest(force=args.force)