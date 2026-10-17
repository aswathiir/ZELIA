import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, Activity } from 'lucide-react';

const ZeliaCopilot = () => {
    // Chatbot State
    const [chatMessages, setChatMessages] = useState([
        { role: 'assistant', text: 'Namaskar! I am ZELIA, your Official Scheme Eligibility Guide. How can I assist you today?' }
    ]);
    const [chatInput, setChatInput] = useState('');
    const [isThinking, setIsThinking] = useState(false);
    const chatEndRef = useRef(null);

    // Scroll chat to bottom
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages]);

    // Handle Chat Submission natively
    const handleChatSubmit = async (e) => {
        e.preventDefault();
        if (!chatInput.trim()) return;

        const userMsg = chatInput;
        setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setChatInput('');
        setIsThinking(true);

        try {
            // N8N Webhook Chat Trigger inherently expects strict JSON
            // wrapping the payload with action, sessionId, and chatInput elements.
            const payload = { chatInput: userMsg };
            const response = await fetch('http://localhost:8017/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const data = await response.json();
                setChatMessages(prev => [...prev, { role: 'assistant', text: data.output || "I'm sorry, I couldn't process that response." }]);
            } else {
                setChatMessages(prev => [...prev, { role: 'assistant', text: "Error connecting to the ZELIA RAG Knowledgebase." }]);
            }
        } catch (error) {
            console.error("Chat error:", error);
            setChatMessages(prev => [...prev, { role: 'assistant', text: "Network Error: Could not reach the Assistant." }]);
        } finally {
            setIsThinking(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, height: '100%' }}>
            {/* The Copilot Chat Window */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'white', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
                <div style={{ flex: 1, padding: 16, overflowY: 'auto', background: 'var(--ink-50)', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {chatMessages.map((msg, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                            <div style={{
                                maxWidth: '88%',
                                padding: '10px 14px',
                                borderRadius: 12,
                                fontSize: 13,
                                lineHeight: 1.4,
                                background: msg.role === 'user' ? 'var(--ms-navy-dark)' : 'white',
                                color: msg.role === 'user' ? 'white' : 'var(--ink-900)',
                                border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
                                borderBottomRightRadius: msg.role === 'user' ? 2 : 12,
                                borderBottomLeftRadius: msg.role === 'assistant' ? 2 : 12,
                                boxShadow: '0 2px 5px rgba(0,0,0,0.02)'
                            }}>
                                {msg.text}
                            </div>
                        </div>
                    ))}
                    {isThinking && (
                        <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                            <div style={{ background: 'white', border: '1px solid var(--border)', padding: '10px 14px', borderRadius: 12, borderBottomLeftRadius: 2, fontSize: 13, color: 'var(--ink-500)', fontStyle: 'italic' }}>
                                ZELIA is retrieving guidelines...
                            </div>
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>
                {/* Chat Input Area */}
                <form onSubmit={handleChatSubmit} style={{ padding: '12px', borderTop: '1px solid var(--border)', background: 'white', display: 'flex', gap: 8 }}>
                    <input
                        type="text"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        placeholder="Type a policy query..."
                        style={{ flex: 1, background: 'var(--ink-50)', border: '1px solid var(--border)', borderRadius: 20, padding: '10px 14px', fontSize: 13, outline: 'none' }}
                        disabled={isThinking}
                    />
                    <button type="submit" disabled={!chatInput.trim() || isThinking} style={{ background: chatInput.trim() ? 'var(--ms-green-primary)' : 'var(--ink-200)', color: 'white', border: 'none', borderRadius: '50%', width: 38, height: 38, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: chatInput.trim() ? 'pointer' : 'default', transition: 'background 0.2s' }}>
                        <Send size={16} />
                    </button>
                </form>
            </div>

            {/* Status Monitor Hooked inside Utility Panel */}
            <div>
                <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--ink-400)', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 }}>System Automation Status</div>
                <div style={{ background: 'white', border: '1px solid var(--border)', borderRadius: 8, padding: 14 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                        <Activity size={16} color="var(--ms-green-primary)" />
                        <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--ink-800)' }}>N8N Workflow Core</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                        <span style={{ color: 'var(--ink-500)', fontWeight: 600 }}>Connection:</span>
                        <span style={{ color: 'var(--ms-green-primary)', fontWeight: 800 }}>RAG Webhook Active</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                        <span style={{ color: 'var(--ink-500)', fontWeight: 600 }}>Telemetry:</span>
                        <span style={{ color: 'var(--ink-700)', fontWeight: 700 }}>~42ms Latency</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ZeliaCopilot;
