"""
rag_pipeline.py

Core RAG logic using:
  - Groq (llama-3.3-70b) as the LLM
  - HuggingFace API for embeddings
  - ChromaDB for vector search
  - PostgreSQL for persistent conversation history
"""

import os
import random
import psycopg2
import chromadb
from groq import Groq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from dotenv import load_dotenv
from utils import detect_location, detect_crop, get_weather, get_market_prices, get_safety_disclaimer

load_dotenv()

#  ChromaDB config
CHROMA_SERVER_MODE = os.getenv("CHROMA_SERVER_MODE", "http") # 'http' or 'persistent'
CHROMA_HOST        = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT        = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_DIR         = os.getenv("CHROMA_DIR", "/app/chroma_data")
COLLECTION_NAME    = os.getenv("CHROMA_COLLECTION", "shamba_rag")

#  PostgreSQL config 
PG_HOST         = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT         = os.getenv("POSTGRES_PORT", "5432")
PG_USER         = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD     = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB           = os.getenv("POSTGRES_DB", "shambadb")
PG_SSL          = os.getenv("POSTGRES_SSL", "require") # Neon requires SSL

#  Vector DB Toggle
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "chroma") # 'chroma' or 'pinecone'
PINECONE_API_KEY  = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX    = os.getenv("PINECONE_INDEX_NAME", "shamba-ai")

GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
HF_API_KEY      = os.getenv("HF_API_KEY")
GROQ_MODEL      = "llama-3.3-70b-versatile"

#  Clients 
groq_client = Groq(api_key=GROQ_API_KEY)

print("Initializing HuggingFace embeddings via API...")
embeddings = HuggingFaceInferenceAPIEmbeddings(
    api_key=HF_API_KEY,
    api_url="https://router.huggingface.co/hf-inference/models/intfloat/multilingual-e5-large"
)

if VECTOR_STORE_TYPE == "pinecone" and PINECONE_API_KEY:
    from langchain_pinecone import PineconeVectorStore
    print("Initializing Pinecone vector store...")
    vectorstore = PineconeVectorStore(
        index_name=PINECONE_INDEX,
        embedding=embeddings,
        pinecone_api_key=PINECONE_API_KEY
    )
else:
    if CHROMA_SERVER_MODE == "persistent":
        print(f"Initializing ChromaDB in PERSISTENT mode at {CHROMA_DIR}...")
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    else:
        print(f"Initializing ChromaDB in HTTP mode ({CHROMA_HOST}:{CHROMA_PORT})...")
        chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION_NAME,
        client=chroma_client
    )

#  System prompts 
SYSTEM_PROMPTS = {
    "sw": """Wewe ni Mkulima — msaidizi wa kilimo wa AI kwa wakulima wa Kenya. 

KANUNI ZAKO:
1. USALAMA KWANZA: Daima hamsisha wakulima kutumia dawa kwa usalama.
2. USHAHIDI: Tumia taarifa zilizotolewa tu. Kama hujui, taja "Sina taarifa za kutosha, wasiliana na afisa wa kilimo."
3. CITATION: Taja chanzo cha taarifa yako (mfano: "Kulingana na mwongozo wa [chanzo]...").
4. LUGHA RAHISI: Epuka maneno magumu ya kisayansi. Ongea kama rafiki shambani.
5. UFUPI: Toa majibu kwa njia ya nukta (bullet points) ili yaweze kusomeka haraka kwa sauti.

UNASAIDIA NA:
- Magonjwa ya mazao, mbolea, misimu ya kupanda, na mifugo.
- Hali ya hewa na bei za soko zilizopo.

JINSI YA KUJIBU:
- Salimia kwa urafiki ukisalimiwa.
- Ikiwa unajua eneo la mkulima, taja jinsi hali ya hewa inavyoweza kuathiri ushauri wako.""",

    "ki": """Wee uri Mũrĩmi — mũteithia wa ûrĩmi wa AI ũteithagĩria arĩmi a Kenya.

Watho Waku:
1. ŨGITIRI: Hinda ciothe teithia arĩmi kũmenya kũhũthĩra ndawa na njĩra ya ũgitĩri.
2. ŨMA: Tumia ûhoro ũrĩa ũheetwo tu. Kama ûtarĩ na ûhoro: "Ndĩrathime ûhoro ûyũ. Hoya afisa wa ûrĩmi."
3. CITATION: Taũra kũrĩa ũhoro ũyũ ũmoimire (mfano: "Kũringana na mwongozo wa [chanzo]...").
4. RŨRĨMĨ RŨTEITHIA: Tũmĩra rũrĩmĩ rũhũthũ. Aria ta mũrata mũgũnda-inĩ.
5. KĨHUI: Cookia na njĩra ya nukta nĩguo ûhoro ũmenyeke na mĩtũkĩ.""",
}

#  Greeting detection 
GREETINGS = {
    "sw": ["habari", "mambo", "sasa", "hujambo", "niaje", "salamu", "hey", "hi", "hello", "karibu"],
    "ki": ["wĩ mwega", "mwega", "ũhoro", "nĩatĩa", "hey", "hi"],
}

GREETING_RESPONSES = {
    "sw": [
        "Mambo sana!  Mimi ni Mkulima, msaidizi wako wa kilimo. Shamba lako liko salama? Niambie unachohitaji!",
        "Habari njema!  Karibu Shamba AI. Ninaweza kukusaidia na magonjwa ya mazao, mbolea, mifugo, na zaidi. Una swali gani leo?",
        "Poa kabisa!  Shamba lako liko vipi? Niko hapa kukusaidia na kilimo chochote.",
    ],
    "ki": [
        "Nĩ mwega sana!  Nĩ Mũrĩmi, mũteithia waku wa ûrĩmi. Mũgũnda waku ūko atĩa? Ũnjĩra ûhoro ûrĩa ûhitũkia!",
        "Wĩ mwega!  Nĩ ngwenda gũkũteithia na ûrĩmi. Ūna ûhoro ûrĩkũ ũhĩtie ũteithio ûyũ mũthenya?",
    ],
}

def is_greeting(text: str, language: str) -> bool:
    text_lower = text.lower().strip()
    greets = GREETINGS.get(language, GREETINGS["sw"])
    if len(text_lower) < 20:
        for g in greets:
            if g in text_lower:
                return True
    return False

#  PostgreSQL helpers 
def _pg_conn():
    if PG_HOST.startswith("postgresql://") or PG_HOST.startswith("postgres://"):
        return psycopg2.connect(PG_HOST)
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=PG_DB,
        sslmode=PG_SSL
    )

def get_history(session_id: str, limit: int = 20) -> list[dict]:
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT role, content FROM conversation_history
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (session_id, limit))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"role": row[0], "content": row[1]} for row in rows]
    except Exception as e:
        print(f"[DB] get_history error: {e}")
        return []

def save_message(session_id: str, role: str, content: str, language: str):
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO conversation_history (session_id, role, content, language)
            VALUES (%s, %s, %s, %s)
        """, (session_id, role, content, language))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB] save_message error: {e}")

def clear_history(session_id: str):
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM conversation_history WHERE session_id = %s", (session_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[DB] clear_history error: {e}")

#  RAG query 
def query_rag(question: str, language: str = "sw", session_id: str = "default") -> str:
    # Handle greetings
    if is_greeting(question, language):
        responses = GREETING_RESPONSES.get(language, GREETING_RESPONSES["sw"])
        answer = random.choice(responses)
        save_message(session_id, "user", question, language)
        save_message(session_id, "assistant", answer, language)
        return answer

    # Detect context
    location = detect_location(question)
    crop = detect_crop(question)
    
    context_extras = []
    if location:
        weather_info = get_weather(location)
        context_extras.append(f"Hali ya hewa {location}: {weather_info}")
    if crop:
        market_info = get_market_prices(crop)
        context_extras.append(f"Bei ya soko ya {crop}: {market_info}")

    # 1. Retrieve relevant chunks
    try:
        docs = vectorstore.similarity_search(question, k=4)
        context_parts = []
        for doc in docs:
            source = doc.metadata.get('source', 'maktaba ya kilimo')
            context_parts.append(f"[Chanzo: {source}]\n{doc.page_content}")
        context = "\n\n".join(context_parts)
    except Exception as e:
        print(f"[RAG] Vector search error: {e}")
        context = ""

    # 2. Load history
    history = get_history(session_id)

    # 3. Build messages
    system_base = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["sw"])
    if context_extras:
        extra_prompt = "\nTaarifa za ziada za hivi sasa:\n" + "\n".join(context_extras)
        system = system_base + extra_prompt
    else:
        system = system_base

    if context:
        user_message = f"MAKTABA YA KILIMO:\n{context}\n\nSWALI LA MKULIMA: {question}"
    else:
        user_message = question

    messages = history + [{"role": "user", "content": user_message}]

    # 4. Call Groq
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=1024,
            temperature=0.3
        )
        answer = response.choices[0].message.content
    except Exception as e:
        print(f"[RAG] Groq error: {e}")
        answer = "Samahani, jaribu tena."

    # Safety disclaimer
    safety_keywords = ["dawa", "pesticide", "fungicide", "mbolea", "ndawa"]
    if any(k in question.lower() for k in safety_keywords):
        answer += get_safety_disclaimer(language)

    # 5. Save
    save_message(session_id, "user", question, language)
    save_message(session_id, "assistant", answer, language)

    return answer