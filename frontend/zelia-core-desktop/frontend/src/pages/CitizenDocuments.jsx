import React, { useState, useEffect, useRef } from 'react';
import { Camera, FileText, CheckCircle, Clock, AlertCircle, Upload, RefreshCw, ChevronLeft } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { DOC_TYPES } from '../context/DocumentStore';
import { GiantButton } from '../components/GiantButton';
import { useNavigate } from 'react-router-dom';
import { getAuthHeaders } from '../utils/api';
import GovHeader, { GovFooter } from '../components/GovHeader';

const asArray = (v) => {
    if (Array.isArray(v)) return v;
    if (typeof v === 'string') return v.split(',').map((x) => x.trim()).filter(Boolean);
    return [];
};

const uriToVaultFileUrl = (householdHash, uri) => {
    const raw = String(uri || '').trim();
    if (!raw || !householdHash) return null;

    let bucket = null;
    let key = null;
    if (raw.startsWith('minio://')) {
        const path = raw.replace('minio://', '');
        const parts = path.split('/');
        if (parts.length >= 2) {
            bucket = parts[0];
            key = parts.slice(1).join('/');
        }
    } else if (raw.includes('/')) {
        const parts = raw.split('/');
        if (parts.length >= 2) {
            bucket = parts[0];
            key = parts.slice(1).join('/');
        }
    }
    if (!bucket || !key) return null;
    const encodedKey = key.split('/').map(encodeURIComponent).join('/');
    return `http://localhost:8009/households/${encodeURIComponent(householdHash)}/files/${encodeURIComponent(bucket)}/${encodedKey}`;
};

const CitizenDocuments = () => {
    const { language } = useLanguage();
    const navigate = useNavigate();
    const [docs, setDocs] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [verifying, setVerifying] = useState(false);
    const [missingFields, setMissingFields] = useState([]);
    const [fieldValues, setFieldValues] = useState({});
    const [workflowStatus, setWorkflowStatus] = useState(null);
    const [storageTree, setStorageTree] = useState(null);
    const [statusMessage, setStatusMessage] = useState('');
    const fileInputRef = useRef(null);

    // Save hash from URL to local storage on load
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const hash = params.get('hash');
        if (hash) {
            localStorage.setItem('zelia_user_id', hash);
        }
    }, [window.location.search]);

    const getCurrentHouseholdHash = () => {
        const params = new URLSearchParams(window.location.search);
        return params.get('hash') || localStorage.getItem('zelia_user_id');
    };

    const loadWorkflowStatus = async (userId) => {
        try {
            const res = await fetch(`http://localhost:8013/households/${encodeURIComponent(userId)}/workflow-status`);
            if (res.ok) {
                const data = await res.json();
                if (data.success) {
                    setWorkflowStatus(data);
                    return;
                }
            }
            setWorkflowStatus(null);
        } catch (e) {
            console.error('Failed to load workflow status:', e);
            setWorkflowStatus(null);
        }
    };

    const loadStorageTree = async (userId) => {
        try {
            const res = await fetch(`http://localhost:8009/households/${encodeURIComponent(userId)}/storage-tree`);
            if (res.ok) {
                const data = await res.json();
                setStorageTree(data.storage || data || null);
                return;
            }
            setStorageTree(null);
        } catch (e) {
            console.error('Failed to load storage tree:', e);
            setStorageTree(null);
        }
    };

    const loadDocuments = async () => {
        const userId = getCurrentHouseholdHash();
        if (!userId) return;
        try {
            const res = await fetch(`http://localhost:8009/submissions/session/${userId}`, {
                headers: getAuthHeaders()
            });
            if (res.ok) {
                const data = await res.json();
                const fetchedDocs = data.submissions.map(sub => ({
                    id: sub.submission_id,
                    typeId: sub.metadata?.document_type || 'aadhaar',
                    status: sub.status === 'verified' ? 'verified' : (sub.status === 'rejected' ? 'rejected' : 'pending'),
                    missingFields: sub.correction_required_fields || [],
                    schemeId: sub.scheme_id || sub.metadata?.scheme_id || null,
                    fileUri: sub.filled_pdf_uri || sub.file_uri || sub.storage_path || null,
                }));
                setDocs(fetchedDocs);
            }
        } catch (e) {
            console.error('Failed to load documents:', e);
        }
        await loadWorkflowStatus(userId);
        await loadStorageTree(userId);
    };

    useEffect(() => {
        loadDocuments();
    }, []);

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        let userId = getCurrentHouseholdHash();
        if (!userId) {
            userId = 'citizen-' + Math.floor(Math.random() * 10000);
            localStorage.setItem('zelia_user_id', userId);
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('document_type', 'auto');
            formData.append('citizen_id', userId);

            const response = await fetch('http://localhost:8004/documents/upload', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });

            if (response.ok) {
                setStatusMessage('Document uploaded. OCR extraction has started.');
                await loadDocuments(); // Refresh the list
            } else {
                alert('Upload failed. Please try again.');
            }
        } catch (err) {
            console.error('Upload Error:', err);
            alert('Upload service unavailable.');
        } finally {
            setUploading(false);
        }
    };

    const handleCompleteVerification = async () => {
        let userId = getCurrentHouseholdHash();
        if (!userId) {
            alert(language === 'English' ? "No session found." : "कोई सत्र नहीं मिला।");
            return;
        }

        setVerifying(true);
        try {
            const res = await fetch('http://localhost:8013/trigger-verification', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ household_hash: userId })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                setStatusMessage(data.message || 'Verification completed. Your filled form is ready in the vault.');
                await loadDocuments();
                // Stay on the document vault page instead of redirecting
            } else if (data.status === 'incomplete' && data.missing_fields) {
                setMissingFields(data.missing_fields);
                setStatusMessage('Some required fields are still missing. Please complete them below.');
            } else {
                alert(data.message || "Error triggering verification.");
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to verification service.");
        } finally {
            setVerifying(false);
        }
    };

    const handleSubmitMissingFields = async () => {
        const userId = new URLSearchParams(window.location.search).get('hash')
                       || localStorage.getItem('zelia_user_id');
        try {
            // Save to ultravox-handler (existing endpoint)
            await fetch('http://localhost:8013/submit-missing-fields', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ household_hash: userId, corrected_fields: fieldValues })
            });

            // Trigger PDF re-fill via submission-service
            const refillRes = await fetch('http://localhost:8009/submissions/refill-with-corrections', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ household_hash: userId, corrected_fields: fieldValues })
            });
            const data = refillRes.ok ? await refillRes.json() : {};

            setFieldValues({});
            setMissingFields([]);
            setStatusMessage(data.success
                ? '✅ Corrections saved. Updated form is ready in your vault.'
                : '⏳ Corrections saved. Your form will be updated shortly.');

            await loadDocuments();
        } catch (err) {
            alert('Failed to submit corrections. Please try again.');
        }
    
    };

    const filledForms = (() => {
        const userId = getCurrentHouseholdHash();
        const fromWorkflow = asArray(workflowStatus?.filled_forms).map((f) => ({
            label: `${f.scheme_id || 'scheme'} (submission ${f.submission_id})`,
            url: uriToVaultFileUrl(userId, f.filled_pdf_uri),
        })).filter((x) => x.url);

        const fromStorage = asArray(storageTree?.filled_forms).map((f) => ({
            label: (f.object_name || f.name || 'filled_form.pdf').split('/').pop(),
            url: f.url || null,
        })).filter((x) => x.url);

        const uniq = new Map();
        [...fromWorkflow, ...fromStorage].forEach((item) => {
            if (!uniq.has(item.url)) uniq.set(item.url, item);
        });
        return Array.from(uniq.values());
    })();

    const nextSteps = (() => {
        const steps = [];
        const missingDocs = asArray(workflowStatus?.missing_required_documents);
        if (missingDocs.length > 0) {
            steps.push(`Upload required documents: ${missingDocs.join(', ')}`);
        } else {
            steps.push('Upload any pending identity/supporting documents clearly (photo or PDF).');
        }
        if (missingFields.length > 0) {
            steps.push('Fill the missing fields shown below and submit correction.');
        }
        if (filledForms.length > 0) {
            steps.push('Open filled form, verify details, then complete verification for CHW review.');
        } else {
            steps.push('After OCR + validation, the filled government form will appear in “Filled Forms Ready”.');
        }
        return steps;
    })();

    // Render large icons for the grid
    const DocIcon = ({ typeId, status, missingFields }) => {
        const typeInfo = DOC_TYPES.find(d => d.id === typeId) || DOC_TYPES.find(d => d.id === 'other');
        const IconComponent = typeInfo?.icon || FileText;

        const isRejected = status === 'rejected';

        return (
            <div style={{
                background: isRejected ? '#FFFBEB' : 'white',
                borderRadius: 24,
                padding: '24px 16px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                boxShadow: '0 8px 16px rgba(13,27,51,0.08)',
                position: 'relative',
                border: isRejected ? '2px solid #FCD34D' : '2px solid #EAF0F7'
            }}>
                <div style={{
                    width: 72, height: 72, borderRadius: 20,
                    background: isRejected ? '#FEF3C7' : '#F5F8FC', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    marginBottom: 16
                }}>
                    <IconComponent size={40} color={isRejected ? "#D97706" : "#0D1B33"} />
                </div>

                <span style={{ fontWeight: 800, color: '#0D1B33', fontSize: 16, textAlign: 'center' }}>
                    {typeInfo?.label || 'Document'}
                </span>

                {isRejected && (
                    <span style={{ fontSize: 12, color: '#D97706', fontWeight: 700, marginTop: 8, textAlign: 'center' }}>
                        Needs update
                    </span>
                )}

                {/* Status Badge */}
                <div style={{ position: 'absolute', top: -10, right: -10 }}>
                    {status === 'verified' ? (
                        <CheckCircle size={32} color="#1A5C3A" fill="white" />
                    ) : isRejected ? (
                        <AlertCircle size={32} color="#D97706" fill="white" />
                    ) : (
                        <Clock size={32} color="#7A97BA" fill="white" />
                    )}
                </div>
            </div>
        );
    };


    // WebSocket for real-time vault refresh when workflow completes
    useEffect(() => {
        const userId = new URLSearchParams(window.location.search).get('hash')
                       || localStorage.getItem('zelia_user_id');
        if (!userId) return;
        let ws;
        try {
            ws = new WebSocket('ws://localhost:8013/ws/calls');
            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.event === 'workflow_complete' &&
                        msg.payload?.household_hash === userId) {
                        setStatusMessage('✅ Your filled government form is ready!');
                        loadDocuments();
                    }
                } catch {}
            };
            ws.onerror = () => {};
        } catch {}
        return () => { if (ws) ws.close(); };
    }, []);

    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#EEF2F7', fontFamily: "'Noto Sans','Noto Sans Devanagari',sans-serif" }}>
            <GovHeader backHref="/citizen" backLabel={language === 'Hindi' ? 'पोर्टल पर वापस' : 'Back to Portal'} />

            <main id="main-content" style={{ flex: 1, maxWidth: 780, width: '100%', margin: '0 auto', padding: '24px 16px 48px' }}>

                {/* Breadcrumb */}
                <div style={{ fontSize: 12, color: '#555', marginBottom: 16 }}>
                    <a href="/" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>Home</a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <a href="/citizen" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>Dashboard</a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <span style={{ fontWeight: 700, color: '#333' }}>
                        {language === 'Hindi' ? 'दस्तावेज़ वॉल्ट' : 'Document Vault'}
                    </span>
                </div>

                {/* Page heading */}
                <div style={{ marginBottom: 20 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 900, color: '#1B3D6E', margin: '0 0 4px' }}>
                        {language === 'Hindi' ? 'मेरा दस्तावेज़ वॉल्ट' : 'My Document Vault'}
                    </h1>
                    <p style={{ color: '#555', fontSize: 13, margin: 0 }}>
                        {language === 'Hindi'
                            ? 'यहाँ अपने दस्तावेज़ अपलोड और प्रबंधित करें। फ़ोटो या PDF स्वीकार किए जाते हैं।'
                            : 'Upload and manage your documents here. Photos or PDFs are accepted for OCR processing.'}
                    </p>
                </div>

                {/* Status notification banner */}
                {statusMessage && (
                    <div style={{ marginBottom: 16, background: '#E8F5E9', border: '1px solid #A5D6A7', borderLeft: '4px solid #138808', borderRadius: 4, padding: '12px 16px', fontSize: 13, color: '#1B5E20', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                        ✅ {statusMessage}
                    </div>
                )}

                {/* Case Processing Status card */}
                <div style={{ marginBottom: 20, background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ background: '#1B3D6E', padding: '10px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                            CASE PROCESSING STATUS / केस प्रोसेसिंग स्थिति
                        </span>
                        <button onClick={loadDocuments} style={{ background: 'rgba(255,255,255,.15)', border: '1px solid rgba(255,255,255,.3)', borderRadius: 3, padding: '4px 10px', color: 'white', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 5, fontFamily: 'inherit' }}>
                            <RefreshCw size={11} /> Refresh
                        </button>
                    </div>
                    <div style={{ padding: '14px 16px' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                            <tbody>
                                {[
                                    ['Status', 'स्थिति', workflowStatus?.status || 'Awaiting workflow status'],
                                    ['Matched Scheme', 'मिलान योजना', workflowStatus?.best_match_scheme?.scheme_name || workflowStatus?.best_match_scheme?.scheme_id || 'Not yet matched'],
                                    ['Required Documents', 'आवश्यक दस्तावेज़', asArray(workflowStatus?.required_documents).join(', ') || 'Not specified'],
                                    ['Missing Documents', 'लापता दस्तावेज़', asArray(workflowStatus?.missing_required_documents).join(', ') || 'None flagged'],
                                    ['Next Action', 'अगली कार्रवाई', workflowStatus?.next_action || 'Upload missing documents'],
                                ].map(([en, hi, val], i) => (
                                    <tr key={en} style={{ background: i % 2 === 0 ? 'white' : '#FAFBFD' }}>
                                        <td style={{ padding: '8px 12px', fontWeight: 700, color: '#333', width: '35%', borderBottom: '1px solid #EEF2F7', verticalAlign: 'top' }}>
                                            {language === 'Hindi' ? hi : en}
                                        </td>
                                        <td style={{ padding: '8px 12px', color: '#555', borderBottom: '1px solid #EEF2F7' }}>{val}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {workflowStatus?.response_text && (
                            <div style={{ marginTop: 10, padding: '8px 12px', background: '#F0F4FA', borderRadius: 3, fontSize: 12, color: '#444', borderLeft: '3px solid #1B3D6E' }}>
                                <strong>System:</strong> {workflowStatus.response_text}
                            </div>
                        )}
                    </div>
                </div>

                {/* What to do next */}
                <div style={{ marginBottom: 20, background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                    <div style={{ background: '#FF9933', padding: '10px 16px' }}>
                        <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                            WHAT TO DO NEXT / आगे क्या करें
                        </span>
                    </div>
                    <div style={{ padding: '14px 16px' }}>
                        <ol style={{ margin: 0, paddingLeft: 20 }}>
                            {nextSteps.map((step, idx) => (
                                <li key={idx} style={{ fontSize: 13, color: '#444', lineHeight: 1.7, fontWeight: idx === 0 ? 700 : 500, marginBottom: 4 }}>{step}</li>
                            ))}
                        </ol>
                    </div>
                </div>

                {/* Filled Forms Ready */}
                {filledForms.length > 0 && (
                    <div style={{ marginBottom: 20, background: 'white', border: '1px solid #A5D6A7', borderLeft: '4px solid #138808', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ background: '#E8F5E9', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <CheckCircle size={14} color="#1B5E20" />
                            <span style={{ color: '#1B5E20', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                                FILLED FORMS READY / भरे हुए फॉर्म तैयार
                            </span>
                        </div>
                        <div style={{ padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {filledForms.map((f) => (
                                <div key={f.url} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '10px 14px', border: '1px solid #C8E6C9', borderRadius: 3, background: 'white' }}>
                                    <div style={{ fontSize: 13, color: '#1B5E20', fontWeight: 600, wordBreak: 'break-word', display: 'flex', alignItems: 'center', gap: 8 }}>
                                        <FileText size={14} color="#138808" /> {f.label}
                                    </div>
                                    <a href={f.url} target="_blank" rel="noreferrer"
                                        style={{ whiteSpace: 'nowrap', fontSize: 12, fontWeight: 800, color: 'white', background: '#1B3D6E', padding: '6px 14px', borderRadius: 3, textDecoration: 'none' }}>
                                        Open PDF ↗
                                    </a>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
                    <input type="file" ref={fileInputRef} onChange={handleUpload} accept="image/*,.pdf" capture="environment" style={{ display: 'none' }} />
                    <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
                        style={{ flex: 1, minWidth: 160, padding: '13px 16px', borderRadius: 3, border: 'none', background: '#1B3D6E', color: 'white', fontSize: 14, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontFamily: 'inherit', opacity: uploading ? 0.7 : 1 }}>
                        <Upload size={16} /> {uploading ? (language === 'Hindi' ? 'अपलोड हो रहा है…' : 'Uploading…') : (language === 'Hindi' ? 'दस्तावेज़ जोड़ें' : 'Add Document')}
                    </button>
                    {docs.length > 0 && missingFields.length === 0 && (
                        <button onClick={handleCompleteVerification} disabled={verifying}
                            style={{ flex: 1, minWidth: 160, padding: '13px 16px', borderRadius: 3, border: 'none', background: '#138808', color: 'white', fontSize: 14, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontFamily: 'inherit', opacity: verifying ? 0.7 : 1 }}>
                            <CheckCircle size={16} /> {verifying ? 'Processing…' : (language === 'Hindi' ? 'सत्यापन पूरा करें' : 'Complete Verification')}
                        </button>
                    )}
                </div>

                {/* Documents grid */}
                <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden', marginBottom: 20 }}>
                    <div style={{ background: '#F0F4FA', padding: '10px 16px', borderBottom: '2px solid #D8E0EA', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 800, color: '#1B3D6E', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                            {language === 'Hindi' ? 'अपलोड किए गए दस्तावेज़' : 'Uploaded Documents'}
                        </span>
                        <span style={{ fontSize: 12, color: '#777', fontWeight: 600 }}>{docs.length} file{docs.length !== 1 ? 's' : ''}</span>
                    </div>

                    {docs.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                            <FileText size={48} color="#CCC" style={{ marginBottom: 10 }} />
                            <div style={{ fontSize: 15, fontWeight: 800, color: '#555', marginBottom: 4 }}>
                                {language === 'Hindi' ? 'वॉल्ट खाली है' : 'Vault is Empty'}
                            </div>
                            <div style={{ fontSize: 13, color: '#888' }}>
                                {language === 'Hindi'
                                    ? 'आधार, PAN, राशन कार्ड, जन्म प्रमाण पत्र अपलोड करें'
                                    : 'Upload Aadhaar, PAN, Ration Card, Birth Certificate, Income Certificate'}
                            </div>
                        </div>
                    ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 1, background: '#E8EEF5' }}>
                            {docs.map(doc => (
                                <div key={doc.id} style={{ background: doc.status === 'rejected' ? '#FFFBEB' : 'white', padding: '16px 12px' }}>
                                    <DocIcon typeId={doc.typeId} status={doc.status} missingFields={doc.missingFields} />
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Missing fields form */}
                {missingFields.length > 0 && (
                    <div style={{ background: 'white', border: '1px solid #FFB74D', borderLeft: '4px solid #FF9800', borderRadius: 4, overflow: 'hidden', marginBottom: 20 }}>
                        <div style={{ background: '#FFF3E0', padding: '10px 16px', borderBottom: '1px solid #FFE0B2', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <AlertCircle size={14} color="#E65100" />
                            <span style={{ color: '#E65100', fontWeight: 800, fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.4 }}>
                                Missing Information — Action Required
                            </span>
                        </div>
                        <div style={{ padding: '16px' }}>
                            <p style={{ fontSize: 13, color: '#555', marginBottom: 16, borderLeft: '3px solid #FF9800', paddingLeft: 10, lineHeight: 1.6 }}>
                                {language === 'Hindi'
                                    ? 'आपके दस्तावेज़ों से सभी आवश्यक विवरण निकाले नहीं जा सके। कृपया नीचे दिए गए फ़ील्ड भरें:'
                                    : 'We could not extract all required details from your documents. Please provide the following information:'}
                            </p>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 14, marginBottom: 16 }}>
                                {missingFields.map(field => (
                                    <div key={field}>
                                        <label style={{ display: 'block', fontSize: 12, fontWeight: 800, color: '#333', marginBottom: 5, textTransform: 'capitalize' }}>
                                            {field.replace(/_/g, ' ')} <span style={{ color: '#C62828' }}>*</span>
                                        </label>
                                        <input type="text"
                                            value={fieldValues[field] || ''}
                                            onChange={(e) => setFieldValues({ ...fieldValues, [field]: e.target.value })}
                                            style={{ width: '100%', padding: '10px 12px', borderRadius: 3, border: '1.5px solid #CCC', fontSize: 14, boxSizing: 'border-box', outline: 'none', fontFamily: 'inherit' }}
                                            onFocus={e => e.target.style.borderColor = '#1B3D6E'}
                                            onBlur={e => e.target.style.borderColor = '#CCC'} />
                                    </div>
                                ))}
                            </div>
                            <button onClick={handleSubmitMissingFields}
                                style={{ padding: '12px 24px', borderRadius: 3, border: 'none', background: '#1B3D6E', color: 'white', fontSize: 14, fontWeight: 800, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'inherit' }}>
                                <CheckCircle size={15} />
                                {language === 'Hindi' ? 'विवरण सबमिट करें और PDF पुनः भरें' : 'Submit Details & Re-fill PDF'}
                            </button>
                        </div>
                    </div>
                )}

                {/* Bottom nav */}
                <div style={{ display: 'flex', gap: 10 }}>
                    <button onClick={loadDocuments}
                        style={{ flex: 1, padding: '11px', borderRadius: 3, border: '1.5px solid #1B3D6E', background: 'white', color: '#1B3D6E', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                        <RefreshCw size={13} /> {language === 'Hindi' ? 'वॉल्ट ताज़ा करें' : 'Refresh Vault'}
                    </button>
                    <button onClick={() => navigate('/citizen')}
                        style={{ flex: 1, padding: '11px', borderRadius: 3, border: '1.5px solid #CCC', background: '#F0F4FA', color: '#333', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                        <ChevronLeft size={13} /> {language === 'Hindi' ? 'पोर्टल पर वापस' : 'Back to Portal'}
                    </button>
                </div>
            </main>

            <GovFooter />
        </div>
    );
};

export default CitizenDocuments;
