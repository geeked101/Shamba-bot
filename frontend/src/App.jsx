import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import BotAvatar from "./components/BotAvatar";
import ChatBox from "./components/ChatBox";
import VoiceInput from "./components/VoiceInput";
import TopicQuickSelect from "./components/TopicQuickSelect";
import axios from "axios";

const COLORS = {
    green: "#2d7a3a",
    lightGreen: "#e8f5e9",
    white: "#ffffff",
    gray: "#f5f5f5",
    textDark: "#1a1a1a",
    textMid: "#555",
};

export default function App() {
    const [language, setLanguage] = useState("sw");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [sessionId] = useState(() => uuidv4()); // unique per browser session

    // Greeting message on load
    useEffect(() => {
        const greetings = {
            sw: "Habari! Mimi ni Mkulima, Msaidizi wako wa kilimo. Ninaweza kukusaidia na magonjwa ya mazao, mbolea, misimu ya kupanda, na utunzaji wa mifugo. Unahitaji msaada gani leo?",
            ki: "Wĩ mwega! Nĩ Mũrĩmi, Mũteithia waku wa ûrĩmi. Nĩngũkũteithia na mirimu ya mimea, mbolea, ihinda rĩa gũtema mbeu, na ũhoro wa nyamũ. Ûhoro ûrĩkũ ûrĩa ûkũhoya ũteithio?"
        };
        setMessages([{
            role: "assistant",
            content: greetings[language],
            timestamp: new Date()
        }]);
    }, [language]);

    const sendMessage = async (text) => {
        if (!text.trim()) return;

        const userMsg = { role: "user", content: text, timestamp: new Date() };
        setMessages(prev => [...prev, userMsg]);
        setLoading(true);

        try {
            const formData = new FormData();
            formData.append("question", text);
            formData.append("language", language);
            formData.append("session_id", sessionId);

            const res = await axios.post("/text-query", formData);
            setMessages(prev => [...prev, {
                role: "assistant",
                content: res.data.answer,
                timestamp: new Date()
            }]);
        } catch (err) {
            setMessages(prev => [...prev, {
                role: "assistant",
                content: language === "sw"
                    ? "Samahani, kuna hitilafu ya mfumo. Jaribu tena."
                    : "Ngũngũrũka, harĩa kĩndũ gĩakĩrwo. Ũgerie rĩngĩ.",
                timestamp: new Date(),
                isError: true
            }]);
        } finally {
            setLoading(false);
        }
    };

    const handleVoiceResult = (transcription) => {
        sendMessage(transcription);
    };

    const handleClearChat = async () => {
        const formData = new FormData();
        formData.append("session_id", sessionId);
        await axios.post("/clear-history", formData);
        const greetings = {
            sw: "Mazungumzo yameanzishwa upya. Ninaweza kukusaidia na nini?",
            ki: "Maũndũ mautharathaitwo. Nĩngũkũteithia na kĩ?"
        };
        setMessages([{ role: "assistant", content: greetings[language], timestamp: new Date() }]);
    };

    return (
        <div style={{
            minHeight: "100vh",
            background: COLORS.gray,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            fontFamily: "'Segoe UI', sans-serif"
        }}>
            {/* Header */}
            <div style={{
                width: "100%",
                background: COLORS.green,
                padding: "12px 24px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                boxShadow: "0 2px 8px rgba(0,0,0,0.2)"
            }}>
                <BotAvatar language={language} />

                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    {/* Language Toggle */}
                    {["sw", "ki"].map(lang => (
                        <button
                            key={lang}
                            onClick={() => setLanguage(lang)}
                            style={{
                                padding: "6px 14px",
                                background: language === lang ? "#fff" : "transparent",
                                color: language === lang ? COLORS.green : "#fff",
                                border: "2px solid #fff",
                                borderRadius: 20,
                                cursor: "pointer",
                                fontWeight: "bold",
                                fontSize: 13
                            }}
                        >
                            {lang === "sw" ? "Swahili" : "Kikuyu"}
                        </button>
                    ))}

                    {/* Clear Chat */}
                    <button
                        onClick={handleClearChat}
                        style={{
                            padding: "6px 12px",
                            background: "transparent",
                            color: "#fff",
                            border: "1px solid rgba(255,255,255,0.5)",
                            borderRadius: 20,
                            cursor: "pointer",
                            fontSize: 12
                        }}
                    >
                        {language === "sw" ? "Anza Upya" : "Anza Rĩngĩ"}
                    </button>
                </div>
            </div>

            {/* Main Chat Area */}
            <div style={{
                width: "100%",
                maxWidth: 700,
                flex: 1,
                display: "flex",
                flexDirection: "column",
                padding: "0 16px"
            }}>

                {/* Quick Topic Buttons */}
                <TopicQuickSelect language={language} onSelect={sendMessage} />

                {/* Chat Messages */}
                <ChatBox messages={messages} loading={loading} language={language} />

                {/* Voice + Text Input */}
                <VoiceInput
                    language={language}
                    onSend={sendMessage}
                    onVoiceResult={handleVoiceResult}
                    loading={loading}
                    sessionId={sessionId}
                />
            </div>
        </div>
    );
}
