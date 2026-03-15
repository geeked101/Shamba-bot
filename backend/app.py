"""
app.py — Shamba AI Backend
Routes:
  GET  /                  → health check
  POST /text-query        → text → RAG answer
  POST /voice-query       → audio → STT → RAG answer
  POST /clear-history     → clear session
  GET  /history/{session} → get history
  POST /sms               → Africa's Talking SMS webhook
  POST /whatsapp          → Twilio WhatsApp webhook
"""

import os
import tempfile
import re
import random
from fastapi import FastAPI, UploadFile, File, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import whisper
from rag_pipeline import query_rag, get_history, clear_history

load_dotenv()

# ── Africa's Talking ───────────────────────────────────────────────
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY  = os.getenv("AT_API_KEY", "")
AT_SENDER   = os.getenv("AT_SENDER_ID", "SHAMBA")

sms_service = None
if AT_API_KEY:
    try:
        import africastalking
        africastalking.initialize(AT_USERNAME, AT_API_KEY)
        sms_service = africastalking.SMS
        print(f"✅ Africa's Talking SMS ready (user: {AT_USERNAME})")
    except Exception as e:
        print(f"⚠️  Africa's Talking error: {e}")
else:
    print("⚠️  AT_API_KEY not set — SMS disabled")

# ── Twilio WhatsApp ─────────────────────────────────────────────────
TWILIO_SID       = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN     = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WA_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "")  # e.g. whatsapp:+14155238886

twilio_client = None
if TWILIO_SID and TWILIO_TOKEN:
    try:
        from twilio.rest import Client as TwilioClient
        twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
        print(f"✅ Twilio WhatsApp ready ({TWILIO_WA_NUMBER})")
    except Exception as e:
        print(f"⚠️  Twilio error: {e}")
else:
    print("⚠️  Twilio not configured — WhatsApp disabled")

# ── FastAPI ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Shamba AI API",
    description="Smart Agriculture Assistant — Swahili & Kikuyu",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Whisper STT ─────────────────────────────────────────────────────
print("Loading Whisper STT model...")
stt_model = whisper.load_model("base")
print("✅ Whisper ready")


# ── Helpers ─────────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    """Detect Kikuyu vs Swahili from message content."""
    kikuyu_chars = set("ūīāēōũĩĀĒĪŌŪĨŨ")
    if any(c in kikuyu_chars for c in text):
        return "ki"
    kikuyu_words = ["nĩ", "gũkũ", "mũgũnda", "kahũa", "mbembe",
                    "nĩngũ", "ûrĩmi", "arĩmi", "mũrĩmi"]
    if any(w in text.lower() for w in kikuyu_words):
        return "ki"
    return "sw"


def truncate_sms(text: str, max_chars: int = 459) -> str:
    """Fit response into SMS limit (3 concatenated SMS = 459 chars)."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars - 20]
    last_stop = max(truncated.rfind(". "), truncated.rfind(".\n"),
                    truncated.rfind("! "), truncated.rfind("? "))
    if last_stop > 100:
        truncated = truncated[:last_stop + 1]
    return truncated + "\n[...]"


def send_sms_at(phone: str, message: str) -> bool:
    """Send SMS via Africa's Talking."""
    if not sms_service:
        print(f"[SMS] (disabled) To {phone}: {message[:60]}")
        return False
    try:
        sms_service.send(message, [phone], AT_SENDER)
        print(f"[SMS] ✅ Sent to {phone}")
        return True
    except Exception as e:
        print(f"[SMS] ❌ Error: {e}")
        return False


def send_whatsapp(to: str, message: str) -> bool:
    """Send WhatsApp message via Twilio."""
    if not twilio_client:
        print(f"[WhatsApp] (disabled) To {to}: {message[:60]}")
        return False
    try:
        # Ensure proper whatsapp: prefix
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        twilio_client.messages.create(
            from_=TWILIO_WA_NUMBER,
            to=to,
            body=message
        )
        print(f"[WhatsApp] ✅ Sent to {to}")
        return True
    except Exception as e:
        print(f"[WhatsApp] ❌ Error: {e}")
        return False


HELP_MSG = {
    "sw": (
        "🌱 *Shamba AI — Msaidizi wa Kilimo*\n\n"
        "Niulize kuhusu:\n"
        "🌽 Magonjwa ya mazao\n"
        "🌿 Mbolea na lishe\n"
        "📅 Misimu ya kupanda\n"
        "🐄 Utunzaji wa mifugo\n\n"
        "Tuma *STOP* kusimama."
    ),
    "ki": (
        "🌱 *Shamba AI — Mũteithia wa Ûrĩmi*\n\n"
        "Ûnjĩria ûhoro wa:\n"
        "🌽 Mĩrimũ ya mimea\n"
        "🌿 Mbolea na ûhoro wa tĩĩrĩ\n"
        "📅 Ihinda rĩa gũtema mbeu\n"
        "🐄 Ũhoro wa nyamũ\n\n"
        "Tũma *STOP* gũthia."
    )
}

STOP_COMMANDS  = {"stop", "quit", "end", "acha", "simama", "ondoka"}
HELP_COMMANDS  = {"help", "msaada", "ũteithio", "menu"}


# ── Core routes ──────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "bot": "Shamba AI 🌱",
        "languages": ["sw", "ki"],
        "channels": {
            "web": "✅ active",
            "sms": "✅ active" if sms_service else "⚠️  not configured",
            "whatsapp": "✅ active" if twilio_client else "⚠️  not configured",
        },
        "version": "1.0.0"
    }


@app.post("/text-query")
async def text_query(
    question: str = Form(...),
    language: str = Form(default="sw"),
    session_id: str = Form(default="default")
):
    answer = query_rag(question, language, session_id)
    return {"question": question, "answer": answer,
            "language": language, "session_id": session_id}


@app.post("/voice-query")
async def voice_query(
    audio: UploadFile = File(...),
    language: str = Form(default="sw"),
    session_id: str = Form(default="default")
):
    whisper_lang = {"sw": "sw", "ki": None}.get(language, "sw")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name
    try:
        result = stt_model.transcribe(tmp_path, language=whisper_lang)
        transcription = result["text"].strip()
    finally:
        os.unlink(tmp_path)
    answer = query_rag(transcription, language, session_id)
    return {"transcription": transcription, "answer": answer,
            "language": language, "session_id": session_id}


@app.post("/clear-history")
async def clear_session(session_id: str = Form(default="default")):
    clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/history/{session_id}")
def get_session_history(session_id: str):
    return {"session_id": session_id, "messages": get_history(session_id)}


# ── SMS Webhook (Africa's Talking) ───────────────────────────────────
@app.post("/sms")
async def sms_webhook(request: Request):
    form    = await request.form()
    sender  = form.get("from", "")
    message = form.get("text", "").strip()

    print(f"[SMS] From {sender}: {message}")
    if not message:
        return Response(content="", media_type="text/plain")

    session_id = f"sms_{sender.replace('+','').replace(' ','')}"
    language   = detect_language(message)
    msg_lower  = message.lower().strip()

    if msg_lower in STOP_COMMANDS:
        clear_history(session_id)
        reply = {"sw": "Asante! Tutaonana. 🌱", "ki": "Nĩ wega! Tigwo na Ngai. 🌱"}[language]
    elif msg_lower in HELP_COMMANDS:
        reply = HELP_MSG[language]
    else:
        try:
            answer = query_rag(message, language, session_id)
            reply  = truncate_sms(f"🌱 {answer}")
        except Exception as e:
            print(f"[SMS] RAG error: {e}")
            reply = {"sw": "Samahani, jaribu tena.", "ki": "Ngũngũrũka, ûgerie rĩngĩ."}[language]

    send_sms_at(sender, reply)
    return Response(content="", media_type="text/plain")


# ── WhatsApp Webhook (Twilio) ────────────────────────────────────────
@app.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio sends form data:
      From: whatsapp:+254712345678
      Body: farmer's message
      NumMedia: number of images (0 or more)
      MediaUrl0: image URL if sent
    """
    form      = await request.form()
    sender    = form.get("From", "")       # e.g. whatsapp:+254712345678
    message   = form.get("Body", "").strip()
    num_media = int(form.get("NumMedia", 0))
    media_url = form.get("MediaUrl0", "")  # image if sent

    print(f"[WhatsApp] From {sender}: {message[:80]}")

    if not message and num_media == 0:
        return Response(content="", media_type="text/xml")

    # Session ID from phone number
    phone      = sender.replace("whatsapp:", "").replace("+", "").replace(" ", "")
    session_id = f"wa_{phone}"
    language   = detect_language(message)
    msg_lower  = message.lower().strip()

    # Handle image (future: plant disease photo diagnosis)
    if num_media > 0 and media_url:
        reply = (
            "📸 Nimepokea picha yako!\n\n"
            "Kwa sasa, niambie kwa maneno dalili unazoziona — "
            "mfano: 'majani yana madoa ya njano' au 'matunda yanaoza'.\n\n"
            "Tunaendelea kuongeza uwezo wa kutambua magonjwa kutoka picha. 🌱"
            if language == "sw" else
            "📸 Nĩndĩkeire itũi yaku!\n\n"
            "Rĩu ûnjĩra kwa mawĩra mĩambirĩria ûrĩa ûonaga — "
            "ta: 'majani marĩ na madoa ma njano'.\n\n"
            "Nĩtũgaathuranĩria gũtambũra mĩrimũ kũuma itũi. 🌱"
        )
        send_whatsapp(sender, reply)
        return Response(content="", media_type="text/xml")

    # Commands
    if msg_lower in STOP_COMMANDS:
        clear_history(session_id)
        reply = {"sw": "Asante kwa kutumia Shamba AI! Tutaonana. 🌱",
                 "ki": "Nĩ wega mũno! Tigwo na Ngai. 🌱"}[language]

    elif msg_lower in HELP_COMMANDS:
        reply = HELP_MSG[language]

    else:
        try:
            answer = query_rag(message, language, session_id)
            reply  = f"🌱 {answer}"
        except Exception as e:
            print(f"[WhatsApp] RAG error: {e}")
            reply = {
                "sw": "Samahani, kuna tatizo kidogo. Jaribu tena. 🙏",
                "ki": "Ngũngũrũka, harĩa ûguo. Ûgerie rĩngĩ. 🙏"
            }[language]

    send_whatsapp(sender, reply)

    # Twilio expects TwiML response (empty is fine)
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="text/xml"
    )


# ── WhatsApp test endpoint ───────────────────────────────────────────
@app.post("/whatsapp/send")
async def whatsapp_send_manual(
    phone: str   = Form(...),   # e.g. +254712345678
    message: str = Form(...)
):
    """Manually send a WhatsApp message — for testing."""
    to      = f"whatsapp:{phone}" if not phone.startswith("whatsapp:") else phone
    success = send_whatsapp(to, message)
    return {"success": success, "to": to, "message": message}