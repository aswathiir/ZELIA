import React, { useState, useEffect } from 'react';
import {
    Activity, CheckCircle, AlertCircle, FileText, Search,
    ChevronDown, ChevronRight, User, FolderOpen, ArrowRight,
    Filter, XCircle, Clock, PhoneCall, Phone
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Dashboard = () => {
    const navigate = useNavigate();

    const [submissions, setSubmissions] = useState([]);
    const [stats, setStats] = useState({ total: 0, approved: 0, pending: 0, rejected: 0 });
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');

    /* Call Modal state */
    const [showCallModal, setShowCallModal] = useState(false);
    const [callForm, setCallForm] = useState({ phone: '+91', name: '', citizen_id: '' });
    const [callLoading, setCallLoading] = useState(false);
    const [callResult, setCallResult] = useState(null);

    const handleStartCall = async () => {
        if (!callForm.phone || callForm.phone.length < 10) {
            alert('Please enter a valid phone number.');
            return;
        }
        setCallLoading(true);
        setCallResult(null);
        try {
            const res = await fetch('http://localhost:8013/calls/initiate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone_number: callForm.phone,
                    name: callForm.name || 'New Citizen',
                    citizen_id: callForm.citizen_id || `cit_${Date.now()}`,
                    reason: 'eligibility_assessment'
                })
            });
            if (res.ok) {
                const data = await res.json();
                const callId = data.callId || data.call_id;
                const joinUrl = data.joinUrl || data.join_url;
                const householdHash = data.household_hash;
                setCallResult({ success: true, callId });
                // Navigate to live call page with joinUrl
                if (joinUrl) {
                    setTimeout(() => {
                        setShowCallModal(false);
                        navigate('/call-in-progress', {
                            state: {
                                joinUrl,
                                callId,
                                citizenName: callForm.name || 'New Citizen',
                                phoneNumber: callForm.phone,
                                householdHash
                            }
                        });
                    }, 600);
                }
            } else {
                const errText = await res.text();
                setCallResult({ success: false, error: errText });
            }
        } catch (e) {
            console.error('Call error:', e);
            setCallResult({ success: false, error: e.message });
        } finally {
            setCallLoading(false);
        }
    };

    useEffect(() => {
        const fetchSubmissions = async () => {
            try {
                /* Try both approaches: query param and header */
                let res = await fetch('http://localhost:8009/submissions', {
                    headers: { 'x-user-role': 'admin' }
                });
                if (!res.ok) {
                    res = await fetch('http://localhost:8009/submissions?role=admin');
                }
                if (res.ok) {
                    const data = await res.json();
                    const subs = data.submissions || [];

                    let app = 0, pen = 0, rej = 0;
                    const parsedTable = subs.map(sub => {
                        const hashId = sub.household_hash || sub.submission_id;
                        const district = sub.applicant_data?.district || sub.metadata?.user_profile?.district || 'Unknown District';
                        const schemes = sub.scheme_id || sub.metadata?.eligible_schemes?.[0] || 'Evaluating...';

                        let sStatus = sub.status || 'pending';
                        if (sStatus === 'approved' || sStatus === 'verified' || sStatus === 'accepted') { app++; sStatus = 'Approved'; }
                        else if (sStatus === 'rejected') { rej++; sStatus = 'Rejected'; }
                        else { pen++; sStatus = 'Pending'; }

                        return {
                            id: sub.submission_id,
                            hashId,
                            district,
                            schemes,
                            status: sStatus,
                            date: new Date(sub.created_at).toLocaleDateString('en-IN'),
                            phone: sub.applicant_data?.phone || sub.metadata?.user_profile?.phone || ''
                        };
                    });

                    setSubmissions(parsedTable);
                    setStats({ total: subs.length, approved: app, pending: pen, rejected: rej });
                }
            } catch (err) {
                console.error('Failed to fetch dashboard submissions', err);
            } finally {
                setLoading(false);
            }
        };
        fetchSubmissions();
    }, []);

    const filtered = submissions.filter(s =>
        (s.hashId || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.district || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    const STAT_WIDGETS = [
        { label: 'Total Households', val: loading ? '...' : stats.total, icon: User, color: 'var(--ms-navy-dark)' },
        { label: 'Approved Cases', val: loading ? '...' : stats.approved, icon: CheckCircle, color: 'var(--ms-green-primary)' },
        { label: 'Pending CHW Verif', val: loading ? '...' : stats.pending, icon: Clock, color: '#f59e0b' },
        { label: 'Rejected Cases', val: loading ? '...' : stats.rejected, icon: XCircle, color: '#B91C1C' },
    ];

    return (
        <div style={{ paddingBottom: 60 }}>
            {/* Page Header with Call Button */}
            <div style={{ marginBottom: 32, paddingBottom: 20, borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h1 style={{ fontSize: 28, fontWeight: 900, color: 'var(--ms-navy-dark)', margin: 0 }}>Welfare Eligibility Dashboard</h1>
                    <p style={{ color: 'var(--ink-500)', fontSize: 14, marginTop: 6, fontWeight: 500 }}>Real-time telemetry of citizen applications and automated eligibility workflows.</p>
                </div>

                {/* ═══ PROMINENT CALL BUTTON ═══ */}
                <button
                    onClick={() => setShowCallModal(true)}
                    style={{
                        padding: '12px 24px', background: 'linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)',
                        color: 'white', borderRadius: 10, fontSize: 15, fontWeight: 800,
                        border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                        boxShadow: '0 4px 14px rgba(15,23,42,0.35)', transition: 'all 0.2s',
                        flexShrink: 0
                    }}
                    onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(15,23,42,0.45)'; }}
                    onMouseOut={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 14px rgba(15,23,42,0.35)'; }}
                >
                    <PhoneCall size={18} />
                    Start Ultravox Call
                </button>
            </div>

            {/* ═══ CALL MODAL ═══ */}
            {showCallModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.5)', zIndex: 1000,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }} onClick={() => { setShowCallModal(false); setCallResult(null); }}>
                    <div style={{
                        background: 'white', borderRadius: 16, padding: '32px', width: 440, maxWidth: '90vw',
                        boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
                    }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
                            <div style={{
                                width: 48, height: 48, borderRadius: 12, background: '#1e3a5f',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                <Phone size={22} color="white" />
                            </div>
                            <div>
                                <h2 style={{ margin: 0, fontSize: 20, fontWeight: 900, color: '#0f172a' }}>Start Verification Call</h2>
                                <p style={{ margin: 0, fontSize: 13, color: '#64748b' }}>Ultravox AI-powered voice interview</p>
                            </div>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>
                            <div>
                                <label style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6, display: 'block' }}>Phone Number *</label>
                                <input
                                    type="tel" value={callForm.phone}
                                    onChange={e => setCallForm({ ...callForm, phone: e.target.value })}
                                    placeholder="+919876543210"
                                    style={{ width: '100%', padding: '12px 16px', borderRadius: 8, border: '1.5px solid #e2e8f0', fontSize: 15, fontWeight: 600, outline: 'none', boxSizing: 'border-box' }}
                                />
                            </div>
                            <div>
                                <label style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6, display: 'block' }}>Citizen Name</label>
                                <input
                                    type="text" value={callForm.name}
                                    onChange={e => setCallForm({ ...callForm, name: e.target.value })}
                                    placeholder="Rajesh Kumar"
                                    style={{ width: '100%', padding: '12px 16px', borderRadius: 8, border: '1.5px solid #e2e8f0', fontSize: 15, fontWeight: 600, outline: 'none', boxSizing: 'border-box' }}
                                />
                            </div>
                            <div>
                                <label style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: 6, display: 'block' }}>Citizen ID (optional)</label>
                                <input
                                    type="text" value={callForm.citizen_id}
                                    onChange={e => setCallForm({ ...callForm, citizen_id: e.target.value })}
                                    placeholder="cit_001"
                                    style={{ width: '100%', padding: '12px 16px', borderRadius: 8, border: '1.5px solid #e2e8f0', fontSize: 15, fontWeight: 600, outline: 'none', boxSizing: 'border-box' }}
                                />
                            </div>
                        </div>

                        {/* Call Result */}
                        {callResult && (
                            <div style={{
                                padding: '12px 16px', borderRadius: 8, marginBottom: 16, fontSize: 13, fontWeight: 600,
                                background: callResult.success ? '#dcfce7' : '#fee2e2',
                                color: callResult.success ? '#166534' : '#991b1b',
                                border: `1px solid ${callResult.success ? '#bbf7d0' : '#fecaca'}`
                            }}>
                                {callResult.success
                                    ? `✅ Call initiated! ID: ${callResult.callId}`
                                    : `❌ Failed: ${callResult.error}`
                                }
                            </div>
                        )}

                        <div style={{ display: 'flex', gap: 12 }}>
                            <button
                                onClick={() => { setShowCallModal(false); setCallResult(null); }}
                                style={{
                                    flex: 1, padding: '12px', borderRadius: 8, border: '1.5px solid #e2e8f0',
                                    background: 'white', color: '#64748b', fontSize: 14, fontWeight: 700, cursor: 'pointer'
                                }}
                            >Cancel</button>
                            <button
                                onClick={handleStartCall}
                                disabled={callLoading}
                                style={{
                                    flex: 2, padding: '12px', borderRadius: 8, border: 'none',
                                    background: callLoading ? '#94a3b8' : '#1e3a5f', color: 'white',
                                    fontSize: 14, fontWeight: 800, cursor: callLoading ? 'wait' : 'pointer',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
                                }}
                            >
                                <PhoneCall size={16} />
                                {callLoading ? 'Connecting via Ultravox...' : 'Start Call'}
                            </button>
                        </div>

                        <p style={{ margin: '16px 0 0', fontSize: 11, color: '#94a3b8', textAlign: 'center' }}>
                            Supports Hindi & English • Ultravox AI Voice Interview • Data extracted in English
                        </p>
                    </div>
                </div>
            )}

            {/* 4 Top Widgets */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 32 }}>
                {STAT_WIDGETS.map((s, idx) => (
                    <div key={idx} className="stat-card" style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: '24px', display: 'flex', alignItems: 'center', gap: 18, borderTop: `4px solid ${s.color}`, boxShadow: 'var(--shadow-sm)' }}>
                        <div style={{ width: 52, height: 52, borderRadius: 12, background: 'var(--ink-50)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border)' }}>
                            <s.icon size={22} color={s.color} />
                        </div>
                        <div>
                            <div style={{ fontSize: 30, fontWeight: 900, color: 'var(--ms-navy-dark)', lineHeight: 1 }}>{s.val}</div>
                            <div style={{ fontSize: 11, color: 'var(--ink-400)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: 0.8, marginTop: 6 }}>{s.label}</div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Main Data Table */}
            <div className="card" style={{ padding: 0, overflow: 'hidden', border: '1.5px solid var(--border)', borderRadius: 14, boxShadow: 'var(--shadow-md)', background: 'white' }}>
                {/* Table Toolbar */}
                <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--ink-50)' }}>
                    <div style={{ fontWeight: 900, fontSize: 15, color: 'var(--ms-navy-dark)', textTransform: 'uppercase', letterSpacing: 0.5 }}>CITIZEN DATABASE REGISTRY</div>
                    <div style={{ display: 'flex', gap: 12 }}>
                        <div style={{ position: 'relative' }}>
                            <Search size={16} color="var(--ink-400)" style={{ position: 'absolute', top: 12, left: 14 }} />
                            <input
                                type="text"
                                placeholder="Search by Hash or District..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                style={{ padding: '10px 14px 10px 42px', fontSize: 13, border: '1.5px solid var(--border)', borderRadius: 10, minWidth: 280, outline: 'none', background: 'white', fontWeight: 500 }}
                            />
                        </div>
                        <button style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', background: 'white', border: '1.5px solid var(--border)', borderRadius: 10, fontSize: 13, fontWeight: 700, color: 'var(--ink-700)', cursor: 'pointer' }}>
                            <Filter size={16} /> Filters
                        </button>
                    </div>
                </div>

                {/* Table Data */}
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead style={{ background: 'var(--surface-alt)', borderBottom: '2px solid var(--border)', fontSize: 12, color: 'var(--ink-500)', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                            <tr>
                                <th style={{ padding: '16px 24px', fontWeight: 800 }}>Applicant Hash ID</th>
                                <th style={{ padding: '16px 24px', fontWeight: 800 }}>District</th>
                                <th style={{ padding: '16px 24px', fontWeight: 800 }}>Eligible Schemes</th>
                                <th style={{ padding: '16px 24px', fontWeight: 800 }}>Submission Date</th>
                                <th style={{ padding: '16px 24px', fontWeight: 800 }}>CHW Status</th>
                                <th style={{ padding: '16px 24px', fontWeight: 800, textAlign: 'right' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loading ? (
                                <tr>
                                    <td colSpan="6" style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)', fontSize: 14 }}>Synchronizing live data...</td>
                                </tr>
                            ) : filtered.length === 0 ? (
                                <tr>
                                    <td colSpan="6" style={{ padding: 40, textAlign: 'center', color: 'var(--ink-400)', fontSize: 14 }}>No citizen cases found matching your criteria.</td>
                                </tr>
                            ) : filtered.map((row, i) => (
                                <tr key={row.id} style={{ borderBottom: '1px solid var(--border)', background: i % 2 === 0 ? 'white' : 'var(--ink-50)', transition: 'background 0.2s', cursor: 'pointer' }} onClick={() => navigate(`/case/${row.hashId}`)}>
                                    <td style={{ padding: '16px 24px', fontFamily: 'monospace', fontSize: 13, color: 'var(--ms-navy-dark)', fontWeight: 600 }}>
                                        {(row.hashId || '').length > 20 ? row.hashId.substring(0, 20) + '...' : row.hashId}
                                    </td>
                                    <td style={{ padding: '16px 24px', fontSize: 13, color: 'var(--ink-800)', fontWeight: 500 }}>{row.district}</td>
                                    <td style={{ padding: '16px 24px', fontSize: 13 }}>
                                        <span style={{ padding: '4px 8px', background: 'var(--ink-100)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--ink-700)', fontWeight: 500 }}>
                                            {(row.schemes || '').length > 25 ? row.schemes.substring(0, 25) + '...' : row.schemes}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px 24px', fontSize: 13, color: 'var(--ink-600)' }}>{row.date}</td>
                                    <td style={{ padding: '16px 24px' }}>
                                        <div style={{
                                            display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700,
                                            color: row.status === 'Approved' ? '#16a34a' : (row.status === 'Rejected' ? '#B91C1C' : '#f59e0b')
                                        }}>
                                            {row.status === 'Approved' && <CheckCircle size={14} />}
                                            {row.status === 'Rejected' && <XCircle size={14} />}
                                            {row.status === 'Pending' && <Clock size={14} />}
                                            {row.status.toUpperCase()}
                                        </div>
                                    </td>
                                    <td style={{ padding: '16px 24px', textAlign: 'right' }}>
                                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                                            <button onClick={(e) => { e.stopPropagation(); navigate(`/case/${row.hashId}`); }} style={{ padding: '6px 12px', background: 'var(--ms-navy-dark)', color: 'white', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                                                View <ArrowRight size={12} />
                                            </button>
                                            {row.phone && (
                                                <button onClick={(e) => {
                                                    e.stopPropagation();
                                                    setCallForm({ phone: row.phone, name: '', citizen_id: row.hashId });
                                                    setShowCallModal(true);
                                                }} style={{ padding: '6px 12px', background: '#16a34a', color: 'white', border: 'none', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                                                    <Phone size={12} /> Call
                                                </button>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
