import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    CheckCircle,
    Clock,
    Download,
    Hash,
    PhoneCall,
    Upload,
    ChevronRight,
    AlertCircle,
    FileText,
} from 'lucide-react';

const WORKFLOW_STAGES = [
    { id: 'interview', label: 'AI Voice Interview' },
    { id: 'documents', label: 'Document Upload' },
    { id: 'ocr', label: 'OCR Processing' },
    { id: 'autofill', label: 'Form Auto-Fill' },
    { id: 'chw_verification', label: 'CHW Verification' },
    { id: 'decision', label: 'Approval/ Rejection' },
    { id: 'submission', label: 'Final Submission' }
];

const parseMaybeJson = (v, fallback = {}) => {
    if (v && typeof v === 'object') return v;
    if (typeof v === 'string') {
        try { return JSON.parse(v); } catch { return fallback; }
    }
    return fallback;
};

const asArray = (v) => {
    if (Array.isArray(v)) return v;
    if (typeof v === 'string') return v.split(',').map((x) => x.trim()).filter(Boolean);
    return [];
};

const statusLabel = (s) => {
    const x = String(s || '').toLowerCase();
    if (['approved', 'accepted', 'verified'].includes(x)) return 'Approved';
    if (x === 'rejected') return 'Rejected';
    return 'Pending Verification';
};

const CaseDetail = () => {
    const { hashId } = useParams();
    const navigate = useNavigate();

    const [loading, setLoading] = useState(true);
    const [caseData, setCaseData] = useState(null);
    const [workflowStatus, setWorkflowStatus] = useState(null);
    const [callLoading, setCallLoading] = useState(false);
    const [callStatus, setCallStatus] = useState(null);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            try {
                const [subRes, wfRes] = await Promise.all([
                    fetch(`http://localhost:8009/submissions/session/${encodeURIComponent(hashId)}`, {
                        headers: { 'x-user-role': 'admin' },
                    }),
                    fetch(`http://localhost:8013/households/${encodeURIComponent(hashId)}/workflow-status`),
                ]);

                const subJson = subRes.ok ? await subRes.json() : { submissions: [] };
                const wfJson = wfRes.ok ? await wfRes.json() : null;
                const submissions = Array.isArray(subJson.submissions) ? subJson.submissions : [];
                submissions.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

                const lead = submissions[0] || {};
                const leadMeta = parseMaybeJson(lead.metadata, {});
                const leadProfile = parseMaybeJson(leadMeta.user_profile, {});
                const leadApplicant = parseMaybeJson(lead.applicant_data, {});
                const leadChecklist = parseMaybeJson(lead.verification_checklist, {});
                const leadValidation = parseMaybeJson(lead.document_validation_summary, {});

                const missingFields = Array.from(new Set([
                    ...asArray(lead.correction_required_fields),
                    ...asArray(leadChecklist.missing_required_documents),
                    ...asArray(leadChecklist.missing_form_fields),
                    ...asArray(leadValidation.missing_form_fields),
                    ...asArray((leadValidation.mismatched_fields || []).map((m) => m?.field).filter(Boolean)),
                ]));

                const docs = submissions.map((s) => {
                    const status = String(s.status || '').toLowerCase();
                    const validation = parseMaybeJson(s.document_validation_summary, {});
                    const checklist = parseMaybeJson(s.verification_checklist, {});
                    const docMissing = Array.from(new Set([
                        ...asArray(s.correction_required_fields),
                        ...asArray(checklist.missing_required_documents),
                        ...asArray(checklist.missing_form_fields),
                        ...asArray(validation.missing_form_fields),
                    ]));
                    const fileUri = s.filled_pdf_uri || s.file_uri || s.storage_path || null;
                    return {
                        id: s.submission_id,
                        status,
                        displayStatus: statusLabel(status),
                        name: fileUri ? String(fileUri).split('/').pop() : `submission_${s.submission_id}.pdf`,
                        date: s.created_at ? new Date(s.created_at).toLocaleString('en-IN') : 'N/A',
                        url: `http://localhost:8009/submissions/${s.submission_id}/pdf`,
                        validationStatus: s.document_validation_status || checklist.document_validation_status || 'pending',
                        missingFields: docMissing,
                    };
                });

                const overallStatus = docs.length > 0
                    ? (docs.some((d) => d.status === 'rejected')
                        ? 'Rejected'
                        : (docs.every((d) => ['approved', 'accepted', 'verified'].includes(d.status))
                            ? 'Approved'
                            : 'Pending Verification'))
                    : 'Pending Verification';

                const wf = wfJson && wfJson.success ? wfJson : null;
                setWorkflowStatus(wf);
                setCaseData({
                    hashId,
                    status: overallStatus,
                    profile: {
                        name: leadProfile.name || leadApplicant.name || 'Citizen Applicant',
                        aadhaar: leadProfile.aadhaar_number || leadApplicant.aadhaar_number || `${hashId?.substring(0, 18)}...`,
                        district: leadProfile.district || leadApplicant.district || 'Unspecified',
                        address: leadProfile.address || leadApplicant.address || 'Not provided',
                        phone: leadProfile.phone || leadApplicant.phone || '+91 - Not Provided',
                        age: leadProfile.age || leadApplicant.age || 'Not provided',
                        gender: leadProfile.gender || leadApplicant.gender || 'Not specified',
                        monthlyIncome: leadProfile.monthly_income || leadApplicant.monthly_income || 'Not provided',
                    },
                    generatedResponse:
                        wf?.response_text
                        || leadMeta.response_text
                        || (wf?.best_match_scheme?.scheme_name
                            ? `Best matched scheme is ${wf.best_match_scheme.scheme_name}.`
                            : 'Call completed. Awaiting scheme matching and document validation.'),
                    bestScheme:
                        wf?.best_match_scheme?.scheme_name
                        || wf?.best_match_scheme?.scheme_id
                        || lead.scheme_id
                        || 'Not yet matched',
                    requiredDocs: asArray(wf?.required_documents),
                    missingDocs: asArray(wf?.missing_required_documents),
                    missingFields,
                    chwNotes: lead.review_notes
                        || leadMeta.chw_notes
                        || 'CHW verification notes will appear here after document cross-validation.',
                    docs,
                });
            } catch (e) {
                console.error('Failed to load case detail:', e);
                setCaseData(null);
            } finally {
                setLoading(false);
            }
        };

        load();
    }, [hashId]);

    const currentStageIndex = useMemo(() => {
        if (!caseData) return 1;
        const hasDocs = caseData.docs.length > 0;
        if (!hasDocs) return 1;
        if (caseData.status === 'Approved') return 6;
        if (caseData.status === 'Rejected') return 5;
        if (workflowStatus?.status === 'form_ready') return 4;
        if (workflowStatus?.status === 'documents_pending') return 2;
        return 4;
    }, [caseData, workflowStatus]);

    const handleStartCall = async () => {
        if (!caseData) return;
        setCallLoading(true);
        try {
            const cleanPhone = String(caseData.profile.phone || '').replace(/[^0-9+]/g, '') || '+91';
            const res = await fetch('http://localhost:8013/calls/initiate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone_number: cleanPhone,
                    name: caseData.profile.name || 'Citizen Applicant',
                    citizen_id: caseData.hashId,
                    reason: 'document_verification',
                }),
            });
            if (!res.ok) {
                const txt = await res.text();
                throw new Error(txt || 'Call initiation failed');
            }
            const data = await res.json();
            const callId = data.callId || data.call_id;
            const joinUrl = data.joinUrl || data.join_url;
            setCallStatus({ id: callId, status: 'initiated' });
            if (joinUrl) {
                navigate('/call-in-progress', {
                    state: {
                        joinUrl,
                        callId,
                        citizenName: caseData.profile.name,
                        phoneNumber: cleanPhone,
                        householdHash: data.household_hash || caseData.hashId,
                    },
                });
            } else {
                alert(`Call initiated (${callId}) but join URL missing.`);
            }
        } catch (e) {
            console.error('Call error:', e);
            alert(`Failed to start call: ${e.message}`);
        } finally {
            setCallLoading(false);
        }
    };

    if (loading) {
        return <div style={{ padding: 60, textAlign: 'center', color: '#64748b', fontSize: 15 }}>Synchronizing Case Vault...</div>;
    }
    if (!caseData) {
        return <div style={{ padding: 60, textAlign: 'center', color: '#B91C1C', fontSize: 16, fontWeight: 700 }}>Citizen Hash Not Found in Records.</div>;
    }

    return (
        <div style={{ maxWidth: 1050, margin: '0 auto', paddingBottom: 60 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#94a3b8', marginBottom: 16 }}>
                <button onClick={() => navigate('/dashboard')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', fontSize: 13, fontWeight: 600 }}>Home</button>
                <ChevronRight size={14} />
                <button onClick={() => navigate(-1)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', fontSize: 13, fontWeight: 600 }}>Applications</button>
                <ChevronRight size={14} />
                <span style={{ color: '#334155', fontWeight: 600 }}>{caseData.hashId?.substring(0, 20)}...</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 26, fontWeight: 900, color: '#0f172a', margin: '0 0 6px 0' }}>Citizen Application Dossier</h1>
                    <div style={{ fontSize: 13, color: '#64748b', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Hash size={14} /> SHA256/Household: {caseData.hashId}
                    </div>
                </div>
                <button
                    onClick={handleStartCall}
                    disabled={callLoading}
                    style={{
                        padding: '10px 20px',
                        background: '#1e3a5f',
                        color: 'white',
                        borderRadius: 8,
                        fontSize: 14,
                        fontWeight: 700,
                        border: 'none',
                        cursor: callLoading ? 'wait' : 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                    }}
                >
                    <PhoneCall size={16} />
                    {callLoading ? 'Connecting...' : 'Start Verification Call'}
                </button>
            </div>

            <div style={{ background: 'white', border: '1.5px solid #e2e8f0', borderRadius: 14, padding: '24px 30px', marginBottom: 20 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative' }}>
                    <div style={{ position: 'absolute', top: 14, left: 40, right: 40, height: 3, background: '#e2e8f0', zIndex: 0 }} />
                    <div style={{
                        position: 'absolute',
                        top: 14,
                        left: 40,
                        width: `${Math.min(100, (currentStageIndex / (WORKFLOW_STAGES.length - 1)) * 100)}%`,
                        height: 3,
                        background: '#16a34a',
                        zIndex: 1,
                    }} />
                    {WORKFLOW_STAGES.map((stage, idx) => {
                        const done = idx < currentStageIndex;
                        const current = idx === currentStageIndex;
                        return (
                            <div key={stage.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, zIndex: 2 }}>
                                <div style={{
                                    width: 28, height: 28, borderRadius: '50%',
                                    background: done ? '#16a34a' : (current ? '#ffffff' : '#f1f5f9'),
                                    border: current ? '3px solid #16a34a' : (done ? '2px solid #16a34a' : '2px solid #cbd5e1'),
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    {done && <CheckCircle size={16} color="white" />}
                                    {current && <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#16a34a' }} />}
                                </div>
                                <div style={{ fontSize: 11, fontWeight: current ? 800 : 600, color: current ? '#0f172a' : '#94a3b8', textAlign: 'center', maxWidth: 90 }}>
                                    {stage.label}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
                <div style={{ background: 'white', border: '1.5px solid #e2e8f0', borderRadius: 14, padding: '24px 28px' }}>
                    <h3 style={{ fontSize: 18, fontWeight: 900, color: '#0f172a', margin: '0 0 18px 0' }}>Applicant Information</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 14 }}>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Applicant Name</div><div style={{ fontSize: 16, fontWeight: 700 }}>{caseData.profile.name}</div></div>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Aadhaar Hash</div><div style={{ fontSize: 14, fontWeight: 600, fontFamily: 'monospace' }}>{caseData.profile.aadhaar}</div></div>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>District</div><div style={{ fontSize: 16, fontWeight: 700 }}>{caseData.profile.district}</div></div>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Phone</div><div style={{ fontSize: 16, fontWeight: 700 }}>{caseData.profile.phone}</div></div>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Address</div><div style={{ fontSize: 14, fontWeight: 600 }}>{caseData.profile.address}</div></div>
                        <div><div style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>Age / Gender / Monthly Income</div><div style={{ fontSize: 14, fontWeight: 600 }}>{caseData.profile.age} / {caseData.profile.gender} / ₹{caseData.profile.monthlyIncome}</div></div>
                    </div>
                </div>

                <div style={{ background: 'white', border: '1.5px solid #e2e8f0', borderRadius: 14, padding: '24px 28px' }}>
                    <h3 style={{ fontSize: 18, fontWeight: 900, color: '#0f172a', margin: '0 0 14px 0' }}>Generated Response & Validation</h3>
                    <div style={{ fontSize: 14, color: '#334155', lineHeight: 1.7, marginBottom: 10 }}>{caseData.generatedResponse}</div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}><strong>Best Matched Scheme:</strong> {caseData.bestScheme}</div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}><strong>Required Documents:</strong> {caseData.requiredDocs.length ? caseData.requiredDocs.join(', ') : 'Not specified'}</div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}><strong>Missing Documents:</strong> {caseData.missingDocs.length ? caseData.missingDocs.join(', ') : 'None'}</div>
                    <div style={{ fontSize: 13, marginBottom: 6 }}><strong>Missing/Mismatched Fields:</strong> {caseData.missingFields.length ? caseData.missingFields.join(', ') : 'None'}</div>
                    {workflowStatus?.next_action && (
                        <div style={{ marginTop: 8, fontSize: 12, fontWeight: 700, color: '#1e40af', background: '#eff6ff', border: '1px solid #dbeafe', padding: '6px 10px', borderRadius: 8 }}>
                            Next action: {workflowStatus.next_action}
                        </div>
                    )}
                </div>
            </div>

            <div style={{ background: 'white', border: '1.5px solid #e2e8f0', borderRadius: 14, padding: '24px 28px', marginBottom: 20 }}>
                <h3 style={{ fontSize: 18, fontWeight: 900, color: '#0f172a', margin: '0 0 14px 0' }}>Document Status</h3>
                {caseData.docs.length === 0 ? (
                    <div style={{ color: '#94a3b8', border: '1.5px dashed #e2e8f0', borderRadius: 8, padding: 24, textAlign: 'center' }}>
                        No documents uploaded yet
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        {caseData.docs.map((doc) => (
                            <div key={doc.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', borderRadius: 10, border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                                    <div style={{ width: 38, height: 38, borderRadius: 8, background: '#eff6ff', border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <Upload size={18} color="#3b82f6" />
                                    </div>
                                    <div style={{ minWidth: 0 }}>
                                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{doc.name}</div>
                                        <div style={{ fontSize: 12, color: '#94a3b8' }}>{doc.date}</div>
                                        <div style={{ fontSize: 11, color: '#64748b' }}>Validation: {doc.validationStatus}</div>
                                        {doc.missingFields.length > 0 && (
                                            <div style={{ fontSize: 11, color: '#b45309', marginTop: 2 }}>
                                                Missing: {doc.missingFields.join(', ')}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 12 }}>
                                    {['approved', 'accepted', 'verified'].includes(doc.status) ? (
                                        <span style={{ fontSize: 11, fontWeight: 700, color: '#16a34a', background: '#dcfce7', padding: '3px 10px', borderRadius: 12 }}>Verified</span>
                                    ) : doc.status === 'rejected' ? (
                                        <span style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', background: '#fee2e2', padding: '3px 10px', borderRadius: 12 }}>Rejected</span>
                                    ) : (
                                        <span style={{ fontSize: 11, fontWeight: 700, color: '#f59e0b', background: '#fef3c7', padding: '3px 10px', borderRadius: 12 }}>Pending</span>
                                    )}
                                    <a href={doc.url} target="_blank" rel="noreferrer" style={{ width: 32, height: 32, borderRadius: 6, border: '1px solid #e2e8f0', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}>
                                        <Download size={14} color="#64748b" />
                                    </a>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div style={{ background: 'white', border: '1.5px solid #e2e8f0', borderRadius: 14, padding: '24px 28px' }}>
                <h3 style={{ fontSize: 18, fontWeight: 900, color: '#0f172a', margin: '0 0 10px 0' }}>CHW Notes</h3>
                <p style={{ fontSize: 14, color: '#475569', lineHeight: 1.7, margin: 0 }}>{caseData.chwNotes}</p>
            </div>

            {callStatus && (
                <div style={{ marginTop: 16, padding: '14px 20px', background: '#eff6ff', border: '1.5px solid #93c5fd', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 12, fontSize: 14, color: '#1e40af', fontWeight: 600 }}>
                    <PhoneCall size={18} />
                    Call {callStatus.status}: ID = <code style={{ background: '#dbeafe', padding: '2px 8px', borderRadius: 4 }}>{callStatus.id}</code>
                </div>
            )}
        </div>
    );
};

export default CaseDetail;
