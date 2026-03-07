export default function BotAvatar({ language }) {
  const name = language === "ki" ? "Mũrĩmi" : "Mkulima";
  const tagline = language === "ki"
    ? "Mũteithia wa Ûrĩmi wa AI"
    : "Msaidizi wa Kilimo wa AI";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{
        width: 44,
        height: 44,
        borderRadius: "50%",
        background: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        boxShadow: "0 2px 6px rgba(0,0,0,0.2)"
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2C6.5 2 3 7 3 12c0 3.5 2 6.5 5 8l1-2c-2-1.5-3-4-3-6 0-3.5 2.5-7 6-7s6 3.5 6 7c0 2-1 4.5-3 6l1 2c3-1.5 5-4.5 5-8 0-5-3.5-10-9-10z" fill="#2d7a3a" />
          <line x1="12" y1="12" x2="12" y2="22" stroke="#2d7a3a" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </div>
      <div>
        <div style={{ color: "#fff", fontWeight: "bold", fontSize: 18 }}>
          Shamba AI — {name}
        </div>
        <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 12 }}>
          {tagline}
        </div>
      </div>
    </div>
  );
}
