import { useState, useRef } from "react";
import axios from "axios";

export default function VoiceInput({ language, onSend, onVoiceResult, loading, sessionId }) {
  const [text, setText] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const mimeType = useRef("audio/webm");

  const placeholder = {
    sw: "Andika swali lako hapa...",
    ki: "Ûndĩke ûũria waku haha..."
  }[language];

  const handleSend = () => {
    if (!text.trim() || loading) return;
    onSend(text);
    setText("");
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Pick a MIME type the browser actually supports
      const supportedType = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/ogg;codecs=opus",
        "audio/ogg",
        "audio/mp4",
      ].find((t) => MediaRecorder.isTypeSupported(t)) || "";

      mimeType.current = supportedType || "audio/webm";
      mediaRecorder.current = new MediaRecorder(stream, supportedType ? { mimeType: supportedType } : {});
      audioChunks.current = [];

      mediaRecorder.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.current.push(e.data);
      };

      mediaRecorder.current.onstop = async () => {
        // Stop all tracks so the mic indicator goes away
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(audioChunks.current, { type: mimeType.current });
        // Derive extension from mime type for backend clarity
        const ext = mimeType.current.includes("ogg") ? "ogg" : mimeType.current.includes("mp4") ? "m4a" : "webm";
        const formData = new FormData();
        formData.append("audio", blob, `recording.${ext}`);
        formData.append("language", language);
        formData.append("session_id", sessionId);

        setTranscribing(true);
        try {
          const res = await axios.post("/voice-query", formData);
          const transcription = res.data.transcription || "";
          if (transcription) {
            // Populate text field so user can review/edit before sending
            setText(transcription);
            onVoiceResult(transcription);
          } else {
            alert(language === "sw" ? "Sauti haikutambuliwa. Jaribu tena." : "Sauti itarathimwa rĩngĩ.");
          }
        } catch (err) {
          console.error("Voice query failed:", err);
          alert(language === "sw" ? "Hitilafu ya sauti. Jaribu tena." : "Kĩndũ gĩakĩrwo na sauti.");
        } finally {
          setTranscribing(false);
        }
      };

      // Request data every 250ms so we always get chunks
      mediaRecorder.current.start(250);
      setRecording(true);
    } catch (err) {
      console.error("Mic error:", err);
      alert("Microphone access denied. Please enable mic permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      mediaRecorder.current.stop();
    }
    setRecording(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", padding: "12px 0 20px", gap: 6 }}>
      {transcribing && (
        <div style={{ fontSize: 12, color: "#888", textAlign: "center", paddingBottom: 4 }}>
          {language === "sw" ? "Inabadilisha sauti..." : "Nĩkũhindura sauti..."}
        </div>
      )}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {/* Mic Button */}
        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          disabled={loading || transcribing}
          title="Hold to speak"
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: recording ? "#e53e3e" : "#2d7a3a",
            border: "none",
            color: "#fff",
            fontSize: 20,
            cursor: "pointer",
            flexShrink: 0,
            boxShadow: recording ? "0 0 0 4px rgba(229,62,62,0.3)" : "none",
            transition: "all 0.2s"
          }}
        >
          {recording ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <rect x="4" y="4" width="16" height="16" rx="2" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
              <rect x="9" y="2" width="6" height="12" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />
              <line x1="12" y1="17" x2="12" y2="21" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="9" y1="21" x2="15" y2="21" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
        </button>

        {/* Text Input */}
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder={recording ? (language === "sw" ? "Sikiliza..." : "Nĩkũigua...") : placeholder}
          disabled={loading || recording || transcribing}
          style={{
            flex: 1,
            padding: "12px 16px",
            borderRadius: 24,
            border: "1px solid #ccc",
            fontSize: 15,
            outline: "none",
            background: recording ? "#fff8f8" : "#fff"
          }}
        />

        {/* Send Button */}
        <button
          onClick={handleSend}
          disabled={!text.trim() || loading || transcribing}
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: text.trim() && !loading && !transcribing ? "#2d7a3a" : "#ccc",
            border: "none",
            color: "#fff",
            fontSize: 20,
            cursor: text.trim() && !loading && !transcribing ? "pointer" : "default",
            flexShrink: 0
          }}
        >
          
        </button>
      </div>
    </div>
  );
}
