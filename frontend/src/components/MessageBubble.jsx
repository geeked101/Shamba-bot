export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: 12
    }}>
      {!isUser && (
        <div style={{ marginRight: 8, alignSelf: "flex-end", display: "flex", alignItems: "center" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.5 2 3 7 3 12c0 3.5 2 6.5 5 8l1-2c-2-1.5-3-4-3-6 0-3.5 2.5-7 6-7s6 3.5 6 7c0 2-1 4.5-3 6l1 2c3-1.5 5-4.5 5-8 0-5-3.5-10-9-10z" fill="#2d7a3a" />
            <line x1="12" y1="12" x2="12" y2="22" stroke="#2d7a3a" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
      )}

      <div style={{
        maxWidth: "75%",
        padding: "12px 16px",
        borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
        background: isUser ? "#2d7a3a" : "#fff",
        color: isUser ? "#fff" : "#1a1a1a",
        boxShadow: "0 1px 4px rgba(0,0,0,0.1)",
        lineHeight: 1.6,
        fontSize: 15,
        border: message.isError ? "1px solid #e53e3e" : "none"
      }}>
        {message.content}
        <div style={{
          fontSize: 10,
          marginTop: 4,
          color: isUser ? "rgba(255,255,255,0.6)" : "#aaa",
          textAlign: "right"
        }}>
          {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>

      {isUser && (
        <div style={{ marginLeft: 8, alignSelf: "flex-end", display: "flex", alignItems: "center" }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="12" cy="8" r="4" fill="#2d7a3a" />
            <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" fill="#2d7a3a" />
          </svg>
        </div>
      )}
    </div>
  );
}
