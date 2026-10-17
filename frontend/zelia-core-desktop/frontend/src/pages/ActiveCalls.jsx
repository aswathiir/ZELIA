import React, { useState, useEffect } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Volume2, Clock, Video, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ActiveCalls = () => {
    const navigate = useNavigate();
    const [muted, setMuted] = useState({});
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);

    const toggleMute = (id) => setMuted(m => ({ ...m, [id]: !m[id] }));

    useEffect(() => {
        let ws;
        let pollTimer;

        const mapCalls = (data) => {
            return (data || []).map(c => {
                const meta = typeof c.metadata === 'string' ? JSON.parse(c.metadata || '{}') : (c.metadata || {});
                const rawDuration = Number(c.duration_secs || meta.duration || 0);
                return {
                    id: c.call_id,
                    beneficiary: meta.name || 'Anonymous Citizen',
                    scheme: meta.reason || 'General Assistance',
                    schemeName: meta.reason || 'General',
                    duration: rawDuration > 0
                        ? `${Math.floor(rawDuration / 60).toString().padStart(2, '0')}:${(rawDuration % 60).toString().padStart(2, '0')}`
                        : 'Live',
                    status: (c.status === 'completed' || c.status === 'ended') ? 'completed' : 'active',
                    language: meta.language || 'English/Hindi',
                    householdHash: meta.household_hash || 'N/A',
                    joinUrl: meta.joinUrl || meta.join_url || null,
                    phoneNumber: c.phone_number || meta.phone_number || null,
                };
            });
        };

        const fetchCalls = async () => {
            try {
                const res = await fetch('http://localhost:8013/calls');
                if (res.ok) {
                    const data = await res.json();
                    setCalls(mapCalls(data));
                } else {
                    console.error("Failed to load active calls.");
                }
            } catch (err) {
                console.error("Network error fetching active calls.", err);
            } finally {
                setLoading(false);
            }
        };

        const openWs = () => {
            try {
                ws = new WebSocket('ws://localhost:8013/ws/calls');
                ws.onmessage = () => {
                    // Keep source-of-truth from API to avoid client-side drift.
                    fetchCalls();
                };
                ws.onerror = (e) => {
                    // fallback polling handles resilience, log quietly
                    console.warn('WS connection failing, falling back to polling.', e);
                };
            } catch (e) {
                console.warn('WS initialization failed', e);
            }
        };

        fetchCalls();
        openWs();
        pollTimer = window.setInterval(fetchCalls, 15000);

        return () => {
            if (pollTimer) window.clearInterval(pollTimer);
            if (ws && ws.readyState === WebSocket.OPEN) ws.close();
        };
    }, []);

    return (
        <div>
            <div style={{ marginBottom: 24, paddingBottom: 16, borderBottom: '3px solid var(--ms-green-primary)' }}>
                <h1 className="page-title" style={{ color: 'var(--ms-navy-dark)' }}>Call Center Telemetry</h1>
                <p className="page-subtitle">Real-time ZELIA Voice Assistant sessions</p>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ink-500)', fontSize: 14 }}>
                    Synchronizing Telemetry Feed...
                </div>
            ) : calls.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ink-500)', fontSize: 14 }}>
                    <AlertCircle size={32} color="var(--ink-300)" style={{ marginBottom: 10 }} />
                    <div>No active WebRTC bridges found in the network.</div>
                </div>
            ) : (
                <>
                    {/* Summary */}
                    <div style={{ display: 'flex', gap: 12, marginBottom: 26 }}>
                        {[
                            [calls.filter(c => c.status === 'active').length, 'Active Streams'],
                            [calls.filter(c => c.status === 'on-hold').length, 'On-Hold'],
                            [calls.length, 'Total Bridged'],
                        ].map(([n, label]) => (
                            <div key={label} className="stat-card" style={{ flex: 1, borderColor: 'var(--border-dark)' }}>
                                <div style={{ width: 42, height: 42, borderRadius: 10, background: 'var(--ink-100)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <Phone size={20} color="var(--ms-navy-dark)" />
                                </div>
                                <div>
                                    <div style={{ fontSize: 24, fontWeight: 800, color: 'var(--ink-900)' }}>{n}</div>
                                    <div style={{ fontSize: 12, color: 'var(--ink-600)', fontWeight: 600 }}>{label}</div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Call cards */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                        {calls.map(call => (
                            <div key={call.id} className="card" style={{ padding: '20px 24px', borderLeft: call.status === 'active' ? '4px solid var(--ms-green-primary)' : '4px solid var(--ink-300)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                                        <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'var(--ms-navy-dark)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 17, flexShrink: 0 }}>
                                            {call.beneficiary.charAt(0)}
                                        </div>
                                        <div>
                                            <div style={{ fontWeight: 800, fontSize: 16, color: 'var(--ink-900)' }}>{call.beneficiary}</div>
                                            <div style={{ fontSize: 13, color: 'var(--ink-500)', marginTop: 2 }}>{call.scheme} · {call.language}</div>
                                            <div style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--ink-400)', marginTop: 4 }}>ID: {call.id}</div>
                                            <div style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--ink-400)', marginTop: 2 }}>HH: {call.householdHash}</div>
                                        </div>
                                    </div>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                        <span className="badge" style={{ background: call.status === 'active' ? 'var(--ok-bg)' : 'var(--ink-100)', color: call.status === 'active' ? 'var(--ok-text)' : 'var(--ink-600)' }}>
                                            {call.status === 'active' ? 'Live Stream' : 'Completed'}
                                        </span>
                                        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'monospace', fontSize: 14, fontWeight: 700, color: 'var(--ink-700)' }}>
                                            <Clock size={14} /> {call.duration}
                                        </span>
                                    </div>

                                    <div style={{ display: 'flex', gap: 10 }}>
                                        <button onClick={() => toggleMute(call.id)}
                                            style={{
                                                padding: '9px 16px', borderRadius: 8, fontWeight: 700, fontSize: 13, fontFamily: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, transition: 'all .15s',
                                                background: muted[call.id] ? 'var(--gov-navy)' : 'white',
                                                color: muted[call.id] ? 'white' : 'var(--ink-700)',
                                                border: `1.5px solid ${muted[call.id] ? 'var(--gov-navy)' : 'var(--border)'}`,
                                            }}>
                                            {muted[call.id] ? <MicOff size={15} /> : <Mic size={15} />}
                                            {muted[call.id] ? 'Unmute' : 'Mute'}
                                        </button>
                                        <button
                                            onClick={() => navigate('/call-in-progress', {
                                                state: {
                                                    joinUrl: call.joinUrl,
                                                    callId: call.id,
                                                    citizenName: call.beneficiary,
                                                    phoneNumber: call.phoneNumber,
                                                    householdHash: call.householdHash,
                                                    scheme: { name: call.schemeName },
                                                    language: call.language
                                                }
                                            })}
                                            style={{ padding: '9px 18px', borderRadius: 8, fontWeight: 800, fontSize: 13, fontFamily: 'inherit', cursor: 'pointer', background: 'var(--gov-navy)', color: 'white', border: 'none', display: 'flex', alignItems: 'center', gap: 6 }}
                                            disabled={call.status === 'completed' || !call.joinUrl}
                                            title={call.status === 'completed' ? "Call has ended" : (!call.joinUrl ? "Join URL unavailable" : "Join live stream")}
                                        >
                                            <Video size={15} /> Join Live
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

export default ActiveCalls;
