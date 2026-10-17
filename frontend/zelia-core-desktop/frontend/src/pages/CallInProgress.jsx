import React, { useState, useEffect, useRef, useCallback } from 'react';
import { PhoneOff, Mic, MicOff, User, CheckCircle, Clock, ChevronRight, MessageSquare, Loader, Wifi, WifiOff, Volume2, VolumeX } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { UltravoxSession } from 'ultravox-client';

/* ── Helper: elapsed timer ── */
const useTimer = () => {
    const [secs, setSecs] = useState(0);
    useEffect(() => {
        const id = setInterval(() => setSecs(s => s + 1), 1000);
        return () => clearInterval(id);
    }, []);
    const mm = String(Math.floor(secs / 60)).padStart(2, '0');
    const ss = String(secs % 60).padStart(2, '0');
    return `${mm}:${ss}`;
};

/* ── Status badge colors ── */
const STATUS_STYLE = {
    disconnected: { bg: '#fee2e2', color: '#991b1b', label: 'Disconnected' },
    connecting: { bg: '#fef3c7', color: '#92400e', label: 'Connecting...' },
    idle: { bg: '#e0f2fe', color: '#075985', label: 'Connected — Idle' },
    listening: { bg: '#dcfce7', color: '#166534', label: '🎤 Listening...' },
    thinking: { bg: '#fef3c7', color: '#92400e', label: '🧠 Thinking...' },
    speaking: { bg: '#ede9fe', color: '#5b21b6', label: '🔊 Speaking...' },
    ended: { bg: '#f1f5f9', color: '#475569', label: 'Call Ended' },
};

const parseElapsedToSeconds = (elapsed) => {
    const parts = String(elapsed || '').split(':').map((p) => Number(p));
    if (parts.length === 2 && Number.isFinite(parts[0]) && Number.isFinite(parts[1])) {
        return (parts[0] * 60) + parts[1];
    }
    if (parts.length === 1 && Number.isFinite(parts[0])) {
        return parts[0];
    }
    return 0;
};

const normalizeDocuments = (docs) => {
    if (Array.isArray(docs)) return docs.map((d) => String(d).trim()).filter(Boolean);
    if (typeof docs === 'string') return docs.split(',').map((d) => d.trim()).filter(Boolean);
    return [];
};

const buildResultFromWebhook = ({
    webhookData,
    callId,
    citizenName,
    householdHash,
    transcriptCount,
    elapsed,
}) => {
    const normalized = webhookData?.result || {};
    const raw = normalized.raw_workflow || webhookData?.n8n?.response_json || {};
    const best = normalized.best_match_scheme || {};
    const schemeName = best.scheme_name || raw.scheme_name || raw.scheme || 'No exact match found';
    const requiredDocuments = normalizeDocuments(normalized.required_documents || best.required_documents);
    const missingDocuments = normalizeDocuments(normalized.missing_required_documents);
    const storagePath = normalized.storage_path || raw.storage_path || null;
    const responseText = normalized.response_text || raw.response_text || raw.response || 'Processing complete';

    const finalHouseholdHash = normalized.household_hash || webhookData?.household_hash || householdHash || '';
    const documentFilled = Boolean(normalized.document_filled || storagePath);
    const matched = schemeName && schemeName !== 'No exact match found';

    return {
        status: documentFilled ? 'Form Ready' : (matched ? 'Scheme Matched' : 'No Match'),
        beneficiary: citizenName,
        callId,
        id: callId,
        timestamp: new Date().toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }),
        transcriptCount,
        duration: elapsed,
        householdHash: finalHouseholdHash,
        scheme: schemeName,
        requiredDocuments,
        missingRequiredDocuments: missingDocuments,
        responseText,
        storagePath,
        documentFilled,
        nextAction: normalized.next_action || (missingDocuments.length ? 'upload_missing_documents' : 'review_filled_form'),
    };
};

const CallInProgress = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const elapsed = useTimer();
    const transcriptRef = useRef(null);
    const sessionRef = useRef(null);

    // Pull joinUrl from router state
    const { joinUrl, callId, citizenName = 'Citizen', phoneNumber = '', householdHash = '' } = location.state || {};

    // State
    const [status, setStatus] = useState('disconnected');
    const [isMicMuted, setIsMicMuted] = useState(false);
    const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
    const [transcript, setTranscript] = useState([]);
    const [ending, setEnding] = useState(false);
    const [error, setError] = useState(null);

    // Connect to Ultravox via SDK
    useEffect(() => {
        if (!joinUrl) {
            setError('No joinUrl provided. Please initiate a call from the Dashboard first.');
            return;
        }

        const session = new UltravoxSession();
        sessionRef.current = session;
        setStatus('connecting');

        try {
            // joinCall returns an UltravoxSessionState object which is an EventTarget
            const callState = session.joinCall(joinUrl);

            // Listen for status changes
            callState.addEventListener('ultravoxSessionStatusChanged', () => {
                setStatus(callState.getStatus() || 'disconnected');
            });

            // Listen for transcript updates
            callState.addEventListener('ultravoxTranscriptsChanged', (e) => {
                const transcripts = e.transcripts || callState.getTranscripts();
                console.log("[Ultravox] Transcript Event Received:", transcripts);
                if (transcripts && transcripts.length > 0) {
                    const mapped = transcripts.map((t, i) => ({
                        id: i,
                        from: t.speaker === 'agent' ? 'agent' : 'user',
                        text: t.text,
                        isFinal: t.isFinal,
                        time: new Date().toTimeString().slice(0, 5),
                    }));
                    setTranscript(mapped);
                }
            });
        } catch (err) {
            console.error('Failed to join call:', err);
            setError(`Microphone error or connection failed: ${err.message || 'Unknown error'}`);
            setStatus('disconnected');
        }

        // Cleanup on unmount
        return () => {
            try {
                if (session && session.status !== 'ended' && session.status !== 'disconnected') {
                    session.leaveCall();
                }
            } catch (e) {
                console.error('Cleanup error:', e);
            }
        };
    }, [joinUrl]);

    // Auto-scroll transcript
    useEffect(() => {
        if (transcriptRef.current) {
            transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
        }
    }, [transcript]);

    // Mute/unmute mic
    const toggleMic = useCallback(() => {
        const session = sessionRef.current;
        if (!session) return;
        try {
            if (isMicMuted) {
                session.unmuteMic();
            } else {
                session.muteMic();
            }
            setIsMicMuted(!isMicMuted);
        } catch (e) {
            console.error('Mic toggle error:', e);
        }
    }, [isMicMuted]);

    // Mute/unmute speaker
    const toggleSpeaker = useCallback(() => {
        const session = sessionRef.current;
        if (!session) return;
        try {
            if (isSpeakerMuted) {
                session.unmuteSpeaker();
            } else {
                session.muteSpeaker();
            }
            setIsSpeakerMuted(!isSpeakerMuted);
        } catch (e) {
            console.error('Speaker toggle error:', e);
        }
    }, [isSpeakerMuted]);

    // End call
    const handleEndCall = useCallback(async () => {
        setEnding(true);
        const session = sessionRef.current;

        try {
            if (session) {
                session.leaveCall();
            }
        } catch (e) {
            console.error('Leave call error:', e);
        }
        const durationSecs = parseElapsedToSeconds(elapsed);

        try {
            await fetch(`http://localhost:8013/session/end/${callId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'completed', duration: durationSecs }),
            });
        } catch (e) {
            console.error('Session end update failed:', e);
        }

        let webhookData = {};
        try {
            const webhookPayload = {
                event_type: 'call_ended',
                call_id: callId,
                customer_number: phoneNumber || null,
                duration_secs: durationSecs,
                status: 'completed',
                language: 'auto',
                household_hash: householdHash || null,
                messages: transcript.map((msg) => ({
                    role: msg.from === 'agent' ? 'agent' : 'user',
                    text: msg.text || '',
                })),
                metadata: {
                    source: 'frontend_call_end',
                    citizen_name: citizenName,
                    household_hash: householdHash || null,
                },
            };

            const webhookRes = await fetch('http://localhost:8013/webhook/call-ended', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(webhookPayload),
            });
            webhookData = await webhookRes.json();
        } catch (e) {
            console.error('call-ended webhook failed:', e);
        }

        const result = buildResultFromWebhook({
            webhookData,
            callId,
            citizenName,
            householdHash,
            transcriptCount: transcript.length,
            elapsed,
        });

        navigate('/results', { state: { result } });
    }, [callId, citizenName, elapsed, navigate, transcript, phoneNumber, householdHash]);

    // Send text message to agent
    const [textMsg, setTextMsg] = useState('');
    const sendText = () => {
        if (!textMsg.trim() || !sessionRef.current) return;
        try {
            const msg = textMsg.trim();
            sessionRef.current.sendText(msg);
            
            // Explicitly add it to our frontend transcript state so it doesn't get lost
            // if the Ultravox SDK doesn't echo it back immediately.
            setTranscript(prev => [...prev, {
                id: prev.length,
                from: 'user',
                text: msg,
                isFinal: true,
                time: new Date().toTimeString().slice(0, 5),
            }]);
            
            setTextMsg('');
        } catch (e) {
            console.error('Send text error:', e);
        }
    };

    const currentStatus = STATUS_STYLE[status] || STATUS_STYLE.disconnected;

    // If no joinUrl, show error state
    if (error) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 'calc(100vh - 130px)' }}>
                <div style={{ textAlign: 'center', maxWidth: 440 }}>
                    <WifiOff size={48} color="#991b1b" style={{ marginBottom: 16 }} />
                    <h2 style={{ color: '#991b1b', fontSize: 20, fontWeight: 800, margin: '0 0 8px' }}>Connection Error</h2>
                    <p style={{ color: '#64748b', fontSize: 14, marginBottom: 24 }}>{error}</p>
                    <button onClick={() => navigate('/dashboard')}
                        style={{ padding: '10px 24px', borderRadius: 8, background: '#1e3a5f', color: 'white', border: 'none', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,2fr) 380px', gap: 20, height: 'calc(100vh - 130px)' }}>

            {/* ── LEFT: main call area ── */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

                {/* Call display area */}
                <div style={{ flex: 1, background: '#060E1F', borderRadius: 12, border: '1.5px solid #1F3358', position: 'relative', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>

                    {/* Center content based on status */}
                    <div style={{ textAlign: 'center', color: 'rgba(255,255,255,.7)' }}>
                        {status === 'connecting' ? (
                            <>
                                <Loader size={56} style={{ margin: '0 auto 16px', animation: 'spin 1.5s linear infinite' }} />
                                <div style={{ fontSize: 18, fontWeight: 700 }}>Connecting to Ultravox...</div>
                                <div style={{ fontSize: 13, marginTop: 6, opacity: 0.5 }}>Establishing voice channel</div>
                            </>
                        ) : status === 'ended' ? (
                            <>
                                <CheckCircle size={56} color="#4ade80" style={{ margin: '0 auto 16px' }} />
                                <div style={{ fontSize: 18, fontWeight: 700 }}>Call Ended</div>
                                <div style={{ fontSize: 13, marginTop: 6, opacity: 0.5 }}>Processing results...</div>
                            </>
                        ) : (
                            <>
                                {/* Animated pulse ring for active call */}
                                <div style={{ position: 'relative', width: 120, height: 120, margin: '0 auto 20px' }}>
                                    {(status === 'listening' || status === 'speaking') && (
                                        <div style={{
                                            position: 'absolute', inset: -8, borderRadius: '50%',
                                            border: `3px solid ${status === 'listening' ? '#4ade80' : '#a78bfa'}`,
                                            animation: 'pulse 1.5s ease-in-out infinite', opacity: 0.5,
                                        }} />
                                    )}
                                    <div style={{
                                        width: 120, height: 120, borderRadius: '50%',
                                        background: status === 'listening' ? 'linear-gradient(135deg, #166534, #15803d)'
                                            : status === 'speaking' ? 'linear-gradient(135deg, #5b21b6, #7c3aed)'
                                                : 'linear-gradient(135deg, #1e3a5f, #334155)',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        transition: 'background 0.5s',
                                    }}>
                                        <User size={48} color="white" />
                                    </div>
                                </div>
                                <div style={{ fontSize: 20, fontWeight: 800, color: 'white' }}>{citizenName}</div>
                                <div style={{ fontSize: 13, marginTop: 4, opacity: 0.5 }}>{phoneNumber}</div>
                            </>
                        )}
                    </div>

                    {/* REC badge */}
                    {status !== 'disconnected' && status !== 'ended' && (
                        <div style={{ position: 'absolute', top: 14, left: 14, background: 'rgba(0,0,0,.65)', color: 'white', padding: '4px 12px', borderRadius: 6, fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#E53E3E', animation: 'pulse 1.2s ease-in-out infinite' }} />
                            REC
                        </div>
                    )}

                    {/* Timer */}
                    <div style={{ position: 'absolute', top: 14, right: 14, background: 'rgba(0,0,0,.65)', color: 'white', padding: '4px 12px', borderRadius: 6, fontSize: 13, fontWeight: 700, fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Clock size={13} /> {elapsed}
                    </div>

                    {/* Status indicator */}
                    <div style={{
                        position: 'absolute', bottom: 14, left: 14,
                        background: currentStatus.bg, color: currentStatus.color,
                        padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 700,
                        display: 'flex', alignItems: 'center', gap: 6,
                    }}>
                        {status === 'connecting' ? <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} /> : <Wifi size={12} />}
                        {currentStatus.label}
                    </div>

                    {/* Call ID badge */}
                    <div style={{ position: 'absolute', bottom: 14, right: 14, background: 'rgba(13,27,51,.85)', color: 'rgba(255,255,255,.6)', padding: '6px 14px', borderRadius: 6, fontSize: 11, fontFamily: 'monospace' }}>
                        {callId ? callId.substring(0, 16) + '...' : 'N/A'}
                    </div>
                </div>

                {/* ── Controls bar ── */}
                <div className="card" style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16 }}>
                    {/* Mic toggle */}
                    <button onClick={toggleMic}
                        title={isMicMuted ? 'Unmute Mic' : 'Mute Mic'}
                        style={{
                            width: 52, height: 52, borderRadius: '50%', border: '1.5px solid var(--border)', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all .15s',
                            background: isMicMuted ? '#fee2e2' : 'var(--ink-100)',
                            color: isMicMuted ? '#991b1b' : 'var(--ink-600)',
                        }}>
                        {isMicMuted ? <MicOff size={22} /> : <Mic size={22} />}
                    </button>

                    {/* Speaker toggle */}
                    <button onClick={toggleSpeaker}
                        title={isSpeakerMuted ? 'Unmute Speaker' : 'Mute Speaker'}
                        style={{
                            width: 52, height: 52, borderRadius: '50%', border: '1.5px solid var(--border)', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all .15s',
                            background: isSpeakerMuted ? '#fee2e2' : 'var(--ink-100)',
                            color: isSpeakerMuted ? '#991b1b' : 'var(--ink-600)',
                        }}>
                        {isSpeakerMuted ? <VolumeX size={22} /> : <Volume2 size={22} />}
                    </button>

                    {/* End call */}
                    <button onClick={handleEndCall} disabled={ending || status === 'ended'}
                        style={{
                            padding: '14px 36px', borderRadius: 24, background: '#C53030', color: 'white',
                            fontWeight: 800, fontSize: 15, border: 'none', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 8,
                            opacity: ending ? .6 : 1, transition: 'all .2s', fontFamily: 'inherit',
                        }}>
                        <PhoneOff size={18} /> {ending ? 'Ending...' : 'End Call'}
                    </button>
                </div>
            </div>

            {/* ── RIGHT: Live transcript panel ── */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>

                {/* Panel header */}
                <div style={{ padding: '16px 20px', borderBottom: '1.5px solid var(--border)', background: 'var(--ink-900)' }}>
                    <div style={{ fontWeight: 800, fontSize: 14, color: 'white', display: 'flex', alignItems: 'center', gap: 8 }}>
                        <MessageSquare size={16} /> Live Transcript
                    </div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,.5)', marginTop: 4 }}>
                        {citizenName} · {phoneNumber} · {transcript.length} utterance{transcript.length !== 1 ? 's' : ''}
                    </div>
                </div>

                {/* Transcript messages */}
                <div ref={transcriptRef} style={{ flex: 1, padding: '16px 18px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {transcript.length === 0 ? (
                        <div style={{ textAlign: 'center', color: '#94a3b8', fontSize: 13, padding: '40px 0' }}>
                            <MessageSquare size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
                            <div>Waiting for conversation to begin...</div>
                            <div style={{ fontSize: 11, marginTop: 4 }}>Speak clearly into your microphone</div>
                        </div>
                    ) : transcript.map((msg) => (
                        <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.from === 'agent' ? 'flex-start' : 'flex-end' }}>
                            <div style={{
                                maxWidth: '88%', padding: '10px 14px', borderRadius: 12, fontSize: 13, lineHeight: 1.6,
                                background: msg.from === 'agent' ? '#f0f4f9' : '#1e3a5f',
                                color: msg.from === 'agent' ? '#1e293b' : 'white',
                                borderBottomLeftRadius: msg.from === 'agent' ? 3 : 12,
                                borderBottomRightRadius: msg.from === 'agent' ? 12 : 3,
                                opacity: msg.isFinal ? 1 : 0.7,
                                fontStyle: msg.isFinal ? 'normal' : 'italic',
                            }}>
                                {msg.text}
                            </div>
                            <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 3, paddingLeft: 4, paddingRight: 4 }}>
                                {msg.from === 'agent' ? '🤖 ZELIA Agent' : '👤 ' + citizenName}
                                {!msg.isFinal && ' (transcribing...)'}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Text input (send message to agent) */}
                <div style={{ padding: '12px 14px', borderTop: '1.5px solid var(--border)', background: 'white', display: 'flex', gap: 8 }}>
                    <input type="text" placeholder="Type a message to the AI agent..."
                        value={textMsg} onChange={e => setTextMsg(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && sendText()}
                        style={{ flex: 1, padding: '9px 12px', borderRadius: 8, border: '1.5px solid var(--border)', fontSize: 13, fontFamily: 'inherit', color: 'var(--ink-900)', outline: 'none' }} />
                    <button onClick={sendText}
                        style={{ padding: '9px 14px', borderRadius: 8, background: 'var(--ink-900)', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: 13, fontFamily: 'inherit' }}>
                        Send
                    </button>
                </div>
            </div>

            {/* CSS keyframes for animations */}
            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                @keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.5; } 50% { transform: scale(1.15); opacity: 0.2; } }
            `}</style>
        </div>
    );
};

export default CallInProgress;
