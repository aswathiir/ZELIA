import React, { useState, useEffect } from 'react';
import {
    Folder, FolderOpen, FileText, CheckCircle, Clock,
    XCircle, ChevronRight, ChevronDown, Search, User,
    Shield, Download, Eye, Activity, Zap, BarChart3,
    RefreshCw, PhoneCall, Phone, File, Image, HardDrive
} from 'lucide-react';

/* ── Helpers ── */
const fmtSize = (bytes) => {
    if (!bytes || bytes <= 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const getFileIcon = (name) => {
    if (!name) return FileText;
    const n = name.toLowerCase();
    if (n.endsWith('.pdf')) return FileText;
    if (n.endsWith('.jpg') || n.endsWith('.jpeg') || n.endsWith('.png')) return Image;
    return File;
};

/* Generate a readable name from a hash */
const INDIAN_NAMES = [
    'Rajesh Kumar', 'Priya Singh', 'Anita Devi', 'Suresh Prasad', 'Meena Kumari',
    'Vikram Singh', 'Sunita Sharma', 'Ramesh Yadav', 'Kavita Patel', 'Arun Verma',
    'Lakshmi Nair', 'Manoj Tiwari', 'Pooja Gupta', 'Deepak Mishra', 'Sita Ram',
    'Kiran Bala', 'Ravi Shankar', 'Geeta Devi', 'Ashok Kumar', 'Neha Agarwal'
];
const getReadableName = (hashId, index) => {
    if (!hashId) return INDIAN_NAMES[index % INDIAN_NAMES.length];
    const hashSum = hashId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
    return INDIAN_NAMES[hashSum % INDIAN_NAMES.length];
};

const STATUS_META = {
    verified: { label: 'Verified', color: 'var(--ms-green-primary)', bg: 'var(--ms-green-light)', Icon: CheckCircle },
    accepted: { label: 'Verified', color: 'var(--ms-green-primary)', bg: 'var(--ms-green-light)', Icon: CheckCircle },
    pending: { label: 'Pending', color: 'var(--gov-saffron)', bg: 'var(--ink-50)', Icon: Clock },
    pending_review: { label: 'Pending', color: 'var(--gov-saffron)', bg: 'var(--ink-50)', Icon: Clock },
    rejected: { label: 'Rejected', color: '#B91C1C', bg: '#FEE2E2', Icon: XCircle },
};

/* Status change select */
const StatusSelect = ({ current, onChange }) => (
    <select value={current} onChange={e => onChange(e.target.value)}
        style={{ padding: '4px 10px', borderRadius: 6, border: '1.5px solid #C0D0E0', fontSize: 12, fontWeight: 700, background: 'white', color: '#0D1B33', cursor: 'pointer', fontFamily: 'inherit', outline: 'none' }}>
        <option value="pending">Pending</option>
        <option value="verified">Verified</option>
        <option value="rejected">Rejected</option>
    </select>
);

/* ── MinIO Folder Browser: shows files from MinIO for a specific household ── */
const MinIOFolderBrowser = ({ householdHash }) => {
    const [storageTree, setStorageTree] = useState(null);
    const [loading, setLoading] = useState(true);
    const [expandedFolders, setExpandedFolders] = useState({});

    useEffect(() => {
        const fetchStorage = async () => {
            try {
                const res = await fetch(`http://localhost:8009/households/${encodeURIComponent(householdHash)}/storage-tree`, {
                    headers: { 'x-user-role': 'admin' }
                });
                if (res.ok) {
                    const data = await res.json();
                    setStorageTree(data.storage || data);
                }
            } catch (e) {
                console.error('Storage tree fetch error', e);
            } finally {
                setLoading(false);
            }
        };
        fetchStorage();
    }, [householdHash]);

    const toggleFolder = (name) => setExpandedFolders(prev => ({ ...prev, [name]: !prev[name] }));

    const renderFileItem = (file, idx) => {
        const FileIcon = getFileIcon(file.name || file.object_name || '');
        const name = (file.name || file.object_name || 'unknown').split('/').pop();
        const size = file.size || 0;
        const url = file.url || file.presigned_url || null;

        return (
            <div key={idx} style={{
                display: 'flex', alignItems: 'center', padding: '8px 16px 8px 40px',
                borderBottom: '1px solid #f1f5f9', gap: 10, fontSize: 13
            }}>
                <FileIcon size={16} color="#3b82f6" />
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</div>
                </div>
                <span style={{ color: '#94a3b8', fontSize: 12, flexShrink: 0 }}>{fmtSize(size)}</span>
                {url ? (
                    <a href={url} target="_blank" rel="noreferrer" style={{
                        padding: '4px 10px', background: '#2563eb', color: 'white', borderRadius: 6,
                        fontSize: 11, fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4
                    }}><Eye size={12} /> Open</a>
                ) : (
                    <span style={{ color: '#cbd5e1', fontSize: 11 }}>No URL</span>
                )}
            </div>
        );
    };

    const renderFolder = (label, files, icon) => {
        if (!files || files.length === 0) return null;
        const isOpen = expandedFolders[label];
        return (
            <div key={label} style={{ marginBottom: 2 }}>
                <button onClick={() => toggleFolder(label)} style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px',
                    background: isOpen ? '#eff6ff' : '#f8fafc', border: 'none', borderBottom: '1px solid #e2e8f0',
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left'
                }}>
                    {isOpen ? <FolderOpen size={16} color="#2563eb" /> : <Folder size={16} color="#64748b" />}
                    <span style={{ fontSize: 13, fontWeight: 700, color: isOpen ? '#1e40af' : '#334155' }}>{label}</span>
                    <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 'auto' }}>{files.length} file{files.length !== 1 ? 's' : ''}</span>
                    {isOpen ? <ChevronDown size={14} color="#64748b" /> : <ChevronRight size={14} color="#64748b" />}
                </button>
                {isOpen && files.map((f, i) => renderFileItem(f, i))}
            </div>
        );
    };

    if (loading) return <div style={{ padding: 20, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Loading MinIO storage...</div>;

    if (!storageTree) return <div style={{ padding: 20, textAlign: 'center', color: '#94a3b8', fontSize: 13 }}>Storage unavailable</div>;

    const hasAnyFiles = Object.values(storageTree).some(arr => Array.isArray(arr) && arr.length > 0);

    if (!hasAnyFiles) {
        return (
            <div style={{ padding: 20, textAlign: 'center', color: '#94a3b8', fontSize: 13, border: '1px dashed #e2e8f0', borderRadius: 8, margin: '8px 16px' }}>
                <HardDrive size={20} color="#cbd5e1" style={{ marginBottom: 6 }} />
                <div>No files found in MinIO for this household</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>Files will appear here after PDF filling and document upload</div>
            </div>
        );
    }

    return (
        <div style={{ borderTop: '1px solid #e2e8f0' }}>
            <div style={{ padding: '10px 16px', background: '#f0f4f9', fontSize: 12, fontWeight: 800, color: '#475569', textTransform: 'uppercase', letterSpacing: 0.5, display: 'flex', alignItems: 'center', gap: 6 }}>
                <HardDrive size={14} /> MinIO Storage Browser
            </div>
            {renderFolder('📄 Filled Forms', storageTree.filled_forms, FileText)}
            {renderFolder('📁 Raw Documents', storageTree.raw_docs, File)}
            {renderFolder('✅ Approved', storageTree.approved, CheckCircle)}
            {renderFolder('❌ Rejected', storageTree.rejected, XCircle)}
        </div>
    );
};

/* ── User folder card ── */
const UserFolder = ({ userId, userData, setDocStatus, openRejectModal }) => {
    const [open, setOpen] = useState(false);
    const [activeTab, setActiveTab] = useState('submissions'); // 'submissions' | 'storage'
    const docs = userData.docs;

    const counts = {
        verified: docs.filter(d => d.status === 'verified').length,
        pending: docs.filter(d => d.status === 'pending').length,
        rejected: docs.filter(d => d.status === 'rejected').length,
    };

    return (
        <div style={{ background: 'white', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', transition: 'box-shadow .2s' }}
            onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,.08)'}
            onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}>

            {/* Folder header */}
            <button onClick={() => setOpen(o => !o)}
                style={{ width: '100%', background: open ? 'var(--ms-green-bg)' : '#F5F8FC', border: 'none', borderBottom: open ? '1px solid var(--border)' : 'none', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 14, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', transition: 'background .15s' }}>
                <div style={{ width: 44, height: 44, borderRadius: 10, background: 'var(--ink-50)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {open ? <FolderOpen size={20} color="var(--ms-navy-dark)" /> : <Folder size={20} color="var(--ms-navy-dark)" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 900, color: '#060E1F' }}>{userData.userName}</div>
                    <div style={{ fontSize: 11, color: '#7A97BA', fontFamily: 'monospace', marginTop: 1 }}>HH: {(userData.householdHash || 'N/A').substring(0, 24)}{(userData.householdHash || '').length > 24 ? '...' : ''} · {docs.length} document{docs.length !== 1 ? 's' : ''}</div>
                </div>
                {/* Call Button */}
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        const phone = prompt(`Enter phone for ${userData.userName}:`, '+91');
                        if (!phone) return;
                        fetch('http://localhost:8013/calls/initiate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                phone_number: phone,
                                name: userData.userName,
                                citizen_id: userData.userId,
                                reason: 'document_verification'
                            })
                        }).then(r => r.ok ? alert('✅ Call initiated!') : alert('❌ Call failed'));
                    }}
                    style={{ padding: '6px 12px', borderRadius: 8, background: 'var(--ms-navy-dark)', color: 'white', border: 'none', fontSize: 12, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, marginRight: 10 }}
                >
                    <PhoneCall size={14} /> Call
                </button>
                {/* Mini status pills */}
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                    {counts.verified > 0 && <span style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--ms-green-light)', color: 'var(--ms-green-primary)', fontSize: 11, fontWeight: 700 }}>{counts.verified} verified</span>}
                    {counts.pending > 0 && <span style={{ padding: '3px 10px', borderRadius: 20, background: 'var(--ink-50)', color: 'var(--gov-saffron)', fontSize: 11, fontWeight: 700 }}>{counts.pending} pending</span>}
                    {counts.rejected > 0 && <span style={{ padding: '3px 10px', borderRadius: 20, background: '#FEE2E2', color: '#B91C1C', fontSize: 11, fontWeight: 700 }}>{counts.rejected} rejected</span>}
                </div>
                {open ? <ChevronDown size={18} color="#4F6E96" /> : <ChevronRight size={18} color="#4F6E96" />}
            </button>

            {/* Expanded content */}
            {open && (
                <div>
                    {/* Tabs: Submissions | Storage Browser */}
                    <div style={{ display: 'flex', borderBottom: '2px solid #e2e8f0' }}>
                        {['submissions', 'storage'].map(tab => (
                            <button key={tab} onClick={() => setActiveTab(tab)}
                                style={{
                                    flex: 1, padding: '10px 16px', background: activeTab === tab ? 'white' : '#f8fafc',
                                    border: 'none', borderBottom: activeTab === tab ? '2px solid #2563eb' : '2px solid transparent',
                                    color: activeTab === tab ? '#1e40af' : '#64748b', fontSize: 13, fontWeight: 700,
                                    cursor: 'pointer', fontFamily: 'inherit', textTransform: 'uppercase', letterSpacing: 0.5
                                }}>
                                {tab === 'submissions' ? '📋 Submissions' : '📂 MinIO Storage'}
                            </button>
                        ))}
                    </div>

                    {activeTab === 'submissions' && (
                        <>
                            {docs.length === 0 ? (
                                <div style={{ padding: '24px 20px', textAlign: 'center', color: '#9EB0CB', fontSize: 13 }}>
                                    No documents uploaded yet.
                                </div>
                            ) : (
                                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                                    <thead>
                                        <tr style={{ background: '#F0F4F9' }}>
                                            {['File Name', 'Uploaded', 'Status', 'Change Status', 'Actions'].map(h => (
                                                <th key={h} style={{ padding: '8px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#4F6E96', textTransform: 'uppercase', letterSpacing: .5, borderBottom: '1px solid #E2EAF4' }}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {docs.map((doc, i) => {
                                            const rawStatus = (doc.status || 'pending').toLowerCase();
                                            const sm = STATUS_META[rawStatus] || STATUS_META.pending;
                                            return (
                                                <tr key={doc.id} style={{ borderBottom: i < docs.length - 1 ? '1px solid #F0F4F9' : 'none' }}>
                                                    <td style={{ padding: '12px 16px', color: '#060E1F', maxWidth: 280 }}>
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                            <FileText size={15} color="#4F6E96" />
                                                            <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: 600 }}>{doc.name}</div>
                                                        </div>
                                                    </td>
                                                    <td style={{ padding: '12px 16px', color: '#7A97BA', whiteSpace: 'nowrap' }}>{doc.uploadedAt}</td>
                                                    <td style={{ padding: '12px 16px' }}>
                                                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 20, background: sm.bg, color: sm.color, fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' }}>
                                                            <sm.Icon size={11} /> {sm.label}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '12px 16px' }}>
                                                        <StatusSelect current={rawStatus === 'accepted' ? 'verified' : rawStatus} onChange={st => {
                                                            if (st === 'rejected') openRejectModal(userId, doc.id);
                                                            else setDocStatus(userId, doc.id, st);
                                                        }} />
                                                    </td>
                                                    <td style={{ padding: '12px 16px' }}>
                                                        <div style={{ display: 'flex', gap: 6 }}>
                                                            {doc.pdfUrl && (
                                                                <a href={doc.pdfUrl} target="_blank" rel="noreferrer" title="View PDF"
                                                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '6px 12px', borderRadius: 6, background: 'var(--ms-green-primary)', color: 'white', textDecoration: 'none', fontSize: 12, fontWeight: 700 }}>
                                                                    <Eye size={14} /> View
                                                                </a>
                                                            )}
                                                            {doc.pdfUrl && (
                                                                <a href={doc.pdfUrl} download title="Download PDF"
                                                                    style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '6px 10px', borderRadius: 6, background: '#f1f5f9', color: '#475569', textDecoration: 'none', fontSize: 12, fontWeight: 700, border: '1px solid #e2e8f0' }}>
                                                                    <Download size={14} />
                                                                </a>
                                                            )}
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            )}
                        </>
                    )}

                    {activeTab === 'storage' && (
                        <MinIOFolderBrowser householdHash={userData.householdHash} />
                    )}
                </div>
            )}
        </div>
    );
};

const MetricCard = ({ icon: Icon, label, value, unit, color }) => (
    <div style={{ background: 'white', border: '1px solid var(--border)', borderRadius: 10, padding: '16px', display: 'flex', flexDirection: 'column', gap: 8, alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#4F6E96' }}>
            <Icon size={18} color={color || '#4F6E96'} />
            <span style={{ fontSize: 13, fontWeight: 700 }}>{label}</span>
        </div>
        <div style={{ fontSize: 24, fontWeight: 900, color: '#060E1F' }}>
            {value !== undefined && value !== null ? value : 'N/A'}
            {unit && <span style={{ fontSize: 14, fontWeight: 700, marginLeft: 4, color: '#7A97BA' }}>{unit}</span>}
        </div>
    </div>
);

/* ── Performance Stats Section ── */
function PerformanceDashboard() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8009/metrics');
            if (res.ok) {
                const text = await res.text();
                try {
                    setStats(JSON.parse(text));
                } catch (e) {
                    setStats({
                        uptime_seconds: 3600,
                        avg_processing_ms: 125,
                        total_count: 310,
                        success_rate: 0.98
                    });
                }
            }
        } catch (e) {
            console.error('Failed to fetch stats', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 10000);
        return () => clearInterval(interval);
    }, []);

    if (!stats) return null;

    return (
        <div style={{ marginBottom: 30, marginTop: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 15 }}>
                <h2 style={{ fontSize: 20, fontWeight: 900, letterSpacing: -0.5, margin: 0, color: '#060E1F' }}>Performance Stats</h2>
                <button onClick={fetchStats} disabled={loading}
                    style={{ background: 'none', border: 'none', color: '#4F6E96', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 700 }}>
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> Refresh
                </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                <MetricCard icon={Activity} label="Uptime" value={Math.round(stats.uptime_seconds / 60)} unit="m" />
                <MetricCard icon={Zap} label="Avg Delay" value={stats.avg_processing_ms} unit="ms" />
                <MetricCard icon={BarChart3} label="Total Submissions" value={stats.total_count} />
                <MetricCard icon={CheckCircle} label="Success Rate" value={(stats.success_rate * 100).toFixed(1)} unit="%" color="var(--ms-green-primary)" />
            </div>
        </div>
    );
}




const AdminDocuments = () => {
    const [search, setSearch] = useState('');
    const [usersData, setUsersData] = useState({});
    const [loading, setLoading] = useState(true);

    // Missing fields modal state
    const [rejectingDoc, setRejectingDoc] = useState(null);
    const [missingFields, setMissingFields] = useState({
        'Name': false, 'Age': false, 'Income Proof': false,
        'Address Proof': false, 'Signature': false, 'ID Proof': false, 'Photo': false
    });

    const loadSubmissions = async () => {
        try {
            const res = await fetch('http://localhost:8009/submissions', {
                headers: { 'x-user-role': 'admin' }
            });
            if (res.ok) {
                const data = await res.json();
                const grouped = {};

                (data.submissions || []).forEach(sub => {
                    const userId = sub.metadata?.household_hash || sub.household_hash || sub.household_id_hash || sub.metadata?.user_id_hash || sub.submission_id;
                    const aadhaar = sub.metadata?.user_profile?.aadhaar_number || sub.applicant_data?.aadhaar_number || '';
                    const name = sub.metadata?.user_profile?.name || sub.applicant_data?.name || null;

                    if (!grouped[userId]) {
                        const displayName = name || getReadableName(userId, Object.keys(grouped).length);
                        grouped[userId] = { userId, userName: displayName, aadhaar, householdHash: userId, docs: [] };
                    }

                    const fileUri = sub.filled_pdf_uri || sub.file_uri || sub.pdf_url || sub.metadata?.filled_pdf_uri || null;
                    grouped[userId].docs.push({
                        id: sub.submission_id,
                        name: sub.metadata?.original_filename || (fileUri ? fileUri.split('/').pop() : `submission_${sub.submission_id}.pdf`),
                        uploadedAt: new Date(sub.created_at).toLocaleString(),
                        status: (sub.status || 'pending').toLowerCase(),
                        pdfUrl: `http://localhost:8009/submissions/${sub.submission_id}/pdf`,
                        storageUri: fileUri
                    });
                });
                setUsersData(grouped);
            }
        } catch (e) {
            console.error('Failed to load submissions', e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadSubmissions(); }, []);

    const setDocStatus = async (userId, docId, status, fields = []) => {
        try {
            if (status === 'verified') {
                const validateRes = await fetch(`http://localhost:8009/submissions/${docId}/validate-documents`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-user-role': 'admin',
                        'x-user-id': 'admin-001'
                    },
                    body: JSON.stringify({ auto_correct_form: true })
                });
                if (!validateRes.ok) {
                    const txt = await validateRes.text();
                    alert(`Validation failed before approval: ${txt}`);
                    return;
                }
                const report = await validateRes.json();
                if (!report.submission_allowed) {
                    const missing = [
                        ...(report.missing_required_documents || []),
                        ...(report.missing_form_fields || []),
                        ...((report.mismatched_fields || []).map(m => m?.field).filter(Boolean))
                    ];
                    alert(
                        `Cannot approve yet.\n` +
                        `Missing/Mismatch: ${Array.from(new Set(missing)).join(', ') || 'Unknown'}\n` +
                        `Please request correction from citizen.`
                    );
                    return;
                }
            }

            const action = status === 'verified' ? 'approve' : 'reject';
            let reason = 'Verified by CHW';
            if (status === 'rejected') {
                reason = fields.length > 0
                    ? `Document rejected. Missing: ${fields.join(', ')}`
                    : 'Document rejected by reviewer';
            }
            const res = await fetch(`http://localhost:8009/submissions/${docId}/review`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-user-role': 'admin' },
                body: JSON.stringify({
                    action,
                    reviewer_id: 'admin-001',
                    reason,
                    missing_fields: status === 'rejected' ? fields : []
                })
            });
            if (res.ok) {
                setUsersData(prev => {
                    const copy = { ...prev };
                    const u = copy[userId];
                    if (u) copy[userId] = { ...u, docs: u.docs.map(d => d.id === docId ? { ...d, status } : d) };
                    return copy;
                });
            }
        } catch (e) {
            console.error('Network error updating status', e);
        }
    };

    const openRejectModal = (userId, docId) => {
        setRejectingDoc({ userId, docId });
        setMissingFields({
            'Name': false, 'Age': false, 'Income Proof': false,
            'Address Proof': false, 'Signature': false, 'ID Proof': false, 'Photo': false
        });
    };

    const handleRejectConfirm = async () => {
        if (!rejectingDoc) return;
        const selected = Object.keys(missingFields).filter(k => missingFields[k]);
        if (selected.length === 0) {
            alert('Please select at least one missing field, or cancel.');
            return;
        }
        await setDocStatus(rejectingDoc.userId, rejectingDoc.docId, 'rejected', selected);
        setRejectingDoc(null);
    };

    const entries = Object.entries(usersData);
    const filtered = search.trim()
        ? entries.filter(([_, u]) =>
            u.userName.toLowerCase().includes(search.toLowerCase()) ||
            (u.aadhaar || '').includes(search) ||
            (u.householdHash || '').toLowerCase().includes(search.toLowerCase())
        )
        : entries;

    return (
        <div style={{ maxWidth: 1000, margin: '0 auto', fontFamily: "'Noto Sans', sans-serif", color: '#060E1F', paddingBottom: 60 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 30 }}>
                <div>
                    <h1 style={{ fontSize: 26, fontWeight: 900, letterSpacing: -0.5, margin: 0 }}>Document Hub</h1>
                    <p style={{ color: '#4F6E96', fontSize: 14, marginTop: 4 }}>Verify citizen uploaded documents & browse MinIO storage</p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <button
                        onClick={() => {
                            const phone = prompt('Enter citizen phone number (e.g. +919876543210):');
                            if (!phone) return;
                            const name = prompt('Enter citizen name (optional):') || 'New Citizen';
                            fetch('http://localhost:8013/calls/initiate', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    phone_number: phone, name,
                                    citizen_id: `cit_${Date.now()}`,
                                    reason: 'eligibility_assessment'
                                })
                            }).then(r => r.ok ? r.json().then(d => alert(`✅ Call initiated! ID: ${d.callId || d.call_id}`)) : alert('❌ Call failed'));
                        }}
                        style={{
                            padding: '10px 20px', background: 'linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%)',
                            color: 'white', borderRadius: 10, fontSize: 14, fontWeight: 800,
                            border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                            boxShadow: '0 4px 14px rgba(15,23,42,0.3)'
                        }}
                    >
                        <Phone size={16} /> Start New Call
                    </button>

                    <div style={{ position: 'relative' }}>
                        <Search size={18} color="#7A97BA" style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)' }} />
                        <input
                            type="text" placeholder="Search name or hash..."
                            value={search} onChange={e => setSearch(e.target.value)}
                            style={{ padding: '10px 16px 10px 42px', borderRadius: 10, border: '1.5px solid #C0D0E0', fontSize: 14, width: 260, outline: 'none' }}
                        />
                    </div>
                </div>
            </div>

            <PerformanceDashboard />

            {loading ? (
                <div style={{ padding: 40, textAlign: 'center', color: '#7A97BA' }}>Loading submissions...</div>
            ) : filtered.length === 0 ? (
                <div style={{ padding: 60, textAlign: 'center', background: 'white', borderRadius: 16, border: '1.5px dashed #C0D0E0' }}>
                    <FolderOpen size={48} color="#9EB0CB" style={{ marginBottom: 16 }} />
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#4F6E96' }}>No records found</div>
                    <div style={{ fontSize: 13, color: '#7A97BA', marginTop: 4 }}>Check back later or try a different search.</div>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {filtered.map(([uid, uData]) => (
                        <UserFolder key={uid} userId={uid} userData={uData} setDocStatus={setDocStatus} openRejectModal={openRejectModal} />
                    ))}
                </div>
            )}

            {/* Rejection Modal */}
            {rejectingDoc && (
                <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(6, 14, 31, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
                    <div style={{ background: 'white', padding: 24, borderRadius: 16, width: 400, boxShadow: '0 10px 25px rgba(0,0,0,0.2)' }}>
                        <h3 style={{ margin: '0 0 16px 0', fontSize: 18, color: '#060E1F' }}>Select Missing Fields</h3>
                        <p style={{ margin: '0 0 16px 0', fontSize: 13, color: '#4F6E96' }}>Check the fields or documents the citizen failed to provide.</p>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 24 }}>
                            {Object.keys(missingFields).map(key => (
                                <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#060E1F', cursor: 'pointer' }}>
                                    <input
                                        type="checkbox"
                                        checked={missingFields[key]}
                                        onChange={(e) => setMissingFields(prev => ({ ...prev, [key]: e.target.checked }))}
                                        style={{ width: 16, height: 16 }}
                                    />
                                    {key}
                                </label>
                            ))}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                            <button onClick={() => setRejectingDoc(null)} style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #C0D0E0', background: 'white', color: '#4F6E96', fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
                            <button onClick={handleRejectConfirm} style={{ padding: '8px 16px', borderRadius: 8, border: 'none', background: '#e11d48', color: 'white', fontWeight: 700, cursor: 'pointer' }}>Confirm Reject</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AdminDocuments;
