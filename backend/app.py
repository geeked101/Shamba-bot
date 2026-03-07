"""
app.py

FastAPI entry point for Shamba AI backend.

Routes:
  GET  /                  → health check
  POST /text-query        → text question → RAG answer
  POST /voice-query       → audio file → STT → RAG answer
  POST /clear-history     → clear conversation memory for a session
  GET  /history/{session} → get conversation history
"""

import os
import tempfile
import uuid
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import whisper
from rag_pipeline import query_rag, get_history, clear_history

load_dotenv()

app = FastAPI(
    title="Shamba AI API",
    description="Smart Agriculture Assistant in Kikuyu & Swahili",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Load Whisper STT model at startup
# Use "base" for speed during hackathon, "large-v3" for best accuracy
print("Loading Whisper STT model...")
stt_model = whisper.load_model("base")
print("Whisper ready.")


@app.get("/")
def root():
    return {
        "status": "running",
        "bot": "Shamba AI - Mkulima",
        "languages": ["sw", "ki"],
        "version": "1.0.0"
    }


@app.post("/text-query")
async def text_query(
    question: str = Form(...),
    language: str = Form(default="sw"),
    session_id: str = Form(default="default")
):
    """Accept a text question and return a RAG-powered answer."""
    answer = query_rag(question, language, session_id)
    return {
        "question": question,
        "answer": answer,
        "language": language,
        "session_id": session_id
    }


@app.post("/voice-query")
async def voice_query(
    audio: UploadFile = File(...),
    language: str = Form(default="sw"),
    session_id: str = Form(default="default")
):
    """Accept an audio file, transcribe it, then return a RAG-powered answer."""

    # Map language code to Whisper language code
    whisper_lang = {"sw": "sw", "ki": None}.get(language, "sw")
    # Kikuyu: Whisper doesn't support it natively, fall back to auto-detect

    # Save audio temporarily
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        # Transcribe
        result = stt_model.transcribe(tmp_path, language=whisper_lang)
        transcription = result["text"].strip()
    finally:
        os.unlink(tmp_path)

    # RAG answer
    answer = query_rag(transcription, language, session_id)

    return {
        "transcription": transcription,
        "answer": answer,
        "language": language,
        "session_id": session_id
    }


@app.post("/clear-history")
async def clear_session_history(session_id: str = Form(default="default")):
    """Clear conversation memory for a session."""
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    """Return conversation history for a session."""
    return {
        "session_id": session_id,
        "messages": get_history(session_id)
    }
