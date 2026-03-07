"""
rag_pipeline.py

Core RAG logic using:
  - Groq (llama-3.3-70b) as the LLM
  - HuggingFace API for embeddings
  - ChromaDB for vector search
  - PostgreSQL for persistent conversation history
"""

import os
import psycopg2
import chromadb
from groq import Groq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from dotenv import load_dotenv

load_dotenv()

#  Config 
CHROMA_HOST     = os.getenv("CHROMA_HOST", "chromadb")
CHROMA_PORT     = int(os.getenv("CHROMA_PORT", 8000))
CHROMA_DIR      = "/app/chroma_data"
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "shamba_rag")

PG_HOST         = os.getenv("POSTGRES_HOST", "postgres")
PG_PORT         = os.getenv("POSTGRES_PORT", "5432")
PG_USER         = os.getenv("POSTGRES_USER", "postgres")
PG_PASSWORD     = os.getenv("POSTGRES_PASSWORD", "password")
PG_DB           = os.getenv("POSTGRES_DB", "shambadb")

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

vectorstore = Chroma(
    persist_directory=CHROMA_DIR,
    embedding_function=embeddings,
    collection_name=COLLECTION_NAME,
    client=chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
)

#  System prompts 
SYSTEM_PROMPTS = {
    "sw": """Wewe ni Mkulima  — msaidizi wa kilimo wa AI kwa wakulima wa Kenya.
Unajibu kwa Kiswahili tu, kwa lugha rahisi inayoeleweka.

UTU WAKO:
- Una moyo wa huruma na urafiki — kama jirani anayesaidia
- Unasalimia vizuri na kujibu mazungumzo ya kawaida
- Unajua mambo mengi lakini mada yako kuu ni kilimo

UNASAIDIA NA:
- Magonjwa ya mazao (mahindi, kahawa, chai, nyanya, viazi, n.k.)
- Mbolea na lishe ya udongo
- Misimu ya kupanda kwa kanda mbalimbali za Kenya
- Utunzaji wa mifugo (ng'ombe, mbuzi, kuku)
- Mazao ya biashara (kahawa, chai)
- Hali ya hewa na kilimo

JINSI YA KUJIBU:
- Salimia kwa urafiki ukisalimiwa ("Mambo" → "Poa sana! Habari za shamba?")
- Tumia muktadha uliotolewa kama una taarifa husika
- Kama swali lipo nje ya kilimo, jibu kwa ufupi kisha urejee kilimo
- Kama huna jibu sahihi: "Sina taarifa za kutosha. Wasiliana na afisa wa kilimo."
- Jibu kwa ufupi lakini kamili — pointi 3-5 ni bora kwa SMS na mazungumzo""",

    "ki": """Wee uri Mũrĩmi  — mũteithia wa ûrĩmi wa AI ũteithagĩria arĩmi a Kenya.
Ũrĩa na Gĩkũyũ gũkũ, kwa rũrĩmĩ rũũgĩ.

ŪHO WAKU:
- Ūna ngoro ya ũrĩa na ũrata — ta mũirĩtu ũteithagĩria
- Ūcookia mĩambirĩria mĩega na kũũrĩria ûhoro wa kawaida
- Ūĩ na ûhoro mũingi no mada yaku nĩ ûrĩmi

ŨTEITHAGĨRIA NA:
- Mĩrimũ ya mimea (mbembe, kahũa, chai, nyanya, ngwaci, na ingĩ)
- Mbolea na ûhoro wa tĩĩrĩ
- Ihinda rĩa gũtema mbeu kwa itũra itũndũ cia Kenya
- Ũhoro wa nyamũ (ng'ombe, mbuzi, ngũkũ)
- Mazao ya kũũzĩa (kahũa, chai)

NĨATĨA ŨRĨAGA:
- Cookia mĩambirĩria mĩega ûsalimiagwo ("Mambo" → "Nĩ mwega! Ûhoro wa mũgũnda?")
- Tumia muktadha ûrĩa ûtũmĩire kama ūna ûhoro ũũgĩ
- Kama ûtarĩ na ûhoro: "Ndĩrathime ûhoro ûyũ. Hoya afisa wa ûrĩmi."
- Cookia na ngoro nini no ûhoro mũno — pointi ĩtatũ na ĩnya nĩ njega""",
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

import random

def is_greeting(text: str, language: str) -> bool:
    text_lower = text.lower().strip()
    greets = GREETINGS.get(language, GREETINGS["sw"])
    # Check if the entire message is just a greeting
    if len(text_lower) < 20:
        for g in greets:
            if g in text_lower:
                return True
    return False


#  PostgreSQL helpers 
def _pg_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=PG_DB
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

    # Handle greetings immediately without hitting RAG
    if is_greeting(question, language):
        responses = GREETING_RESPONSES.get(language, GREETING_RESPONSES["sw"])
        answer = random.choice(responses)
        save_message(session_id, "user", question, language)
        save_message(session_id, "assistant", answer, language)
        return answer

    # 1. Retrieve relevant chunks from ChromaDB
    try:
        docs = vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([
            f"[{doc.metadata.get('topic', 'kilimo')}]\n{doc.page_content}"
            for doc in docs
        ]) if docs else ""
    except Exception as e:
        print(f"[RAG] Vector search error: {e}")
        context = ""

    # 2. Load conversation history from PostgreSQL
    history = get_history(session_id)

    # 3. Build messages
    system = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["sw"])

    if context:
        user_message = f"Taarifa kutoka maktaba ya kilimo:\n{context}\n\nSwali la mkulima: {question}"
    else:
        user_message = question

    messages = history + [{"role": "user", "content": user_message}]

    # 4. Call Groq with error handling
    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=1024,
            temperature=0.4
        )
        answer = response.choices[0].message.content

    except Exception as e:
        print(f"[RAG] Groq error: {e}")
        answer = {
            "sw": "Samahani, seva yangu ina tatizo kidogo sasa hivi. Tafadhali jaribu tena baada ya dakika moja. ",
            "ki": "Ngũngũrũka, seva nĩĩna ûguo mũnini. Ûgerie rĩngĩ thutha wa dakika imwe. "
        }.get(language, "Samahani, jaribu tena.")

    # 5. Save to PostgreSQL
    save_message(session_id, "user", question, language)
    save_message(session_id, "assistant", answer, language)

    return answer