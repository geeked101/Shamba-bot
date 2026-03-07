import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function ChatBox({ messages, loading, language }) {
  const bottomRef = useRef(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div style={{
      flex: 1,
      overflowY: "auto",
      padding: "16px 0",
      minHeight: 300,
      maxHeight: "60vh"
    }}>
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center" }}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.5 2 3 7 3 12c0 3.5 2 6.5 5 8l1-2c-2-1.5-3-4-3-6 0-3.5 2.5-7 6-7s6 3.5 6 7c0 2-1 4.5-3 6l1 2c3-1.5 5-4.5 5-8 0-5-3.5-10-9-10z" fill="#2d7a3a" />
              <line x1="12" y1="12" x2="12" y2="22" stroke="#2d7a3a" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <div style={{
            padding: "12px 16px",
            background: "#fff",
            borderRadius: "18px 18px 18px 4px",
            boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
            color: "#888",
            fontSize: 15
          }}>
            <span style={{ animation: "pulse 1s infinite" }}>
              {language === "ki" ? "Nĩfikĩria..." : "Inafikiri..."}
            </span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
