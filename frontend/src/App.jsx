import { useState, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import BotAvatar from "./components/BotAvatar";
import ChatBox from "./components/ChatBox";
import VoiceInput from "./components/VoiceInput";
import TopicQuickSelect from "./components/TopicQuickSelect";
import axios from "axios";
import "./App.css"; // Premium Styles

const API_BASE_URL = process.env.REACT_APP_API_URL || "";

export default function App() {
    const [language, setLanguage] = useState("sw");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);
    const [sessionId] = useState(() => uuidv4());

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

            const res = await axios.post(`${API_BASE_URL}/text-query`, formData);
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
        await axios.post(`${API_BASE_URL}/clear-history`, formData);
        const greetings = {
            sw: "Mazungumzo yameanzishwa upya. Ninaweza kukusaidia na nini?",
            ki: "Maũndũ mautharathaitwo. Nĩngũkũteithia na kĩ?"
        };
        setMessages([{ role: "assistant", content: greetings[language], timestamp: new Date() }]);
    };

    return (
        <div className="app-container">
            {/* Header */}
            <header className="header">
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <BotAvatar language={language} />
                    <h1 style={{ color: "white", fontSize: "1.25rem", margin: 0, fontWeight: 700 }}>Shamba AI</h1>
                </div>

                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                    {["sw", "ki"].map(lang => (
                        <button
                            key={lang}
                            onClick={() => setLanguage(lang)}
                            className={`lang-btn ${language === lang ? 'active' : ''}`}
                        >
                            {lang === "sw" ? "Swahili" : "Kikuyu"}
                        </button>
                    ))}

                    <button onClick={handleClearChat} className="lang-btn" style={{ fontSize: '0.8rem', opacity: 0.8 }}>
                        {language === "sw" ? "Anza Upya" : "Anza Rĩngĩ"}
                    </button>
                </div>
            </header>

            {/* Main Chat Area */}
            <main className="chat-wrapper">
                <div className="glass-card" style={{ flex: 1, padding: "1rem" }}>
                    {/* Quick Topic Buttons */}
                    <TopicQuickSelect language={language} onSelect={sendMessage} />

                    {/* Chat Messages */}
                    <ChatBox messages={messages} loading={loading} language={language} />
                </div>

                {/* Voice + Text Input - Fixed at bottom of wrapper */}
                <div className="glass-card" style={{ padding: "10px" }}>
                    <VoiceInput
                        language={language}
                        onSend={sendMessage}
                        onVoiceResult={handleVoiceResult}
                        loading={loading}
                        sessionId={sessionId}
                    />
                </div>
                
                <footer style={{ textAlign: 'center', fontSize: '0.8rem', color: '#94a3b8', padding: '1rem' }}>
                    © 2026 Shamba Bot — Verified Agricultural Advice
                </footer>
            </main>
        </div>
    );
}
